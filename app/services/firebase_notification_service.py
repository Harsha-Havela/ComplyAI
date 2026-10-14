"""
Firebase Notification Service
Manages in-app notifications with Firestore
"""
from datetime import datetime
from app.models.firebase_database import (
    Collections, create_document, get_document, update_document,
    delete_document, query_documents
)


# Add notifications collection
class NotificationCollections:
    NOTIFICATIONS = 'notifications'


def create_notification(user_id, title, message, notification_type='info', link=None, related_entity_type=None, related_entity_id=None):
    """
    Create a new notification for a user.
    
    Args:
        user_id: User ID to notify
        title: Notification title
        message: Notification message
        notification_type: Type (info, success, warning, danger)
        link: Optional link URL
        related_entity_type: Optional related entity type (task, client, compliance)
        related_entity_id: Optional related entity ID
        
    Returns:
        str: Notification ID
    """
    notification_data = {
        'user_id': str(user_id),
        'title': title,
        'message': message,
        'type': notification_type,
        'link': link,
        'related_entity_type': related_entity_type,
        'related_entity_id': str(related_entity_id) if related_entity_id else None,
        'is_read': False,
        'created_at': datetime.now(),
        'read_at': None
    }
    
    return create_document(NotificationCollections.NOTIFICATIONS, notification_data)


def get_user_notifications(user_id, unread_only=False, limit=50):
    """
    Get notifications for a user.
    
    Args:
        user_id: User ID
        unread_only: Only return unread notifications
        limit: Maximum number of notifications
        
    Returns:
        list: List of notifications
    """
    filters = [('user_id', '==', str(user_id))]
    
    if unread_only:
        filters.append(('is_read', '==', False))
    
    notifications = query_documents(
        NotificationCollections.NOTIFICATIONS,
        filters=filters,
        limit=limit
    )
    
    # Sort by created_at descending (most recent first)
    notifications.sort(key=lambda x: x.get('created_at', datetime.now()), reverse=True)
    
    return notifications


def mark_notification_read(notification_id):
    """
    Mark notification as read.
    
    Args:
        notification_id: Notification ID
        
    Returns:
        bool: Success status
    """
    return update_document(NotificationCollections.NOTIFICATIONS, notification_id, {
        'is_read': True,
        'read_at': datetime.now()
    })


def mark_all_read(user_id):
    """
    Mark all notifications as read for a user.
    
    Args:
        user_id: User ID
        
    Returns:
        int: Number of notifications marked as read
    """
    notifications = get_user_notifications(user_id, unread_only=True)
    
    count = 0
    for notification in notifications:
        if mark_notification_read(notification['id']):
            count += 1
    
    return count


def get_unread_count(user_id):
    """
    Get count of unread notifications.
    
    Args:
        user_id: User ID
        
    Returns:
        int: Count of unread notifications
    """
    unread_notifications = get_user_notifications(user_id, unread_only=True)
    return len(unread_notifications)


def delete_notification(notification_id):
    """
    Delete a notification.
    
    Args:
        notification_id: Notification ID
        
    Returns:
        bool: Success status
    """
    return delete_document(NotificationCollections.NOTIFICATIONS, notification_id)


def delete_old_notifications(days=30):
    """
    Delete notifications older than specified days.
    
    Args:
        days: Number of days to keep
        
    Returns:
        int: Number of notifications deleted
    """
    from datetime import timedelta
    
    cutoff_date = datetime.now() - timedelta(days=days)
    
    all_notifications = query_documents(NotificationCollections.NOTIFICATIONS)
    
    count = 0
    for notification in all_notifications:
        if notification.get('created_at') and notification['created_at'] < cutoff_date:
            if delete_notification(notification['id']):
                count += 1
    
    return count


# Specific notification creators

def notify_task_assignment(user_id, task_id, task_title, client_name):
    """
    Notify user of new task assignment.
    
    Args:
        user_id: User ID to notify
        task_id: Task ID
        task_title: Task title
        client_name: Client name
    """
    title = "New Task Assigned"
    message = f"You have been assigned: {task_title} for {client_name}"
    create_notification(
        user_id, 
        title, 
        message, 
        'info', 
        f'/tasks/{task_id}',
        'task',
        task_id
    )


def notify_task_status_change(user_id, task_id, task_title, old_status, new_status):
    """
    Notify user of task status change.
    
    Args:
        user_id: User ID to notify
        task_id: Task ID
        task_title: Task title
        old_status: Previous status
        new_status: New status
    """
    title = "Task Status Updated"
    message = f"Task '{task_title}' status changed from {old_status} to {new_status}"
    
    notification_type = 'success' if new_status == 'completed' else 'info'
    
    create_notification(
        user_id,
        title,
        message,
        notification_type,
        f'/tasks/{task_id}',
        'task',
        task_id
    )


def notify_deadline_approaching(user_id, compliance_id, compliance_type, client_name, days_remaining):
    """
    Notify user of approaching compliance deadline.
    
    Args:
        user_id: User ID to notify
        compliance_id: Compliance deadline ID
        compliance_type: Type of compliance
        client_name: Client name
        days_remaining: Days until deadline
    """
    title = "Deadline Approaching"
    
    if client_name:
        message = f"{compliance_type} for {client_name} is due in {days_remaining} day(s)"
    else:
        message = f"{compliance_type} deadline is {days_remaining} day(s) away"
    
    notification_type = 'danger' if days_remaining <= 2 else 'warning' if days_remaining <= 7 else 'info'
    
    create_notification(
        user_id,
        title,
        message,
        notification_type,
        f'/compliance/{compliance_id}',
        'compliance',
        compliance_id
    )


def notify_task_completed(creator_id, task_id, task_title, completed_by_name):
    """
    Notify task creator of task completion.
    
    Args:
        creator_id: Task creator user ID
        task_id: Task ID
        task_title: Task title
        completed_by_name: Name of user who completed the task
    """
    title = "Task Completed"
    message = f"Task '{task_title}' has been completed by {completed_by_name}"
    
    create_notification(
        creator_id,
        title,
        message,
        'success',
        f'/tasks/{task_id}',
        'task',
        task_id
    )


def notify_task_comment(user_id, task_id, task_title, commenter_name, comment_preview):
    """
    Notify user of new comment on their task.
    
    Args:
        user_id: User ID to notify
        task_id: Task ID
        task_title: Task title
        commenter_name: Name of person who commented
        comment_preview: Preview of the comment (first 50 chars)
    """
    title = "New Comment on Task"
    message = f"{commenter_name} commented on '{task_title}': {comment_preview}"
    
    create_notification(
        user_id,
        title,
        message,
        'info',
        f'/tasks/{task_id}',
        'task',
        task_id
    )


def notify_client_assigned(user_id, client_id, client_name):
    """
    Notify user of new client assignment.
    
    Args:
        user_id: User ID to notify
        client_id: Client ID
        client_name: Client company name
    """
    title = "New Client Assigned"
    message = f"You have been assigned to manage: {client_name}"
    
    create_notification(
        user_id,
        title,
        message,
        'info',
        f'/clients/{client_id}',
        'client',
        client_id
    )


def notify_compliance_overdue(user_id, compliance_id, compliance_type, client_name):
    """
    Notify user of overdue compliance.
    
    Args:
        user_id: User ID to notify
        compliance_id: Compliance ID
        compliance_type: Type of compliance
        client_name: Client name
    """
    title = "Compliance Overdue"
    
    if client_name:
        message = f"OVERDUE: {compliance_type} for {client_name}"
    else:
        message = f"OVERDUE: {compliance_type}"
    
    create_notification(
        user_id,
        title,
        message,
        'danger',
        f'/compliance/{compliance_id}',
        'compliance',
        compliance_id
    )
