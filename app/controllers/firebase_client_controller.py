"""
Firebase Client Controller
Handles all client management business logic with Firestore
"""
import re
from datetime import datetime
from app.models.firebase_database import (
    Collections, create_document, get_document, update_document,
    delete_document, query_documents, search_documents, count_documents
)
from app.services.firebase_activity_service import log_activity


def validate_pan(pan):
    """Validate PAN number format."""
    pan_pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
    return bool(re.match(pan_pattern, pan.upper())) if pan else False


def validate_gstin(gstin):
    """Validate GSTIN number format."""
    gstin_pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$'
    return bool(re.match(gstin_pattern, gstin.upper())) if gstin else False


def create_client(company_name, pan, gstin, contact_person, email, phone, 
                 address, status, assigned_to, created_by):
    """
    Create a new client.
    
    Args:
        company_name: Client company name
        pan: PAN number (required)
        gstin: GSTIN number (optional)
        contact_person: Primary contact person
        email: Contact email
        phone: Contact phone
        address: Company address
        status: Client status (active, inactive, suspended)
        assigned_to: User ID assigned to manage this client
        created_by: User ID creating the client
        
    Returns:
        tuple: (success, client_id or error_message)
    """
    # Validate required fields
    if not all([company_name, pan]):
        return False, "Company name and PAN are required."
    
    # Validate PAN format
    if not validate_pan(pan):
        return False, "Invalid PAN format. Expected format: AAAAA9999A"
    
    # Validate GSTIN format if provided
    if gstin and not validate_gstin(gstin):
        return False, "Invalid GSTIN format. Expected format: 99AAAAA9999A9Z9"
    
    # Validate status
    if status not in ['active', 'inactive', 'suspended']:
        return False, "Invalid status. Must be active, inactive, or suspended."
    
    # Check if PAN already exists
    existing_pan = query_documents(
        Collections.CLIENTS,
        filters=[('pan', '==', pan.upper())]
    )
    
    if existing_pan:
        return False, "PAN number already exists in the system."
    
    # Check if GSTIN already exists (if provided)
    if gstin:
        existing_gstin = query_documents(
            Collections.CLIENTS,
            filters=[('gstin', '==', gstin.upper())]
        )
        
        if existing_gstin:
            return False, "GSTIN already exists in the system."
    
    # Validate assigned user exists
    if assigned_to:
        assigned_user = get_document(Collections.USERS, assigned_to)
        if not assigned_user:
            return False, "Assigned user not found."
    
    # Create client document
    client_data = {
        'company_name': company_name,
        'pan': pan.upper(),
        'gstin': gstin.upper() if gstin else None,
        'contact_person': contact_person,
        'email': email,
        'phone': phone,
        'address': address,
        'status': status,
        'assigned_to': str(assigned_to) if assigned_to else None,
        'created_by': str(created_by),
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    
    try:
        client_id = create_document(Collections.CLIENTS, client_data)
        
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
        dict: Client information with related data
    """
    client = get_document(Collections.CLIENTS, client_id)
    
    if client:
        # Enrich with user information
        if client.get('assigned_to'):
            assigned_user = get_document(Collections.USERS, client['assigned_to'])
            if assigned_user:
                client['assigned_username'] = assigned_user.get('username')
                client['assigned_name'] = assigned_user.get('full_name')
        
        if client.get('created_by'):
            creator = get_document(Collections.USERS, client['created_by'])
            if creator:
                client['created_by_username'] = creator.get('username')
                client['created_by_name'] = creator.get('full_name')
    
    return client


def get_all_clients(user_id=None, user_role=None, status=None, limit=None):
    """
    Get all clients based on user role and filters.
    
    Args:
        user_id: Current user ID
        user_role: Current user role
        status: Filter by status
        limit: Optional limit
        
    Returns:
        list: List of client dictionaries
    """
    filters = []
    
    # Role-based filtering
    if user_role == 'employee':
        # Employees see only assigned clients
        filters.append(('assigned_to', '==', str(user_id)))
    
    # Status filtering
    if status:
        filters.append(('status', '==', status))
    
    clients = query_documents(
        Collections.CLIENTS,
        filters=filters if filters else None,
        limit=limit
    )
    
    # Enrich with assigned user information
    enriched_clients = []
    for client in clients:
        if client.get('assigned_to'):
            assigned_user = get_document(Collections.USERS, client['assigned_to'])
            if assigned_user:
                client['assigned_username'] = assigned_user.get('username')
                client['assigned_name'] = assigned_user.get('full_name')
        enriched_clients.append(client)
    
    return enriched_clients


def update_client(client_id, company_name, pan, gstin, contact_person, 
                 email, phone, address, status, assigned_to, user_id):
    """
    Update client information.
    
    Args:
        client_id: Client ID to update
        company_name: Updated company name
        pan: Updated PAN (cannot be changed if already set)
        gstin: Updated GSTIN
        contact_person: Updated contact person
        email: Updated email
        phone: Updated phone
        address: Updated address
        status: Updated status
        assigned_to: Updated assigned user
        user_id: User ID performing the update
        
    Returns:
        tuple: (success, message)
    """
    # Get existing client
    existing_client = get_document(Collections.CLIENTS, client_id)
    if not existing_client:
        return False, "Client not found."
    
    # Validate required fields
    if not all([company_name, pan]):
        return False, "Company name and PAN are required."
    
    # Validate PAN format
    if not validate_pan(pan):
        return False, "Invalid PAN format."
    
    # Validate GSTIN if provided
    if gstin and not validate_gstin(gstin):
        return False, "Invalid GSTIN format."
    
    # Validate status
    if status not in ['active', 'inactive', 'suspended']:
        return False, "Invalid status."
    
    # Check if PAN is being changed and conflicts
    if pan.upper() != existing_client['pan']:
        existing_pan = query_documents(
            Collections.CLIENTS,
            filters=[('pan', '==', pan.upper())]
        )
        if existing_pan:
            return False, "PAN number already exists."
    
    # Check if GSTIN is being changed and conflicts
    if gstin and gstin.upper() != existing_client.get('gstin'):
        existing_gstin = query_documents(
            Collections.CLIENTS,
            filters=[('gstin', '==', gstin.upper())]
        )
        if existing_gstin:
            return False, "GSTIN already exists."
    
    # Validate assigned user
    if assigned_to:
        assigned_user = get_document(Collections.USERS, assigned_to)
        if not assigned_user:
            return False, "Assigned user not found."
    
    # Update client
    updated_data = {
        'company_name': company_name,
        'pan': pan.upper(),
        'gstin': gstin.upper() if gstin else None,
        'contact_person': contact_person,
        'email': email,
        'phone': phone,
        'address': address,
        'status': status,
        'assigned_to': str(assigned_to) if assigned_to else None,
        'updated_at': datetime.now()
    }
    
    try:
        update_document(Collections.CLIENTS, client_id, updated_data)
        
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
    # Get client for logging
    client = get_document(Collections.CLIENTS, client_id)
    if not client:
        return False, "Client not found."
    
    # Check if client has associated tasks/compliance (prevent deletion)
    tasks = query_documents(
        Collections.TASKS,
        filters=[('client_id', '==', client_id)],
        limit=1
    )
    
    compliance = query_documents(
        Collections.COMPLIANCE,
        filters=[('client_id', '==', client_id)],
        limit=1
    )
    
    if tasks or compliance:
        return False, "Cannot delete client with associated tasks or compliance records."
    
    try:
        delete_document(Collections.CLIENTS, client_id)
        
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
        status: New status
        user_id: User performing the update
        
    Returns:
        tuple: (success, message)
    """
    if status not in ['active', 'inactive', 'suspended']:
        return False, "Invalid status."
    
    client = get_document(Collections.CLIENTS, client_id)
    if not client:
        return False, "Client not found."
    
    try:
        update_document(Collections.CLIENTS, client_id, {
            'status': status,
            'updated_at': datetime.now()
        })
        
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
    Search clients by company name, PAN, or GSTIN.
    
    Args:
        search_term: Search keyword
        user_id: Current user ID
        user_role: Current user role
        
    Returns:
        list: List of matching clients
    """
    results = []
    
    # Search by company name
    company_results = search_documents(Collections.CLIENTS, 'company_name', search_term)
    results.extend(company_results)
    
    # Search by PAN
    pan_results = search_documents(Collections.CLIENTS, 'pan', search_term.upper())
    results.extend(pan_results)
    
    # Search by GSTIN
    gstin_results = search_documents(Collections.CLIENTS, 'gstin', search_term.upper())
    results.extend(gstin_results)
    
    # Remove duplicates
    seen_ids = set()
    unique_results = []
    
    for client in results:
        if client['id'] not in seen_ids:
            seen_ids.add(client['id'])
            
            # Apply role-based filtering
            if user_role == 'employee':
                if client.get('assigned_to') == str(user_id):
                    unique_results.append(client)
            else:
                unique_results.append(client)
    
    return unique_results


def get_clients_by_status(status, user_id=None, user_role=None):
    """
    Get clients by status.
    
    Args:
        status: Client status
        user_id: Current user ID
        user_role: Current user role
        
    Returns:
        list: List of clients with specified status
    """
    return get_all_clients(user_id, user_role, status)


def get_client_statistics(user_id=None, user_role=None):
    """
    Get client statistics.
    
    Args:
        user_id: Current user ID
        user_role: Current user role
        
    Returns:
        dict: Statistics including total, active, inactive counts
    """
    filters = []
    
    # Role-based filtering
    if user_role == 'employee':
        filters.append(('assigned_to', '==', str(user_id)))
    
    # Get all clients for this user's scope
    all_clients = query_documents(
        Collections.CLIENTS,
        filters=filters if filters else None
    )
    
    stats = {
        'total': len(all_clients),
        'active': 0,
        'inactive': 0,
        'suspended': 0
    }
    
    for client in all_clients:
        status = client.get('status', 'active')
        if status in stats:
            stats[status] += 1
    
    return stats


def assign_client(client_id, assigned_to, user_id):
    """
    Assign client to a user.
    
    Args:
        client_id: Client ID
        assigned_to: User ID to assign to
        user_id: User performing the assignment
        
    Returns:
        tuple: (success, message)
    """
    # Get client
    client = get_document(Collections.CLIENTS, client_id)
    if not client:
        return False, "Client not found."
    
    # Validate assigned user
    if assigned_to:
        assigned_user = get_document(Collections.USERS, assigned_to)
        if not assigned_user:
            return False, "Assigned user not found."
    
    try:
        update_document(Collections.CLIENTS, client_id, {
            'assigned_to': str(assigned_to) if assigned_to else None,
            'updated_at': datetime.now()
        })
        
        # Log activity
        assignment_text = f"Assigned to {assigned_user['full_name']}" if assigned_to else "Unassigned"
        log_activity(
            user_id,
            'assign_client',
            'client',
            client_id,
            f"{assignment_text}: {client['company_name']}"
        )
        
        return True, f"Client assignment updated successfully."
    except Exception as e:
        return False, f"Failed to assign client: {str(e)}"