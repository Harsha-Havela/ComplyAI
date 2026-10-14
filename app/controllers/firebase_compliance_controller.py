"""
Firebase Compliance Controller
Handles all compliance tracking business logic with Firestore
"""
from datetime import datetime, timedelta
from app.models.firebase_database import (
    Collections, create_document, get_document, update_document,
    delete_document, query_documents, search_documents, count_documents
)
from app.services.firebase_activity_service import log_activity


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
    client = None
    if client_id:
        client = get_document(Collections.CLIENTS, client_id)
        if not client:
            return False, "Client not found."
    
    # Create compliance deadline document
    compliance_data = {
        'compliance_type': compliance_type,
        'description': description,
        'due_date': due_date,
        'client_id': str(client_id) if client_id else None,
        'frequency': frequency,
        'status': 'pending',
        'reminder_sent': False,
        'created_by': str(created_by),
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    
    try:
        compliance_id = create_document(Collections.COMPLIANCE, compliance_data)
        
        # Log activity
        client_name = client['company_name'] if client else 'General'
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
    compliance = get_document(Collections.COMPLIANCE, compliance_id)
    
    if compliance:
        # Enrich with related information
        # Client information
        if compliance.get('client_id'):
            client = get_document(Collections.CLIENTS, compliance['client_id'])
            if client:
                compliance['client_name'] = client.get('company_name')
        
        # Creator information
        if compliance.get('created_by'):
            creator = get_document(Collections.USERS, compliance['created_by'])
            if creator:
                compliance['created_by_username'] = creator.get('username')
                compliance['created_by_name'] = creator.get('full_name')
    
    return compliance


def get_all_compliance(user_id=None, user_role=None, status=None, client_id=None,
                      compliance_type=None, limit=None):
    """
    Get all compliance deadlines based on user role and filters.
    
    Args:
        user_id: Current user ID
        user_role: Current user role
        status: Filter by status (pending, completed, overdue)
        client_id: Filter by client ID
        compliance_type: Filter by compliance type
        limit: Optional limit
        
    Returns:
        list: List of compliance deadline dictionaries
    """
    filters = []
    
    # Role-based filtering
    if user_role == 'employee':
        # Employees see compliance for their assigned clients only
        # First get their assigned clients
        assigned_clients = query_documents(
            Collections.CLIENTS,
            filters=[('assigned_to', '==', str(user_id))]
        )
        
        if assigned_clients:
            client_ids = [client['id'] for client in assigned_clients]
            # Note: Firestore doesn't support SQL-like IN queries directly
            # We'll need to handle this differently or get all and filter client-side
            
            # For now, get all compliance and filter client-side
            all_compliance = query_documents(Collections.COMPLIANCE)
            
            filtered_compliance = []
            for compliance in all_compliance:
                # Include if assigned to employee's clients or general compliance
                if (not compliance.get('client_id') or 
                    compliance.get('client_id') in client_ids):
                    filtered_compliance.append(compliance)
            
            # Apply additional filters
            if status:
                filtered_compliance = [c for c in filtered_compliance if c.get('status') == status]
            if client_id:
                filtered_compliance = [c for c in filtered_compliance if c.get('client_id') == str(client_id)]
            if compliance_type:
                filtered_compliance = [c for c in filtered_compliance if c.get('compliance_type') == compliance_type]
            
            return filtered_compliance[:limit] if limit else filtered_compliance
        else:
            # No assigned clients, return empty list
            return []
    
    # For admin/manager - apply filters directly
    if status:
        filters.append(('status', '==', status))
    
    if client_id:
        filters.append(('client_id', '==', str(client_id)))
    
    if compliance_type:
        filters.append(('compliance_type', '==', compliance_type))
    
    compliance_list = query_documents(
        Collections.COMPLIANCE,
        filters=filters if filters else None,
        limit=limit
    )
    
    # Enrich with client information
    enriched_compliance = []
    for compliance in compliance_list:
        if compliance.get('client_id'):
            client = get_document(Collections.CLIENTS, compliance['client_id'])
            if client:
                compliance['client_name'] = client.get('company_name')
        enriched_compliance.append(compliance)
    
    return enriched_compliance


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
        client = get_document(Collections.CLIENTS, client_id)
        if not client:
            return False, "Client not found."
    
    # Get compliance for logging
    compliance = get_document(Collections.COMPLIANCE, compliance_id)
    if not compliance:
        return False, "Compliance deadline not found."
    
    # Update compliance
    updated_data = {
        'compliance_type': compliance_type,
        'description': description,
        'due_date': due_date,
        'client_id': str(client_id) if client_id else None,
        'frequency': frequency,
        'updated_at': datetime.now()
    }
    
    try:
        update_document(Collections.COMPLIANCE, compliance_id, updated_data)
        
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
    compliance = get_document(Collections.COMPLIANCE, compliance_id)
    if not compliance:
        return False, "Compliance deadline not found."
    
    try:
        update_document(Collections.COMPLIANCE, compliance_id, {
            'status': status,
            'updated_at': datetime.now()
        })
        
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
    compliance = get_document(Collections.COMPLIANCE, compliance_id)
    if not compliance:
        return False, "Compliance deadline not found."
    
    try:
        delete_document(Collections.COMPLIANCE, compliance_id)
        
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
    current_date = datetime.now().date().strftime('%Y-%m-%d')
    
    # Get all pending compliance
    all_compliance = get_all_compliance(user_id, user_role, status='pending')
    
    # Filter for overdue items
    overdue_compliance = []
    for compliance in all_compliance:
        if compliance.get('due_date') and compliance['due_date'] < current_date:
            overdue_compliance.append(compliance)
    
    # Sort by due date (most overdue first)
    overdue_compliance.sort(key=lambda x: x['due_date'])
    
    return overdue_compliance


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
    current_date = datetime.now().date()
    future_date = current_date + timedelta(days=days_ahead)
    
    current_date_str = current_date.strftime('%Y-%m-%d')
    future_date_str = future_date.strftime('%Y-%m-%d')
    
    # Get all pending compliance
    all_compliance = get_all_compliance(user_id, user_role, status='pending')
    
    # Filter for upcoming items
    upcoming_compliance = []
    for compliance in all_compliance:
        if (compliance.get('due_date') and 
            current_date_str <= compliance['due_date'] <= future_date_str):
            upcoming_compliance.append(compliance)
    
    # Sort by due date
    upcoming_compliance.sort(key=lambda x: x['due_date'])
    
    return upcoming_compliance


def get_compliance_statistics(user_id=None, user_role=None):
    """
    Get compliance statistics.
    
    Args:
        user_id: Current user ID
        user_role: Current user role
        
    Returns:
        dict: Statistics including total, pending, completed, overdue counts
    """
    # Get all compliance for this user's scope
    all_compliance = get_all_compliance(user_id, user_role)
    
    stats = {
        'total': len(all_compliance),
        'pending': 0,
        'completed': 0,
        'overdue': 0
    }
    
    current_date = datetime.now().date().strftime('%Y-%m-%d')
    
    for compliance in all_compliance:
        status = compliance.get('status', 'pending')
        
        if status == 'completed':
            stats['completed'] += 1
        elif status == 'pending':
            stats['pending'] += 1
            
            # Check if overdue
            if (compliance.get('due_date') and 
                compliance['due_date'] < current_date):
                stats['overdue'] += 1
    
    return stats


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
    results = []
    
    # Search by compliance type
    type_results = search_documents(Collections.COMPLIANCE, 'compliance_type', search_term)
    results.extend(type_results)
    
    # Search by description
    desc_results = search_documents(Collections.COMPLIANCE, 'description', search_term)
    results.extend(desc_results)
    
    # Remove duplicates and apply role-based filtering
    seen_ids = set()
    unique_results = []
    
    for compliance in results:
        if compliance['id'] not in seen_ids:
            seen_ids.add(compliance['id'])
            
            # Apply role-based filtering
            if user_role == 'employee':
                # Check if compliance is for assigned client
                if compliance.get('client_id'):
                    client = get_document(Collections.CLIENTS, compliance['client_id'])
                    if client and client.get('assigned_to') == str(user_id):
                        unique_results.append(compliance)
                else:
                    # General compliance - include for all
                    unique_results.append(compliance)
            else:
                unique_results.append(compliance)
    
    # Enrich with client information
    for compliance in unique_results:
        if compliance.get('client_id'):
            client = get_document(Collections.CLIENTS, compliance['client_id'])
            if client:
                compliance['client_name'] = client.get('company_name')
    
    return unique_results


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
        # Get all completed recurring compliance
        all_compliance = query_documents(Collections.COMPLIANCE)
        
        recurring_compliance = [
            c for c in all_compliance 
            if c.get('frequency') != 'one_time' and c.get('status') == 'completed'
        ]
        
        for compliance in recurring_compliance:
            # Calculate next due date based on frequency
            last_due_date = datetime.strptime(compliance['due_date'], '%Y-%m-%d').date()
            
            if compliance['frequency'] == 'monthly':
                next_due_date = last_due_date + timedelta(days=30)  # Approximate monthly
            elif compliance['frequency'] == 'quarterly':
                next_due_date = last_due_date + timedelta(days=90)  # Quarterly
            elif compliance['frequency'] == 'yearly':
                next_due_date = last_due_date + timedelta(days=365)  # Yearly
            
            # Check if next deadline already exists
            existing = query_documents(
                Collections.COMPLIANCE,
                filters=[
                    ('compliance_type', '==', compliance['compliance_type']),
                    ('client_id', '==', compliance.get('client_id')),
                    ('due_date', '==', next_due_date.strftime('%Y-%m-%d'))
                ]
            )
            
            if not existing and next_due_date >= datetime.now().date():
                # Create new compliance deadline
                new_compliance_data = {
                    'compliance_type': compliance['compliance_type'],
                    'description': compliance['description'],
                    'due_date': next_due_date.strftime('%Y-%m-%d'),
                    'client_id': compliance.get('client_id'),
                    'frequency': compliance['frequency'],
                    'status': 'pending',
                    'reminder_sent': False,
                    'created_by': compliance['created_by'],
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                }
                
                create_document(Collections.COMPLIANCE, new_compliance_data)
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
        current_date = datetime.now().date().strftime('%Y-%m-%d')
        
        # Get all pending compliance
        pending_compliance = query_documents(
            Collections.COMPLIANCE,
            filters=[('status', '==', 'pending')]
        )
        
        marked_count = 0
        for compliance in pending_compliance:
            if (compliance.get('due_date') and 
                compliance['due_date'] < current_date):
                
                update_document(Collections.COMPLIANCE, compliance['id'], {
                    'status': 'overdue',
                    'updated_at': datetime.now()
                })
                marked_count += 1
        
        return marked_count
    except Exception as e:
        print(f"Error marking overdue compliance: {e}")
        return 0