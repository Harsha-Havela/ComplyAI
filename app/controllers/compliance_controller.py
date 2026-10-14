"""
Compliance Controller
Handles all compliance tracking business logic
"""
from app.models.database import query_db, execute_db
from app.services.activity_service import log_activity
from app.utils.helpers import is_overdue
from datetime import datetime, timedelta


def create_compliance_deadline(compliance_type, description, due_date, client_id, 
                              frequency, created_by):
    """
    Create a new compliance deadline.
    
    Args:
        compliance_type: Type of compliance (GST Return, Income Tax, etc.)
        description: Description of the compliance requirement
        due_date: Due date for compliance (YYYY-MM-DD format)
        client_id: ID of the client (optional for general compliance)
        frequency: Frequency of compliance (monthly, quarterly, yearly, one_time)
        created_by: User ID creating the compliance deadline
        
    Returns:
        tuple: (success, compliance_id or error_message)
    """
    # Validate required fields
    if not all([compliance_type, due_date]):
        return False, "Compliance type and due date are required."
    
    # Validate frequency
    if frequency not in ['monthly', 'quarterly', 'yearly', 'one_time']:
        return False, "Invalid frequency. Must be one of: monthly, quarterly, yearly, one_time."
    
    # Validate due date
    try:
        due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
        if due_date_obj < datetime.now().date():
            return False, "Due date cannot be in the past."
    except ValueError:
        return False, "Invalid due date format. Use YYYY-MM-DD."
    
    # Validate client exists if provided
    if client_id:
        client = query_db('SELECT id, company_name FROM clients WHERE id = ?', (client_id,), one=True)
        if not client:
            return False, "Client not found."
    
    # Insert compliance deadline
    query = '''
        INSERT INTO compliance_deadlines 
        (compliance_type, description, due_date, client_id, frequency, created_by)
        VALUES (?, ?, ?, ?, ?, ?)
    '''
    
    try:
        compliance_id = execute_db(
            query,
            (compliance_type, description, due_date, client_id, frequency, created_by)
        )
        
        # Log activity
        client_name = client['company_name'] if client_id else 'General'
        log_activity(
            created_by,
            'create_compliance',
            'compliance',
            compliance_id,
            f"Created {compliance_type} deadline for {client_name}"
        )
        
        return True, compliance_id
    except Exception as e:
        return False, f"Failed to create compliance deadline: {str(e)}"


def get_compliance_by_id(compliance_id):
    """
    Get compliance deadline details by ID.
    
    Args:
        compliance_id: Compliance deadline ID
        
    Returns:
        dict: Compliance information with related data
    """
    query = '''
        SELECT cd.*, 
               c.company_name as client_name,
               u.username as created_by_username,
               u.full_name as created_by_name
        FROM compliance_deadlines cd
        LEFT JOIN clients c ON cd.client_id = c.id
        LEFT JOIN users u ON cd.created_by = u.id
        WHERE cd.id = ?
    '''
    
    return query_db(query, (compliance_id,), one=True)


def get_all_compliance(user_id=None, user_role=None, status=None, client_id=None,
                      compliance_type=None):
    """
    Get all compliance deadlines based on user role and filters.
    
    Args:
        user_id: Current user ID
        user_role: Current user role
        status: Filter by status (pending, completed, overdue)
        client_id: Filter by client ID
        compliance_type: Filter by compliance type
        
    Returns:
        list: List of compliance deadline dictionaries
    """
    # Base query
    base_query = '''
        SELECT cd.*, 
               c.company_name as client_name
        FROM compliance_deadlines cd
        LEFT JOIN clients c ON cd.client_id = c.id
    '''
    
    where_conditions = []
    params = []
    
    # Role-based filtering
    if user_role == 'employee':
        # Employees see compliance for their assigned clients only
        where_conditions.append('c.assigned_to = ?')
        params.append(user_id)
    
    # Status filtering
    if status:
        where_conditions.append('cd.status = ?')
        params.append(status)
    
    # Client filtering
    if client_id:
        where_conditions.append('cd.client_id = ?')
        params.append(client_id)
    
    # Compliance type filtering
    if compliance_type:
        where_conditions.append('cd.compliance_type = ?')
        params.append(compliance_type)
    
    # Build final query
    if where_conditions:
        query = base_query + ' WHERE ' + ' AND '.join(where_conditions)
    else:
        query = base_query
    
    query += ' ORDER BY cd.due_date ASC, cd.created_at DESC'
    
    return query_db(query, tuple(params))


def update_compliance(compliance_id, compliance_type, description, due_date, 
                     client_id, frequency, user_id):
    """
    Update compliance deadline information.
    
    Args:
        compliance_id: Compliance deadline ID to update
        compliance_type: Type of compliance
        description: Description
        due_date: Due date (YYYY-MM-DD)
        client_id: Client ID (optional)
        frequency: Frequency
        user_id: User ID performing the update
        
    Returns:
        tuple: (success, message)
    """
    # Validate required fields
    if not all([compliance_type, due_date]):
        return False, "Compliance type and due date are required."
    
    # Validate frequency
    if frequency not in ['monthly', 'quarterly', 'yearly', 'one_time']:
        return False, "Invalid frequency."
    
    # Validate due date
    try:
        datetime.strptime(due_date, '%Y-%m-%d').date()
    except ValueError:
        return False, "Invalid due date format. Use YYYY-MM-DD."
    
    # Validate client if provided
    if client_id:
        client = query_db('SELECT id FROM clients WHERE id = ?', (client_id,), one=True)
        if not client:
            return False, "Client not found."
    
    # Get compliance for logging
    compliance = get_compliance_by_id(compliance_id)
    if not compliance:
        return False, "Compliance deadline not found."
    
    # Update compliance
    query = '''
        UPDATE compliance_deadlines 
        SET compliance_type = ?, description = ?, due_date = ?, 
            client_id = ?, frequency = ?, updated_at = ?
        WHERE id = ?
    '''
    
    try:
        execute_db(
            query,
            (compliance_type, description, due_date, client_id, frequency,
             datetime.now(), compliance_id)
        )
        
        # Log activity
        log_activity(
            user_id,
            'update_compliance',
            'compliance',
            compliance_id,
            f"Updated {compliance_type} deadline"
        )
        
        return True, "Compliance deadline updated successfully."
    except Exception as e:
        return False, f"Failed to update compliance deadline: {str(e)}"


def update_compliance_status(compliance_id, status, user_id):
    """
    Update compliance deadline status.
    
    Args:
        compliance_id: Compliance deadline ID
        status: New status (pending, completed, overdue)
        user_id: User ID performing the update
        
    Returns:
        tuple: (success, message)
    """
    if status not in ['pending', 'completed', 'overdue']:
        return False, "Invalid status."
    
    # Get compliance for logging
    compliance = get_compliance_by_id(compliance_id)
    if not compliance:
        return False, "Compliance deadline not found."
    
    try:
        execute_db(
            'UPDATE compliance_deadlines SET status = ?, updated_at = ? WHERE id = ?',
            (status, datetime.now(), compliance_id)
        )
        
        # Log activity
        log_activity(
            user_id,
            'update_compliance_status',
            'compliance',
            compliance_id,
            f"Changed status to {status} for {compliance['compliance_type']}"
        )
        
        return True, f"Compliance status updated to {status}."
    except Exception as e:
        return False, f"Failed to update status: {str(e)}"


def delete_compliance(compliance_id, user_id):
    """
    Delete a compliance deadline (admin only).
    
    Args:
        compliance_id: Compliance deadline ID to delete
        user_id: User ID performing the deletion
        
    Returns:
        tuple: (success, message)
    """
    # Get compliance for logging
    compliance = get_compliance_by_id(compliance_id)
    if not compliance:
        return False, "Compliance deadline not found."
    
    try:
        execute_db('DELETE FROM compliance_deadlines WHERE id = ?', (compliance_id,))
        
        # Log activity
        log_activity(
            user_id,
            'delete_compliance',
            'compliance',
            compliance_id,
            f"Deleted {compliance['compliance_type']} deadline"
        )
        
        return True, "Compliance deadline deleted successfully."
    except Exception as e:
        return False, f"Failed to delete compliance deadline: {str(e)}"


def get_overdue_compliance(user_id=None, user_role=None):
    """
    Get overdue compliance deadlines.
    
    Args:
        user_id: Current user ID
        user_role: Current user role
        
    Returns:
        list: List of overdue compliance deadlines
    """
    base_query = '''
        SELECT cd.*, 
               c.company_name as client_name
        FROM compliance_deadlines cd
        LEFT JOIN clients c ON cd.client_id = c.id
        WHERE cd.due_date < ? AND cd.status = 'pending'
    '''
    
    params = [datetime.now().date()]
    
    if user_role == 'employee':
        query = base_query + ' AND c.assigned_to = ? ORDER BY cd.due_date ASC'
        params.append(user_id)
    else:
        query = base_query + ' ORDER BY cd.due_date ASC'
    
    return query_db(query, tuple(params))


def get_upcoming_compliance(days_ahead=30, user_id=None, user_role=None):
    """
    Get upcoming compliance deadlines within specified days.
    
    Args:
        days_ahead: Number of days to look ahead
        user_id: Current user ID
        user_role: Current user role
        
    Returns:
        list: List of upcoming compliance deadlines
    """
    future_date = datetime.now().date() + timedelta(days=days_ahead)
    
    base_query = '''
        SELECT cd.*, 
               c.company_name as client_name
        FROM compliance_deadlines cd
        LEFT JOIN clients c ON cd.client_id = c.id
        WHERE cd.due_date BETWEEN ? AND ? AND cd.status = 'pending'
    '''
    
    params = [datetime.now().date(), future_date]
    
    if user_role == 'employee':
        query = base_query + ' AND c.assigned_to = ? ORDER BY cd.due_date ASC'
        params.append(user_id)
    else:
        query = base_query + ' ORDER BY cd.due_date ASC'
    
    return query_db(query, tuple(params))


def get_compliance_statistics(user_id=None, user_role=None):
    """
    Get compliance statistics.
    
    Args:
        user_id: Current user ID
        user_role: Current user role
        
    Returns:
        dict: Statistics including total, pending, completed, overdue counts
    """
    base_conditions = ""
    params = []
    
    if user_role == 'employee':
        base_conditions = "JOIN clients c ON cd.client_id = c.id WHERE c.assigned_to = ?"
        params = [user_id]
    
    # Total compliance deadlines
    total_query = f"SELECT COUNT(*) as count FROM compliance_deadlines cd {base_conditions}"
    total = query_db(total_query, tuple(params), one=True)
    
    # Pending compliance
    pending_params = params + ["pending"] if params else ["pending"]
    pending_query = f"SELECT COUNT(*) as count FROM compliance_deadlines cd {base_conditions}"
    if base_conditions:
        pending_query += " AND cd.status = ?"
    else:
        pending_query += " WHERE cd.status = ?"
    pending = query_db(pending_query, tuple(pending_params), one=True)
    
    # Completed compliance
    completed_params = params + ["completed"] if params else ["completed"]
    completed_query = f"SELECT COUNT(*) as count FROM compliance_deadlines cd {base_conditions}"
    if base_conditions:
        completed_query += " AND cd.status = ?"
    else:
        completed_query += " WHERE cd.status = ?"
    completed = query_db(completed_query, tuple(completed_params), one=True)
    
    # Overdue compliance
    overdue_params = params + [datetime.now().date(), "pending"] if params else [datetime.now().date(), "pending"]
    overdue_query = f"SELECT COUNT(*) as count FROM compliance_deadlines cd {base_conditions}"
    if base_conditions:
        overdue_query += " AND cd.due_date < ? AND cd.status = ?"
    else:
        overdue_query += " WHERE cd.due_date < ? AND cd.status = ?"
    overdue = query_db(overdue_query, tuple(overdue_params), one=True)
    
    return {
        'total': total['count'] if total else 0,
        'pending': pending['count'] if pending else 0,
        'completed': completed['count'] if completed else 0,
        'overdue': overdue['count'] if overdue else 0
    }


def search_compliance(search_term, user_id=None, user_role=None):
    """
    Search compliance deadlines by type or description.
    
    Args:
        search_term: Search keyword
        user_id: Current user ID
        user_role: Current user role
        
    Returns:
        list: List of matching compliance deadlines
    """
    search_pattern = f"%{search_term}%"
    
    base_query = '''
        SELECT cd.*, 
               c.company_name as client_name
        FROM compliance_deadlines cd
        LEFT JOIN clients c ON cd.client_id = c.id
        WHERE (cd.compliance_type LIKE ? OR cd.description LIKE ?)
    '''
    
    params = [search_pattern, search_pattern]
    
    if user_role == 'employee':
        query = base_query + ' AND c.assigned_to = ? ORDER BY cd.due_date ASC'
        params.append(user_id)
    else:
        query = base_query + ' ORDER BY cd.due_date ASC'
    
    return query_db(query, tuple(params))


def get_compliance_types():
    """
    Get list of common compliance types.
    
    Returns:
        list: List of compliance type dictionaries
    """
    return [
        {'value': 'GST Return - GSTR1', 'label': 'GST Return - GSTR1'},
        {'value': 'GST Return - GSTR3B', 'label': 'GST Return - GSTR3B'},
        {'value': 'Income Tax Return', 'label': 'Income Tax Return'},
        {'value': 'TDS Return', 'label': 'TDS Return'},
        {'value': 'PF Return', 'label': 'PF Return'},
        {'value': 'ESI Return', 'label': 'ESI Return'},
        {'value': 'Annual Filing', 'label': 'Annual Filing'},
        {'value': 'Audit Report', 'label': 'Audit Report'},
        {'value': 'ROC Filing', 'label': 'ROC Filing (Registrar of Companies)'},
        {'value': 'Other', 'label': 'Other'}
    ]


def auto_generate_recurring_compliance():
    """
    Automatically generate recurring compliance deadlines.
    This should be run periodically (e.g., daily cron job).
    
    Returns:
        dict: Summary of generated compliance deadlines
    """
    generated = {'monthly': 0, 'quarterly': 0, 'yearly': 0}
    
    try:
        # Get all recurring compliance templates
        recurring = query_db(
            "SELECT * FROM compliance_deadlines WHERE frequency != 'one_time' AND status = 'completed'"
        )
        
        for compliance in recurring:
            # Calculate next due date based on frequency
            last_due_date = datetime.strptime(compliance['due_date'], '%Y-%m-%d').date()
            
            if compliance['frequency'] == 'monthly':
                next_due_date = last_due_date + timedelta(days=30)  # Approximate monthly
            elif compliance['frequency'] == 'quarterly':
                next_due_date = last_due_date + timedelta(days=90)  # Quarterly
            elif compliance['frequency'] == 'yearly':
                next_due_date = last_due_date + timedelta(days=365)  # Yearly
            
            # Check if next deadline already exists
            existing = query_db(
                "SELECT id FROM compliance_deadlines WHERE compliance_type = ? AND client_id = ? AND due_date = ?",
                (compliance['compliance_type'], compliance['client_id'], next_due_date.strftime('%Y-%m-%d')),
                one=True
            )
            
            if not existing and next_due_date >= datetime.now().date():
                # Create new compliance deadline
                execute_db(
                    '''INSERT INTO compliance_deadlines 
                       (compliance_type, description, due_date, client_id, frequency, created_by)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (compliance['compliance_type'], compliance['description'], 
                     next_due_date.strftime('%Y-%m-%d'), compliance['client_id'], 
                     compliance['frequency'], compliance['created_by'])
                )
                generated[compliance['frequency']] += 1
        
        return generated
    except Exception as e:
        return {'error': str(e)}


def mark_overdue_compliance():
    """
    Mark compliance deadlines as overdue if past due date.
    This should be run periodically (e.g., daily cron job).
    
    Returns:
        int: Number of compliance deadlines marked as overdue
    """
    try:
        result = execute_db(
            "UPDATE compliance_deadlines SET status = 'overdue' WHERE due_date < ? AND status = 'pending'",
            (datetime.now().date(),)
        )
        return result
    except Exception as e:
        return 0