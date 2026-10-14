"""
Task Controller
Handles all task management business logic
"""
from app.models.database import query_db, execute_db
from app.services.activity_service import log_activity
from datetime import datetime, timedelta


def create_task(title, description, client_id, assigned_to, created_by, 
                priority='medium', due_date=None, reminder_date=None):
    """
    Create a new task.
    
    Args:
        title: Task title
        description: Task description
        client_id: ID of the client this task is for
        assigned_to: User ID to assign the task to
        created_by: User ID creating the task
        priority: Task priority (low, medium, high, urgent)
        due_date: Due date for the task (YYYY-MM-DD format)
        reminder_date: Reminder date (YYYY-MM-DD format)
        
    Returns:
        tuple: (success, task_id or error_message)
    """
    # Validate required fields
    if not all([title, client_id, assigned_to]):
        return False, "Title, client, and assigned user are required."
    
    # Validate priority
    if priority not in ['low', 'medium', 'high', 'urgent']:
        return False, "Invalid priority level."
    
    # Validate client exists
    client = query_db('SELECT id, company_name FROM clients WHERE id = ?', (client_id,), one=True)
    if not client:
        return False, "Client not found."
    
    # Validate assigned user exists
    user = query_db('SELECT id, full_name FROM users WHERE id = ? AND is_active = 1', (assigned_to,), one=True)
    if not user:
        return False, "Assigned user not found or inactive."
    
    # Validate dates if provided
    if due_date:
        try:
            due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
            if due_date_obj < datetime.now().date():
                return False, "Due date cannot be in the past."
        except ValueError:
            return False, "Invalid due date format. Use YYYY-MM-DD."
    
    if reminder_date:
        try:
            reminder_date_obj = datetime.strptime(reminder_date, '%Y-%m-%d').date()
            if reminder_date_obj < datetime.now().date():
                return False, "Reminder date cannot be in the past."
            if due_date and reminder_date_obj > due_date_obj:
                return False, "Reminder date cannot be after due date."
        except ValueError:
            return False, "Invalid reminder date format. Use YYYY-MM-DD."
    
    # Insert task
    query = '''
        INSERT INTO tasks 
        (title, description, client_id, assigned_to, created_by, priority, due_date, reminder_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    '''
    
    try:
        task_id = execute_db(
            query,
            (title, description, client_id, assigned_to, created_by, priority, due_date, reminder_date)
        )
        
        # Log activity
        log_activity(
            created_by,
            'create_task',
            'task',
            task_id,
            f"Created task '{title}' for {client['company_name']}"
        )
        
        return True, task_id
    except Exception as e:
        return False, f"Failed to create task: {str(e)}"


def get_task_by_id(task_id):
    """
    Get task details by ID.
    
    Args:
        task_id: Task ID
        
    Returns:
        dict: Task information with related data
    """
    query = '''
        SELECT t.*, 
               c.company_name as client_name,
               u1.username as assigned_to_username,
               u1.full_name as assigned_to_name,
               u2.username as created_by_username,
               u2.full_name as created_by_name
        FROM tasks t
        JOIN clients c ON t.client_id = c.id
        LEFT JOIN users u1 ON t.assigned_to = u1.id
        LEFT JOIN users u2 ON t.created_by = u2.id
        WHERE t.id = ?
    '''
    
    return query_db(query, (task_id,), one=True)


def get_all_tasks(user_id=None, user_role=None, status=None, client_id=None):
    """
    Get all tasks based on user role and filters.
    
    Args:
        user_id: Current user ID
        user_role: Current user role
        status: Filter by status (pending, in_progress, completed, cancelled)
        client_id: Filter by client ID
        
    Returns:
        list: List of task dictionaries
    """
    # Base query
    base_query = '''
        SELECT t.*, 
               c.company_name as client_name,
               u.username as assigned_to_username,
               u.full_name as assigned_to_name
        FROM tasks t
        JOIN clients c ON t.client_id = c.id
        LEFT JOIN users u ON t.assigned_to = u.id
    '''
    
    where_conditions = []
    params = []
    
    # Role-based filtering
    if user_role == 'employee':
        where_conditions.append('t.assigned_to = ?')
        params.append(user_id)
    
    # Status filtering
    if status:
        where_conditions.append('t.status = ?')
        params.append(status)
    
    # Client filtering
    if client_id:
        where_conditions.append('t.client_id = ?')
        params.append(client_id)
    
    # Build final query
    if where_conditions:
        query = base_query + ' WHERE ' + ' AND '.join(where_conditions)
    else:
        query = base_query
    
    query += ' ORDER BY t.created_at DESC'
    
    return query_db(query, tuple(params))


def update_task(task_id, title, description, priority, due_date, reminder_date, user_id):
    """
    Update task information.
    
    Args:
        task_id: Task ID to update
        title: Task title
        description: Task description
        priority: Task priority
        due_date: Due date (YYYY-MM-DD or None)
        reminder_date: Reminder date (YYYY-MM-DD or None)
        user_id: User ID performing the update
        
    Returns:
        tuple: (success, message)
    """
    # Validate required fields
    if not title:
        return False, "Title is required."
    
    # Validate priority
    if priority not in ['low', 'medium', 'high', 'urgent']:
        return False, "Invalid priority level."
    
    # Validate dates if provided
    if due_date:
        try:
            due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
        except ValueError:
            return False, "Invalid due date format. Use YYYY-MM-DD."
    
    if reminder_date:
        try:
            reminder_date_obj = datetime.strptime(reminder_date, '%Y-%m-%d').date()
            if due_date and reminder_date_obj > due_date_obj:
                return False, "Reminder date cannot be after due date."
        except ValueError:
            return False, "Invalid reminder date format. Use YYYY-MM-DD."
    
    # Get task for logging
    task = get_task_by_id(task_id)
    if not task:
        return False, "Task not found."
    
    # Update task
    query = '''
        UPDATE tasks 
        SET title = ?, description = ?, priority = ?, due_date = ?, 
            reminder_date = ?, updated_at = ?
        WHERE id = ?
    '''
    
    try:
        execute_db(
            query,
            (title, description, priority, due_date, reminder_date, datetime.now(), task_id)
        )
        
        # Log activity
        log_activity(
            user_id,
            'update_task',
            'task',
            task_id,
            f"Updated task '{title}'"
        )
        
        return True, "Task updated successfully."
    except Exception as e:
        return False, f"Failed to update task: {str(e)}"


def update_task_status(task_id, status, user_id):
    """
    Update task status.
    
    Args:
        task_id: Task ID
        status: New status (pending, in_progress, completed, cancelled)
        user_id: User ID performing the update
        
    Returns:
        tuple: (success, message)
    """
    if status not in ['pending', 'in_progress', 'completed', 'cancelled']:
        return False, "Invalid status."
    
    # Get task for logging
    task = get_task_by_id(task_id)
    if not task:
        return False, "Task not found."
    
    # Set completed timestamp if marking as completed
    completed_at = datetime.now() if status == 'completed' else None
    
    try:
        execute_db(
            'UPDATE tasks SET status = ?, completed_at = ?, updated_at = ? WHERE id = ?',
            (status, completed_at, datetime.now(), task_id)
        )
        
        # Log activity
        log_activity(
            user_id,
            'update_task_status',
            'task',
            task_id,
            f"Changed status to {status} for task '{task['title']}'"
        )
        
        return True, f"Task status updated to {status}."
    except Exception as e:
        return False, f"Failed to update status: {str(e)}"


def delete_task(task_id, user_id):
    """
    Delete a task (admin only).
    
    Args:
        task_id: Task ID to delete
        user_id: User ID performing the deletion
        
    Returns:
        tuple: (success, message)
    """
    # Get task for logging
    task = get_task_by_id(task_id)
    if not task:
        return False, "Task not found."
    
    try:
        execute_db('DELETE FROM tasks WHERE id = ?', (task_id,))
        
        # Log activity
        log_activity(
            user_id,
            'delete_task',
            'task',
            task_id,
            f"Deleted task '{task['title']}'"
        )
        
        return True, "Task deleted successfully."
    except Exception as e:
        return False, f"Failed to delete task: {str(e)}"


def assign_task(task_id, assigned_to, user_id):
    """
    Assign or reassign a task to a user.
    
    Args:
        task_id: Task ID
        assigned_to: User ID to assign the task to
        user_id: User ID performing the assignment
        
    Returns:
        tuple: (success, message)
    """
    # Validate assigned user exists
    user = query_db('SELECT id, full_name FROM users WHERE id = ? AND is_active = 1', (assigned_to,), one=True)
    if not user:
        return False, "Assigned user not found or inactive."
    
    # Get task for logging
    task = get_task_by_id(task_id)
    if not task:
        return False, "Task not found."
    
    try:
        execute_db(
            'UPDATE tasks SET assigned_to = ?, updated_at = ? WHERE id = ?',
            (assigned_to, datetime.now(), task_id)
        )
        
        # Log activity
        log_activity(
            user_id,
            'assign_task',
            'task',
            task_id,
            f"Assigned task '{task['title']}' to {user['full_name']}"
        )
        
        return True, f"Task assigned to {user['full_name']}."
    except Exception as e:
        return False, f"Failed to assign task: {str(e)}"


def search_tasks(search_term, user_id=None, user_role=None):
    """
    Search tasks by title or description.
    
    Args:
        search_term: Search keyword
        user_id: Current user ID
        user_role: Current user role
        
    Returns:
        list: List of matching tasks
    """
    search_pattern = f"%{search_term}%"
    
    base_query = '''
        SELECT t.*, 
               c.company_name as client_name,
               u.username as assigned_to_username,
               u.full_name as assigned_to_name
        FROM tasks t
        JOIN clients c ON t.client_id = c.id
        LEFT JOIN users u ON t.assigned_to = u.id
        WHERE (t.title LIKE ? OR t.description LIKE ?)
    '''
    
    if user_role == 'employee':
        query = base_query + ' AND t.assigned_to = ? ORDER BY t.created_at DESC'
        return query_db(query, (search_pattern, search_pattern, user_id))
    else:
        query = base_query + ' ORDER BY t.created_at DESC'
        return query_db(query, (search_pattern, search_pattern))


def get_task_statistics(user_id=None, user_role=None):
    """
    Get task statistics.
    
    Args:
        user_id: Current user ID
        user_role: Current user role
        
    Returns:
        dict: Statistics including total, pending, completed counts
    """
    if user_role == 'admin' or user_role == 'manager':
        # All tasks statistics
        total = query_db('SELECT COUNT(*) as count FROM tasks', one=True)
        pending = query_db(
            "SELECT COUNT(*) as count FROM tasks WHERE status = 'pending'",
            one=True
        )
        in_progress = query_db(
            "SELECT COUNT(*) as count FROM tasks WHERE status = 'in_progress'",
            one=True
        )
        completed = query_db(
            "SELECT COUNT(*) as count FROM tasks WHERE status = 'completed'",
            one=True
        )
        overdue = query_db(
            "SELECT COUNT(*) as count FROM tasks WHERE due_date < ? AND status NOT IN ('completed', 'cancelled')",
            (datetime.now().date(),),
            one=True
        )
    else:
        # Only assigned tasks statistics
        total = query_db(
            'SELECT COUNT(*) as count FROM tasks WHERE assigned_to = ?',
            (user_id,),
            one=True
        )
        pending = query_db(
            "SELECT COUNT(*) as count FROM tasks WHERE assigned_to = ? AND status = 'pending'",
            (user_id,),
            one=True
        )
        in_progress = query_db(
            "SELECT COUNT(*) as count FROM tasks WHERE assigned_to = ? AND status = 'in_progress'",
            (user_id,),
            one=True
        )
        completed = query_db(
            "SELECT COUNT(*) as count FROM tasks WHERE assigned_to = ? AND status = 'completed'",
            (user_id,),
            one=True
        )
        overdue = query_db(
            "SELECT COUNT(*) as count FROM tasks WHERE assigned_to = ? AND due_date < ? AND status NOT IN ('completed', 'cancelled')",
            (user_id, datetime.now().date()),
            one=True
        )
    
    return {
        'total': total['count'] if total else 0,
        'pending': pending['count'] if pending else 0,
        'in_progress': in_progress['count'] if in_progress else 0,
        'completed': completed['count'] if completed else 0,
        'overdue': overdue['count'] if overdue else 0
    }


def get_tasks_by_priority(priority, user_id=None, user_role=None):
    """
    Get tasks filtered by priority.
    
    Args:
        priority: Task priority (low, medium, high, urgent)
        user_id: Current user ID
        user_role: Current user role
        
    Returns:
        list: List of tasks with specified priority
    """
    base_query = '''
        SELECT t.*, 
               c.company_name as client_name,
               u.username as assigned_to_username,
               u.full_name as assigned_to_name
        FROM tasks t
        JOIN clients c ON t.client_id = c.id
        LEFT JOIN users u ON t.assigned_to = u.id
        WHERE t.priority = ?
    '''
    
    if user_role == 'employee':
        query = base_query + ' AND t.assigned_to = ? ORDER BY t.created_at DESC'
        return query_db(query, (priority, user_id))
    else:
        query = base_query + ' ORDER BY t.created_at DESC'
        return query_db(query, (priority,))


def get_overdue_tasks(user_id=None, user_role=None):
    """
    Get overdue tasks.
    
    Args:
        user_id: Current user ID
        user_role: Current user role
        
    Returns:
        list: List of overdue tasks
    """
    base_query = '''
        SELECT t.*, 
               c.company_name as client_name,
               u.username as assigned_to_username,
               u.full_name as assigned_to_name
        FROM tasks t
        JOIN clients c ON t.client_id = c.id
        LEFT JOIN users u ON t.assigned_to = u.id
        WHERE t.due_date < ? AND t.status NOT IN ('completed', 'cancelled')
    '''
    
    if user_role == 'employee':
        query = base_query + ' AND t.assigned_to = ? ORDER BY t.due_date ASC'
        return query_db(query, (datetime.now().date(), user_id))
    else:
        query = base_query + ' ORDER BY t.due_date ASC'
        return query_db(query, (datetime.now().date(),))


def add_task_comment(task_id, user_id, comment):
    """
    Add a comment to a task.
    
    Args:
        task_id: Task ID
        user_id: User ID adding the comment
        comment: Comment text
        
    Returns:
        tuple: (success, comment_id or error_message)
    """
    if not comment.strip():
        return False, "Comment cannot be empty."
    
    # Verify task exists
    task = get_task_by_id(task_id)
    if not task:
        return False, "Task not found."
    
    try:
        comment_id = execute_db(
            'INSERT INTO task_comments (task_id, user_id, comment) VALUES (?, ?, ?)',
            (task_id, user_id, comment.strip())
        )
        
        # Log activity
        log_activity(
            user_id,
            'add_task_comment',
            'task',
            task_id,
            f"Added comment to task '{task['title']}'"
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
        list: List of comment dictionaries
    """
    query = '''
        SELECT tc.*, u.full_name as user_name, u.username
        FROM task_comments tc
        JOIN users u ON tc.user_id = u.id
        WHERE tc.task_id = ?
        ORDER BY tc.created_at ASC
    '''
    
    return query_db(query, (task_id,))