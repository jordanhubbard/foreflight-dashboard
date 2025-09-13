#!/usr/bin/env python3
"""Database initialization script for ForeFlight Dashboard."""

import os
import sys
from datetime import datetime, timezone

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from core.database import SessionLocal, engine, Base, init_database
from core.auth import create_default_admin_user


def init_db_script():
    """Initialize database with tables and default data."""
    print("Creating database tables...")
    
    try:
        # Initialize database tables
        init_database()
        
        # Create default admin user
        print("Creating default admin user...")
        db_session = SessionLocal()
        try:
            admin_user = create_default_admin_user(db_session)
            db_session.commit()
            
            print("Database initialization complete!")
            print(f"\nDefault admin credentials:")
            print(f"Email: {admin_user.email}")
            print(f"Password: admin123")
            print("\nPlease change the admin password after first login!")
            
        finally:
            db_session.close()
            
    except Exception as e:
        print(f"Error during database initialization: {e}")
        raise


if __name__ == '__main__':
    init_db_script()