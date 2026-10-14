"""
Firebase Authentication Routes
Handles all authentication HTTP requests with Firebase backend
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.controllers.firebase_auth_controller import (
    authenticate_user, register_user, logout_user, change_password,
    get_user_by_id, get_all_users, update_user_status
)
from app.utils.firebase_auth import login_required, role_required, get_current_user

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login route."""
    if request.method == 'POST':
        username = request.form.get('username_or_email', '').strip()
        password = request.form.get('password', '').strip()
        remember_me = request.form.get('remember') == '1'
        
        print(f"🔍 Login attempt - Username: '{username}', Password length: {len(password)}")
        
        if not username or not password:
            print("❌ Missing username or password")
            flash('Username and password are required.', 'danger')
            return render_template('auth/login.html')
        
        # Authenticate user
        print("🔐 Calling authenticate_user...")
        success, result = authenticate_user(username, password)
        print(f"🔐 Authentication result: {success}, {result if not success else 'SUCCESS'}")
        
        if success:
            user = result
            # Store user information in session
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            session['email'] = user['email']
            
            # Make session permanent if remember me is checked
            if remember_me:
                session.permanent = True
            
            print(f"✅ Login successful for user: {user['username']}")
            flash(f'Welcome back, {user["full_name"]}!', 'success')
            
            # Redirect to dashboard or intended page
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('auth.dashboard'))
        else:
            print(f"❌ Login failed: {result}")
            flash(result, 'danger')
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout route."""
    user_id = session.get('user_id')
    
    # Log logout activity
    if user_id:
        logout_user(user_id)
    
    # Clear session
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def register():
    """User registration route (admin only)."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', '').strip()
        phone = request.form.get('phone', '').strip()
        
        # Validate required fields
        if not all([username, email, full_name, role]):
            flash('Username, email, full name, and role are required.', 'danger')
            return render_template('auth/register.html')
        
        # Register user without password (will send activation email)
        success, result = register_user(
            username, email, None, full_name, role, phone, send_activation_email=True
        )
        
        if success:
            flash(f'User "{username}" created successfully! Activation email sent to {email}', 'success')
            return redirect(url_for('auth.users'))
        else:
            flash(result, 'danger')
    
    return render_template('auth/register.html')


@auth_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard route."""
    user = get_current_user()
    
    # Get client statistics with error handling
    try:
        from app.controllers.firebase_client_controller import get_client_statistics
        client_stats = get_client_statistics(user['id'], user['role'])
    except Exception as e:
        print(f"⚠️ Client query failed: {e}")
        client_stats = {
            'total': 0,
            'active': 0,
            'inactive': 0
        }
    
    # Get task statistics with error handling
    try:
        from app.controllers.firebase_task_controller import get_task_statistics
        task_stats = get_task_statistics(user['id'], user['role'])
    except Exception as e:
        print(f"⚠️ Task query failed (index required): {e}")
        # Use default values if task query fails
        task_stats = {
            'total': 0,
            'pending': 0,
            'in_progress': 0,
            'completed': 0,
            'cancelled': 0,
            'overdue': 0,
            'due_today': 0,
            'due_this_week': 0,
            'by_priority': {
                'low': 0,
                'medium': 0,
                'high': 0,
                'urgent': 0
            }
        }
    
    # Get compliance statistics with error handling
    try:
        from app.controllers.firebase_compliance_controller import get_compliance_statistics, get_upcoming_compliance
        compliance_stats = get_compliance_statistics(user['id'], user['role'])
        upcoming_compliance = get_upcoming_compliance(7, user['id'], user['role'])  # Next 7 days
        upcoming_compliance_count = len(upcoming_compliance)
    except Exception as e:
        print(f"⚠️ Compliance query failed (index required): {e}")
        # Use default values if compliance query fails
        compliance_stats = {
            'total': 0,
            'pending': 0,
            'completed': 0,
            'overdue': 0
        }
        upcoming_compliance_count = 0
    
    from datetime import datetime
    return render_template(
        'auth/dashboard.html', 
        user=user, 
        client_stats=client_stats, 
        task_stats=task_stats,
        compliance_stats=compliance_stats,
        upcoming_compliance_count=upcoming_compliance_count,
        now=datetime.now()
    )


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile and password change route."""
    user = get_current_user()
    
    if request.method == 'POST':
        old_password = request.form.get('old_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Validate required fields
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


@auth_bp.route('/users/<string:user_id>/toggle-status', methods=['POST'])
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



@auth_bp.route('/activate/<token>', methods=['GET', 'POST'])
def activate_account(token):
    """Account activation route."""
    if request.method == 'GET':
        # Verify token is valid
        from app.controllers.firebase_auth_controller import verify_activation_token
        valid, user_data = verify_activation_token(token)
        
        if not valid:
            flash(user_data, 'danger')  # user_data contains error message
            return redirect(url_for('auth.login'))
        
        # Show password setup page
        return render_template('auth/activate.html', token=token, user=user_data)
    
    elif request.method == 'POST':
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        if not password or not confirm_password:
            flash('Password is required.', 'danger')
            return redirect(url_for('auth.activate_account', token=token))
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.activate_account', token=token))
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return redirect(url_for('auth.activate_account', token=token))
        
        # Activate account with new password
        from app.controllers.firebase_auth_controller import activate_user_account
        success, message = activate_user_account(token, password)
        
        if success:
            flash('Account activated successfully! You can now login.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(message, 'danger')
            return redirect(url_for('auth.activate_account', token=token))
