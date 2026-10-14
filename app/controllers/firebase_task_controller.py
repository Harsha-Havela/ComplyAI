"""
Firebase Task Controller
Handles all task management business logic with Firestore
"""
from datetime import datetime, timedelta
from app.models.firebase_database import (
    Collections, create_document, get_document, update_document,
    delete_document, query_documents, search_documents, count_documents
)
from app.services.firebase_activity_service import log_activity


def create_task(title, description, client_id, assigned_to, priority, 
               due_date, reminder_date, created_by):
    """
    Create a new task.
    
    Args:
        title: Task title (required)
        description: Task description
        client_id: ID of the client
        assigned_to: User ID of assignee
        priority: Task priority (low, medium, high, urgent)
        due_date: Due date (YYYY-MM-DD)
        reminder_date: Reminder date (YYYY-MM-DD)
        created_by: User ID of creator
        
    Returns:
        tuple: (success, task_id or error_message)
    """
    if not title or not title.strip():
        return False, "Task title is required."
    
    if not client_id:
        return False, "Client is required."
        
    if not assigned_to:
        return False, "Assignee is required."
    
    # Validate priority
    valid_priorities = ['low', 'medium', 'high', 'urgent']
    if priority not in valid_priorities:
        priority = 'medium'
    
    # Validate dates
    if due_date:
        try:
            datetime.strptime(due_date, '%Y-%m-%d')
        except ValueError:
            return False, "Invalid due date format. Use YYYY-MM-DD."
    
    if reminder_date:
        try:
            datetime.strptime(reminder_date, '%Y-%m-%d')
        except ValueError:
            return False, "Invalid reminder date format. Use YYYY-MM-DD."
    
    # Create task document
    task_data = {
        'title': title.strip(),
        'description': description.strip() if description else '',
        'client_id': str(client_id),
        'assigned_to': str(assigned_to),
        'priority': priority,
        'due_date': due_date,
        'reminder_date': reminder_date,
        'status': 'pending',
        'created_by': str(created_by),
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
        'completed_at': None
    }
    
    # Debug: Print assignment details
    print(f"🔧 Creating task - Assigned to: '{assigned_to}' (type: {type(assigned_to)})")
    
    try:
        task_id = create_document(Collections.TASKS, task_data)
        
        # Log activity
        log_activity(
            created_by,
            'create_task',
            'task',
            task_id,
            f"Created task: {title}"
        )
        
        print(f"✅ Task created with ID: {task_id}")
        
        return True, task_id
    except Exception as e:
        print(f"❌ Task creation failed: {e}")
        return False, f"Failed to create task: {str(e)}"


def get_task_by_id(task_id):
    """
    Get a specific task by ID.
    
    Args:
        task_id: Task ID to retrieve
        
    Returns:
        dict or None: Task document or None if not found
    """
    task = get_document(Collections.TASKS, task_id)
    
    if task:
        # Enrich with client information
        if task.get('client_id'):
            client = get_document(Collections.CLIENTS, task['client_id'])
            if client:
                task['client_name'] = client.get('company_name', 'Unknown Client')
        
        # Enrich with user information
        if task.get('assigned_to'):
            user = get_document(Collections.USERS, task['assigned_to'])
            if user:
                task['assigned_to_name'] = user.get('full_name', user.get('username'))
        
        if task.get('created_by'):
            creator = get_document(Collections.USERS, task['created_by'])
            if creator:
                task['created_by_name'] = creator.get('full_name', creator.get('username'))
    
    return task


def get_all_tasks(user_id=None, user_role=None, status=None, priority=None, 
                 client_id=None, assigned_to=None):
    """
    Get all tasks with optional filtering.
    
    Args:
        user_id: Current user ID
        user_role: Current user role (admin, manager, employee)
        status: Filter by status
        priority: Filter by priority
        client_id: Filter by client
        assigned_to: Filter by assignee
        
    Returns:
        list: List of tasks
    """
    filters = []
    
    # Role-based filtering
    if user_role == 'employee':
        filters.append(('assigned_to', '==', str(user_id)))
    
    # Status filter
    if status:
        filters.append(('status', '==', status))
    
    # Priority filter
    if priority:
        filters.append(('priority', '==', priority))
    
    # Client filter
    if client_id:
        filters.append(('client_id', '==', str(client_id)))
    
    # Assigned to filter
    if assigned_to:
        filters.append(('assigned_to', '==', str(assigned_to)))
    
    # Query WITHOUT order_by to avoid index requirement
    tasks = query_documents(
        Collections.TASKS,
        filters=filters if filters else None
    )
    
    # Sort in Python instead of Firestore
    tasks = list(reversed(tasks))  # Most recent first
    
    # Enrich tasks with additional information
    enriched_tasks = []
    for task in tasks:
        # Add client information
        if task.get('client_id'):
            client = get_document(Collections.CLIENTS, task['client_id'])
            if client:
                task['client_name'] = client.get('company_name')
        
        # Add user information
        if task.get('assigned_to'):
            user = get_document(Collections.USERS, task['assigned_to'])
            if user:
                task['assigned_to_name'] = user.get('full_name', user.get('username'))
        
        enriched_tasks.append(task)
    
    return enriched_tasks


def update_task(task_id, title=None, description=None, client_id=None,
               assigned_to=None, priority=None, due_date=None, 
               reminder_date=None, status=None, updated_by=None):
    """
    Update a task.
    
    Args:
        task_id: Task ID to update
        title: New title (optional)
        description: New description (optional)
        client_id: New client ID (optional)
        assigned_to: New assignee (optional)
        priority: New priority (optional)
        due_date: New due date (optional)
        reminder_date: New reminder date (optional)
        status: New status (optional)
        updated_by: User ID making the update
        
    Returns:
        tuple: (success, message)
    """
    # Get existing task
    task = get_document(Collections.TASKS, task_id)
    if not task:
        return False, "Task not found."
    
    # Prepare update data
    update_data = {'updated_at': datetime.now()}
    
    if title is not None:
        if not title.strip():
            return False, "Task title cannot be empty."
        update_data['title'] = title.strip()
    
    if description is not None:
        update_data['description'] = description.strip()
    
    if client_id is not None:
        update_data['client_id'] = str(client_id)
    
    if assigned_to is not None:
        update_data['assigned_to'] = str(assigned_to)
    
    if priority is not None:
        valid_priorities = ['low', 'medium', 'high', 'urgent']
        if priority in valid_priorities:
            update_data['priority'] = priority
    
    if due_date is not None:
        if due_date:
            try:
                datetime.strptime(due_date, '%Y-%m-%d')
                update_data['due_date'] = due_date
            except ValueError:
                return False, "Invalid due date format. Use YYYY-MM-DD."
        else:
            update_data['due_date'] = None
    
    if reminder_date is not None:
        if reminder_date:
            try:
                datetime.strptime(reminder_date, '%Y-%m-%d')
                update_data['reminder_date'] = reminder_date
            except ValueError:
                return False, "Invalid reminder date format. Use YYYY-MM-DD."
        else:
            update_data['reminder_date'] = None
    
    if status is not None:
        valid_statuses = ['pending', 'in_progress', 'completed', 'cancelled']
        if status in valid_statuses:
            update_data['status'] = status
            
            # Set completion timestamp if marking as completed
            if status == 'completed' and task.get('status') != 'completed':
                update_data['completed_at'] = datetime.now()
            elif status != 'completed':
                update_data['completed_at'] = None
    
    try:
        update_document(Collections.TASKS, task_id, update_data)
        
        # Log activity
        if updated_by:
            log_activity(
                updated_by,
                'update_task',
                'task',
                task_id,
                f"Updated task: {task['title']}"
            )
        
        return True, "Task updated successfully."
    except Exception as e:
        return False, f"Failed to update task: {str(e)}"


def delete_task(task_id, deleted_by):
    """
    Delete a task.
    
    Args:
        task_id: Task ID to delete
        deleted_by: User ID performing deletion
        
    Returns:
        tuple: (success, message)
    """
    # Get task for logging
    task = get_document(Collections.TASKS, task_id)
    if not task:
        return False, "Task not found."
    
    try:
        # Delete related comments first
        comments = query_documents(
            Collections.COMMENTS,
            filters=[
                ('entity_type', '==', 'task'),
                ('entity_id', '==', str(task_id))
            ]
        )
        
        for comment in comments:
            delete_document(Collections.COMMENTS, comment['id'])
        
        # Delete the task
        delete_document(Collections.TASKS, task_id)
        
        # Log activity
        log_activity(
            deleted_by,
            'delete_task',
            'task',
            task_id,
            f"Deleted task: {task['title']}"
        )
        
        return True, "Task deleted successfully."
    except Exception as e:
        return False, f"Failed to delete task: {str(e)}"


def get_tasks_by_priority(priority, user_id=None, user_role=None):
    """
    Get tasks with specified priority.
    
    Args:
        priority: Priority level to filter by
        user_id: Current user ID
        user_role: Current user role
        
    Returns:
        list: List of tasks with specified priority
    """
    return get_all_tasks(user_id, user_role, priority=priority)


def get_overdue_tasks(user_id=None, user_role=None):
    """
    Get overdue tasks.
    
    Args:
        user_id: Current user ID
        user_role: Current user role
        
    Returns:
        list: List of overdue tasks
    """
    current_date = datetime.now().date()
    
    # Get all pending and in-progress tasks
    tasks = get_all_tasks(user_id, user_role)
    
    overdue_tasks = []
    for task in tasks:
        if (task.get('due_date') and 
            task.get('status') in ['pending', 'in_progress'] and
            datetime.strptime(task['due_date'], '%Y-%m-%d').date() < current_date):
            overdue_tasks.append(task)
    
    return overdue_tasks


def add_task_comment(task_id, comment_text, user_id):
    """
    Add a comment to a task.
    
    Args:
        task_id: Task ID
        comment_text: Comment content
        user_id: User adding the comment
        
    Returns:
        tuple: (success, comment_id or error_message)
    """
    if not comment_text.strip():
        return False, "Comment cannot be empty."
    
    # Verify task exists
    task = get_document(Collections.TASKS, task_id)
    if not task:
        return False, "Task not found."
    
    # Create comment
    comment_data = {
        'entity_type': 'task',
        'entity_id': str(task_id),
        'user_id': str(user_id),
        'comment': comment_text.strip(),
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    
    try:
        comment_id = create_document(Collections.COMMENTS, comment_data)
        
        # Log activity
        log_activity(
            user_id,
            'add_comment',
            'task',
            task_id,
            f"Added comment to task: {task['title']}"
        )
        
        return True, comment_id
    except Exception as e:
        return False, f"Failed to add comment: {str(e)}"


def get_task_comments(task_id):
    """
    Get all comments for a task.
    
    Args:
        task_id: Task ID
        
    Returns:
        list: List of comments with user information
    """
    comments = query_documents(
        Collections.COMMENTS,
        filters=[
            ('entity_type', '==', 'task'),
            ('entity_id', '==', str(task_id))
        ]
    )
    
    # Enrich with user information
    enriched_comments = []
    for comment in comments:
        user = get_document(Collections.USERS, comment['user_id'])
        if user:
            comment['username'] = user.get('username')
            comment['user_full_name'] = user.get('full_name')
        enriched_comments.append(comment)
    
    return enriched_comments


def get_my_tasks(user_id, status=None):
    """
    Get tasks assigned to a specific user.
    
    Args:
        user_id: User ID
        status: Optional status filter
        
    Returns:
        list: List of assigned tasks
    """
    # Build filters for this user's tasks
    filters = [('assigned_to', '==', str(user_id))]
    
    if status:
        filters.append(('status', '==', status))
    
    # Query WITHOUT order_by to avoid index requirement
    try:
        tasks = query_documents(
            Collections.TASKS,
            filters=filters
        )
    except Exception as e:
        print(f"Error querying my tasks: {e}")
        return []
    
    # Sort in Python by created_at (most recent first)
    tasks = sorted(tasks, key=lambda x: x.get('created_at', datetime.now()), reverse=True)
    
    # Enrich tasks with additional information
    enriched_tasks = []
    for task in tasks:
        # Add client information
        if task.get('client_id'):
            client = get_document(Collections.CLIENTS, task['client_id'])
            if client:
                task['client_name'] = client.get('company_name')
        
        # Add user information
        if task.get('assigned_to'):
            user = get_document(Collections.USERS, task['assigned_to'])
            if user:
                task['assigned_to_name'] = user.get('full_name', user.get('username'))
        
        enriched_tasks.append(task)
    
    return enriched_tasks


def get_tasks_due_soon(days_ahead=7, user_id=None, user_role=None):
    """
    Get tasks due within specified days.
    
    Args:
        days_ahead: Number of days to look ahead
        user_id: Current user ID
        user_role: Current user role
        
    Returns:
        list: List of tasks due soon
    """
    future_date = datetime.now().date() + timedelta(days=days_ahead)
    current_date = datetime.now().date()
    
    # Get all pending and in-progress tasks
    tasks = get_all_tasks(user_id, user_role)
    
    due_soon_tasks = []
    for task in tasks:
        if (task.get('due_date') and 
            task.get('status') in ['pending', 'in_progress']):
            
            due_date = datetime.strptime(task['due_date'], '%Y-%m-%d').date()
            if current_date <= due_date <= future_date:
                due_soon_tasks.append(task)
    
    # Sort by due date
    due_soon_tasks.sort(key=lambda x: x['due_date'])
    
    return due_soon_tasks


def search_tasks(query, user_id=None, user_role=None):
    """
    Search tasks by title or description.
    
    Args:
        query: Search query
        user_id: Current user ID
        user_role: Current user role
        
    Returns:
        list: List of matching tasks
    """
    if not query or not query.strip():
        return []
    
    # Get all tasks for the user
    all_tasks = get_all_tasks(user_id, user_role)
    
    # Filter tasks by query
    query = query.lower().strip()
    matching_tasks = []
    
    for task in all_tasks:
        title_match = query in task.get('title', '').lower()
        description_match = query in task.get('description', '').lower()
        
        if title_match or description_match:
            matching_tasks.append(task)
    
    return matching_tasks


def get_task_statistics(user_id=None, user_role=None):
    """
    Get task statistics.
    
    Args:
        user_id: Current user ID
        user_role: Current user role
        
    Returns:
        dict: Task statistics
    """
    all_tasks = get_all_tasks(user_id, user_role)
    
    stats = {
        'total': len(all_tasks),
        'pending': 0,
        'in_progress': 0,
        'completed': 0,
        'cancelled': 0,
        'overdue': 0,
        'due_today': 0,
        'due_this_week': 0,
        'by_priority': {
            'low': 0,
            'medium': 0,
            'high': 0,
            'urgent': 0
        }
    }
    
    today = datetime.now().date()
    week_end = today + timedelta(days=7)
    
    for task in all_tasks:
        # Count by status
        status = task.get('status', 'pending')
        if status in stats:
            stats[status] += 1
        
        # Count by priority
        priority = task.get('priority', 'medium')
        if priority in stats['by_priority']:
            stats['by_priority'][priority] += 1
        
        # Count overdue and due dates
        if task.get('due_date') and status in ['pending', 'in_progress']:
            due_date = datetime.strptime(task['due_date'], '%Y-%m-%d').date()
            
            if due_date < today:
                stats['overdue'] += 1
            elif due_date == today:
                stats['due_today'] += 1
            elif due_date <= week_end:
                stats['due_this_week'] += 1
    
    return stats


def update_task_status(task_id, new_status, updated_by):
    """
    Update task status.
    
    Args:
        task_id: Task ID to update
        new_status: New status (pending, in_progress, completed, cancelled)
        updated_by: User ID making the update
        
    Returns:
        tuple: (success, message)
    """
    valid_statuses = ['pending', 'in_progress', 'completed', 'cancelled']
    
    if new_status not in valid_statuses:
        return False, f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
    
    return update_task(task_id, status=new_status, updated_by=updated_by)


def assign_task(task_id, assigned_to, updated_by):
    """
    Assign task to a user.
    
    Args:
        task_id: Task ID to assign
        assigned_to: User ID to assign task to
        updated_by: User ID making the assignment
        
    Returns:
        tuple: (success, message)
    """
    return update_task(task_id, assigned_to=assigned_to, updated_by=updated_by)