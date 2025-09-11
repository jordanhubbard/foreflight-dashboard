#!/usr/bin/env python3
"""
Simple standalone script to create test accounts without Flask app context issues.
"""

import os
import json
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from flask_security.utils import get_hmac
from passlib.hash import bcrypt

def create_test_accounts():
    """Create test accounts directly using SQLAlchemy."""
    
    # Database setup
    data_dir = os.path.join(os.getcwd(), 'data')
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, 'app.db')
    database_url = f'sqlite:///{db_path}'
    
    print(f"📊 Connecting to database: {db_path}")
    
    engine = create_engine(database_url)
    
    # Load accounts from JSON
    if not os.path.exists('test-accounts.json'):
        print("❌ test-accounts.json not found")
        return False
    
    with open('test-accounts.json', 'r') as f:
        data = json.load(f)
    
    accounts = data.get('accounts', [])
    print(f"📋 Found {len(accounts)} accounts to create")
    
    created_count = 0
    
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        
        try:
            for account in accounts:
                email = account['email']
                password = account['password']
                first_name = account['first_name']
                last_name = account['last_name']
                roles = account.get('roles', ['pilot'])
                
                # Check if user already exists
                result = conn.execute(
                    text("SELECT id FROM user WHERE email = :email"),
                    {"email": email}
                )
                
                if result.fetchone():
                    print(f"⚠️  User {email} already exists, skipping")
                    continue
                
                # Create password hash using Flask-Security-Too compatible method
                # We need to set up the HMAC salt manually since we're outside Flask context
                import hashlib
                import hmac
                salt = 'dev-secret-key'  # Use the same salt as in the app config
                hmac_password = hmac.new(salt.encode('utf-8'), password.encode('utf-8'), hashlib.sha512).hexdigest()
                hashed_password = bcrypt.hash(hmac_password)
                
                # Generate unique identifier
                import uuid
                fs_uniquifier = str(uuid.uuid4()).replace('-', '')
                
                # Insert user
                result = conn.execute(
                    text("""
                        INSERT INTO user (
                            email, password, active, fs_uniquifier, confirmed_at,
                            first_name, last_name, pilot_certificate_number, 
                            student_pilot, created_at, login_count, preferences
                        ) VALUES (
                            :email, :password, :active, :fs_uniquifier, :confirmed_at,
                            :first_name, :last_name, :pilot_certificate_number,
                            :student_pilot, :created_at, :login_count, :preferences
                        )
                    """),
                    {
                        "email": email,
                        "password": hashed_password,
                        "active": True,
                        "fs_uniquifier": fs_uniquifier,
                        "confirmed_at": datetime.now(),
                        "first_name": first_name,
                        "last_name": last_name,
                        "pilot_certificate_number": account.get('pilot_certificate_number'),
                        "student_pilot": account.get('student_pilot', False),
                        "created_at": datetime.now(),
                        "login_count": 0,
                        "preferences": "{}"
                    }
                )
                
                user_id = result.lastrowid
                
                # Add roles
                for role_name in roles:
                    # Get role ID
                    role_result = conn.execute(
                        text("SELECT id FROM role WHERE name = :name"),
                        {"name": role_name}
                    )
                    role_row = role_result.fetchone()
                    
                    if role_row:
                        role_id = role_row[0]
                        # Insert user-role relationship
                        conn.execute(
                            text("INSERT INTO roles_users (user_id, role_id) VALUES (:user_id, :role_id)"),
                            {"user_id": user_id, "role_id": role_id}
                        )
                
                print(f"✅ Created user: {email} with roles: {roles}")
                created_count += 1
            
            # Commit transaction
            trans.commit()
            
            print(f"\n🎉 Successfully created {created_count} test accounts!")
            
            # Verify accounts were created
            result = conn.execute(text("SELECT email, first_name, last_name FROM user"))
            print("\n📋 All users in database:")
            for row in result:
                print(f"  - {row[0]} ({row[1]} {row[2]})")
            
            return True
            
        except Exception as e:
            trans.rollback()
            print(f"❌ Error creating accounts: {e}")
            return False

if __name__ == '__main__':
    success = create_test_accounts()
    sys.exit(0 if success else 1)
