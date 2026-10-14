"""
Firebase Client Routes
Handles all client management HTTP requests with Firebase backend
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.controllers.firebase_client_controller import (
    create_client, get_client_by_id, get_all_clients, update_client,
    delete_client, update_client_status, search_clients, get_clients_by_status,
    get_client_statistics, assign_client
)
from app.controllers.firebase_auth_controller import get_users_by_role
from app.utils.firebase_auth import login_required, role_required, get_current_user

client_bp = Blueprint('client', __name__, url_prefix='/clients')


@client_bp.route('/')
@login_required
def list_clients():
    """
    List all clients based on user role.
    """
    user = get_current_user()
    
    # Get filter parameters
    status_filter = request.args.get('status')
    search_term = request.args.get('search')
    
    if search_term:
        # Search clients
        clients = search_clients(search_term, user['id'], user['role'])
    elif status_filter:
        # Get clients by status
        clients = get_clients_by_status(status_filter, user['id'], user['role'])
    else:
        # Get all clients
        clients = get_all_clients(user['id'], user['role'])
    
    # Get statistics
    stats = get_client_statistics(user['id'], user['role'])
    
    return render_template(
        'clients/list.html',
        clients=clients,
        stats=stats,
        current_status=status_filter,
        search_term=search_term,
        user=user
    )


@client_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def add_client():
    """
    Add new client (admin and manager only).
    """
    if request.method == 'POST':
        company_name = request.form.get('company_name', '').strip()
        pan = request.form.get('pan', '').strip()
        gstin = request.form.get('gstin', '').strip()
        contact_person = request.form.get('contact_person', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        status = request.form.get('status', 'active')
        assigned_to = request.form.get('assigned_to', type=str) or None
        
        # Create client
        success, result = create_client(
            company_name, pan, gstin, contact_person, email, phone,
            address, status, assigned_to, session['user_id']
        )
        
        if success:
            flash(f'Client "{company_name}" created successfully!', 'success')
            return redirect(url_for('client.view_client', client_id=result))
        else:
            flash(result, 'danger')
    
    # Get users for assignment dropdown
    users = get_users_by_role('employee')
    managers = get_users_by_role('manager')
    users.extend(managers)  # Include managers in assignment options
    
    return render_template('clients/add.html', users=users)


@client_bp.route('/<string:client_id>')
@login_required
def view_client(client_id):
    """
    View client details.
    """
    user = get_current_user()
    client = get_client_by_id(client_id)
    
    if not client:
        flash('Client not found.', 'danger')
        return redirect(url_for('client.list_clients'))
    
    # Check permission for employees
    if user['role'] == 'employee' and client.get('assigned_to') != user['id']:
        flash('You do not have permission to view this client.', 'danger')
        return redirect(url_for('client.list_clients'))
    
    # Get client's tasks
    from app.controllers.firebase_task_controller import get_all_tasks
    client_tasks = get_all_tasks(user['id'], user['role'], client_id=client_id)
    
    # Get client's compliance
    from app.controllers.firebase_compliance_controller import get_all_compliance
    client_compliance = get_all_compliance(user['id'], user['role'], client_id=client_id)
    
    return render_template(
        'clients/view.html',
        client=client,
        tasks=client_tasks,
        compliance=client_compliance,
        user=user
    )


@client_bp.route('/<string:client_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def edit_client(client_id):
    """
    Edit client information (admin and manager only).
    """
    client = get_client_by_id(client_id)
    
    if not client:
        flash('Client not found.', 'danger')
        return redirect(url_for('client.list_clients'))
    
    if request.method == 'POST':
        company_name = request.form.get('company_name', '').strip()
        pan = request.form.get('pan', '').strip()
        gstin = request.form.get('gstin', '').strip()
        contact_person = request.form.get('contact_person', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        status = request.form.get('status', 'active')
        assigned_to = request.form.get('assigned_to', type=str) or None
        
        # Update client
        success, message = update_client(
            client_id, company_name, pan, gstin, contact_person, email,
            phone, address, status, assigned_to, session['user_id']
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('client.view_client', client_id=client_id))
        else:
            flash(message, 'danger')
    
    # Get users for assignment dropdown
    users = get_users_by_role('employee')
    managers = get_users_by_role('manager')
    users.extend(managers)
    
    return render_template('clients/edit.html', client=client, users=users)


@client_bp.route('/<string:client_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_client_route(client_id):
    """
    Delete client (admin only).
    """
    success, message = delete_client(client_id, session['user_id'])
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('client.list_clients'))


@client_bp.route('/<string:client_id>/status', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def change_status(client_id):
    """
    Change client status (admin and manager only).
    """
    status = request.form.get('status')
    success, message = update_client_status(client_id, status, session['user_id'])
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('client.view_client', client_id=client_id))


@client_bp.route('/<string:client_id>/assign', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def assign_client_route(client_id):
    """
    Assign client to user (admin and manager only).
    """
    assigned_to = request.form.get('assigned_to', type=str) or None
    success, message = assign_client(client_id, assigned_to, session['user_id'])
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('client.view_client', client_id=client_id))


@client_bp.route('/api/stats')
@login_required
def api_client_stats():
    """
    API endpoint for client statistics (for AJAX updates).
    """
    user = get_current_user()
    stats = get_client_statistics(user['id'], user['role'])
    return jsonify(stats)