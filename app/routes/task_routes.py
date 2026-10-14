"""
Task Routes
Handles all task-related HTTP requests
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.controllers.task_controller import (
    create_task, get_task_by_id, get_all_tasks, update_task, delete_task,
    update_task_status, assign_task, search_tasks, get_task_statistics,
    get_tasks_by_priority, get_overdue_tasks, add_task_comment, get_task_comments
)
from app.controllers.client_controller import get_all_clients
from app.controllers.auth_controller import get_all_users
from app.utils.auth import login_required, role_required, get_current_user

task_bp = Blueprint('task', __name__, url_prefix='/tasks')


@task_bp.route('/')
@login_required
def list_tasks():
    """
    List all tasks based on user role.
    """
    user = get_current_user()
    
    # Get filter and search parameters
    status_filter = request.args.get('status')
    priority_filter = request.args.get('priority')
    client_filter = request.args.get('client_id', type=int)
    search_term = request.args.get('search')
    
    if search_term:
        # Search tasks
        tasks = search_tasks(search_term, user['id'], user['role'])
    elif priority_filter:
        # Filter by priority
        tasks = get_tasks_by_priority(priority_filter, user['id'], user['role'])
    elif request.args.get('overdue'):
        # Get overdue tasks
        tasks = get_overdue_tasks(user['id'], user['role'])
    else:
        # Get all tasks with filters
        tasks = get_all_tasks(user['id'], user['role'], status_filter, client_filter)
    
    # Get statistics
    stats = get_task_statistics(user['id'], user['role'])
    
    # Get clients for filter dropdown (only if user can see multiple clients)
    if user['role'] in ['admin', 'manager']:
        clients = get_all_clients(user['id'], user['role'])
    else:
        # Get only clients assigned to this user
        clients = get_all_clients(user['id'], user['role'])
    
    return render_template(
        'tasks/list.html',
        tasks=tasks,
        stats=stats,
        clients=clients,
        current_status=status_filter,
        current_priority=priority_filter,
        current_client=client_filter,
        search_term=search_term,
        user=user
    )


@task_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def add_task():
    """
    Add new task (admin and manager only).
    """
    user = get_current_user()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        client_id = request.form.get('client_id', type=int)
        assigned_to = request.form.get('assigned_to', type=int)
        priority = request.form.get('priority', 'medium')
        due_date = request.form.get('due_date', '').strip() or None
        reminder_date = request.form.get('reminder_date', '').strip() or None
        
        # Create task
        success, result = create_task(
            title, description, client_id, assigned_to, session['user_id'],
            priority, due_date, reminder_date
        )
        
        if success:
            flash(f'Task "{title}" created successfully!', 'success')
            return redirect(url_for('task.view_task', task_id=result))
        else:
            flash(result, 'danger')
    
    # Get clients and users for dropdowns
    clients = get_all_clients(user['id'], user['role'])
    users = get_all_users()
    
    return render_template('tasks/add.html', clients=clients, users=users, user=user)


@task_bp.route('/<int:task_id>')
@login_required
def view_task(task_id):
    """
    View task details.
    """
    user = get_current_user()
    task = get_task_by_id(task_id)
    
    if not task:
        flash('Task not found.', 'danger')
        return redirect(url_for('task.list_tasks'))
    
    # Check permission for employees
    if user['role'] == 'employee' and task['assigned_to'] != user['id']:
        flash('You do not have permission to view this task.', 'danger')
        return redirect(url_for('task.list_tasks'))
    
    # Get task comments
    comments = get_task_comments(task_id)
    
    # Get users for reassignment (admin/manager only)
    users = []
    if user['role'] in ['admin', 'manager']:
        users = get_all_users()
    
    return render_template('tasks/view.html', task=task, comments=comments, users=users, user=user)


@task_bp.route('/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def edit_task(task_id):
    """
    Edit task information (admin and manager only).
    """
    user = get_current_user()
    task = get_task_by_id(task_id)
    
    if not task:
        flash('Task not found.', 'danger')
        return redirect(url_for('task.list_tasks'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        priority = request.form.get('priority', 'medium')
        due_date = request.form.get('due_date', '').strip() or None
        reminder_date = request.form.get('reminder_date', '').strip() or None
        
        # Update task
        success, message = update_task(
            task_id, title, description, priority, due_date, reminder_date, session['user_id']
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('task.view_task', task_id=task_id))
        else:
            flash(message, 'danger')
    
    return render_template('tasks/edit.html', task=task, user=user)


@task_bp.route('/<int:task_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_task_route(task_id):
    """
    Delete task (admin only).
    """
    success, message = delete_task(task_id, session['user_id'])
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('task.list_tasks'))


@task_bp.route('/<int:task_id>/status', methods=['POST'])
@login_required
def change_status(task_id):
    """
    Change task status.
    """
    user = get_current_user()
    task = get_task_by_id(task_id)
    
    if not task:
        flash('Task not found.', 'danger')
        return redirect(url_for('task.list_tasks'))
    
    # Check permission - only assigned user, managers, and admins can change status
    if user['role'] == 'employee' and task['assigned_to'] != user['id']:
        flash('You can only change status of your assigned tasks.', 'danger')
        return redirect(url_for('task.view_task', task_id=task_id))
    
    status = request.form.get('status')
    success, message = update_task_status(task_id, status, session['user_id'])
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('task.view_task', task_id=task_id))


@task_bp.route('/<int:task_id>/assign', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def assign_task_route(task_id):
    """
    Assign or reassign task (admin and manager only).
    """
    assigned_to = request.form.get('assigned_to', type=int)
    success, message = assign_task(task_id, assigned_to, session['user_id'])
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('task.view_task', task_id=task_id))


@task_bp.route('/<int:task_id>/comment', methods=['POST'])
@login_required
def add_comment(task_id):
    """
    Add comment to task.
    """
    user = get_current_user()
    task = get_task_by_id(task_id)
    
    if not task:
        flash('Task not found.', 'danger')
        return redirect(url_for('task.list_tasks'))
    
    # Check permission for employees
    if user['role'] == 'employee' and task['assigned_to'] != user['id']:
        flash('You can only comment on your assigned tasks.', 'danger')
        return redirect(url_for('task.view_task', task_id=task_id))
    
    comment = request.form.get('comment', '').strip()
    success, result = add_task_comment(task_id, session['user_id'], comment)
    
    if success:
        flash('Comment added successfully.', 'success')
    else:
        flash(result, 'danger')
    
    return redirect(url_for('task.view_task', task_id=task_id))


@task_bp.route('/api/stats')
@login_required
def api_task_stats():
    """
    API endpoint for task statistics (for AJAX updates).
    """
    user = get_current_user()
    stats = get_task_statistics(user['id'], user['role'])
    return jsonify(stats)


@task_bp.route('/my')
@login_required
def my_tasks():
    """
    Show tasks assigned to current user.
    """
    user = get_current_user()
    
    # Get only tasks assigned to current user
    tasks = get_all_tasks(user['id'], 'employee')  # Force employee view to show only assigned
    stats = get_task_statistics(user['id'], 'employee')
    
    return render_template(
        'tasks/my_tasks.html',
        tasks=tasks,
        stats=stats,
        user=user
    )


@task_bp.route('/overdue')
@login_required
def overdue_tasks():
    """
    Show overdue tasks.
    """
    user = get_current_user()
    tasks = get_overdue_tasks(user['id'], user['role'])
    
    return render_template(
        'tasks/overdue.html',
        tasks=tasks,
        user=user
    )