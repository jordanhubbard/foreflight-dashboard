#!/usr/bin/env python3
"""CLI commands for account management."""

import os
import sys
from flask import Flask

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.auth_models import db
from core.account_manager import AccountManager
from core.security import create_user_datastore


def create_app():
    """Create Flask app for CLI commands."""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    
    # Database configuration
    data_dir = os.path.join(os.getcwd(), 'data')
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, 'app.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{db_path}')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Flask-Security-Too configuration
    app.config['SECURITY_JOIN_USER_ROLES'] = True
    app.config['WTF_CSRF_CHECK_DEFAULT'] = False
    app.config['SECURITY_PASSWORD_SINGLE_HASH'] = False
    app.config['SECURITY_PASSWORD_HASH'] = 'bcrypt'
    app.config['SECURITY_PASSWORD_SALT'] = app.config.get('SECRET_KEY', 'dev-secret-key')
    
    # Initialize database
    db.init_app(app)
    
    return app


def create_test_accounts(json_file_path: str = 'test-accounts.json'):
    """Create test accounts from JSON file.
    
    Args:
        json_file_path: Path to the JSON file containing account definitions
    """
    print(f"Creating test accounts from {json_file_path}...")
    
    app = create_app()
    
    try:
        with app.app_context():
            # Ensure database tables exist
            db.create_all()
            
            # Create default roles if they don't exist
            user_datastore = create_user_datastore()
            roles = [
                ('admin', 'Administrator - Full access to all features'),
                ('pilot', 'Certified Pilot - Access to all pilot features'),
                ('student', 'Student Pilot - Access to student-specific features'),
                ('instructor', 'Flight Instructor - Can manage student endorsements')
            ]
            
            for role_name, description in roles:
                if not user_datastore.find_role(role_name):
                    user_datastore.create_role(name=role_name, description=description)
                    print(f"Created role: {role_name}")
            
            db.session.commit()
            
            # Create accounts from JSON
            manager = AccountManager(app)
            
            # Validate the JSON file first
            if not manager.validate_accounts_json(json_file_path):
                print("❌ Account validation failed. Please check the JSON file.")
                return False
            
            # Create accounts and collect basic info for summary
            created_users = manager.create_accounts_from_json(json_file_path)
            
            # Collect user info while still in session
            user_info = []
            for user in created_users:
                roles_list = [role.name for role in user.roles]
                user_info.append({
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'roles': roles_list
                })
            
            # Final commit and close
            db.session.commit()
        
        # Print summary outside of app context
        print(f"✅ Successfully created {len(created_users)} test accounts!")
        print("\n📋 Created accounts:")
        for info in user_info:
            roles_str = ', '.join(info['roles'])
            print(f"  - {info['email']} ({info['first_name']} {info['last_name']}) - Roles: [{roles_str}]")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating test accounts: {e}")
        return False


def validate_accounts_file(json_file_path: str = 'test-accounts.json'):
    """Validate test accounts JSON file.
    
    Args:
        json_file_path: Path to the JSON file containing account definitions
    """
    print(f"Validating account definitions in {json_file_path}...")
    
    try:
        from core.account_manager import validate_accounts_file
        if validate_accounts_file(json_file_path):
            print("✅ All account definitions are valid!")
            return True
        else:
            print("❌ Some account definitions are invalid.")
            return False
    except Exception as e:
        print(f"❌ Error validating accounts file: {e}")
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Account management CLI')
    parser.add_argument('command', choices=['create', 'validate'], 
                       help='Command to execute')
    parser.add_argument('--file', '-f', default='test-accounts.json',
                       help='Path to the accounts JSON file (default: test-accounts.json)')
    
    args = parser.parse_args()
    
    if args.command == 'create':
        success = create_test_accounts(args.file)
        sys.exit(0 if success else 1)
    elif args.command == 'validate':
        success = validate_accounts_file(args.file)
        sys.exit(0 if success else 1)
