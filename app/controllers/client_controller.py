"""
Client Controller
Handles all client management business logic
"""
from app.models.database import query_db, execute_db
from app.utils.validators import validate_email, validate_pan, validate_gstin, validate_phone
from app.services.activity_service import log_activity
from datetime import datetime


def create_client(company_name, pan, email, created_by, gstin=None, business_type=None,
                  phone=None, address=None, city=None, state=None, pincode=None,
                  assigned_to=None):
    """
    Create a new client.
    
    Args:
        company_name: Company name
        pan: PAN number (required)
        email: Email address
        created_by: User ID creating the client
        gstin: GSTIN number (optional)
        business_type: Type of business
        phone: Phone number
        address: Physical address
        city: City
        state: State
        pincode: PIN code
        assigned_to: User ID to assign client to
        
    Returns:
        tuple: (success, client_id or error_message)
    """
    # Validate required fields
    if not all([company_name, pan, email]):
        return False, "Company name, PAN, and email are required."
    
    # Validate PAN
    if not validate_pan(pan):
        return False, "Invalid PAN format. Expected format: AAAAA9999A"
    
    # Validate GSTIN if provided
    if gstin and not validate_gstin(gstin):
        return False, "Invalid GSTIN format. Expected format: 99AAAAA9999A9Z9"
    
    # Validate email
    if not validate_email(email):
        return False, "Invalid email address format."
    
    # Validate phone if provided
    if phone and not validate_phone(phone):
        return False, "Invalid phone number format."
    
    # Check if PAN already exists
    existing = query_db(
        'SELECT id, company_name FROM clients WHERE pan = ?',
        (pan.upper(),),
        one=True
    )
    if existing:
        return False, f"PAN already registered for {existing['company_name']}."
    
    # Check if GSTIN already exists
    if gstin:
        existing = query_db(
            'SELECT id, company_name FROM clients WHERE gstin = ?',
            (gstin.upper(),),
            one=True
        )
        if existing:
            return False, f"GSTIN already registered for {existing['company_name']}."
    
    # Insert client
    query = '''
        INSERT INTO clients 
        (company_name, pan, gstin, business_type, email, phone, 
         address, city, state, pincode, assigned_to, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    
    try:
        client_id = execute_db(
            query,
            (company_name, pan.upper(), gstin.upper() if gstin else None,
             business_type, email, phone, address, city, state, pincode,
             assigned_to, created_by)
        )
        
        # Log activity
        log_activity(
            created_by,
            'create_client',
            'client',
            client_id,
            f"Created client: {company_name}"
        )
        
        return True, client_id
    except Exception as e:
        return False, f"Failed to create client: {str(e)}"


def get_client_by_id(client_id):
    """
    Get client details by ID.
    
    Args:
        client_id: Client ID
        
    Returns:
        dict: Client information with assigned user details
    """
    query = '''
        SELECT c.*, 
               u1.username as assigned_to_username,
               u1.full_name as assigned_to_name,
               u2.username as created_by_username,
               u2.full_name as created_by_name
        FROM clients c
        LEFT JOIN users u1 ON c.assigned_to = u1.id
        LEFT JOIN users u2 ON c.created_by = u2.id
        WHERE c.id = ?
    '''
    
    return query_db(query, (client_id,), one=True)


def get_all_clients(user_id=None, user_role=None):
    """
    Get all clients based on user role.
    
    Args:
        user_id: Current user ID
        user_role: Current user role
        
    Returns:
        list: List of client dictionaries
    """
    if user_role == 'admin' or user_role == 'manager':
        # Admins and managers see all clients
        query = '''
            SELECT c.*, 
                   u.username as assigned_to_username,
                   u.full_name as assigned_to_name
            FROM clients c
            LEFT JOIN users u ON c.assigned_to = u.id
            ORDER BY c.created_at DESC
        '''
        return query_db(query)
    else:
        # Employees see only their assigned clients
        query = '''
            SELECT c.*, 
                   u.username as assigned_to_username,
                   u.full_name as assigned_to_name
            FROM clients c
            LEFT JOIN users u ON c.assigned_to = u.id
            WHERE c.assigned_to = ?
            ORDER BY c.created_at DESC
        '''
        return query_db(query, (user_id,))


def update_client(client_id, company_name, email, user_id, gstin=None,
                  business_type=None, phone=None, address=None, city=None,
                  state=None, pincode=None, assigned_to=None):
    """
    Update client information.
    
    Args:
        client_id: Client ID to update
        company_name: Company name
        email: Email address
        user_id: User ID performing the update
        gstin: GSTIN number (optional)
        business_type: Type of business
        phone: Phone number
        address: Physical address
        city: City
        state: State
        pincode: PIN code
        assigned_to: User ID to assign client to
        
    Returns:
        tuple: (success, message)
    """
    # Validate required fields
    if not all([company_name, email]):
        return False, "Company name and email are required."
    
    # Validate GSTIN if provided
    if gstin and not validate_gstin(gstin):
        return False, "Invalid GSTIN format."
    
    # Validate email
    if not validate_email(email):
        return False, "Invalid email address format."
    
    # Validate phone if provided
    if phone and not validate_phone(phone):
        return False, "Invalid phone number format."
    
    # Check if GSTIN already exists for another client
    if gstin:
        existing = query_db(
            'SELECT id FROM clients WHERE gstin = ? AND id != ?',
            (gstin.upper(), client_id),
            one=True
        )
        if existing:
            return False, "GSTIN already registered for another client."
    
    # Update client
    query = '''
        UPDATE clients 
        SET company_name = ?, gstin = ?, business_type = ?, email = ?, 
            phone = ?, address = ?, city = ?, state = ?, pincode = ?,
            assigned_to = ?, updated_at = ?
        WHERE id = ?
    '''
    
    try:
        execute_db(
            query,
            (company_name, gstin.upper() if gstin else None, business_type,
             email, phone, address, city, state, pincode, assigned_to,
             datetime.now(), client_id)
        )
        
        # Log activity
        log_activity(
            user_id,
            'update_client',
            'client',
            client_id,
            f"Updated client: {company_name}"
        )
        
        return True, "Client updated successfully."
    except Exception as e:
        return False, f"Failed to update client: {str(e)}"


def delete_client(client_id, user_id):
    """
    Delete a client (admin only).
    
    Args:
        client_id: Client ID to delete
        user_id: User ID performing the deletion
        
    Returns:
        tuple: (success, message)
    """
    # Get client name for logging
    client = get_client_by_id(client_id)
    if not client:
        return False, "Client not found."
    
    try:
        execute_db('DELETE FROM clients WHERE id = ?', (client_id,))
        
        # Log activity
        log_activity(
            user_id,
            'delete_client',
            'client',
            client_id,
            f"Deleted client: {client['company_name']}"
        )
        
        return True, "Client deleted successfully."
    except Exception as e:
        return False, f"Failed to delete client: {str(e)}"


def update_client_status(client_id, status, user_id):
    """
    Update client status.
    
    Args:
        client_id: Client ID
        status: New status (active, inactive, suspended)
        user_id: User ID performing the update
        
    Returns:
        tuple: (success, message)
    """
    if status not in ['active', 'inactive', 'suspended']:
        return False, "Invalid status."
    
    # Get client name for logging
    client = get_client_by_id(client_id)
    if not client:
        return False, "Client not found."
    
    try:
        execute_db(
            'UPDATE clients SET status = ?, updated_at = ? WHERE id = ?',
            (status, datetime.now(), client_id)
        )
        
        # Log activity
        log_activity(
            user_id,
            'update_client_status',
            'client',
            client_id,
            f"Changed status to {status} for {client['company_name']}"
        )
        
        return True, f"Client status updated to {status}."
    except Exception as e:
        return False, f"Failed to update status: {str(e)}"


def search_clients(search_term, user_id=None, user_role=None):
    """
    Search clients by name, PAN, or GSTIN.
    
    Args:
        search_term: Search keyword
        user_id: Current user ID
        user_role: Current user role
        
    Returns:
        list: List of matching clients
    """
    search_pattern = f"%{search_term}%"
    
    if user_role == 'admin' or user_role == 'manager':
        # Search all clients
        query = '''
            SELECT c.*, 
                   u.username as assigned_to_username,
                   u.full_name as assigned_to_name
            FROM clients c
            LEFT JOIN users u ON c.assigned_to = u.id
            WHERE c.company_name LIKE ? OR c.pan LIKE ? OR c.gstin LIKE ?
            ORDER BY c.company_name
        '''
        return query_db(query, (search_pattern, search_pattern, search_pattern))
    else:
        # Search only assigned clients
        query = '''
            SELECT c.*, 
                   u.username as assigned_to_username,
                   u.full_name as assigned_to_name
            FROM clients c
            LEFT JOIN users u ON c.assigned_to = u.id
            WHERE c.assigned_to = ? 
              AND (c.company_name LIKE ? OR c.pan LIKE ? OR c.gstin LIKE ?)
            ORDER BY c.company_name
        '''
        return query_db(query, (user_id, search_pattern, search_pattern, search_pattern))


def get_clients_by_status(status, user_id=None, user_role=None):
    """
    Get clients filtered by status.
    
    Args:
        status: Client status (active, inactive, suspended)
        user_id: Current user ID
        user_role: Current user role
        
    Returns:
        list: List of clients with specified status
    """
    if user_role == 'admin' or user_role == 'manager':
        query = '''
            SELECT c.*, 
                   u.username as assigned_to_username,
                   u.full_name as assigned_to_name
            FROM clients c
            LEFT JOIN users u ON c.assigned_to = u.id
            WHERE c.status = ?
            ORDER BY c.created_at DESC
        '''
        return query_db(query, (status,))
    else:
        query = '''
            SELECT c.*, 
                   u.username as assigned_to_username,
                   u.full_name as assigned_to_name
            FROM clients c
            LEFT JOIN users u ON c.assigned_to = u.id
            WHERE c.assigned_to = ? AND c.status = ?
            ORDER BY c.created_at DESC
        '''
        return query_db(query, (user_id, status))


def get_client_statistics(user_id=None, user_role=None):
    """
    Get client statistics.
    
    Args:
        user_id: Current user ID
        user_role: Current user role
        
    Returns:
        dict: Statistics including total, active, inactive counts
    """
    if user_role == 'admin' or user_role == 'manager':
        # All clients statistics
        total = query_db('SELECT COUNT(*) as count FROM clients', one=True)
        active = query_db(
            "SELECT COUNT(*) as count FROM clients WHERE status = 'active'",
            one=True
        )
        inactive = query_db(
            "SELECT COUNT(*) as count FROM clients WHERE status = 'inactive'",
            one=True
        )
        suspended = query_db(
            "SELECT COUNT(*) as count FROM clients WHERE status = 'suspended'",
            one=True
        )
    else:
        # Only assigned clients statistics
        total = query_db(
            'SELECT COUNT(*) as count FROM clients WHERE assigned_to = ?',
            (user_id,),
            one=True
        )
        active = query_db(
            "SELECT COUNT(*) as count FROM clients WHERE assigned_to = ? AND status = 'active'",
            (user_id,),
            one=True
        )
        inactive = query_db(
            "SELECT COUNT(*) as count FROM clients WHERE assigned_to = ? AND status = 'inactive'",
            (user_id,),
            one=True
        )
        suspended = query_db(
            "SELECT COUNT(*) as count FROM clients WHERE assigned_to = ? AND status = 'suspended'",
            (user_id,),
            one=True
        )
    
    return {
        'total': total['count'] if total else 0,
        'active': active['count'] if active else 0,
        'inactive': inactive['count'] if inactive else 0,
        'suspended': suspended['count'] if suspended else 0
    }
