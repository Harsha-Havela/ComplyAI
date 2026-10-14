"""
Application Configuration
Manages all environment-specific settings
"""
import os
from datetime import timedelta


class Config:
    """Base configuration class."""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = False
    TESTING = False
    
    # Session settings
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Database settings - Firebase Firestore (no local database file needed)
    FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID')
    FIREBASE_SERVICE_ACCOUNT_PATH = os.environ.get('FIREBASE_SERVICE_ACCOUNT_PATH')
    FIREBASE_CREDENTIALS = os.environ.get('FIREBASE_CREDENTIALS')
    
    # Legacy database path (for reference, not used with Firebase)
    # DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database', 'complyai.db')
    
    # Upload settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png'}
    
    # Email settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@complyai.com'
    
    # Google Gemini API
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    
    # Pagination
    ITEMS_PER_PAGE = 10
    
    # Application settings
    APP_NAME = 'ComplyAI'
    APP_VERSION = '1.0.0'


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False


class TestingConfig(Config):
    """Testing environment configuration."""
    TESTING = True
    # For testing, we can use Firebase emulator or a test project
    FIREBASE_PROJECT_ID = 'test-project'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
