import sqlite3
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
import os
from typing import List, Optional, Dict, Any
from src.core.models import InstructorEndorsement
from src.core.user_models import User, UserPreferences, PasswordResetToken, hash_password, verify_password, generate_password_reset_token

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app.db')

def init_db():
    """Initialize the database and create tables if they don't exist."""
    with get_db() as db:
        # Users table
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                pilot_certificate_number TEXT,
                student_pilot BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                is_verified BOOLEAN DEFAULT 0,
                created_at TEXT NOT NULL,
                last_login TEXT,
                preferences TEXT NOT NULL DEFAULT '{}'
            )
        ''')
        
        # Password reset tokens table
        db.execute('''
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expires_at TEXT NOT NULL,
                used BOOLEAN DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # User logbooks table (track uploaded files)
        db.execute('''
            CREATE TABLE IF NOT EXISTS user_logbooks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Instructor endorsements table (updated to be user-specific)
        db.execute('''
            CREATE TABLE IF NOT EXISTS instructor_endorsements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                expiration_date TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Create indexes for better performance
        db.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)')
        db.execute('CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON password_reset_tokens (token)')
        db.execute('CREATE INDEX IF NOT EXISTS idx_user_logbooks_user_id ON user_logbooks (user_id)')
        db.execute('CREATE INDEX IF NOT EXISTS idx_instructor_endorsements_user_id ON instructor_endorsements (user_id)')
        
        db.commit()

@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# User management functions
def create_user(email: str, password: str, first_name: str, last_name: str, 
                pilot_certificate_number: Optional[str] = None, 
                student_pilot: bool = False) -> User:
    """Create a new user."""
    password_hash = hash_password(password)
    preferences = UserPreferences(student_pilot=student_pilot)
    
    with get_db() as db:
        cursor = db.execute('''
            INSERT INTO users (email, password_hash, first_name, last_name, 
                             pilot_certificate_number, student_pilot, created_at, preferences)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (email, password_hash, first_name, last_name, 
              pilot_certificate_number, student_pilot, 
              datetime.now(timezone.utc).isoformat(), preferences.json()))
        db.commit()
        user_id = cursor.lastrowid
        
        # Create user directory
        create_user_directory(user_id, email)
        
        return get_user_by_id(user_id)


def get_user_by_id(user_id: int) -> Optional[User]:
    """Get user by ID."""
    with get_db() as db:
        row = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if not row:
            return None
        return _row_to_user(row)


def get_user_by_email(email: str) -> Optional[User]:
    """Get user by email."""
    with get_db() as db:
        row = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if not row:
            return None
        return _row_to_user(row)


def authenticate_user(email: str, password: str) -> Optional[User]:
    """Authenticate user with email and password."""
    user = get_user_by_email(email)
    if not user or not user.is_active:
        return None
    
    if verify_password(password, user.password_hash):
        # Update last login
        update_user_last_login(user.id)
        return user
    return None


def update_user_last_login(user_id: int):
    """Update user's last login timestamp."""
    with get_db() as db:
        db.execute('''
            UPDATE users SET last_login = ? WHERE id = ?
        ''', (datetime.now(timezone.utc).isoformat(), user_id))
        db.commit()


def update_user_preferences(user_id: int, preferences: UserPreferences):
    """Update user preferences."""
    with get_db() as db:
        db.execute('''
            UPDATE users SET preferences = ? WHERE id = ?
        ''', (preferences.json(), user_id))
        db.commit()


def create_password_reset_token(user_id: int) -> PasswordResetToken:
    """Create a password reset token for a user."""
    token = generate_password_reset_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)  # Token expires in 1 hour
    
    with get_db() as db:
        cursor = db.execute('''
            INSERT INTO password_reset_tokens (user_id, token, expires_at, created_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, token, expires_at.isoformat(), datetime.now(timezone.utc).isoformat()))
        db.commit()
        token_id = cursor.lastrowid
        
        return PasswordResetToken(
            id=token_id,
            user_id=user_id,
            token=token,
            expires_at=expires_at,
            used=False,
            created_at=datetime.now(timezone.utc)
        )


def get_password_reset_token(token: str) -> Optional[PasswordResetToken]:
    """Get password reset token by token string."""
    with get_db() as db:
        row = db.execute('''
            SELECT * FROM password_reset_tokens WHERE token = ? AND used = 0
        ''', (token,)).fetchone()
        if not row:
            return None
        
        return PasswordResetToken(
            id=row['id'],
            user_id=row['user_id'],
            token=row['token'],
            expires_at=datetime.fromisoformat(row['expires_at']),
            used=bool(row['used']),
            created_at=datetime.fromisoformat(row['created_at'])
        )


def use_password_reset_token(token: str, new_password: str) -> bool:
    """Use a password reset token to change password."""
    reset_token = get_password_reset_token(token)
    if not reset_token or not reset_token.is_valid():
        return False
    
    password_hash = hash_password(new_password)
    
    with get_db() as db:
        # Update user password
        db.execute('''
            UPDATE users SET password_hash = ? WHERE id = ?
        ''', (password_hash, reset_token.user_id))
        
        # Mark token as used
        db.execute('''
            UPDATE password_reset_tokens SET used = 1 WHERE id = ?
        ''', (reset_token.id,))
        
        db.commit()
        return True


def create_user_directory(user_id: int, email: str):
    """Create a directory for user files."""
    from src.core.user_models import generate_user_directory_name
    import os
    
    user_dir = generate_user_directory_name(user_id, email)
    user_path = os.path.join('uploads', user_dir)
    os.makedirs(user_path, exist_ok=True)
    
    # Create subdirectories
    os.makedirs(os.path.join(user_path, 'logbooks'), exist_ok=True)
    os.makedirs(os.path.join(user_path, 'exports'), exist_ok=True)
    os.makedirs(os.path.join(user_path, 'backups'), exist_ok=True)


def get_user_directory(user_id: int, email: str) -> str:
    """Get the directory path for user files."""
    from src.core.user_models import generate_user_directory_name
    user_dir = generate_user_directory_name(user_id, email)
    return os.path.join('uploads', user_dir)


def _row_to_user(row) -> User:
    """Convert database row to User object."""
    import json
    
    preferences_data = json.loads(row['preferences']) if row['preferences'] else {}
    preferences = UserPreferences(**preferences_data)
    
    return User(
        id=row['id'],
        email=row['email'],
        first_name=row['first_name'],
        last_name=row['last_name'],
        pilot_certificate_number=row['pilot_certificate_number'],
        student_pilot=bool(row['student_pilot']),
        is_active=bool(row['is_active']),
        is_verified=bool(row['is_verified']),
        created_at=datetime.fromisoformat(row['created_at']),
        last_login=datetime.fromisoformat(row['last_login']) if row['last_login'] else None,
        preferences=preferences,
        password_hash=row['password_hash']
    )


# Legacy endorsement functions (updated for user-specific data)
def add_endorsement(user_id: int, start_date: datetime) -> InstructorEndorsement:
    """Add a new endorsement to the database."""
    expiration_date = InstructorEndorsement.calculate_expiration(start_date)
    with get_db() as db:
        cursor = db.execute('''
            INSERT INTO instructor_endorsements (start_date, expiration_date)
            VALUES (?, ?)
        ''', (start_date.isoformat(), expiration_date.isoformat()))
        db.commit()
        endorsement_id = cursor.lastrowid
        return InstructorEndorsement(
            id=endorsement_id,
            start_date=start_date,
            expiration_date=expiration_date
        )

def get_all_endorsements() -> list[InstructorEndorsement]:
    """Get all endorsements from the database."""
    with get_db() as db:
        rows = db.execute('SELECT * FROM instructor_endorsements').fetchall()
        return [
            InstructorEndorsement(
                id=row['id'],
                start_date=datetime.fromisoformat(row['start_date']),
                expiration_date=datetime.fromisoformat(row['expiration_date'])
            )
            for row in rows
        ]

def delete_endorsement(endorsement_id: int) -> bool:
    """Delete an endorsement from the database."""
    with get_db() as db:
        cursor = db.execute('DELETE FROM instructor_endorsements WHERE id = ?', (endorsement_id,))
        db.commit()
        return cursor.rowcount > 0

def verify_pic_endorsements(entries):
    """Verify PIC endorsements for all entries.
    
    Args:
        entries: List of logbook entries to verify
        
    Returns:
        dict: Dictionary containing verification results
    """
    endorsements = get_all_endorsements()
    
    # Sort entries by date
    entries.sort(key=lambda x: x.date)
    
    # Find gaps in endorsement coverage
    gaps = []
    current_gap = None
    
    # Find unendorsed flights
    unendorsed_flights = []
    
    for entry in entries:
        if entry.pic_time > 0:  # Only check flights with PIC time
            if not check_flight_endorsements(entry.date, endorsements):
                unendorsed_flights.append({
                    'date': entry.date.isoformat(),
                    'route': f"{entry.departure.identifier if entry.departure else '---'} → {entry.destination.identifier if entry.destination else '---'}",
                    'pic_time': entry.pic_time,
                    'type': entry.aircraft.type
                })
                
                # Update gaps
                if current_gap is None:
                    current_gap = {'start': entry.date}
            elif current_gap is not None:
                current_gap['end'] = entry.date
                gaps.append(current_gap)
                current_gap = None
    
    # Close any open gap
    if current_gap is not None:
        current_gap['end'] = entries[-1].date if entries else datetime.now()
        gaps.append(current_gap)
    
    return {
        'gaps': [{'start': gap['start'].isoformat(), 'end': gap['end'].isoformat()} for gap in gaps],
        'unendorsed_flights': unendorsed_flights,
        'total_invalid': len(unendorsed_flights)
    }

def check_flight_endorsements(flight_date, endorsements):
    """Check if a flight has valid endorsements for its date.
    
    Args:
        flight_date: The date of the flight to check
        endorsements: List of InstructorEndorsement objects
        
    Returns:
        bool: True if the flight has valid endorsements, False otherwise
    """
    for endorsement in endorsements:
        if endorsement.is_valid_for_date(flight_date):
            return True
    return False

def find_endorsement_gaps():
    """Find date ranges that are not covered by any endorsement."""
    endorsements = get_all_endorsements()
    if not endorsements:
        return []
    
    # Sort endorsements by start date
    endorsements.sort(key=lambda x: x.start_date)
    
    gaps = []
    current_date = endorsements[0].start_date
    
    for i in range(len(endorsements)):
        # Check if there's a gap between current endorsement's expiration and next endorsement's start
        if i < len(endorsements) - 1:
            current_exp = endorsements[i].expiration_date
            next_start = endorsements[i + 1].start_date
            
            if current_exp < next_start:
                gaps.append({
                    'start': current_exp,
                    'end': next_start
                })
    
    return gaps 