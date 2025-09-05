#!/usr/bin/env python3
"""Account management utilities for creating test and production accounts."""

import json
import os
from datetime import datetime
from typing import List, Dict, Any
from flask import Flask
from flask_security.utils import get_hmac
from passlib.hash import bcrypt

from .auth_models import db, User, Role
from .security import create_user_datastore


class AccountManager:
    """Manages account creation from JSON definitions."""
    
    def __init__(self, app: Flask):
        """Initialize the account manager with Flask app context."""
        self.app = app
        self.user_datastore = create_user_datastore()
    
    def load_accounts_from_json(self, json_file_path: str) -> List[Dict[str, Any]]:
        """Load account definitions from a JSON file.
        
        Args:
            json_file_path: Path to the JSON file containing account definitions
            
        Returns:
            List of account dictionaries
            
        Raises:
            FileNotFoundError: If the JSON file doesn't exist
            json.JSONDecodeError: If the JSON is invalid
        """
        if not os.path.exists(json_file_path):
            raise FileNotFoundError(f"Account definition file not found: {json_file_path}")
        
        with open(json_file_path, 'r') as f:
            data = json.load(f)
        
        if 'accounts' not in data:
            raise ValueError("JSON file must contain an 'accounts' key with a list of account definitions")
        
        return data['accounts']
    
    def create_account(self, account_def: Dict[str, Any]) -> User:
        """Create a single account from a definition dictionary.
        
        Args:
            account_def: Dictionary containing account information
            
        Returns:
            Created User object
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        required_fields = ['email', 'password', 'first_name', 'last_name']
        for field in required_fields:
            if field not in account_def:
                raise ValueError(f"Missing required field: {field}")
        
        email = account_def['email']
        password = account_def['password']
        first_name = account_def['first_name']
        last_name = account_def['last_name']
        
        # Optional fields with defaults
        student_pilot = account_def.get('student_pilot', False)
        pilot_certificate_number = account_def.get('pilot_certificate_number')
        roles = account_def.get('roles', ['pilot'])
        
        # Check if user already exists
        existing_user = self.user_datastore.find_user(email=email)
        if existing_user:
            print(f"User {email} already exists, skipping creation")
            return existing_user
        
        # Create password hash using Flask-Security-Too's method
        with self.app.app_context():
            hmac_password = get_hmac(password)
            hashed_password = bcrypt.hash(hmac_password)
        
        # Get roles
        user_roles = []
        for role_name in roles:
            role = self.user_datastore.find_role(role_name)
            if not role:
                print(f"Warning: Role '{role_name}' not found for user {email}")
            else:
                user_roles.append(role)
        
        # Create user
        user = self.user_datastore.create_user(
            email=email,
            password=hashed_password,
            first_name=first_name,
            last_name=last_name,
            pilot_certificate_number=pilot_certificate_number,
            student_pilot=student_pilot,
            roles=user_roles,
            confirmed_at=datetime.now()
        )
        
        db.session.commit()
        print(f"Created user: {email} with roles: {[r.name for r in user_roles]}")
        
        # Create user directory
        from .security import create_user_directory
        create_user_directory(user)
        
        return user
    
    def create_accounts_from_json(self, json_file_path: str) -> List[User]:
        """Create multiple accounts from a JSON file.
        
        Args:
            json_file_path: Path to the JSON file containing account definitions
            
        Returns:
            List of created User objects
        """
        accounts_data = self.load_accounts_from_json(json_file_path)
        created_users = []
        
        with self.app.app_context():
            for account_def in accounts_data:
                try:
                    user = self.create_account(account_def)
                    created_users.append(user)
                except Exception as e:
                    print(f"Error creating account {account_def.get('email', 'unknown')}: {e}")
                    continue
        
        print(f"Successfully created {len(created_users)} accounts")
        return created_users
    
    def validate_account_definition(self, account_def: Dict[str, Any]) -> bool:
        """Validate an account definition dictionary.
        
        Args:
            account_def: Dictionary containing account information
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['email', 'password', 'first_name', 'last_name']
        
        # Check required fields
        for field in required_fields:
            if field not in account_def:
                print(f"Missing required field: {field}")
                return False
        
        # Validate email format (basic check)
        email = account_def['email']
        if '@' not in email or '.' not in email:
            print(f"Invalid email format: {email}")
            return False
        
        # Validate roles
        roles = account_def.get('roles', [])
        valid_roles = ['admin', 'pilot', 'student', 'instructor']
        for role in roles:
            if role not in valid_roles:
                print(f"Invalid role: {role}. Valid roles are: {valid_roles}")
                return False
        
        return True
    
    def validate_accounts_json(self, json_file_path: str) -> bool:
        """Validate all account definitions in a JSON file.
        
        Args:
            json_file_path: Path to the JSON file containing account definitions
            
        Returns:
            True if all accounts are valid, False otherwise
        """
        try:
            accounts_data = self.load_accounts_from_json(json_file_path)
        except Exception as e:
            print(f"Error loading JSON file: {e}")
            return False
        
        all_valid = True
        for i, account_def in enumerate(accounts_data):
            print(f"Validating account {i + 1}: {account_def.get('email', 'unknown')}")
            if not self.validate_account_definition(account_def):
                all_valid = False
        
        return all_valid


def create_accounts_from_file(app: Flask, json_file_path: str) -> List[User]:
    """Convenience function to create accounts from a JSON file.
    
    Args:
        app: Flask application instance
        json_file_path: Path to the JSON file containing account definitions
        
    Returns:
        List of created User objects
    """
    manager = AccountManager(app)
    return manager.create_accounts_from_json(json_file_path)


def validate_accounts_file(json_file_path: str) -> bool:
    """Convenience function to validate accounts JSON file without Flask app.
    
    Args:
        json_file_path: Path to the JSON file containing account definitions
        
    Returns:
        True if valid, False otherwise
    """
    # Create a minimal Flask app for validation
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'validation-key'
    
    manager = AccountManager(app)
    return manager.validate_accounts_json(json_file_path)
