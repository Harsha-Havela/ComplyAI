#!/usr/bin/env python3
"""
ComplyAI - Tax Compliance Management System
Entry point for the Flask application with Firebase backend
"""
from app import create_app
import os

if __name__ == '__main__':
    # Load environment variables from .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Environment variables loaded from .env")
    except ImportError:
        print("⚠️ python-dotenv not installed, using system environment variables")
    except Exception as e:
        print(f"⚠️ Could not load .env file: {e}")
    
    # Create Flask app with Firebase
    print("🔥 Starting ComplyAI with Firebase Firestore!")
    print("="*50)
    
    try:
        app = create_app('development')
        
        print("📊 Database: Firebase Firestore (Cloud)")
        print("🔐 Authentication: Firebase Admin SDK") 
        print("🌐 URL: http://127.0.0.1:5000")
        print("👤 Default Login: admin / Admin123")
        print("="*50)
        
        # Run the application
        port = int(os.environ.get('PORT', 5000))
        app.run(
            host='127.0.0.1', 
            port=port,
            debug=True,
            threaded=True
        )
        
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Run: python install_firebase.py")
        print("2. Set up Firebase credentials in .env file")
        print("3. See FIREBASE_SETUP.md for detailed instructions")
        exit(1)

else:
    # For production deployment (Heroku, etc.)
    app = create_app(os.getenv('FLASK_ENV', 'default'))
