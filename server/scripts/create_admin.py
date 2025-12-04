"""
Create Initial Admin User
==========================

Script to create the first admin account.
Run this once to bootstrap your admin access.

Usage:
    python create_admin.py

Author: Travel Agent P Team
Date: December 4, 2025
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.di_container import DIContainer
from app.service.auth_service import AuthService
from app import create_app


def create_initial_admin():
    """Create the first admin user."""
    print("=" * 60)
    print("CREATE INITIAL ADMIN USER")
    print("=" * 60)
    
    # Create Flask app and push application context
    print("\n⏳ Initializing Flask application...")
    app = create_app()
    
    with app.app_context():
        # Get AuthService from DI container (already initialized by create_app)
        container = DIContainer.get_instance()
        auth_service = container.resolve('AuthService')
        
        # Get admin credentials
        print("\nEnter admin credentials:")
        username = input("Username (default: admin): ").strip() or "admin"
        password = input("Password (min 8 chars): ").strip()
        
        while len(password) < 8:
            print("❌ Password must be at least 8 characters!")
            password = input("Password (min 8 chars): ").strip()
        
        email = input("Email (optional, press Enter to skip): ").strip() or None
        name = input("Display name (optional): ").strip() or username
        
        print("\n" + "-" * 60)
        print("Creating admin user...")
        print(f"Username: {username}")
        print(f"Email: {email or '(not set)'}")
        print(f"Name: {name}")
        print("-" * 60)
        
        # Create admin
        admin = auth_service.create_admin_user(
            username=username,
            password=password,
            email=email,
            name=name
        )
        
        if admin:
            print("\n✅ ADMIN USER CREATED SUCCESSFULLY!")
            print(f"\nAdmin Details:")
            print(f"  ID: {admin.id}")
            print(f"  Username: {admin.username}")
            print(f"  Email: {admin.email}")
            print(f"  Name: {admin.name}")
            print(f"  Roles: {[r.role_name for r in admin.roles]}")
            print(f"\n🔐 You can now login at:")
            print(f"  POST /api/admin/auth/login")
            print(f"  Body: {{\"username\": \"{username}\", \"password\": \"***\"}}")
            print("\n" + "=" * 60)
            return True
        else:
            print("\n❌ FAILED TO CREATE ADMIN USER!")
            print("Username or email may already exist.")
            print("=" * 60)
            return False


if __name__ == "__main__":
    try:
        success = create_initial_admin()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
