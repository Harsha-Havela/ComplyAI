"""
Firebase Notification Routes
Handles notification-related HTTP requests with Firebase backend
"""
from flask import Blueprint, jsonify, request
from app.services.firebase_notification_service import (
    get_user_notifications, mark_notification_read, mark_all_read,
    get_unread_count, delete_notification
)
from app.utils.firebase_auth import login_required, get_current_user

notification_bp = Blueprint('notification', __name__, url_prefix='/api/notifications')


@notification_bp.route('/')
@login_required
def list_notifications():
    """
    Get notifications for current user.
    Query params:
        - unread_only: boolean (default: false)
        - limit: int (default: 50)
    """
    user = get_current_user()
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    limit = int(request.args.get('limit', 50))
    
    notifications = get_user_notifications(user['id'], unread_only, limit)
    
    # Convert datetime objects to strings for JSON serialization
    for notification in notifications:
        if notification.get('created_at'):
            notification['created_at'] = notification['created_at'].isoformat()
        if notification.get('read_at'):
            notification['read_at'] = notification['read_at'].isoformat()
    
    return jsonify({
        'success': True,
        'notifications': notifications,
        'count': len(notifications)
    })


@notification_bp.route('/unread-count')
@login_required
def unread_count():
    """Get count of unread notifications for current user."""
    user = get_current_user()
    count = get_unread_count(user['id'])
    
    return jsonify({
        'success': True,
        'count': count
    })


@notification_bp.route('/<notification_id>/read', methods=['POST'])
@login_required
def mark_read(notification_id):
    """Mark a notification as read."""
    success = mark_notification_read(notification_id)
    
    if success:
        return jsonify({
            'success': True,
            'message': 'Notification marked as read'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to mark notification as read'
        }), 400


@notification_bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read_route():
    """Mark all notifications as read for current user."""
    user = get_current_user()
    count = mark_all_read(user['id'])
    
    return jsonify({
        'success': True,
        'message': f'{count} notification(s) marked as read',
        'count': count
    })


@notification_bp.route('/<notification_id>', methods=['DELETE'])
@login_required
def delete_notification_route(notification_id):
    """Delete a notification."""
    success = delete_notification(notification_id)
    
    if success:
        return jsonify({
            'success': True,
            'message': 'Notification deleted'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to delete notification'
        }), 400
