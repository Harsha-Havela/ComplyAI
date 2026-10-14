"""
Helper Utilities
General helper functions for the application
"""
from datetime import datetime, date


def is_overdue(due_date_str, status):
    """
    Check if a task is overdue based on due date and status.
    
    Args:
        due_date_str: Due date as string (YYYY-MM-DD) or None
        status: Task status
        
    Returns:
        bool: True if task is overdue, False otherwise
    """
    if not due_date_str or status in ['completed', 'cancelled']:
        return False
    
    try:
        # Handle both string dates and date objects
        if isinstance(due_date_str, str):
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        elif isinstance(due_date_str, date):
            due_date = due_date_str
        else:
            return False
        
        return due_date < datetime.now().date()
    except (ValueError, TypeError):
        return False


def format_date_for_input():
    """
    Get today's date formatted for HTML date input.
    
    Returns:
        str: Today's date in YYYY-MM-DD format
    """
    return datetime.now().strftime('%Y-%m-%d')


def days_until_due(due_date_str):
    """
    Calculate days until due date.
    
    Args:
        due_date_str: Due date as string (YYYY-MM-DD)
        
    Returns:
        int: Days until due (negative if overdue)
    """
    if not due_date_str:
        return None
    
    try:
        if isinstance(due_date_str, str):
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        else:
            due_date = due_date_str
        
        today = datetime.now().date()
        return (due_date - today).days
    except (ValueError, TypeError):
        return None