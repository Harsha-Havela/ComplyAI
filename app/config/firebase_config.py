"""
Firebase Configuration
Handles Firebase/Firestore initialization and connection
"""
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from flask import current_app


class FirebaseConfig:
    """Firebase configuration and initialization."""
    
    _db = None
    _app = None
    
    @classmethod
    def initialize_firebase(cls):
        """Initialize Firebase Admin SDK."""
        if cls._app is not None:
            return cls._db
        
        try:
            # Try to get credentials from environment variable (JSON string)
            firebase_credentials = os.environ.get('FIREBASE_CREDENTIALS')
            
            if firebase_credentials:
                # Parse JSON credentials from environment
                cred_dict = json.loads(firebase_credentials)
                cred = credentials.Certificate(cred_dict)
            else:
                # Try to load from service account file
                service_account_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT_PATH')
                if service_account_path and os.path.exists(service_account_path):
                    cred = credentials.Certificate(service_account_path)
                else:
                    # For development - create a mock configuration
                    print("⚠️ Firebase credentials not found. Creating development mode.")
                    print("Please set FIREBASE_CREDENTIALS or FIREBASE_SERVICE_ACCOUNT_PATH")
                    
                    # Return None to indicate Firebase is not available
                    return None
            
            # Initialize Firebase with credentials
            if not firebase_admin._apps:
                cls._app = firebase_admin.initialize_app(cred)
            else:
                cls._app = firebase_admin.get_app()
            
            # Initialize Firestore
            cls._db = firestore.client()
            
            print("✅ Firebase initialized successfully")
            return cls._db
            
        except Exception as e:
            print(f"❌ Firebase initialization failed: {e}")
            print("📖 See README.md for Firebase setup instructions")
            raise e
    
    @classmethod
    def get_db(cls):
        """Get Firestore database instance."""
        if cls._db is None:
            cls._db = cls.initialize_firebase()
        return cls._db
    
    @classmethod 
    def reset_connection(cls):
        """Reset Firebase connection (useful for testing)."""
        cls._db = None
        cls._app = None
        
        # Delete all Firebase apps
        for app in firebase_admin._apps.values():
            firebase_admin.delete_app(app)


def get_firestore_db():
    """
    Get Firestore database instance.
    
    Returns:
        google.cloud.firestore.Client: Firestore database client
    """
    return FirebaseConfig.get_db()


def init_firebase_app(app):
    """
    Initialize Firebase with Flask app.
    
    Args:
        app: Flask application instance
    """
    with app.app_context():
        FirebaseConfig.initialize_firebase()
        print("🔥 Firebase integrated with Flask app")