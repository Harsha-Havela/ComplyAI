"""
Firebase Activity Service
Handles audit logging and activity tracking with Firestore
"""
from datetime import datetime
from flask import request
from app.models.firebase_database import (
    Collections, create_document, query_documents
)


def log_activity(user_id, action, entity_type=None, entity_id=None, description=None):
    """
    Log user activity for audit trail.
    
    Args:
        user_id: ID of the user performing the action
        action: Action performed (e.g., 'login', 'logout', 'create_client')
        entity_type: Type of entity affected (e.g., 'client', 'task')
        entity_id: ID of the affected entity
        description: Additional description of the action
        
    Returns:
        str: ID of the created activity log entry
    """
    # Get IP address from request
    ip_address = request.remote_addr if request else None
    user_agent = request.headers.get('User-Agent') if request else None
    
    activity_data = {
        'user_id': str(user_id),
        'action': action,
        'entity_type': entity_type,
        'entity_id': str(entity_id) if entity_id else None,
        'description': description,
        'ip_address': ip_address,
        'user_agent': user_agent,
        'timestamp': datetime.now()
    }
    
    try:
        log_id = create_document(Collections.ACTIVITY_LOGS, activity_data)
        return log_id
    except Exception as e:
        # Don't fail the main operation if logging fails
        print(f"Failed to log activity: {e}")
        return None


def get_user_activities(user_id, limit=50):
    """
    Get recent activities for a specific user.
    
    Args:
        user_id: ID of the user
        limit: Maximum number of activities to retrieve
        
    Returns:
        list: List of activity dictionaries
    """
    activities = query_documents(
        Collections.ACTIVITY_LOGS,
        filters=[('user_id', '==', str(user_id))],
        limit=limit
    )
    
    # Reverse to get most recent first (Firestore orders ascending)
    return list(reversed(activities))


def get_all_activities(limit=100):
    """
    Get recent activities across all users (admin function).
    
    Args:
        limit: Maximum number of activities to retrieve
        
    Returns:
        list: List of activity dictionaries with user information
    """
    from app.models.firebase_database import get_document
    
    activities = query_documents(
        Collections.ACTIVITY_LOGS,
        limit=limit
    )
    
    # Reverse to get most recent first
    activities = list(reversed(activities))
    
    # Enrich with user information
    enriched_activities = []
    for activity in activities:
        user = get_document(Collections.USERS, activity['user_id'])
        if user:
            activity['username'] = user.get('username', 'Unknown')
            activity['full_name'] = user.get('full_name', 'Unknown User')
        enriched_activities.append(activity)
    
    return enriched_activities


def get_entity_activities(entity_type, entity_id, limit=50):
    """
    Get activities related to a specific entity.
    
    Args:
        entity_type: Type of entity (e.g., 'client', 'task')
        entity_id: ID of the entity
        limit: Maximum number of activities to retrieve
        
    Returns:
        list: List of activity dictionaries
    """
    from app.models.firebase_database import get_document
    
    activities = query_documents(
        Collections.ACTIVITY_LOGS,
        filters=[
            ('entity_type', '==', entity_type),
            ('entity_id', '==', str(entity_id))
        ],
        limit=limit
    )
    
    # Reverse to get most recent first
    activities = list(reversed(activities))
    
    # Enrich with user information
    enriched_activities = []
    for activity in activities:
        user = get_document(Collections.USERS, activity['user_id'])
        if user:
            activity['username'] = user.get('username', 'Unknown')
            activity['full_name'] = user.get('full_name', 'Unknown User')
        enriched_activities.append(activity)
    
    return enriched_activities


def get_activity_statistics():
    """
    Get activity statistics.
    
    Returns:
        dict: Activity statistics
    """
    all_activities = query_documents(Collections.ACTIVITY_LOGS)
    
    stats = {
        'total_activities': len(all_activities),
        'unique_users': len(set(activity['user_id'] for activity in all_activities)),
        'actions': {}
    }
    
    # Count by action type
    for activity in all_activities:
        action = activity.get('action', 'unknown')
        stats['actions'][action] = stats['actions'].get(action, 0) + 1
    
    return stats


def cleanup_old_activities(days_to_keep=90):
    """
    Clean up old activity logs (keep only recent ones).
    
    Args:
        days_to_keep: Number of days to keep activities
        
    Returns:
        int: Number of activities cleaned up
    """
    from datetime import timedelta
    from app.models.firebase_database import delete_document
    
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    # Get old activities
    old_activities = query_documents(
        Collections.ACTIVITY_LOGS,
        filters=[('timestamp', '<', cutoff_date)]
    )
    
    # Delete old activities
    deleted_count = 0
    for activity in old_activities:
        if delete_document(Collections.ACTIVITY_LOGS, activity['id']):
            deleted_count += 1
    
    return deleted_count


def get_activity_logs(limit=100, user_id=None, action_type=None, days=7):
    """
    Get activity logs with optional filtering (for reports).
    SIMPLIFIED VERSION - No date filtering to avoid timezone issues.
    """
    from app.models.firebase_database import get_document
    
    # Build simple filters
    filters = []
    
    if user_id:
        filters.append(('user_id', '==', str(user_id)))
    
    if action_type:
        filters.append(('action', '==', action_type))
    
    # Query activities WITHOUT any date filtering
    activities = query_documents(
        Collections.ACTIVITY_LOGS,
        filters=filters if filters else None,
        limit=limit
    )
    
    # Simple sort by timestamp (handle both timezone-aware and naive)
    def safe_timestamp(activity):
        ts = activity.get('timestamp')
        if ts:
            return ts
        return datetime(1970, 1, 1)  # Default for missing timestamps
    
    activities = sorted(activities, key=safe_timestamp, reverse=True)
    
    # Limit results
    activities = activities[:limit]
    
    # Enrich with user information
    enriched_activities = []
    for activity in activities:
        try:
            user = get_document(Collections.USERS, activity['user_id'])
            if user:
                activity['username'] = user.get('username', 'Unknown')
                activity['full_name'] = user.get('full_name', 'Unknown User')
            enriched_activities.append(activity)
        except:
            # Skip problematic entries
            continue
    
    return enriched_activities


def get_user_activity_summary(user_id, days=30):
    """
    Get activity summary for a specific user.
    SIMPLIFIED VERSION - Just count all activities.
    """
    # Get user activities without date filtering
    try:
        activities = query_documents(
            Collections.ACTIVITY_LOGS,
            filters=[('user_id', '==', str(user_id))]
        )
    except:
        activities = []
    
    # Calculate summary
    summary = {
        'total_activities': len(activities),
        'by_action': {},
        'by_entity_type': {},
        'most_recent_activity': None
    }
    
    for activity in activities:
        try:
            # Count by action
            action = activity.get('action', 'unknown')
            summary['by_action'][action] = summary['by_action'].get(action, 0) + 1
            
            # Count by entity type
            entity_type = activity.get('entity_type')
            if entity_type:
                summary['by_entity_type'][entity_type] = summary['by_entity_type'].get(entity_type, 0) + 1
        except:
            continue
    
    # Get most recent activity (simplified)
    if activities:
        try:
            # Just take the first activity as "most recent"
            summary['most_recent_activity'] = activities[0].get('timestamp')
        except:
            pass
    
    return summary