# file: commands/resource_audit.py

from audit.resource_audit import run_resource_audit


def handle_resource_audit(chat_id):
    """
    Run the temporary resource/RAM audit from the admin command system.

    The audit itself is read-only and prints the detailed report to
    Render logs. No MongoDB, Telegram delivery, Discord, or queue state
    is modified by the audit.
    """
    try:
        report = run_resource_audit()

        if report is None:
            return False

        from bot import send_message

        final_rss = report.get("final_rss_mb")
        baseline_rss = report.get("baseline_rss_mb")
        queue_size = report.get("final_queue")
        threads = report.get("final_threads", {}).get("count")

        def fmt(value):
            if value is None:
                return "N/A"
            return f"{value:.2f} MB"

        send_message(
            chat_id,
            (
                "✅ RAM AUDIT COMPLETE\n\n"
                f"🧠 Baseline RSS: {fmt(baseline_rss)}\n"
                f"🧠 Final RSS: {fmt(final_rss)}\n"
                f"📦 Queue size: {queue_size}\n"
                f"🧵 Threads: {threads}\n\n"
                "📋 Full allocation details are in Render logs."
            ),
            skip_rate_limit=True
        )

        return True

    except Exception as e:
        from bot import send_message

        send_message(
            chat_id,
            f"❌ RAM audit failed: {str(e)}",
            skip_rate_limit=True
        )

        print("RESOURCE AUDIT COMMAND ERROR:", str(e))
        return True
