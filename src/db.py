import sqlite3
from datetime import datetime, timedelta
from contextlib import contextmanager
import os
from src.core.models import InstructorEndorsement

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'endorsements.db')

def init_db():
    """Initialize the database and create tables if they don't exist."""
    with get_db() as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS instructor_endorsements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_date TEXT NOT NULL,
                expiration_date TEXT NOT NULL
            )
        ''')
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

def add_endorsement(start_date: datetime) -> InstructorEndorsement:
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