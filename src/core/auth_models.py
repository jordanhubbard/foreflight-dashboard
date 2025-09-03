"""Authentication models using Flask-Security-Too."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from flask_sqlalchemy import SQLAlchemy
from flask_security import UserMixin, RoleMixin
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
import json

# Initialize SQLAlchemy
db = SQLAlchemy()

# Association table for many-to-many relationship between users and roles
roles_users = db.Table(
    'roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)


class Role(db.Model, RoleMixin):
    """User roles for role-based access control."""
    __tablename__ = 'role'
    
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))
    
    def __str__(self):
        return self.name


class User(db.Model, UserMixin):
    """User model with Flask-Security-Too integration."""
    __tablename__ = 'user'
    
    # Flask-Security-Too required fields
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean(), default=True)
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False)
    
    # Email verification
    confirmed_at = db.Column(db.DateTime())
    
    # Custom fields for aviation application
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    pilot_certificate_number = db.Column(db.String(20))
    student_pilot = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login_at = db.Column(db.DateTime)
    current_login_at = db.Column(db.DateTime)
    login_count = db.Column(db.Integer, default=0)
    
    # User preferences (stored as JSON)
    preferences = db.Column(db.Text, default='{}')
    
    # Relationships
    roles = db.relationship('Role', secondary=roles_users, backref=backref('users', lazy='dynamic'))
    
    @hybrid_property
    def full_name(self):
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"
    
    @hybrid_property
    def display_name(self):
        """Get user's display name (first name + last initial)."""
        return f"{self.first_name} {self.last_name[0]}." if self.last_name else self.first_name
    
    def get_preferences(self) -> Dict[str, Any]:
        """Get user preferences as a dictionary."""
        try:
            return json.loads(self.preferences) if self.preferences else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_preferences(self, preferences: Dict[str, Any]):
        """Set user preferences from a dictionary."""
        self.preferences = json.dumps(preferences)
    
    def get_user_directory(self) -> str:
        """Get the directory path for user files."""
        import hashlib
        email_hash = hashlib.md5(self.email.encode()).hexdigest()[:8]
        return f"user_{self.id}_{email_hash}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'pilot_certificate_number': self.pilot_certificate_number,
            'student_pilot': self.student_pilot,
            'active': self.active,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'created_at': self.created_at.isoformat(),
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'login_count': self.login_count,
            'preferences': self.get_preferences(),
            'full_name': self.full_name,
            'display_name': self.display_name,
            'roles': [role.name for role in self.roles]
        }
    
    def __repr__(self):
        return f'<User {self.email}>'


class UserLogbook(db.Model):
    """Track user's uploaded logbook files."""
    __tablename__ = 'user_logbook'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    file_size = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('logbooks', lazy='dynamic'))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert logbook to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'uploaded_at': self.uploaded_at.isoformat(),
            'file_size': self.file_size,
            'is_active': self.is_active
        }


class InstructorEndorsement(db.Model):
    """Instructor endorsements for student pilots."""
    __tablename__ = 'instructor_endorsement'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    expiration_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = db.relationship('User', backref=db.backref('endorsements', lazy='dynamic'))
    
    @staticmethod
    def calculate_expiration(start_date: datetime) -> datetime:
        """Calculate the expiration date (90 days from start date)."""
        from datetime import timedelta
        return start_date + timedelta(days=90)
    
    def is_valid_for_date(self, flight_date: datetime) -> bool:
        """Check if the endorsement is valid for a given flight date."""
        return self.start_date <= flight_date <= self.expiration_date
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert endorsement to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'start_date': self.start_date.isoformat(),
            'expiration_date': self.expiration_date.isoformat(),
            'created_at': self.created_at.isoformat()
        }
