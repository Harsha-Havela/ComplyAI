"""
Notification Triggers — NEW isolated module.

This file wires together:
  - firebase_notification_service  (existing in-app notifications)
  - email_sender                   (new SMTP module)

It does NOT modify either of those files.

Call these functions from routes/controllers after a state change.
All functions are safe to call — they swallow their own exceptions
so a notification failure never rolls back the real business operation.
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────────────────────────

def _get_user_email(user_id: str):
    """Return (email, full_name) for a user, or (None, None) on failure."""
    try:
        from app.models.firebase_database import Collections, get_document
        user = get_document(Collections.USERS, user_id)
        if user:
            return user.get('email'), user.get('full_name', user.get('username', ''))
    except Exception as exc:
        logger.warning("Could not fetch user %s for email: %s", user_id, exc)
    return None, None


def _already_notified(key: str) -> bool:
    """
    Idempotency guard — stores a dedupe key in Firestore 'notification_keys'
    collection.  Returns True if key already exists (already sent).
    """
    try:
        from app.models.firebase_database import get_document, create_document
        existing = get_document('notification_keys', key)
        if existing:
            return True
        create_document('notification_keys', {'created_at': datetime.now()}, doc_id=key)
        return False
    except Exception as exc:
        # If the guard fails, allow the notification through (don't block)
        logger.warning("Idempotency check failed for key %s: %s", key, exc)
        return False


# ─────────────────────────────────────────────────────────────────
#  Public trigger functions
# ─────────────────────────────────────────────────────────────────

def trigger_task_assigned(task_id: str, task_title: str, assigned_to_id: str,
                           client_name: str, due_date: str, created_by_id: str):
    """
    Fire in-app notification + email when a task is assigned.
    Call this after create_task() succeeds.
    """
    try:
        # 1. In-app notification (existing service)
        from app.services.firebase_notification_service import notify_task_assignment
        notify_task_assignment(assigned_to_id, task_id, task_title, client_name)

        # 2. Email (new module) — only if assignee != creator (avoid self-spam)
        if str(assigned_to_id) != str(created_by_id):
            email, name = _get_user_email(assigned_to_id)
            if email:
                from app.services.email_sender import send_task_assignment_email
                send_task_assignment_email(
                    to_email=email,
                    employee_name=name,
                    task_title=task_title,
                    client_name=client_name,
                    due_date=due_date or 'Not set',
                    task_id=task_id
                )

    except Exception as exc:
        logger.error("trigger_task_assigned failed for task %s: %s", task_id, exc)


def trigger_task_status_changed(task_id: str, task_title: str,
                                  old_status: str, new_status: str,
                                  assigned_to_id: str, created_by_id: str,
                                  changed_by_id: str):
    """
    Fire in-app notifications when task status changes.
    Call this after update_task_status() succeeds.
    """
    try:
        from app.services.firebase_notification_service import (
            notify_task_status_change, notify_task_completed
        )
        from app.models.firebase_database import Collections, get_document

        # Notify the assigned employee
        if str(assigned_to_id) != str(changed_by_id):
            notify_task_status_change(
                assigned_to_id, task_id, task_title, old_status, new_status
            )

        # Notify the creator if someone else completed the task
        if new_status == 'completed' and str(created_by_id) != str(changed_by_id):
            changer = get_document(Collections.USERS, changed_by_id)
            changer_name = changer.get('full_name', 'Someone') if changer else 'Someone'
            notify_task_completed(created_by_id, task_id, task_title, changer_name)

    except Exception as exc:
        logger.error("trigger_task_status_changed failed for task %s: %s", task_id, exc)


def trigger_task_comment(task_id: str, task_title: str,
                          commenter_id: str, notify_user_id: str):
    """
    Notify task owner/assignee of a new comment.
    Call this after add_task_comment() succeeds.
    """
    try:
        if str(commenter_id) == str(notify_user_id):
            return  # don't notify people of their own comment

        from app.services.firebase_notification_service import notify_task_comment
        from app.models.firebase_database import Collections, get_document

        commenter = get_document(Collections.USERS, commenter_id)
        commenter_name = commenter.get('full_name', 'Someone') if commenter else 'Someone'
        notify_task_comment(notify_user_id, task_id, task_title,
                            commenter_name, "New comment added")

    except Exception as exc:
        logger.error("trigger_task_comment failed for task %s: %s", task_id, exc)


def trigger_compliance_deadline_approaching(compliance_id: str, compliance_type: str,
                                             client_name: str, due_date: str,
                                             days_remaining: int, notify_user_ids: list):
    """
    Fire in-app + email reminders for approaching compliance deadline.
    Called by the scheduler (new scheduler.py).
    Uses idempotency key: one notification per compliance per day.
    """
    today = datetime.now().strftime('%Y-%m-%d')
    idem_key = f"deadline_{compliance_id}_{today}_{days_remaining}d"

    if _already_notified(idem_key):
        logger.debug("Skipping duplicate deadline notification: %s", idem_key)
        return

    try:
        from app.services.firebase_notification_service import notify_deadline_approaching
        from app.services.email_sender import send_compliance_deadline_email

        for user_id in notify_user_ids:
            # In-app
            notify_deadline_approaching(user_id, compliance_id, compliance_type,
                                        client_name, days_remaining)
            # Email
            email, name = _get_user_email(user_id)
            if email:
                send_compliance_deadline_email(
                    to_email=email,
                    recipient_name=name,
                    compliance_type=compliance_type,
                    client_name=client_name,
                    due_date=due_date,
                    days_remaining=days_remaining,
                    compliance_id=compliance_id
                )

    except Exception as exc:
        logger.error("trigger_compliance_deadline_approaching failed for %s: %s",
                     compliance_id, exc)


def trigger_compliance_overdue(compliance_id: str, compliance_type: str,
                                client_name: str, due_date: str,
                                notify_user_ids: list):
    """
    Fire in-app + email alerts when a compliance item becomes overdue.
    Called by the scheduler.
    Uses idempotency key: one alert per compliance item (not repeated daily).
    """
    idem_key = f"overdue_{compliance_id}"

    if _already_notified(idem_key):
        logger.debug("Skipping duplicate overdue notification: %s", idem_key)
        return

    try:
        from app.services.firebase_notification_service import notify_compliance_overdue
        from app.services.email_sender import send_overdue_compliance_email

        for user_id in notify_user_ids:
            # In-app
            notify_compliance_overdue(user_id, compliance_id, compliance_type, client_name)
            # Email
            email, name = _get_user_email(user_id)
            if email:
                send_overdue_compliance_email(
                    to_email=email,
                    recipient_name=name,
                    compliance_type=compliance_type,
                    client_name=client_name,
                    due_date=due_date,
                    compliance_id=compliance_id
                )

    except Exception as exc:
        logger.error("trigger_compliance_overdue failed for %s: %s",
                     compliance_id, exc)
