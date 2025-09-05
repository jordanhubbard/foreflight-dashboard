#!/usr/bin/env python3
"""Database initialization script for ForeFlight Dashboard."""

import os
import sys
from datetime import datetime, timezone

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from core.auth_models import db, User, Role
from core.security import create_user_datastore, create_default_admin
from flask import Flask

def create_app():
    """Create Flask app for database initialization."""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    # Ensure data directory exists
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
    app.config['SECURITY_PASSWORD_SALT'] = 'dev-salt'
    
    # Initialize database
    db.init_app(app)
    
    return app

def init_database():
    """Initialize the database with tables and default data."""
    app = create_app()
    
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        
        print("Creating default roles...")
        user_datastore = create_user_datastore()
        
        # Create default roles
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
        
        # Create default admin user
        print("Creating default admin user...")
        create_default_admin(app, user_datastore)
        
        print("Database initialization complete!")
        print("\nDefault admin credentials:")
        print("Email: admin@foreflight-dashboard.com")
        print("Password: admin123")
        print("\nTo create additional test accounts, run: make test-accounts")
        print("Please change the admin password after first login!")

if __name__ == '__main__':
    init_database()
