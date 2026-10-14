"""
Dashboard Controller
Aggregates data for dashboard views
"""
from app.models.database import query_db
from app.controllers.client_controller import get_client_stats
from app.controllers.task_controller import get_task_stats, get_overdue_tasks
from app.controllers.compliance_controller import get_compliance_stats, get_upcoming_deadlines, get_overdue_deadlines
from app.services.activity_service import get_recent_activities
from datetime import date, timedelta


def get_dashboard_data(user_id, user_role):
    """Get comprehensive dashboard data."""
    # Get statistics
    client_stats = get_client_stats()
    
    if user_role == 'admin' or user_role == 'manager':
        task_stats = get_task_stats()
        overdue_tasks = get_overdue_tasks()
    else:
        task_stats = get_task_stats(user_id)
        overdue_tasks = get_overdue_tasks(user_id)
    
    compliance_stats = get_compliance_stats()
    
    # Get upcoming deadlines (next 7 days)
    upcoming_deadlines = get_upcoming_deadlines(7)
    
    # Get today's deadlines
    today_deadlines = [d for d in upcoming_deadlines if d['due_date'] == str(date.today())]
    
    # Get overdue compliance
    overdue_compliance = get_overdue_deadlines()
    
    # Get recent activities
    if user_role == 'admin':
        recent_activities = get_recent_activities(limit=10)
    else:
        recent_activities = get_recent_activities(user_id, limit=10)
    
    # Calculate task completion rate
    if task_stats['total'] > 0:
        completion_rate = round((task_stats['completed'] / task_stats['total']) * 100, 1)
    else:
        completion_rate = 0
    
    return {
        'client_stats': client_stats,
        'task_stats': task_stats,
        'compliance_stats': compliance_stats,
        'upcoming_deadlines': upcoming_deadlines,
        'today_deadlines': today_deadlines,
        'overdue_deadlines': overdue_compliance,
        'overdue_tasks': overdue_tasks,
        'recent_activities': recent_activities,
        'completion_rate': completion_rate
    }


def get_analytics_data(user_id=None):
    """Get data for analytics charts."""
    # Task status distribution
    if user_id:
        task_status_query = """
            SELECT status, COUNT(*) as count
            FROM tasks WHERE assigned_to = ?
            GROUP BY status
        """
        task_status = query_db(task_status_query, (user_id,))
    else:
        task_status_query = "SELECT status, COUNT(*) as count FROM tasks GROUP BY status"
        task_status = query_db(task_status_query)
    
    # Task priority distribution
    priority_query = """
        SELECT priority, COUNT(*) as count
        FROM tasks {}
        GROUP BY priority
    """.format("WHERE assigned_to = ?" if user_id else "")
    
    task_priority = query_db(priority_query, (user_id,) if user_id else ())
    
    # Monthly compliance completion
    monthly_compliance_query = """
        SELECT strftime('%Y-%m', due_date) as month, 
               status, COUNT(*) as count
        FROM compliance_deadlines
        WHERE due_date >= date('now', '-6 months')
        GROUP BY month, status
        ORDER BY month
    """
    monthly_compliance = query_db(monthly_compliance_query)
    
    # Tasks by client (top 10)
    tasks_by_client_query = """
        SELECT c.company_name, COUNT(t.id) as task_count
        FROM clients c
        LEFT JOIN tasks t ON c.id = t.client_id
        GROUP BY c.id
        ORDER BY task_count DESC
        LIMIT 10
    """
    tasks_by_client = query_db(tasks_by_client_query)
    
    return {
        'task_status': [dict(row) for row in task_status],
        'task_priority': [dict(row) for row in task_priority],
        'monthly_compliance': [dict(row) for row in monthly_compliance],
        'tasks_by_client': [dict(row) for row in tasks_by_client]
    }
