"""
Controllers Package
Business logic and orchestration
"""
from app.controllers.auth_controller import (
    authenticate_user,
    register_user,
    logout_user,
    change_password,
    get_user_by_id,
    get_all_users,
    update_user_status
)

from app.controllers.client_controller import (
    create_client,
    get_client_by_id,
    get_all_clients,
    update_client,
    delete_client,
    update_client_status,
    search_clients,
    get_clients_by_status,
    get_client_statistics
)

from app.controllers.task_controller import (
    create_task,
    get_task_by_id,
    get_all_tasks,
    update_task,
    delete_task,
    update_task_status,
    assign_task,
    search_tasks,
    get_task_statistics,
    get_tasks_by_priority,
    get_overdue_tasks,
    add_task_comment,
    get_task_comments
)

from app.controllers.compliance_controller import (
    create_compliance_deadline,
    get_compliance_by_id,
    get_all_compliance,
    update_compliance,
    delete_compliance,
    update_compliance_status,
    get_overdue_compliance,
    get_upcoming_compliance,
    get_compliance_statistics,
    search_compliance,
    get_compliance_types,
    auto_generate_recurring_compliance,
    mark_overdue_compliance
)

__all__ = [
    'authenticate_user',
    'register_user',
    'logout_user',
    'change_password',
    'get_user_by_id',
    'get_all_users',
    'update_user_status',
    'create_client',
    'get_client_by_id',
    'get_all_clients',
    'update_client',
    'delete_client',
    'update_client_status',
    'search_clients',
    'get_clients_by_status',
    'get_client_statistics',
    'create_task',
    'get_task_by_id',
    'get_all_tasks',
    'update_task',
    'delete_task',
    'update_task_status',
    'assign_task',
    'search_tasks',
    'get_task_statistics',
    'get_tasks_by_priority',
    'get_overdue_tasks',
    'add_task_comment',
    'get_task_comments',
    'create_compliance_deadline',
    'get_compliance_by_id',
    'get_all_compliance',
    'update_compliance',
    'delete_compliance',
    'update_compliance_status',
    'get_overdue_compliance',
    'get_upcoming_compliance',
    'get_compliance_statistics',
    'search_compliance',
    'get_compliance_types',
    'auto_generate_recurring_compliance',
    'mark_overdue_compliance'
]
