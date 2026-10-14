"""
Firebase Authentication Controller
Handles all user authentication and management with Firestore
"""
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.firebase_database import (
    Collections, create_document, get_document, update_document, 
    delete_document, query_documents, search_documents
)
from app.services.firebase_activity_service import log_activity
from datetime import datetime, timedelta


def authenticate_user(username, password):
    """
    Authenticate user credentials.
    
    Args:
        username: Username or email
        password: Plain text password
        
    Returns:
        tuple: (success, user_data or error_message)
    """
    # Query by username or email
    users = query_documents(
        Collections.USERS,
        filters=[('username', '==', username)]
    )
    
    if not users:
        # Try email if username not found
        users = query_documents(
            Collections.USERS,
            filters=[('email', '==', username)]
        )
    
    if not users:
        return False, "Invalid username or password."
    
    user = users[0]
    
    # Check if user is active
    if not user.get('is_active', True):
        return False, "Account is deactivated. Please contact administrator."
    
    # Verify password
    if not check_password_hash(user['password_hash'], password):
        return False, "Invalid username or password."
    
    # Log successful login
    log_activity(user['id'], 'login', description='User logged in successfully')
    
    # Remove password_hash from user dict before returning
    user_data = {k: v for k, v in user.items() if k != 'password_hash'}
    
    return True, user_data


def register_user(username, email, password, full_name, role='employee', phone=None, send_activation_email=False):
    """
    Register a new user.
    
    Args:
        username: Unique username
        email: User email address
        password: Plain text password (None if using activation email)
        full_name: User's full name
        role: User role (admin, manager, employee)
        phone: Optional phone number
        send_activation_email: If True, send activation email instead of setting password
        
    Returns:
        tuple: (success, user_id or error_message)
    """
    # Validate role
    if role not in ['admin', 'manager', 'employee']:
        return False, "Invalid role specified."
    
    # Check if username already exists
    existing_users = query_documents(
        Collections.USERS,
        filters=[('username', '==', username)]
    )
    
    if existing_users:
        return False, "Username already exists."
    
    # Check if email already exists
    existing_emails = query_documents(
        Collections.USERS,
        filters=[('email', '==', email)]
    )
    
    if existing_emails:
        return False, "Email already registered."
    
    # If using activation email, generate token
    if send_activation_email or password is None:
        import secrets
        activation_token = secrets.token_urlsafe(32)
        password_hash = None
        is_active = False
        activation_expires = datetime.now() + timedelta(hours=48)  # 48 hour expiry
    else:
        # Hash password
        password_hash = generate_password_hash(password)
        activation_token = None
        is_active = True
        activation_expires = None
    
    # Create user document
    user_data = {
        'username': username.strip(),
        'email': email.strip().lower(),
        'password_hash': password_hash,
        'full_name': full_name.strip(),
        'role': role,
        'phone': phone.strip() if phone else None,
        'is_active': is_active,
        'activation_token': activation_token,
        'activation_expires': activation_expires,
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    
    try:
        user_id = create_document(Collections.USERS, user_data)
        
        # Send activation email if requested
        if send_activation_email or password is None:
            from app.services.email_service import send_activation_email
            try:
                send_activation_email(email, full_name, username, activation_token)
            except Exception as e:
                print(f"⚠️ Failed to send activation email: {e}")
                # Continue anyway - user created successfully
        
        # Log user registration
        log_activity(user_id, 'register', description=f'New user registered: {username}')
        
        return True, user_id
    except Exception as e:
        return False, f"Failed to register user: {str(e)}"


def logout_user(user_id):
    """
    Log user logout activity.
    
    Args:
        user_id: User ID
        
    Returns:
        bool: Success status
    """
    try:
        log_activity(user_id, 'logout', description='User logged out')
        return True
    except Exception:
        return False


def change_password(user_id, old_password, new_password):
    """
    Change user password.
    
    Args:
        user_id: User ID
        old_password: Current password
        new_password: New password
        
    Returns:
        tuple: (success, message)
    """
    # Get user
    user = get_document(Collections.USERS, user_id)
    if not user:
        return False, "User not found."
    
    # Verify old password
    if not check_password_hash(old_password, user['password_hash']):
        return False, "Current password is incorrect."
    
    # Hash new password
    new_password_hash = generate_password_hash(new_password)
    
    # Update password
    try:
        update_document(Collections.USERS, user_id, {
            'password_hash': new_password_hash,
            'updated_at': datetime.now()
        })
        
        # Log password change
        log_activity(user_id, 'change_password', description='Password changed successfully')
        
        return True, "Password changed successfully."
    except Exception as e:
        return False, f"Failed to change password: {str(e)}"


def get_user_by_id(user_id):
    """
    Get user by ID.
    
    Args:
        user_id: User ID
        
    Returns:
        dict: User data (without password hash)
    """
    user = get_document(Collections.USERS, user_id)
    if user:
        # Remove password hash
        return {k: v for k, v in user.items() if k != 'password_hash'}
    return None


def get_all_users(limit=None):
    """
    Get all users.
    
    Args:
        limit: Optional limit
        
    Returns:
        list: List of user dictionaries (without password hashes)
    """
    users = query_documents(
        Collections.USERS,
        limit=limit
    )
    
    # Remove password hashes and format dates
    formatted_users = []
    for user in users:
        user_data = {k: v for k, v in user.items() if k != 'password_hash'}
        
        # Format datetime fields for display
        if 'created_at' in user_data and user_data['created_at']:
            try:
                user_data['created_at'] = user_data['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            except:
                user_data['created_at'] = str(user_data['created_at'])
        
        if 'updated_at' in user_data and user_data['updated_at']:
            try:
                user_data['updated_at'] = user_data['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
            except:
                user_data['updated_at'] = str(user_data['updated_at'])
        
        formatted_users.append(user_data)
    
    return formatted_users


def update_user_status(user_id, is_active, admin_id):
    """
    Update user active status (admin only).
    
    Args:
        user_id: User ID to update
        is_active: New active status
        admin_id: Admin user ID performing the action
        
    Returns:
        tuple: (success, message)
    """
    # Get user to check if exists
    user = get_document(Collections.USERS, user_id)
    if not user:
        return False, "User not found."
    
    # Prevent deactivating yourself
    if str(user_id) == str(admin_id):
        return False, "You cannot deactivate your own account."
    
    try:
        # Update status
        update_document(Collections.USERS, user_id, {
            'is_active': is_active,
            'updated_at': datetime.now()
        })
        
        # Log activity
        action = 'activate_user' if is_active else 'deactivate_user'
        status_text = 'activated' if is_active else 'deactivated'
        log_activity(
            admin_id, 
            action, 
            'user', 
            user_id, 
            f"User {user['username']} {status_text}"
        )
        
        return True, f"User {status_text} successfully."
    except Exception as e:
        return False, f"Failed to update user status: {str(e)}"


def get_users_by_role(role):
    """
    Get users by role.
    
    Args:
        role: User role (admin, manager, employee)
        
    Returns:
        list: List of users with specified role
    """
    users = query_documents(
        Collections.USERS,
        filters=[('role', '==', role), ('is_active', '==', True)]
    )
    
    # Remove password hashes
    return [
        {k: v for k, v in user.items() if k != 'password_hash'}
        for user in users
    ]


def search_users(search_term):
    """
    Search users by username, email, or full name.
    
    Args:
        search_term: Search keyword
        
    Returns:
        list: List of matching users
    """
    results = []
    
    # Search by username
    username_results = search_documents(Collections.USERS, 'username', search_term)
    results.extend(username_results)
    
    # Search by email
    email_results = search_documents(Collections.USERS, 'email', search_term)
    results.extend(email_results)
    
    # Search by full name
    name_results = search_documents(Collections.USERS, 'full_name', search_term)
    results.extend(name_results)
    
    # Remove duplicates and password hashes
    seen_ids = set()
    unique_results = []
    
    for user in results:
        if user['id'] not in seen_ids:
            seen_ids.add(user['id'])
            user_data = {k: v for k, v in user.items() if k != 'password_hash'}
            unique_results.append(user_data)
    
    return unique_results


def get_user_statistics():
    """
    Get user statistics.
    
    Returns:
        dict: Statistics including total, active, by role
    """
    # Get all users
    all_users = query_documents(Collections.USERS)
    
    stats = {
        'total': len(all_users),
        'active': 0,
        'inactive': 0,
        'admins': 0,
        'managers': 0,
        'employees': 0
    }
    
    for user in all_users:
        # Count by status
        if user.get('is_active', True):
            stats['active'] += 1
        else:
            stats['inactive'] += 1
        
        # Count by role
        role = user.get('role', 'employee')
        if role == 'admin':
            stats['admins'] += 1
        elif role == 'manager':
            stats['managers'] += 1
        else:
            stats['employees'] += 1
    
    return stats


def create_default_admin():
    """
    Create default admin user if no users exist.
    
    Returns:
        tuple: (success, message)
    """
    # Check if any users exist
    existing_users = query_documents(Collections.USERS, limit=1)
    
    if existing_users:
        return False, "Users already exist in the system."
    
    # Create default admin
    success, result = register_user(
        username='admin',
        email='admin@complyai.com',
        password='Admin123',
        full_name='System Administrator',
        role='admin'
    )
    
    if success:
        return True, f"Default admin created with ID: {result}"
    else:
        return False, f"Failed to create default admin: {result}"



def verify_activation_token(token):
    """
    Verify activation token is valid.
    
    Args:
        token: Activation token
        
    Returns:
        tuple: (valid, user_data or error_message)
    """
    # Find user with this token
    users = query_documents(
        Collections.USERS,
        filters=[('activation_token', '==', token)]
    )
    
    if not users:
        return False, "Invalid or expired activation link."
    
    user = users[0]
    
    # Check if already activated
    if user.get('is_active') and user.get('password_hash'):
        return False, "This account has already been activated. Please login."
    
    # Check if token expired
    if user.get('activation_expires'):
        from datetime import timezone
        now_utc = datetime.now(timezone.utc)
        
        # Convert activation_expires to timezone-aware if needed
        expires = user['activation_expires']
        if hasattr(expires, 'tzinfo') and expires.tzinfo is not None:
            # Already timezone-aware
            if now_utc > expires:
                return False, "Activation link has expired. Please contact your administrator."
        else:
            # Timezone-naive, assume UTC
            if datetime.now() > expires:
                return False, "Activation link has expired. Please contact your administrator."
    
    return True, user


def activate_user_account(token, password):
    """
    Activate user account and set password.
    
    Args:
        token: Activation token
        password: New password
        
    Returns:
        tuple: (success, message)
    """
    # Verify token
    valid, user_data = verify_activation_token(token)
    
    if not valid:
        return False, user_data  # user_data contains error message
    
    user_id = user_data['id']
    
    # Hash password
    password_hash = generate_password_hash(password)
    
    # Update user
    try:
        update_document(
            Collections.USERS,
            user_id,
            {
                'password_hash': password_hash,
                'is_active': True,
                'activation_token': None,
                'activation_expires': None,
                'updated_at': datetime.now()
            }
        )
        
        # Log activation
        log_activity(
            user_id,
            'activate_account',
            description=f"Account activated: {user_data['username']}"
        )
        
        return True, "Account activated successfully!"
        
    except Exception as e:
        return False, f"Failed to activate account: {str(e)}"
