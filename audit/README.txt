# Temporary RAM audit integration

## 1. Add this import near the other imports in `main.py`

```python
from audit.resource_audit import AUDIT_ENABLED, run_resource_audit
```

## 2. Add this temporary block inside `init_system()`

Put it after `start_group_worker()` and before `setup_log_ttl()`:

```python
    if AUDIT_ENABLED:
        run_resource_audit()
```

## 3. Create an empty `audit/__init__.py`

The folder should be:

```text
audit/
├── __init__.py
└── resource_audit.py
```

## 4. Render environment variable

Temporarily set:

```text
RESOURCE_AUDIT=1
```

Then deploy/restart once.

The audit will print its report in the Render logs and then automatically stop `tracemalloc`.

## 5. IMPORTANT

After collecting the report, set:

```text
RESOURCE_AUDIT=0
```

and redeploy/restart.

Then the audit is completely inactive.

The audit does not send anything to Telegram, MongoDB, or Discord.
