"""
Validation Utilities
Input validation functions for various data types
"""
import re


def validate_email(email):
    """
    Validate email format.
    
    Args:
        email: Email address string
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_pan(pan):
    """
    Validate PAN (Permanent Account Number) format.
    Format: AAAAA9999A
    
    Args:
        pan: PAN string
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not pan:
        return False
    
    pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]$'
    return re.match(pattern, pan.upper()) is not None


def validate_gstin(gstin):
    """
    Validate GSTIN (GST Identification Number) format.
    Format: 99AAAAA9999A9Z9
    
    Args:
        gstin: GSTIN string
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not gstin:
        return False
    
    pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z][Z][0-9A-Z]$'
    return re.match(pattern, gstin.upper()) is not None


def validate_phone(phone):
    """
    Validate phone number format (Indian).
    
    Args:
        phone: Phone number string
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not phone:
        return True  # Phone is optional
    
    # Remove spaces, dashes, and plus signs
    phone = phone.replace(' ', '').replace('-', '').replace('+', '')
    
    # Check if it's a valid 10-digit number or starts with 91
    pattern = r'^(91)?[6-9][0-9]{9}$'
    return re.match(pattern, phone) is not None


def validate_password(password):
    """
    Validate password strength.
    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    
    Args:
        password: Password string
        
    Returns:
        tuple: (bool, str) - (is_valid, error_message)
    """
    if not password:
        return False, "Password is required."
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."
    
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one digit."
    
    return True, ""


def validate_username(username):
    """
    Validate username format.
    Requirements:
    - 3-50 characters
    - Alphanumeric and underscore only
    - Must start with letter
    
    Args:
        username: Username string
        
    Returns:
        tuple: (bool, str) - (is_valid, error_message)
    """
    if not username:
        return False, "Username is required."
    
    if len(username) < 3 or len(username) > 50:
        return False, "Username must be between 3 and 50 characters."
    
    pattern = r'^[a-zA-Z][a-zA-Z0-9_]*$'
    if not re.match(pattern, username):
        return False, "Username must start with a letter and contain only letters, numbers, and underscores."
    
    return True, ""
