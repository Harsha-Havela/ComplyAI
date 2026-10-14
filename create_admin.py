#!/usr/bin/env python3
"""
Manual Admin Creation Script
Creates the default admin user for Firebase
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up the application context
from app import create_app
from app.controllers.firebase_auth_controller import register_user, query_documents
from app.models.firebase_database import Collections

def create_admin():
    """Create admin user manually."""
    try:
        app = create_app('development')
        
        with app.app_context():
            print("🔍 Checking for existing users...")
            
            # Check if admin already exists
            existing_users = query_documents(Collections.USERS, limit=5)
            
            print(f"📊 Found {len(existing_users)} existing users")
            
            for user in existing_users:
                print(f"   - {user.get('username')} ({user.get('role')})")
            
            # Check if admin exists
            admin_exists = any(user.get('username') == 'admin' for user in existing_users)
            
            if admin_exists:
                print("✅ Admin user already exists!")
                return True
            
            print("👤 Creating admin user...")
            
            # Create admin user
            success, result = register_user(
                username='admin',
                email='admin@complyai.com',
                password='Admin123',
                full_name='System Administrator',
                role='admin'
            )
            
            if success:
                print(f"✅ Admin created successfully! ID: {result}")
                return True
            else:
                print(f"❌ Failed to create admin: {result}")
                return False
                
    except Exception as e:
        print(f"❌ Error in create_admin: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    try:
        create_admin()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()