"""
Firebase Authentication Utilities
Decorators and helper functions for authentication and authorization with Firebase
"""
from functools import wraps
from flask import session, redirect, url_for, flash, request
from app.models.firebase_database import get_document, Collections


def login_required(f):
    """
    Decorator to protect routes that require authentication.
    Redirects to login page if user is not authenticated.
    
    Usage:
        @login_required
        def protected_route():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """
    Decorator to protect routes that require specific roles.
    Checks if user has one of the specified roles.
    
    Args:
        *roles: Variable number of role strings (e.g., 'admin', 'manager')
        
    Usage:
        @role_required('admin', 'manager')
        def manager_only_route():
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            
            # Get user from Firebase
            user = get_document(Collections.USERS, session['user_id'])
            
            if not user or not user.get('is_active', True) or user.get('role') not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('auth.login'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_current_user():
    """
    Get current logged-in user information.
    
    Returns:
        dict: User information dictionary or None
    """
    if 'user_id' not in session:
        return None
    
    user = get_document(Collections.USERS, session['user_id'])
    
    if user and user.get('is_active', True):
        # Remove password hash from returned data
        return {k: v for k, v in user.items() if k != 'password_hash'}
    
    return None


def check_password(password, password_hash):
    """
    Verify password against stored hash.
    
    Args:
        password: Plain text password
        password_hash: Stored password hash
        
    Returns:
        bool: True if password matches, False otherwise
    """
    from werkzeug.security import check_password_hash
    return check_password_hash(password_hash, password)


def hash_password(password):
    """
    Generate password hash using Werkzeug.
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
    """
    from werkzeug.security import generate_password_hash
    return generate_password_hash(password, method='scrypt')