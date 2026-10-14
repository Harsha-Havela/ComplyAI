"""
Firebase Report Routes
Handles report generation and analytics with Firebase backend
"""
from flask import Blueprint, render_template, request, jsonify, send_file
from datetime import datetime, timedelta
from io import BytesIO
import csv

from app.controllers.firebase_task_controller import get_all_tasks, get_task_statistics
from app.controllers.firebase_client_controller import get_all_clients, get_client_statistics
from app.controllers.firebase_compliance_controller import get_all_compliance, get_compliance_statistics
from app.services.firebase_activity_service import get_activity_logs, get_user_activity_summary
from app.utils.firebase_auth import login_required, role_required, get_current_user

report_bp = Blueprint('report', __name__, url_prefix='/reports')


@report_bp.route('/')
@login_required
@role_required('admin', 'manager')
def reports_dashboard():
    """Reports dashboard page."""
    user = get_current_user()
    
    # Get date range from query params or default to last 30 days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    return render_template(
        'reports/dashboard.html',
        user=user,
        start_date=start_date,
        end_date=end_date
    )


@report_bp.route('/tasks')
@login_required
@role_required('admin', 'manager')
def task_report():
    """Task summary report."""
    user = get_current_user()
    
    # Get all tasks
    tasks = get_all_tasks(user['id'], user['role'])
    stats = get_task_statistics(user['id'], user['role'])
    
    return render_template(
        'reports/tasks.html',
        tasks=tasks,
        stats=stats,
        user=user
    )


@report_bp.route('/clients')
@login_required
@role_required('admin', 'manager')
def client_report():
    """Client summary report."""
    user = get_current_user()
    
    # Get all clients
    clients = get_all_clients(user['id'], user['role'])
    stats = get_client_statistics(user['id'], user['role'])
    
    return render_template(
        'reports/clients.html',
        clients=clients,
        stats=stats,
        user=user
    )


@report_bp.route('/compliance')
@login_required
@role_required('admin', 'manager')
def compliance_report():
    """Compliance summary report."""
    user = get_current_user()
    
    # Get all compliance deadlines
    compliance_list = get_all_compliance(user['id'], user['role'])
    stats = get_compliance_statistics(user['id'], user['role'])
    
    return render_template(
        'reports/compliance.html',
        compliance_list=compliance_list,
        stats=stats,
        user=user
    )


@report_bp.route('/activity')
@login_required
@role_required('admin', 'manager')
def activity_report():
    """Activity log report."""
    user = get_current_user()
    
    # Get query parameters
    days = int(request.args.get('days', 7))
    user_filter = request.args.get('user_id')
    action_filter = request.args.get('action')
    
    # Get activity logs
    logs = get_activity_logs(
        limit=100,
        user_id=user_filter,
        action_type=action_filter,
        days=days
    )
    
    return render_template(
        'reports/activity.html',
        logs=logs,
        user=user,
        days=days
    )


@report_bp.route('/user-performance')
@login_required
@role_required('admin', 'manager')
def user_performance_report():
    """User performance report."""
    user = get_current_user()
    
    # Get date range
    days = int(request.args.get('days', 30))
    
    # Get all users (without passing user_id and role)
    from app.controllers.firebase_auth_controller import get_all_users
    users = get_all_users()
    
    # Get activity summary for each user
    user_summaries = []
    for u in users:
        if u.get('is_active'):
            summary = get_user_activity_summary(u['id'], days)
            summary['user'] = u
            user_summaries.append(summary)
    
    # Sort by activity count
    user_summaries.sort(key=lambda x: x.get('total_activities', 0), reverse=True)
    
    return render_template(
        'reports/user_performance.html',
        user_summaries=user_summaries,
        user=user,
        days=days
    )


@report_bp.route('/export/tasks/csv')
@login_required
@role_required('admin', 'manager')
def export_tasks_csv():
    """Export tasks to CSV."""
    try:
        user = get_current_user()
        
        # Get tasks with error handling
        try:
            tasks = get_all_tasks(user['id'], user['role'])
        except Exception as e:
            print(f"Error getting tasks: {e}")
            tasks = []
        
        # Create simple CSV content as string
        csv_content = "ID,Title,Description,Client,Assigned To,Priority,Status,Due Date,Created At\n"
        
        if not tasks:
            # Add sample row if no data
            csv_content += "No Data,No tasks found,Please create some tasks first,-,-,-,-,-,-\n"
        else:
            for task in tasks:
                # Clean data for CSV
                title = str(task.get('title', '')).replace(',', ';').replace('\n', ' ')
                description = str(task.get('description', '')).replace(',', ';').replace('\n', ' ')
                client_name = str(task.get('client_name', '')).replace(',', ';')
                assigned_name = str(task.get('assigned_to_name', '')).replace(',', ';')
                
                csv_content += f"{task.get('id', '')},"
                csv_content += f"{title},"
                csv_content += f"{description},"
                csv_content += f"{client_name},"
                csv_content += f"{assigned_name},"
                csv_content += f"{task.get('priority', '')},"
                csv_content += f"{task.get('status', '')},"
                csv_content += f"{task.get('due_date', '')},"
                csv_content += f"{task.get('created_at', '')}\n"
        
        # Create response
        from flask import Response
        
        filename = f'tasks_report_{datetime.now().strftime("%Y%m%d")}.csv'
        
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename={filename}',
                'Content-Type': 'text/csv; charset=utf-8'
            }
        )
        
    except Exception as e:
        print(f"CSV Export Error: {e}")
        # Return error message as CSV
        error_csv = f"Error,Failed to export tasks: {str(e)}\n"
        return Response(
            error_csv,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=error.csv'}
        )


@report_bp.route('/export/clients/csv')
@login_required
@role_required('admin', 'manager')
def export_clients_csv():
    """Export clients to CSV."""
    try:
        user = get_current_user()
        
        # Get clients with error handling
        try:
            clients = get_all_clients(user['id'], user['role'])
        except Exception as e:
            print(f"Error getting clients: {e}")
            clients = []
        
        # Create simple CSV content
        csv_content = "ID,Company Name,PAN,GSTIN,Contact Person,Email,Phone,Status,Assigned To\n"
        
        if not clients:
            csv_content += "No Data,No clients found,Please create some clients first,-,-,-,-,-,-\n"
        else:
            for client in clients:
                # Clean data for CSV
                company = str(client.get('company_name', '')).replace(',', ';')
                contact = str(client.get('contact_person', '')).replace(',', ';')
                email = str(client.get('email', '')).replace(',', ';')
                assigned = str(client.get('assigned_name', '')).replace(',', ';')
                
                csv_content += f"{client.get('id', '')},"
                csv_content += f"{company},"
                csv_content += f"{client.get('pan', '')},"
                csv_content += f"{client.get('gstin', '')},"
                csv_content += f"{contact},"
                csv_content += f"{email},"
                csv_content += f"{client.get('phone', '')},"
                csv_content += f"{client.get('status', '')},"
                csv_content += f"{assigned}\n"
        
        from flask import Response
        filename = f'clients_report_{datetime.now().strftime("%Y%m%d")}.csv'
        
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename={filename}',
                'Content-Type': 'text/csv; charset=utf-8'
            }
        )
        
    except Exception as e:
        print(f"CSV Export Error: {e}")
        error_csv = f"Error,Failed to export clients: {str(e)}\n"
        return Response(
            error_csv,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=error.csv'}
        )


@report_bp.route('/export/compliance/csv')
@login_required
@role_required('admin', 'manager')
def export_compliance_csv():
    """Export compliance to CSV."""
    try:
        user = get_current_user()
        
        # Get compliance with error handling
        try:
            compliance_list = get_all_compliance(user['id'], user['role'])
        except Exception as e:
            print(f"Error getting compliance: {e}")
            compliance_list = []
        
        # Create simple CSV content
        csv_content = "ID,Type,Description,Client,Due Date,Frequency,Status\n"
        
        if not compliance_list:
            csv_content += "No Data,No compliance deadlines found,Please create some deadlines first,-,-,-,-\n"
        else:
            for compliance in compliance_list:
                # Clean data for CSV
                comp_type = str(compliance.get('compliance_type', '')).replace(',', ';')
                description = str(compliance.get('description', '')).replace(',', ';')
                client_name = str(compliance.get('client_name', '')).replace(',', ';')
                
                csv_content += f"{compliance.get('id', '')},"
                csv_content += f"{comp_type},"
                csv_content += f"{description},"
                csv_content += f"{client_name},"
                csv_content += f"{compliance.get('due_date', '')},"
                csv_content += f"{compliance.get('frequency', '')},"
                csv_content += f"{compliance.get('status', '')}\n"
        
        from flask import Response
        filename = f'compliance_report_{datetime.now().strftime("%Y%m%d")}.csv'
        
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename={filename}',
                'Content-Type': 'text/csv; charset=utf-8'
            }
        )
        
    except Exception as e:
        print(f"CSV Export Error: {e}")
        error_csv = f"Error,Failed to export compliance: {str(e)}\n"
        return Response(
            error_csv,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=error.csv'}
        )


# API endpoints for charts/graphs

@report_bp.route('/api/task-stats')
@login_required
def api_task_stats():
    """API endpoint for task statistics (for charts)."""
    user = get_current_user()
    stats = get_task_statistics(user['id'], user['role'])
    
    return jsonify(stats)


@report_bp.route('/api/client-stats')
@login_required
def api_client_stats():
    """API endpoint for client statistics (for charts)."""
    user = get_current_user()
    stats = get_client_statistics(user['id'], user['role'])
    
    return jsonify(stats)


@report_bp.route('/api/compliance-stats')
@login_required
def api_compliance_stats():
    """API endpoint for compliance statistics (for charts)."""
    user = get_current_user()
    stats = get_compliance_statistics(user['id'], user['role'])
    
    return jsonify(stats)
