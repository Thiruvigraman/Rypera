"""
Temporary resource/RAM audit.

This module is intentionally isolated from the bot's core logic.
It performs read-only measurements and prints a report to Render logs.

Enable with:
    RESOURCE_AUDIT=1

Disable with:
    RESOURCE_AUDIT=0

The audit automatically runs once per Python process when enabled.
It does NOT write to MongoDB, Discord, Telegram, or the delivery queue.
"""

import gc
import os
import sys
import threading
import time
import tracemalloc
from collections import Counter

AUDIT_ENABLED = os.getenv("RESOURCE_AUDIT", "0").strip().lower() in {
    "1", "true", "yes", "on"
}

AUDIT_TOP_ALLOCATIONS = 20


def _rss_mb():
    """Return current process RSS in MB using psutil if available."""
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
    except Exception:
        return None


def _thread_snapshot():
    threads = threading.enumerate()
    return {
        "count": len(threads),
        "alive": sum(1 for t in threads if t.is_alive()),
        "names": [t.name for t in threads if t.is_alive()],
    }


def _queue_snapshot():
    try:
        from database.group_queue import GROUP_SEND_QUEUE
        queue_size = GROUP_SEND_QUEUE.qsize()
        return queue_size
    except Exception:
        return None


def _important_structures():
    result = {}

    try:
        import bot

        recent = getattr(bot, "RECENT_SENDS", None)
        users = getattr(bot, "USER_LAST_REQUEST", None)

        if recent is not None:
            result["RECENT_SENDS_entries"] = len(recent)

        if users is not None:
            result["USER_LAST_REQUEST_entries"] = len(users)

    except Exception as exc:
        result["bot_structures_error"] = str(exc)

    return result


def _group_worker_snapshot():
    result = {}

    try:
        import database.group_queue as gq

        threads = getattr(gq, "GROUP_WORKER_THREADS", None)

        if threads is not None:
            result["tracked_worker_threads"] = len(threads)
            result["live_tracked_workers"] = sum(
                1 for t in threads if t.is_alive()
            )

        result["worker_count_setting"] = getattr(
            gq, "WORKER_COUNT", None
        )

        result["queue_max_files"] = getattr(
            gq, "MAX_GROUP_FILES", None
        )

    except Exception as exc:
        result["group_worker_error"] = str(exc)

    return result


def _top_allocations(snapshot):
    stats = snapshot.statistics("lineno")
    rows = []

    for stat in stats[:AUDIT_TOP_ALLOCATIONS]:
        frame = stat.traceback[0]
        rows.append({
            "file": frame.filename,
            "line": frame.lineno,
            "size_mb": stat.size / 1024 / 1024,
            "count": stat.count,
        })

    return rows


def _module_memory(snapshot):
    stats = snapshot.statistics("filename")
    rows = []

    for stat in stats[:15]:
        rows.append({
            "file": stat.traceback[0].filename,
            "size_mb": stat.size / 1024 / 1024,
            "count": stat.count,
        })

    return rows


def run_resource_audit():
    """
    Run one isolated audit and print a complete report.

    Returns a dictionary for possible future use, but does not modify
    application state apart from temporarily starting tracemalloc.
    """
    if not AUDIT_ENABLED:
        return None

    started = time.time()

    print("")
    print("=" * 72)
    print("RESOURCE / RAM AUDIT - TEMPORARY")
    print("=" * 72)
    print("PID:", os.getpid())
    print("Python:", sys.version.split()[0])
    print("Platform:", sys.platform)
    print("Audit started:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print("")

    before_gc = gc.get_count()
    before_rss = _rss_mb()
    before_threads = _thread_snapshot()
    before_queue = _queue_snapshot()
    before_structures = _important_structures()
    before_workers = _group_worker_snapshot()

    print("[BASELINE]")
    print("RSS MB:", before_rss)
    print("Threads:", before_threads)
    print("Group queue size:", before_queue)
    print("In-memory structures:", before_structures)
    print("Group worker:", before_workers)
    print("GC counts:", before_gc)
    print("")

    tracemalloc.start(10)

    # Give the allocator a moment to settle after starting tracemalloc.
    time.sleep(0.2)

    snapshot = tracemalloc.take_snapshot()
    current, peak = tracemalloc.get_traced_memory()

    after_rss = _rss_mb()
    after_threads = _thread_snapshot()
    after_queue = _queue_snapshot()
    after_structures = _important_structures()
    after_workers = _group_worker_snapshot()

    print("[AFTER TRACEMALLOC START]")
    print("RSS MB:", after_rss)
    print(
        "Traced Python memory current MB:",
        round(current / 1024 / 1024, 3)
    )
    print(
        "Traced Python memory peak MB:",
        round(peak / 1024 / 1024, 3)
    )
    print("Threads:", after_threads)
    print("Group queue size:", after_queue)
    print("In-memory structures:", after_structures)
    print("Group worker:", after_workers)
    print("")

    print("[TOP PYTHON ALLOCATIONS BY LINE]")
    for row in _top_allocations(snapshot):
        print(
            f"{row['size_mb']:.3f} MB | "
            f"{row['count']} allocations | "
            f"{row['file']}:{row['line']}"
        )
    print("")

    print("[TOP PYTHON ALLOCATIONS BY FILE]")
    for row in _module_memory(snapshot):
        print(
            f"{row['size_mb']:.3f} MB | "
            f"{row['count']} allocations | "
            f"{row['file']}"
        )
    print("")

    # A GC collection is read-only from the application's point of view
    # for this audit and helps show whether reclaimable Python objects exist.
    collected = gc.collect()

    post_gc_rss = _rss_mb()
    post_gc_current, post_gc_peak = tracemalloc.get_traced_memory()
    post_gc = gc.get_count()

    print("[AFTER GC]")
    print("Objects collected:", collected)
    print("RSS MB:", post_gc_rss)
    print(
        "Traced current MB:",
        round(post_gc_current / 1024 / 1024, 3)
    )
    print(
        "Traced peak MB:",
        round(post_gc_peak / 1024 / 1024, 3)
    )
    print("GC counts:", post_gc)
    print("")

    # Stop tracing so it does not remain as a production overhead.
    tracemalloc.stop()

    final_rss = _rss_mb()
    final_threads = _thread_snapshot()
    final_queue = _queue_snapshot()

    print("[FINAL]")
    print("RSS MB:", final_rss)
    print("Threads:", final_threads)
    print("Group queue size:", final_queue)
    print("RSS change from baseline MB:",
          None if before_rss is None or final_rss is None
          else round(final_rss - before_rss, 3))
    print("Audit duration seconds:", round(time.time() - started, 3))
    print("")
    print("=" * 72)
    print("RESOURCE / RAM AUDIT COMPLETE")
    print("=" * 72)
    print("")

    return {
        "baseline_rss_mb": before_rss,
        "final_rss_mb": final_rss,
        "baseline_threads": before_threads,
        "final_threads": final_threads,
        "baseline_queue": before_queue,
        "final_queue": final_queue,
        "baseline_structures": before_structures,
        "final_structures": after_structures,
        "baseline_workers": before_workers,
        "final_workers": after_workers,
        "traced_current_mb": post_gc_current / 1024 / 1024,
        "traced_peak_mb": post_gc_peak / 1024 / 1024,
        "gc_collected": collected,
        "duration_seconds": time.time() - started,
    }
