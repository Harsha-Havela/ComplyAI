"""
Notification Service
Manages in-app notifications
"""
from app.models.database import execute_db, query_db


def create_notification(user_id, title, message, notification_type='info', link=None):
    """Create a new notification for a user."""
    query = """
        INSERT INTO notifications (user_id, title, message, type, link)
        VALUES (?, ?, ?, ?, ?)
    """
    return execute_db(query, (user_id, title, message, notification_type, link))


def get_user_notifications(user_id, unread_only=False, limit=10):
    """Get notifications for a user."""
    if unread_only:
        query = """
            SELECT * FROM notifications 
            WHERE user_id = ? AND is_read = 0
            ORDER BY created_at DESC LIMIT ?
        """
    else:
        query = """
            SELECT * FROM notifications 
            WHERE user_id = ?
            ORDER BY created_at DESC LIMIT ?
        """
    
    return query_db(query, (user_id, limit))


def mark_notification_read(notification_id):
    """Mark notification as read."""
    query = "UPDATE notifications SET is_read = 1 WHERE id = ?"
    execute_db(query, (notification_id,))


def mark_all_read(user_id):
    """Mark all notifications as read for a user."""
    query = "UPDATE notifications SET is_read = 1 WHERE user_id = ?"
    execute_db(query, (user_id,))


def get_unread_count(user_id):
    """Get count of unread notifications."""
    query = "SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0"
    result = query_db(query, (user_id,), one=True)
    return result['count'] if result else 0


def notify_task_assignment(user_id, task_title, client_name):
    """Notify user of new task assignment."""
    title = "New Task Assigned"
    message = f"You have been assigned a new task: {task_title} for {client_name}"
    create_notification(user_id, title, message, 'info', '/tasks')


def notify_deadline_approaching(user_id, compliance_type, days_remaining):
    """Notify user of approaching deadline."""
    title = "Deadline Approaching"
    message = f"{compliance_type} deadline is {days_remaining} days away"
    notification_type = 'warning' if days_remaining <= 3 else 'info'
    create_notification(user_id, title, message, notification_type, '/compliance')


def notify_task_completed(user_id, task_title):
    """Notify user of task completion."""
    title = "Task Completed"
    message = f"Task '{task_title}' has been marked as completed"
    create_notification(user_id, title, message, 'success', '/tasks')
