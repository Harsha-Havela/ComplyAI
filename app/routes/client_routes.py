"""
Client Routes
Handles all client-related HTTP requests
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.controllers.client_controller import (
    create_client, get_client_by_id, get_all_clients, update_client,
    delete_client, update_client_status, search_clients, get_clients_by_status,
    get_client_statistics
)
from app.controllers.auth_controller import get_all_users
from app.utils.auth import login_required, role_required, get_current_user

client_bp = Blueprint('client', __name__, url_prefix='/clients')


@client_bp.route('/')
@login_required
def list_clients():
    """
    List all clients based on user role.
    """
    user = get_current_user()
    
    # Get filter and search parameters
    status_filter = request.args.get('status')
    search_term = request.args.get('search')
    
    if search_term:
        # Search clients
        clients = search_clients(search_term, user['id'], user['role'])
    elif status_filter:
        # Filter by status
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
        current_filter=status_filter,
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
    user = get_current_user()
    
    if request.method == 'POST':
        company_name = request.form.get('company_name', '').strip()
        pan = request.form.get('pan', '').strip()
        gstin = request.form.get('gstin', '').strip() or None
        business_type = request.form.get('business_type', '').strip() or None
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip() or None
        address = request.form.get('address', '').strip() or None
        city = request.form.get('city', '').strip() or None
        state = request.form.get('state', '').strip() or None
        pincode = request.form.get('pincode', '').strip() or None
        assigned_to = request.form.get('assigned_to') or None
        
        # Convert assigned_to to int if present
        if assigned_to:
            assigned_to = int(assigned_to)
        
        # Create client
        success, result = create_client(
            company_name, pan, email, session['user_id'],
            gstin, business_type, phone, address, city, state, pincode, assigned_to
        )
        
        if success:
            flash(f'Client {company_name} added successfully!', 'success')
            return redirect(url_for('client.view_client', client_id=result))
        else:
            flash(result, 'danger')
    
    # Get all users for assignment dropdown
    users = get_all_users()
    
    return render_template('clients/add.html', users=users, user=user)


@client_bp.route('/<int:client_id>')
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
    if user['role'] == 'employee' and client['assigned_to'] != user['id']:
        flash('You do not have permission to view this client.', 'danger')
        return redirect(url_for('client.list_clients'))
    
    return render_template('clients/view.html', client=client, user=user)


@client_bp.route('/<int:client_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def edit_client(client_id):
    """
    Edit client information (admin and manager only).
    """
    user = get_current_user()
    client = get_client_by_id(client_id)
    
    if not client:
        flash('Client not found.', 'danger')
        return redirect(url_for('client.list_clients'))
    
    if request.method == 'POST':
        company_name = request.form.get('company_name', '').strip()
        gstin = request.form.get('gstin', '').strip() or None
        business_type = request.form.get('business_type', '').strip() or None
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip() or None
        address = request.form.get('address', '').strip() or None
        city = request.form.get('city', '').strip() or None
        state = request.form.get('state', '').strip() or None
        pincode = request.form.get('pincode', '').strip() or None
        assigned_to = request.form.get('assigned_to') or None
        
        # Convert assigned_to to int if present
        if assigned_to:
            assigned_to = int(assigned_to)
        
        # Update client
        success, message = update_client(
            client_id, company_name, email, session['user_id'],
            gstin, business_type, phone, address, city, state, pincode, assigned_to
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('client.view_client', client_id=client_id))
        else:
            flash(message, 'danger')
    
    # Get all users for assignment dropdown
    users = get_all_users()
    
    return render_template('clients/edit.html', client=client, users=users, user=user)


@client_bp.route('/<int:client_id>/delete', methods=['POST'])
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


@client_bp.route('/<int:client_id>/status', methods=['POST'])
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
