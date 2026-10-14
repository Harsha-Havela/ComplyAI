"""
Activity Service
Handles audit logging and activity tracking
"""
from app.models.database import execute_db
from flask import request


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
        int: ID of the created activity log entry
    """
    # Get IP address from request
    ip_address = request.remote_addr if request else None
    
    query = '''
        INSERT INTO activity_logs 
        (user_id, action, entity_type, entity_id, description, ip_address)
        VALUES (?, ?, ?, ?, ?, ?)
    '''
    
    log_id = execute_db(
        query,
        (user_id, action, entity_type, entity_id, description, ip_address)
    )
    
    return log_id


def get_user_activities(user_id, limit=50):
    """
    Get recent activities for a specific user.
    
    Args:
        user_id: ID of the user
        limit: Maximum number of activities to retrieve
        
    Returns:
        list: List of activity dictionaries
    """
    from app.models.database import query_db
    
    query = '''
        SELECT id, action, entity_type, entity_id, description, 
               ip_address, created_at
        FROM activity_logs
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    '''
    
    return query_db(query, (user_id, limit))


def get_all_activities(limit=100):
    """
    Get recent activities across all users (admin function).
    
    Args:
        limit: Maximum number of activities to retrieve
        
    Returns:
        list: List of activity dictionaries with user information
    """
    from app.models.database import query_db
    
    query = '''
        SELECT a.id, a.user_id, u.username, u.full_name, 
               a.action, a.entity_type, a.entity_id, 
               a.description, a.ip_address, a.created_at
        FROM activity_logs a
        JOIN users u ON a.user_id = u.id
        ORDER BY a.created_at DESC
        LIMIT ?
    '''
    
    return query_db(query, (limit,))


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
    from app.models.database import query_db
    
    query = '''
        SELECT a.id, a.user_id, u.username, u.full_name,
               a.action, a.description, a.ip_address, a.created_at
        FROM activity_logs a
        JOIN users u ON a.user_id = u.id
        WHERE a.entity_type = ? AND a.entity_id = ?
        ORDER BY a.created_at DESC
        LIMIT ?
    '''
    
    return query_db(query, (entity_type, entity_id, limit))
