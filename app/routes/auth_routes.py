"""
Authentication Routes
Handles all authentication-related HTTP requests
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.controllers.auth_controller import (
    authenticate_user, register_user, logout_user, 
    change_password, get_all_users, update_user_status
)
from app.utils.auth import login_required, role_required, get_current_user

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    User login route.
    GET: Display login form
    POST: Process login credentials
    """
    # Redirect if already logged in
    if 'user_id' in session:
        return redirect(url_for('auth.dashboard'))
    
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        # Validate inputs
        if not username_or_email or not password:
            flash('Please provide both username/email and password.', 'danger')
            return render_template('auth/login.html')
        
        # Authenticate user
        success, result = authenticate_user(username_or_email, password)
        
        if success:
            # Store user info in session
            session.permanent = bool(remember)
            session['user_id'] = result['id']
            session['username'] = result['username']
            session['full_name'] = result['full_name']
            session['role'] = result['role']
            
            flash(f'Welcome back, {result["full_name"]}!', 'success')
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('auth.dashboard'))
        else:
            flash(result, 'danger')
    
    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def register():
    """
    User registration route (admin only).
    GET: Display registration form
    POST: Process registration
    """
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', 'employee')
        phone = request.form.get('phone', '').strip() or None
        
        # Validate inputs
        if not all([username, email, password, full_name]):
            flash('All fields except phone are required.', 'danger')
            return render_template('auth/register.html')
        
        # Check password confirmation
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')
        
        # Register user
        success, result = register_user(
            username, email, password, full_name, role, phone
        )
        
        if success:
            flash(f'User {username} registered successfully!', 'success')
            return redirect(url_for('auth.users'))
        else:
            flash(result, 'danger')
    
    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout route."""
    user_id = session.get('user_id')
    
    if user_id:
        logout_user(user_id)
    
    # Clear session
    session.clear()
    
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard route."""
    user = get_current_user()
    
    # Get client statistics
    from app.controllers.client_controller import get_client_statistics
    client_stats = get_client_statistics(user['id'], user['role'])
    
    # Get task statistics
    from app.controllers.task_controller import get_task_statistics
    task_stats = get_task_statistics(user['id'], user['role'])
    
    # Get compliance statistics
    from app.controllers.compliance_controller import get_compliance_statistics, get_upcoming_compliance
    compliance_stats = get_compliance_statistics(user['id'], user['role'])
    upcoming_compliance = get_upcoming_compliance(7, user['id'], user['role'])  # Next 7 days
    
    return render_template(
        'auth/dashboard.html', 
        user=user, 
        client_stats=client_stats, 
        task_stats=task_stats,
        compliance_stats=compliance_stats,
        upcoming_compliance_count=len(upcoming_compliance)
    )


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile and password change route."""
    user = get_current_user()
    
    if request.method == 'POST':
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate inputs
        if not all([old_password, new_password, confirm_password]):
            flash('All password fields are required.', 'danger')
            return render_template('auth/profile.html', user=user)
        
        # Check password confirmation
        if new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
            return render_template('auth/profile.html', user=user)
        
        # Change password
        success, message = change_password(
            session['user_id'], old_password, new_password
        )
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
    
    return render_template('auth/profile.html', user=user)


@auth_bp.route('/users')
@login_required
@role_required('admin')
def users():
    """User management route (admin only)."""
    all_users = get_all_users()
    return render_template('auth/users.html', users=all_users)


@auth_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@role_required('admin')
def toggle_user_status(user_id):
    """Toggle user active status (admin only)."""
    is_active = request.form.get('is_active') == '1'
    admin_id = session['user_id']
    
    success, message = update_user_status(user_id, is_active, admin_id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('auth.users'))
