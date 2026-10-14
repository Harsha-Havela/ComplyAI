"""
Compliance Scheduler — NEW isolated module.

Uses APScheduler to run background jobs automatically.
Calls existing functions:
  - mark_overdue_compliance()          from firebase_compliance_controller
  - auto_generate_recurring_compliance() from firebase_compliance_controller
  - trigger_compliance_deadline_approaching() from notification_triggers
  - trigger_compliance_overdue()            from notification_triggers

Startup: called once from app/__init__.py  (minimal 2-line addition).
Can also be run as a standalone process:
    python -m app.scheduler

NEVER creates duplicate schedulers:
  - Checks WERKZEUG_RUN_MAIN to skip the Flask reloader parent process
  - Guards against double-init with a module-level flag
"""
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_scheduler = None          # module-level singleton
_initialized = False       # guard against double-init


# ─────────────────────────────────────────────────────────────────
#  Job implementations
# ─────────────────────────────────────────────────────────────────

def _job_mark_overdue():
    """Mark eligible pending compliance items as overdue and fire notifications."""
    logger.info("[Scheduler] Running mark_overdue job")
    try:
        from app.controllers.firebase_compliance_controller import mark_overdue_compliance
        count = mark_overdue_compliance()
        logger.info("[Scheduler] Marked %d compliance items as overdue", count)

        # Fire notifications for newly-overdue items
        _fire_overdue_notifications()

    except Exception as exc:
        logger.error("[Scheduler] mark_overdue job failed: %s", exc)


def _job_generate_recurring():
    """Generate next-cycle compliance records from completed recurring items."""
    logger.info("[Scheduler] Running generate_recurring job")
    try:
        from app.controllers.firebase_compliance_controller import auto_generate_recurring_compliance
        result = auto_generate_recurring_compliance()
        total = sum(v for v in result.values() if isinstance(v, int))
        logger.info("[Scheduler] Generated %d recurring compliance records: %s", total, result)
    except Exception as exc:
        logger.error("[Scheduler] generate_recurring job failed: %s", exc)


def _job_deadline_reminders():
    """Send deadline-approaching notifications (7-day and 2-day windows)."""
    logger.info("[Scheduler] Running deadline_reminders job")
    try:
        _fire_upcoming_notifications(days_window=7)
        _fire_upcoming_notifications(days_window=2)
    except Exception as exc:
        logger.error("[Scheduler] deadline_reminders job failed: %s", exc)


# ─────────────────────────────────────────────────────────────────
#  Notification helpers (called by jobs above)
# ─────────────────────────────────────────────────────────────────

def _get_admin_and_manager_ids():
    """Return list of admin + manager user IDs to notify."""
    try:
        from app.models.firebase_database import Collections, query_documents
        users = query_documents(Collections.USERS,
                                filters=[('is_active', '==', True)])
        return [u['id'] for u in users
                if u.get('role') in ('admin', 'manager')]
    except Exception as exc:
        logger.warning("Could not fetch admin/manager IDs: %s", exc)
        return []


def _fire_upcoming_notifications(days_window: int):
    """Notify admins/managers of compliance due within days_window days."""
    try:
        from app.controllers.firebase_compliance_controller import get_upcoming_compliance
        from app.services.notification_triggers import trigger_compliance_deadline_approaching

        # Get items due within the window that aren't already notified today
        items = get_upcoming_compliance(days_ahead=days_window)
        if not items:
            return

        notify_ids = _get_admin_and_manager_ids()
        if not notify_ids:
            return

        today_str = datetime.now().strftime('%Y-%m-%d')

        for item in items:
            try:
                due_date = item.get('due_date', '')
                if not due_date:
                    continue

                days_remaining = (
                    datetime.strptime(due_date, '%Y-%m-%d').date()
                    - datetime.now().date()
                ).days

                if days_remaining < 0:
                    continue  # already overdue — handled elsewhere

                trigger_compliance_deadline_approaching(
                    compliance_id=item['id'],
                    compliance_type=item.get('compliance_type', ''),
                    client_name=item.get('client_name', 'General'),
                    due_date=due_date,
                    days_remaining=days_remaining,
                    notify_user_ids=notify_ids
                )
            except Exception as item_exc:
                # One bad record must not stop the rest
                logger.error("Error processing compliance %s for deadline notification: %s",
                             item.get('id'), item_exc)

    except Exception as exc:
        logger.error("_fire_upcoming_notifications(%d) failed: %s", days_window, exc)


def _fire_overdue_notifications():
    """Notify admins/managers of overdue compliance items."""
    try:
        from app.controllers.firebase_compliance_controller import get_overdue_compliance
        from app.services.notification_triggers import trigger_compliance_overdue

        items = get_overdue_compliance()
        if not items:
            return

        notify_ids = _get_admin_and_manager_ids()
        if not notify_ids:
            return

        for item in items:
            try:
                trigger_compliance_overdue(
                    compliance_id=item['id'],
                    compliance_type=item.get('compliance_type', ''),
                    client_name=item.get('client_name', 'General'),
                    due_date=item.get('due_date', ''),
                    notify_user_ids=notify_ids
                )
            except Exception as item_exc:
                logger.error("Error processing compliance %s for overdue notification: %s",
                             item.get('id'), item_exc)

    except Exception as exc:
        logger.error("_fire_overdue_notifications failed: %s", exc)


# ─────────────────────────────────────────────────────────────────
#  Scheduler lifecycle
# ─────────────────────────────────────────────────────────────────

def start_scheduler(app=None):
    """
    Start APScheduler background jobs.
    Safe to call multiple times — only starts once.
    Skips in Flask debug reloader parent process.

    Args:
        app: Flask app instance (optional, for app context in jobs)
    """
    global _scheduler, _initialized

    # Skip if already running
    if _initialized:
        return

    # Skip if scheduler is disabled via env
    if os.environ.get('SCHEDULER_ENABLED', 'true').lower() == 'false':
        logger.info("[Scheduler] Disabled via SCHEDULER_ENABLED=false")
        return

    # In Flask debug mode, Werkzeug spawns a parent + child process.
    # We only want the scheduler in the child (reloader) process.
    if os.environ.get('FLASK_DEBUG', '').lower() in ('1', 'true') or \
       os.environ.get('FLASK_ENV', '') == 'development':
        if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
            logger.debug("[Scheduler] Skipping in Flask reloader parent process")
            return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.executors.pool import ThreadPoolExecutor

        executors = {'default': ThreadPoolExecutor(max_workers=2)}
        job_defaults = {'coalesce': True, 'max_instances': 1, 'misfire_grace_time': 600}

        scheduler = BackgroundScheduler(executors=executors, job_defaults=job_defaults)

        # Wrap jobs to run inside Flask app context (needed for Firestore)
        def make_job(fn):
            if app is not None:
                def wrapper():
                    with app.app_context():
                        fn()
                return wrapper
            return fn

        # Daily at 01:00 — mark overdue + fire overdue notifications
        scheduler.add_job(
            make_job(_job_mark_overdue),
            'cron', hour=1, minute=0,
            id='mark_overdue', replace_existing=True
        )

        # Daily at 01:30 — generate next recurring deadlines
        scheduler.add_job(
            make_job(_job_generate_recurring),
            'cron', hour=1, minute=30,
            id='generate_recurring', replace_existing=True
        )

        # Daily at 08:00 — send upcoming deadline reminders
        scheduler.add_job(
            make_job(_job_deadline_reminders),
            'cron', hour=8, minute=0,
            id='deadline_reminders', replace_existing=True
        )

        scheduler.start()
        _scheduler = scheduler
        _initialized = True

        logger.info("[Scheduler] Started — jobs: mark_overdue@01:00, "
                    "generate_recurring@01:30, deadline_reminders@08:00")

    except ImportError:
        logger.warning(
            "[Scheduler] APScheduler not installed — background jobs disabled. "
            "Run: pip install apscheduler"
        )
    except Exception as exc:
        logger.error("[Scheduler] Failed to start: %s", exc)


def stop_scheduler():
    """Gracefully shut down the scheduler (call on app teardown)."""
    global _scheduler, _initialized
    if _scheduler and _initialized:
        try:
            _scheduler.shutdown(wait=False)
            logger.info("[Scheduler] Stopped")
        except Exception as exc:
            logger.error("[Scheduler] Error during shutdown: %s", exc)
        finally:
            _scheduler = None
            _initialized = False


# ─────────────────────────────────────────────────────────────────
#  Standalone entry point  (python -m app.scheduler)
# ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import time
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )

    # Force scheduler to start (no Werkzeug guard in standalone mode)
    os.environ['WERKZEUG_RUN_MAIN'] = 'true'

    from dotenv import load_dotenv
    load_dotenv()

    # Import app to get Firebase context
    from app import create_app
    flask_app = create_app()

    start_scheduler(app=flask_app)

    print("\n✅ ComplyAI Scheduler running. Press Ctrl+C to stop.\n")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        stop_scheduler()
        print("\nScheduler stopped.")
