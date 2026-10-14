"""
Compliance Routes
Handles all compliance tracking HTTP requests
"""
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.controllers.compliance_controller import (
    create_compliance_deadline, get_compliance_by_id, get_all_compliance,
    update_compliance, delete_compliance, update_compliance_status,
    get_overdue_compliance, get_upcoming_compliance, get_compliance_statistics,
    search_compliance, get_compliance_types, auto_generate_recurring_compliance,
    mark_overdue_compliance
)
from app.controllers.client_controller import get_all_clients
from app.utils.auth import login_required, role_required, get_current_user

compliance_bp = Blueprint('compliance', __name__, url_prefix='/compliance')


@compliance_bp.route('/')
@login_required
def list_compliance():
    """
    List all compliance deadlines based on user role.
    """
    user = get_current_user()
    
    # Get filter and search parameters
    status_filter = request.args.get('status')
    compliance_type_filter = request.args.get('compliance_type')
    client_filter = request.args.get('client_id', type=int)
    search_term = request.args.get('search')
    
    if search_term:
        # Search compliance
        compliance_deadlines = search_compliance(search_term, user['id'], user['role'])
    elif request.args.get('overdue'):
        # Get overdue compliance
        compliance_deadlines = get_overdue_compliance(user['id'], user['role'])
    elif request.args.get('upcoming'):
        # Get upcoming compliance (next 30 days)
        days_ahead = int(request.args.get('days', 30))
        compliance_deadlines = get_upcoming_compliance(days_ahead, user['id'], user['role'])
    else:
        # Get all compliance with filters
        compliance_deadlines = get_all_compliance(
            user['id'], user['role'], status_filter, client_filter, compliance_type_filter
        )
    
    # Get statistics
    stats = get_compliance_statistics(user['id'], user['role'])
    
    # Get clients for filter dropdown
    if user['role'] in ['admin', 'manager']:
        clients = get_all_clients(user['id'], user['role'])
    else:
        clients = get_all_clients(user['id'], user['role'])
    
    # Get compliance types for filter
    compliance_types = get_compliance_types()
    
    return render_template(
        'compliance/list.html',
        compliance_deadlines=compliance_deadlines,
        stats=stats,
        clients=clients,
        compliance_types=compliance_types,
        current_status=status_filter,
        current_type=compliance_type_filter,
        current_client=client_filter,
        search_term=search_term,
        user=user
    )


@compliance_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def add_compliance():
    """
    Add new compliance deadline (admin and manager only).
    """
    user = get_current_user()
    
    if request.method == 'POST':
        compliance_type = request.form.get('compliance_type', '').strip()
        description = request.form.get('description', '').strip()
        due_date = request.form.get('due_date', '').strip()
        client_id = request.form.get('client_id', type=int) or None
        frequency = request.form.get('frequency', 'one_time')
        
        # Create compliance deadline
        success, result = create_compliance_deadline(
            compliance_type, description, due_date, client_id, frequency, session['user_id']
        )
        
        if success:
            flash(f'Compliance deadline "{compliance_type}" created successfully!', 'success')
            return redirect(url_for('compliance.view_compliance', compliance_id=result))
        else:
            flash(result, 'danger')
    
    # Get clients and compliance types for dropdowns
    clients = get_all_clients(user['id'], user['role'])
    compliance_types = get_compliance_types()
    
    return render_template(
        'compliance/add.html', 
        clients=clients, 
        compliance_types=compliance_types, 
        user=user
    )


@compliance_bp.route('/<int:compliance_id>')
@login_required
def view_compliance(compliance_id):
    """
    View compliance deadline details.
    """
    user = get_current_user()
    compliance = get_compliance_by_id(compliance_id)
    
    if not compliance:
        flash('Compliance deadline not found.', 'danger')
        return redirect(url_for('compliance.list_compliance'))
    
    # Check permission for employees
    if user['role'] == 'employee' and compliance['client_id']:
        # Check if client is assigned to this employee
        from app.controllers.client_controller import get_client_by_id
        client = get_client_by_id(compliance['client_id'])
        if client and client['assigned_to'] != user['id']:
            flash('You do not have permission to view this compliance deadline.', 'danger')
            return redirect(url_for('compliance.list_compliance'))
    
    return render_template('compliance/view.html', compliance=compliance, user=user)


@compliance_bp.route('/<int:compliance_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def edit_compliance(compliance_id):
    """
    Edit compliance deadline information (admin and manager only).
    """
    user = get_current_user()
    compliance = get_compliance_by_id(compliance_id)
    
    if not compliance:
        flash('Compliance deadline not found.', 'danger')
        return redirect(url_for('compliance.list_compliance'))
    
    if request.method == 'POST':
        compliance_type = request.form.get('compliance_type', '').strip()
        description = request.form.get('description', '').strip()
        due_date = request.form.get('due_date', '').strip()
        client_id = request.form.get('client_id', type=int) or None
        frequency = request.form.get('frequency', 'one_time')
        
        # Update compliance
        success, message = update_compliance(
            compliance_id, compliance_type, description, due_date, 
            client_id, frequency, session['user_id']
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('compliance.view_compliance', compliance_id=compliance_id))
        else:
            flash(message, 'danger')
    
    # Get clients and compliance types for dropdowns
    clients = get_all_clients(user['id'], user['role'])
    compliance_types = get_compliance_types()
    
    return render_template(
        'compliance/edit.html', 
        compliance=compliance, 
        clients=clients, 
        compliance_types=compliance_types, 
        user=user
    )


@compliance_bp.route('/<int:compliance_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_compliance_route(compliance_id):
    """
    Delete compliance deadline (admin only).
    """
    success, message = delete_compliance(compliance_id, session['user_id'])
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('compliance.list_compliance'))


@compliance_bp.route('/<int:compliance_id>/status', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def change_status(compliance_id):
    """
    Change compliance deadline status (admin and manager only).
    """
    status = request.form.get('status')
    success, message = update_compliance_status(compliance_id, status, session['user_id'])
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('compliance.view_compliance', compliance_id=compliance_id))


@compliance_bp.route('/overdue')
@login_required
def overdue_compliance():
    """
    Show overdue compliance deadlines.
    """
    user = get_current_user()
    compliance_deadlines = get_overdue_compliance(user['id'], user['role'])
    
    return render_template(
        'compliance/overdue.html',
        compliance_deadlines=compliance_deadlines,
        user=user
    )


@compliance_bp.route('/upcoming')
@login_required
def upcoming_compliance():
    """
    Show upcoming compliance deadlines.
    """
    user = get_current_user()
    days_ahead = int(request.args.get('days', 30))
    compliance_deadlines = get_upcoming_compliance(days_ahead, user['id'], user['role'])
    
    return render_template(
        'compliance/upcoming.html',
        compliance_deadlines=compliance_deadlines,
        days_ahead=days_ahead,
        user=user
    )


@compliance_bp.route('/calendar')
@login_required
def compliance_calendar():
    """
    Show compliance deadlines in calendar view.
    """
    user = get_current_user()
    
    # Get all pending compliance for calendar
    compliance_deadlines = get_all_compliance(user['id'], user['role'], status='pending')
    
    # Format data for calendar
    calendar_data = []
    for compliance in compliance_deadlines:
        calendar_data.append({
            'id': compliance['id'],
            'title': compliance['compliance_type'],
            'date': compliance['due_date'],
            'client': compliance['client_name'] or 'General',
            'frequency': compliance['frequency'],
            'overdue': compliance['due_date'] < str(datetime.now().date()) if compliance['due_date'] else False
        })
    
    return render_template(
        'compliance/calendar.html',
        calendar_data=calendar_data,
        user=user
    )


@compliance_bp.route('/api/stats')
@login_required
def api_compliance_stats():
    """
    API endpoint for compliance statistics (for AJAX updates).
    """
    user = get_current_user()
    stats = get_compliance_statistics(user['id'], user['role'])
    return jsonify(stats)


@compliance_bp.route('/api/generate-recurring', methods=['POST'])
@login_required
@role_required('admin')
def api_generate_recurring():
    """
    API endpoint to generate recurring compliance deadlines (admin only).
    """
    result = auto_generate_recurring_compliance()
    
    if 'error' in result:
        return jsonify({'success': False, 'error': result['error']}), 500
    
    total_generated = sum(result.values())
    return jsonify({
        'success': True, 
        'generated': total_generated,
        'details': result
    })


@compliance_bp.route('/api/mark-overdue', methods=['POST'])
@login_required
@role_required('admin')
def api_mark_overdue():
    """
    API endpoint to mark overdue compliance deadlines (admin only).
    """
    count = mark_overdue_compliance()
    return jsonify({
        'success': True,
        'marked_overdue': count
    })


@compliance_bp.route('/dashboard')
@login_required
def compliance_dashboard():
    """
    Compliance dashboard with overview and quick actions.
    """
    user = get_current_user()
    
    # Get statistics
    stats = get_compliance_statistics(user['id'], user['role'])
    
    # Get upcoming deadlines (next 7 days)
    upcoming = get_upcoming_compliance(7, user['id'], user['role'])
    
    # Get overdue deadlines
    overdue = get_overdue_compliance(user['id'], user['role'])
    
    return render_template(
        'compliance/dashboard.html',
        stats=stats,
        upcoming=upcoming,
        overdue=overdue,
        user=user
    )