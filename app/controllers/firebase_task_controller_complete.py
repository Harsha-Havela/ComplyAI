"""
Firebase Task Controller - Complete Version
Handles all task management business logic with Firestore
"""
from datetime import datetime, timedelta
from app.models.firebase_database import (
    Collections, create_document, get_document, update_document,
    delete_document, query_documents, search_documents, count_documents
)
from app.services.firebase_activity_service import log_activity


def create_task(title, description, client_id, assigned_to, priority, 
               due_date, reminder_date, created_by):
    """
    Create a new task.
    
    Args:
        title: Task title (required)
        description: Task description
        client_id: ID of the