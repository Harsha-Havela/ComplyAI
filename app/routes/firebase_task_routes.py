"""
Firebase Task Routes
Handles all task management HTTP requests with Firebase backend
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.controllers.firebase_task_controller import (
    create_task, get_task_by_id, get_all_tasks, update_task, delete_task,
    update_task_status, assign_task, search_tasks, get_task_statistics,
    get_tasks_by_priority, get_overdue_tasks, add_task_comment, get_task_comments,
    get_my_tasks, get_tasks_due_soon
)
from app.controllers.firebase_client_controller import get_all_clients
from app.controllers.firebase_auth_controller import get_users_by_role
from app.utils.firebase_auth import login_required, role_required, get_current_user

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
    client_filter = request.args.get('client_id', type=str)
    assigned_filter = request.args.get('assigned_to', type=str)
    search_term = request.args.get('search')
    
    if search_term:
        # Search tasks
        tasks = search_tasks(search_term, user['id'], user['role'])
    elif request.args.get('overdue'):
        # Get overdue tasks
        tasks = get_overdue_tasks(user['id'], user['role'])
    elif request.args.get('due_soon'):
        # Get tasks due soon
        days = int(request.args.get('days', 7))
        tasks = get_tasks_due_soon(days, user['id'], user['role'])
    else:
        # Get all tasks with filters
        tasks = get_all_tasks(
            user['id'], user['role'], status_filter, priority_filter,
            client_filter, assigned_filter
        )
    
    # Get statistics
    stats = get_task_statistics(user['id'], user['role'])
    
    # Get clients and users for filter dropdowns
    if user['role'] in ['admin', 'manager']:
        clients = get_all_clients(user['id'], user['role'])
        users = get_users_by_role('employee')
        managers = get_users_by_role('manager')
        users.extend(managers)
    else:
        clients = get_all_clients(user['id'], user['role'])
        users = []
    
    return render_template(
        'tasks/list.html',
        tasks=tasks,
        stats=stats,
        clients=clients,
        users=users,
        current_status=status_filter,
        current_priority=priority_filter,
        current_client=client_filter,
        current_assigned=assigned_filter,
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
        client_id = request.form.get('client_id', type=str)
        assigned_to = request.form.get('assigned_to', type=str)
        priority = request.form.get('priority', 'medium')
        due_date = request.form.get('due_date', '').strip() or None
        reminder_date = request.form.get('reminder_date', '').strip() or None
        
        # Create task
        success, result = create_task(
            title, description, client_id, assigned_to, priority,
            due_date, reminder_date, session['user_id']
        )
        
        if success:
            # Fire assignment notification (in-app + email)
            try:
                from app.services.notification_triggers import trigger_task_assigned
                client_label = next(
                    (c.get('company_name', '') for c in get_all_clients(user['id'], user['role'])
                     if c['id'] == client_id), ''
                )
                trigger_task_assigned(
                    task_id=result,
                    task_title=title,
                    assigned_to_id=assigned_to,
                    client_name=client_label,
                    due_date=due_date or 'Not set',
                    created_by_id=session['user_id']
                )
            except Exception:
                pass  # never block task creation due to notification failure

            flash(f'Task "{title}" created successfully!', 'success')
            return redirect(url_for('task.view_task', task_id=result))
        else:
            flash(result, 'danger')
    
    # Get clients and users for dropdowns
    clients = get_all_clients(user['id'], user['role'])
    users = get_users_by_role('employee')
    managers = get_users_by_role('manager')
    users.extend(managers)
    
    return render_template('tasks/add.html', clients=clients, users=users, user=user)


@task_bp.route('/<string:task_id>')
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
    if user['role'] == 'employee' and task.get('assigned_to') != user['id']:
        flash('You do not have permission to view this task.', 'danger')
        return redirect(url_for('task.list_tasks'))
    
    # Get task comments
    comments = get_task_comments(task_id)
    
    # Get users for reassignment (admin/manager only)
    users = []
    if user['role'] in ['admin', 'manager']:
        users = get_users_by_role('employee')
        managers = get_users_by_role('manager')
        users.extend(managers)
    
    return render_template(
        'tasks/view.html',
        task=task,
        comments=comments,
        users=users,
        user=user
    )


@task_bp.route('/<string:task_id>/edit', methods=['GET', 'POST'])
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
        client_id = request.form.get('client_id', type=str)
        assigned_to = request.form.get('assigned_to', type=str)
        priority = request.form.get('priority', 'medium')
        due_date = request.form.get('due_date', '').strip() or None
        reminder_date = request.form.get('reminder_date', '').strip() or None
        
        # Update task
        success, message = update_task(
            task_id, title, description, client_id, assigned_to,
            priority, due_date, reminder_date, session['user_id']
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('task.view_task', task_id=task_id))
        else:
            flash(message, 'danger')
    
    # Get clients and users for dropdowns
    clients = get_all_clients(user['id'], user['role'])
    users = get_users_by_role('employee')
    managers = get_users_by_role('manager')
    users.extend(managers)
    
    return render_template('tasks/edit.html', task=task, clients=clients, users=users, user=user)


@task_bp.route('/<string:task_id>/delete', methods=['POST'])
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


@task_bp.route('/<string:task_id>/status', methods=['POST'])
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
    
    # Check permission
    if (user['role'] == 'employee' and 
        task.get('assigned_to') != user['id']):
        flash('You can only update status of tasks assigned to you.', 'danger')
        return redirect(url_for('task.view_task', task_id=task_id))
    
    status = request.form.get('status')
    success, message = update_task_status(task_id, status, session['user_id'])
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    # Redirect based on source
    if request.form.get('source') == 'my_tasks':
        return redirect(url_for('task.my_tasks'))
    else:
        return redirect(url_for('task.view_task', task_id=task_id))


@task_bp.route('/<string:task_id>/assign', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def assign_task_route(task_id):
    """
    Assign task to user (admin and manager only).
    """
    assigned_to = request.form.get('assigned_to', type=str)
    success, message = assign_task(task_id, assigned_to, session['user_id'])
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('task.view_task', task_id=task_id))


@task_bp.route('/<string:task_id>/comment', methods=['POST'])
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
    if (user['role'] == 'employee' and 
        task.get('assigned_to') != user['id']):
        flash('You can only comment on tasks assigned to you.', 'danger')
        return redirect(url_for('task.view_task', task_id=task_id))
    
    comment_text = request.form.get('comment', '').strip()
    success, result = add_task_comment(task_id, comment_text, session['user_id'])
    
    if success:
        flash('Comment added successfully!', 'success')
    else:
        flash(result, 'danger')
    
    return redirect(url_for('task.view_task', task_id=task_id))


@task_bp.route('/my')
@login_required
def my_tasks():
    """
    Personal task dashboard showing only assigned tasks.
    """
    user = get_current_user()
    
    # Get status filter
    status_filter = request.args.get('status')
    
    # Debug: Print user ID for troubleshooting
    print(f"🔍 My Tasks - User ID: {user['id']}, Type: {type(user['id'])}")
    
    # Get user's assigned tasks
    tasks = get_my_tasks(user['id'], status_filter)
    
    # Debug: Print task count and assigned_to values
    print(f"📋 Found {len(tasks)} tasks for user {user['id']}")
    if tasks:
        for task in tasks[:3]:  # Show first 3 tasks
            print(f"  Task: {task.get('title')} - Assigned to: {task.get('assigned_to')}")
    
    # Get personal statistics (with error handling)
    try:
        stats = get_task_statistics(user['id'], 'employee')
    except Exception as e:
        print(f"⚠️ Stats query failed: {e}")
        stats = {
            'total': len(tasks),
            'pending': 0,
            'in_progress': 0,
            'completed': 0,
            'overdue': 0,
            'due_today': 0,
            'due_this_week': 0,
            'by_priority': {'low': 0, 'medium': 0, 'high': 0, 'urgent': 0}
        }
    
    # Get overdue tasks for user (with error handling)
    try:
        overdue_tasks = get_overdue_tasks(user['id'], 'employee')
    except Exception as e:
        print(f"⚠️ Overdue tasks query failed: {e}")
        overdue_tasks = []
    
    # Get tasks due soon (with error handling)
    try:
        due_soon_tasks = get_tasks_due_soon(7, user['id'], 'employee')
    except Exception as e:
        print(f"⚠️ Due soon tasks query failed: {e}")
        due_soon_tasks = []
    
    return render_template(
        'tasks/my_tasks.html',
        tasks=tasks,
        stats=stats,
        overdue_tasks=overdue_tasks,
        due_soon_tasks=due_soon_tasks,
        current_status=status_filter,
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


@task_bp.route('/api/stats')
@login_required
def api_task_stats():
    """
    API endpoint for task statistics (for AJAX updates).
    """
    user = get_current_user()
    stats = get_task_statistics(user['id'], user['role'])
    return jsonify(stats)