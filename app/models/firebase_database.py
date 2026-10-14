"""
Firebase Database Module
Handles all Firestore operations and provides SQL-like interface
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from google.cloud import firestore
from google.cloud.firestore import Query
from app.config.firebase_config import get_firestore_db


class FirestoreDB:
    """Firestore database operations with SQL-like interface."""
    
    def __init__(self):
        try:
            self.db = get_firestore_db()
        except Exception as e:
            print(f"⚠️ Firebase not available: {e}")
            self.db = None
    
    def _check_connection(self):
        """Check if Firebase connection is available."""
        if self.db is None:
            raise Exception("Firebase not configured. Please set up Firebase credentials.")
    
    # CRUD Operations
    
    def create(self, collection: str, data: Dict[str, Any], doc_id: str = None) -> str:
        """
        Create a new document in collection.
        
        Args:
            collection: Collection name
            data: Document data
            doc_id: Optional document ID (auto-generated if None)
            
        Returns:
            str: Document ID
        """
        self._check_connection()
        
        # Add timestamps
        data['created_at'] = datetime.now()
        data['updated_at'] = datetime.now()
        
        if doc_id:
            doc_ref = self.db.collection(collection).document(doc_id)
            doc_ref.set(data)
            return doc_id
        else:
            doc_ref = self.db.collection(collection).add(data)[1]
            return doc_ref.id
    
    def get_by_id(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document by ID.
        
        Args:
            collection: Collection name
            doc_id: Document ID
            
        Returns:
            Document data or None if not found
        """
        doc_ref = self.db.collection(collection).document(doc_id)
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None
    
    def update(self, collection: str, doc_id: str, data: Dict[str, Any]) -> bool:
        """
        Update document by ID.
        
        Args:
            collection: Collection name
            doc_id: Document ID
            data: Updated fields
            
        Returns:
            bool: Success status
        """
        try:
            data['updated_at'] = datetime.now()
            doc_ref = self.db.collection(collection).document(doc_id)
            doc_ref.update(data)
            return True
        except Exception:
            return False
    
    def delete(self, collection: str, doc_id: str) -> bool:
        """
        Delete document by ID.
        
        Args:
            collection: Collection name
            doc_id: Document ID
            
        Returns:
            bool: Success status
        """
        try:
            doc_ref = self.db.collection(collection).document(doc_id)
            doc_ref.delete()
            return True
        except Exception:
            return False
    
    # Query Operations
    
    def get_all(self, collection: str, limit: int = None, order_by: str = None, 
                direction: str = 'asc') -> List[Dict[str, Any]]:
        """
        Get all documents from collection.
        
        Args:
            collection: Collection name
            limit: Optional limit
            order_by: Optional field to order by
            direction: Sort direction ('asc' or 'desc')
            
        Returns:
            List of documents
        """
        query = self.db.collection(collection)
        
        if order_by:
            direction_enum = Query.DESCENDING if direction == 'desc' else Query.ASCENDING
            query = query.order_by(order_by, direction=direction_enum)
        
        if limit:
            query = query.limit(limit)
        
        docs = query.stream()
        results = []
        
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            results.append(data)
        
        return results
    
    def query(self, collection: str, filters: List[tuple] = None, 
              limit: int = None, order_by: str = None) -> List[Dict[str, Any]]:
        """
        Query documents with filters.
        
        Args:
            collection: Collection name
            filters: List of (field, operator, value) tuples
            limit: Optional limit
            order_by: Optional field to order by
            
        Returns:
            List of matching documents
        """
        query = self.db.collection(collection)
        
        # Apply filters
        if filters:
            for field, operator, value in filters:
                query = query.where(field, operator, value)
        
        # Apply ordering
        if order_by:
            query = query.order_by(order_by)
        
        # Apply limit
        if limit:
            query = query.limit(limit)
        
        docs = query.stream()
        results = []
        
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            results.append(data)
        
        return results
    
    def count(self, collection: str, filters: List[tuple] = None) -> int:
        """
        Count documents in collection.
        
        Args:
            collection: Collection name
            filters: Optional filters
            
        Returns:
            int: Document count
        """
        query = self.db.collection(collection)
        
        if filters:
            for field, operator, value in filters:
                query = query.where(field, operator, value)
        
        # Get count (Firestore doesn't have direct count, so we fetch and count)
        docs = query.stream()
        return len(list(docs))
    
    def search(self, collection: str, field: str, search_term: str, 
               limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search documents by field containing search term.
        
        Args:
            collection: Collection name
            field: Field to search
            search_term: Search term
            limit: Optional limit
            
        Returns:
            List of matching documents
        """
        # Firestore doesn't support full-text search, so we use range queries
        # for prefix matching
        search_term = search_term.lower()
        
        query = self.db.collection(collection)
        query = query.where(field, '>=', search_term)
        query = query.where(field, '<=', search_term + '\uf8ff')
        
        if limit:
            query = query.limit(limit)
        
        docs = query.stream()
        results = []
        
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            
            # Additional client-side filtering for better matching
            if field in data and search_term in str(data[field]).lower():
                results.append(data)
        
        return results


# Global instance
firestore_db = FirestoreDB()


# Collection Constants
class Collections:
    USERS = 'users'
    CLIENTS = 'clients' 
    TASKS = 'tasks'
    COMPLIANCE = 'compliance_deadlines'
    ACTIVITY_LOGS = 'activity_logs'
    COMMENTS = 'comments'


# Helper functions to maintain compatibility with existing code

def create_document(collection: str, data: Dict[str, Any], doc_id: str = None) -> str:
    """Create document - compatible with existing code."""
    return firestore_db.create(collection, data, doc_id)


def get_document(collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
    """Get document by ID - compatible with existing code."""
    return firestore_db.get_by_id(collection, doc_id)


def update_document(collection: str, doc_id: str, data: Dict[str, Any]) -> bool:
    """Update document - compatible with existing code."""
    return firestore_db.update(collection, doc_id, data)


def delete_document(collection: str, doc_id: str) -> bool:
    """Delete document - compatible with existing code."""
    return firestore_db.delete(collection, doc_id)


def query_documents(collection: str, filters: List[tuple] = None, 
                   limit: int = None, order_by: str = None) -> List[Dict[str, Any]]:
    """Query documents - compatible with existing code."""
    return firestore_db.query(collection, filters, limit, order_by)


def get_all_documents(collection: str, limit: int = None, 
                     order_by: str = None) -> List[Dict[str, Any]]:
    """Get all documents - compatible with existing code."""
    return firestore_db.get_all(collection, limit, order_by)


def count_documents(collection: str, filters: List[tuple] = None) -> int:
    """Count documents - compatible with existing code."""
    return firestore_db.count(collection, filters)


def search_documents(collection: str, field: str, search_term: str) -> List[Dict[str, Any]]:
    """Search documents - compatible with existing code."""
    return firestore_db.search(collection, field, search_term)


def init_firebase_collections():
    """Initialize Firebase collections and indexes."""
    print("🔥 Initializing Firebase collections...")
    
    # Collections will be created automatically when first document is added
    # But we can set up security rules and indexes here if needed
    
    collections_to_init = [
        Collections.USERS,
        Collections.CLIENTS,
        Collections.TASKS, 
        Collections.COMPLIANCE,
        Collections.ACTIVITY_LOGS,
        Collections.COMMENTS
    ]
    
    for collection in collections_to_init:
        print(f"✅ Collection '{collection}' ready")
    
    print("🔥 Firebase collections initialized")


# Compatibility layer for existing database.py functions

def query_db(query_type: str, collection: str, filters: List[tuple] = None, 
             doc_id: str = None, one: bool = False) -> Any:
    """
    Compatibility function for existing query_db calls.
    This helps transition from SQL to Firestore with minimal code changes.
    """
    if query_type == 'SELECT':
        if doc_id:
            result = get_document(collection, doc_id)
            return result if result else (None if one else [])
        else:
            results = query_documents(collection, filters)
            return results[0] if (one and results) else results
    
    return None


def execute_db(operation: str, collection: str, data: Dict[str, Any] = None, 
               doc_id: str = None) -> Any:
    """
    Compatibility function for existing execute_db calls.
    """
    if operation == 'INSERT':
        return create_document(collection, data, doc_id)
    elif operation == 'UPDATE' and doc_id:
        success = update_document(collection, doc_id, data)
        return 1 if success else 0
    elif operation == 'DELETE' and doc_id:
        success = delete_document(collection, doc_id)
        return 1 if success else 0
    
    return 0