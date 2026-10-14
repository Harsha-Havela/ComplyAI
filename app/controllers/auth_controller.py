"""
Authentication Controller
Handles all authentication and user management business logic
"""
from app.models.database import query_db, execute_db
from app.utils.auth import hash_password, check_password
from app.utils.validators import validate_email, validate_password, validate_username
from app.services.activity_service import log_activity
from datetime import datetime


def authenticate_user(username_or_email, password):
    """
    Authenticate user with username/email and password.
    
    Args:
        username_or_email: Username or email address
        password: Plain text password
        
    Returns:
        tuple: (success, user_dict or error_message)
    """
    # Query user by username or email
    user = query_db(
        '''SELECT id, username, email, password_hash, full_name, role, is_active
           FROM users 
           WHERE (username = ? OR email = ?) AND is_active = 1''',
        (username_or_email, username_or_email),
        one=True
    )
    
    if not user:
        return False, "Invalid username or password."
    
    # Verify password
    if not check_password(password, user['password_hash']):
        return False, "Invalid username or password."
    
    # Log successful login
    log_activity(user['id'], 'login', description='User logged in successfully')
    
    # Remove password_hash from user dict before returning
    user_data = {k: v for k, v in user.items() if k != 'password_hash'}
    
    return True, user_data


def register_user(username, email, password, full_name, role='employee', phone=None):
    """
    Register a new user.
    
    Args:
        username: Unique username
        email: Email address
        password: Plain text password
        full_name: Full name of the user
        role: User role (admin, manager, employee)
        phone: Phone number (optional)
        
    Returns:
        tuple: (success, user_id or error_message)
    """
    # Validate username
    is_valid, error = validate_username(username)
    if not is_valid:
        return False, error
    
    # Validate email
    if not validate_email(email):
        return False, "Invalid email address format."
    
    # Validate password
    is_valid, error = validate_password(password)
    if not is_valid:
        return False, error
    
    # Check if username already exists
    existing = query_db(
        'SELECT id FROM users WHERE username = ?',
        (username,),
        one=True
    )
    if existing:
        return False, "Username already exists."
    
    # Check if email already exists
    existing = query_db(
        'SELECT id FROM users WHERE email = ?',
        (email,),
        one=True
    )
    if existing:
        return False, "Email already registered."
    
    # Validate role
    if role not in ['admin', 'manager', 'employee']:
        return False, "Invalid role specified."
    
    # Hash password
    password_hash = hash_password(password)
    
    # Insert user
    query = '''
        INSERT INTO users (username, email, password_hash, full_name, role, phone)
        VALUES (?, ?, ?, ?, ?, ?)
    '''
    
    try:
        user_id = execute_db(
            query,
            (username, email, password_hash, full_name, role, phone)
        )
        
        # Log registration
        log_activity(user_id, 'registration', description='User account created')
        
        return True, user_id
    except Exception as e:
        return False, f"Registration failed: {str(e)}"


def logout_user(user_id):
    """
    Log user logout activity.
    
    Args:
        user_id: ID of the user logging out
    """
    log_activity(user_id, 'logout', description='User logged out')


def change_password(user_id, old_password, new_password):
    """
    Change user password.
    
    Args:
        user_id: ID of the user
        old_password: Current password
        new_password: New password
        
    Returns:
        tuple: (success, message)
    """
    # Get user
    user = query_db(
        'SELECT password_hash FROM users WHERE id = ?',
        (user_id,),
        one=True
    )
    
    if not user:
        return False, "User not found."
    
    # Verify old password
    if not check_password(old_password, user['password_hash']):
        return False, "Current password is incorrect."
    
    # Validate new password
    is_valid, error = validate_password(new_password)
    if not is_valid:
        return False, error
    
    # Hash new password
    new_password_hash = hash_password(new_password)
    
    # Update password
    execute_db(
        'UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?',
        (new_password_hash, datetime.now(), user_id)
    )
    
    # Log password change
    log_activity(user_id, 'password_change', description='User changed password')
    
    return True, "Password changed successfully."


def get_user_by_id(user_id):
    """
    Get user information by ID.
    
    Args:
        user_id: ID of the user
        
    Returns:
        dict: User information (without password_hash)
    """
    user = query_db(
        '''SELECT id, username, email, full_name, role, phone, 
                  is_active, created_at, updated_at
           FROM users 
           WHERE id = ?''',
        (user_id,),
        one=True
    )
    
    return user


def get_all_users():
    """
    Get all users (admin function).
    
    Returns:
        list: List of user dictionaries
    """
    users = query_db(
        '''SELECT id, username, email, full_name, role, phone,
                  is_active, created_at
           FROM users
           ORDER BY created_at DESC'''
    )
    
    return users


def update_user_status(user_id, is_active, admin_id):
    """
    Activate or deactivate a user account.
    
    Args:
        user_id: ID of the user to update
        is_active: Boolean status
        admin_id: ID of the admin performing the action
        
    Returns:
        tuple: (success, message)
    """
    # Prevent deactivating the last admin
    if not is_active:
        user = query_db(
            'SELECT role FROM users WHERE id = ?',
            (user_id,),
            one=True
        )
        
        if user and user['role'] == 'admin':
            admin_count = query_db(
                'SELECT COUNT(*) as count FROM users WHERE role = ? AND is_active = 1',
                ('admin',),
                one=True
            )
            
            if admin_count['count'] <= 1:
                return False, "Cannot deactivate the last active admin account."
    
    # Update status
    execute_db(
        'UPDATE users SET is_active = ?, updated_at = ? WHERE id = ?',
        (1 if is_active else 0, datetime.now(), user_id)
    )
    
    # Log action
    action = 'activate_user' if is_active else 'deactivate_user'
    log_activity(
        admin_id, 
        action, 
        'user', 
        user_id,
        f"User {'activated' if is_active else 'deactivated'}"
    )
    
    return True, f"User {'activated' if is_active else 'deactivated'} successfully."
