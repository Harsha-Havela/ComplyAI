"""
ComplyAI Application Factory
Creates and configures the Flask application instance with Firebase
"""
from flask import Flask
from config import config
import os


def create_app(config_name='default'):
    """
    Application factory function.
    
    Args:
        config_name: Configuration to use (development, production, testing)
        
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Ensure required directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize Firebase instead of SQLite
    from app.config.firebase_config import init_firebase_app
    from app.models.firebase_database import init_firebase_collections
    
    with app.app_context():
        # Initialize Firebase
        init_firebase_app(app)
        init_firebase_collections()
        
        # Create default admin if no users exist (only if Firebase is available)
        try:
            from app.controllers.firebase_auth_controller import create_default_admin
            success, message = create_default_admin()
            if success:
                print(f"✅ {message}")
        except Exception as e:
            print(f"⚠️ Could not create default admin: {e}")
            print("This is normal if Firebase credentials aren't configured")
    
    # Register template filters
    register_template_filters(app)
    
    # Register blueprints
    from app.routes.firebase_auth_routes import auth_bp
    from app.routes.firebase_client_routes import client_bp
    from app.routes.firebase_task_routes import task_bp
    from app.routes.firebase_compliance_routes import compliance_bp
    from app.routes.firebase_notification_routes import notification_bp
    from app.routes.firebase_report_routes import report_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(task_bp)
    app.register_blueprint(compliance_bp)
    app.register_blueprint(notification_bp)
    app.register_blueprint(report_bp)
    
    # Register root route redirect
    @app.route('/')
    def index():
        from flask import redirect, url_for, session
        # Redirect to dashboard if logged in, otherwise to login
        if 'user_id' in session:
            return redirect(url_for('auth.dashboard'))
        return redirect(url_for('auth.login'))
    
    # Register error handlers
    register_error_handlers(app)

    # Start background scheduler (new isolated module — app/scheduler.py)
    from app.scheduler import start_scheduler
    start_scheduler(app=app)

    return app


def register_template_filters(app):
    """Register custom template filters."""
    from app.utils.helpers import is_overdue
    from datetime import datetime, date
    
    @app.template_filter('is_overdue')
    def is_overdue_filter(due_date, status):
        return is_overdue(due_date, status)
    
    @app.template_filter('as_date')
    def as_date_filter(date_str):
        """Convert date string to date object."""
        if isinstance(date_str, str):
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S').date()
        return date_str
    
    @app.template_global()
    def moment():
        """Get current datetime for template use."""
        return datetime.now()


def register_error_handlers(app):
    """Register error handlers for common HTTP errors."""
    
    @app.errorhandler(404)
    def not_found(error):
        from flask import render_template
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(403)
    def forbidden(error):
        from flask import render_template
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template
        return render_template('errors/500.html'), 500
