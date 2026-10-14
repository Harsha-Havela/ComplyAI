"""
Dashboard Routes
Main dashboard and analytics pages
"""
from flask import Blueprint, render_template, session, jsonify
from app.utils.auth import login_required
from app.controllers.dashboard_controller import get_dashboard_data, get_analytics_data

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    """Main dashboard page."""
    data = get_dashboard_data(session['user_id'], session['role'])
    return render_template('dashboard/index.html', **data)


@dashboard_bp.route('/analytics')
@login_required
def analytics():
    """Analytics and reports page."""
    if session['role'] in ['admin', 'manager']:
        data = get_analytics_data()
    else:
        data = get_analytics_data(session['user_id'])
    
    return render_template('dashboard/analytics.html', analytics=data)


@dashboard_bp.route('/api/analytics-data')
@login_required
def analytics_api():
    """API endpoint for analytics data (for Chart.js)."""
    if session['role'] in ['admin', 'manager']:
        data = get_analytics_data()
    else:
        data = get_analytics_data(session['user_id'])
    
    return jsonify(data)
