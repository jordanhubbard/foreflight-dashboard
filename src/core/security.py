"""Flask-Security-Too configuration and setup."""

import os
from datetime import timedelta, datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mail import Mail
from flask_security import Security, SQLAlchemyUserDatastore
import hashlib
from flask_security.utils import send_mail
from flask_security.forms import RegisterForm, LoginForm, ForgotPasswordForm, ResetPasswordForm
from wtforms import StringField, BooleanField, TextAreaField, validators
from wtforms.validators import DataRequired, Email, Length, EqualTo

from .auth_models import db, User, Role, UserLogbook, InstructorEndorsement


class ExtendedRegisterForm(RegisterForm):
    """Extended registration form with aviation-specific fields."""
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=1, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=1, max=50)])
    pilot_certificate_number = StringField('Pilot Certificate Number (Optional)', 
                                         validators=[Length(max=20)])
    student_pilot = BooleanField('I am a student pilot')
    agree_to_terms = BooleanField('I agree to the Terms and Conditions', 
                                validators=[DataRequired()])


class ExtendedLoginForm(LoginForm):
    """Extended login form with remember me functionality."""
    remember = BooleanField('Remember me')


def create_user_datastore():
    """Create and return the user datastore."""
    return SQLAlchemyUserDatastore(db, User, Role)


def init_security(app: Flask, mail: Mail):
    """Initialize Flask-Security-Too with the application."""
    
    # Create user datastore
    user_datastore = create_user_datastore()
    
    # Security configuration
    security_config = {
        # Basic settings
        'SECURITY_PASSWORD_HASH': 'bcrypt',
        'SECURITY_PASSWORD_SALT': app.config.get('SECRET_KEY', 'dev-secret-key'),
        'SECURITY_PASSWORD_SINGLE_HASH': True,
        
        # User registration
        'SECURITY_REGISTERABLE': True,
        'SECURITY_REGISTER_URL': '/register',
        'SECURITY_REGISTER_USER_TEMPLATE': 'security/register_user.html',
        'SECURITY_SEND_REGISTER_EMAIL': True,
        'SECURITY_REGISTER_EMAIL_TEMPLATE': 'security/register_user.html',
        
        # Login/Logout
        'SECURITY_LOGIN_URL': '/login',
        'SECURITY_LOGOUT_URL': '/logout',
        'SECURITY_LOGIN_USER_TEMPLATE': 'security/login_user.html',
        'SECURITY_POST_LOGIN_REDIRECT_ENDPOINT': 'index',
        'SECURITY_POST_LOGOUT_REDIRECT_ENDPOINT': 'index',
        'SECURITY_POST_REGISTER_REDIRECT_ENDPOINT': 'index',
        
        # Password reset
        'SECURITY_RECOVERABLE': True,
        'SECURITY_RESET_URL': '/reset',
        'SECURITY_RESET_PASSWORD_TEMPLATE': 'security/reset_password.html',
        'SECURITY_FORGOT_PASSWORD_TEMPLATE': 'security/forgot_password.html',
        'SECURITY_SEND_PASSWORD_RESET_EMAIL': True,
        'SECURITY_EMAIL_SUBJECT_PASSWORD_RESET': 'Reset Your Password - ForeFlight Dashboard',
        'SECURITY_EMAIL_SUBJECT_PASSWORD_NOTICE': 'Your Password Has Been Reset - ForeFlight Dashboard',
        
        # Email verification
        'SECURITY_CONFIRMABLE': True,
        'SECURITY_CONFIRM_URL': '/confirm',
        'SECURITY_CONFIRM_EMAIL_TEMPLATE': 'security/confirm_email.html',
        'SECURITY_SEND_CONFIRMATION_EMAIL': True,
        'SECURITY_EMAIL_SUBJECT_CONFIRM': 'Please Confirm Your Email - ForeFlight Dashboard',
        
        # Change password
        'SECURITY_CHANGEABLE': True,
        'SECURITY_CHANGE_URL': '/change',
        'SECURITY_CHANGE_PASSWORD_TEMPLATE': 'security/change_password.html',
        'SECURITY_SEND_PASSWORD_CHANGE_EMAIL': True,
        'SECURITY_EMAIL_SUBJECT_PASSWORD_CHANGE_NOTICE': 'Your Password Has Been Changed - ForeFlight Dashboard',
        
        # Session management
        'SECURITY_REMEMBER_SALT': app.config.get('SECRET_KEY', 'dev-secret-key'),
        'SECURITY_DEFAULT_REMEMBER_ME': False,
        'SECURITY_TOKEN_MAX_AGE': 3600,  # 1 hour
        
        # CSRF protection
        'SECURITY_CSRF_PROTECT_MECHANISMS': ['session', 'token'],
        'SECURITY_CSRF_IGNORE_UNAUTH_ENDPOINTS': False,
        'WTF_CSRF_CHECK_DEFAULT': False,
        
        # Rate limiting
        'SECURITY_RATE_LIMIT_ENABLED': True,
        'SECURITY_RATE_LIMIT_STORAGE_URL': 'memory://',
        
        # User roles
        'SECURITY_JOIN_USER_ROLES': True,
        
        # Password hashing
        'SECURITY_PASSWORD_SINGLE_HASH': app.config.get('SECURITY_PASSWORD_SINGLE_HASH', False),
        'SECURITY_PASSWORD_HASH': app.config.get('SECURITY_PASSWORD_HASH', 'bcrypt'),
        'SECURITY_PASSWORD_SALT': app.config.get('SECURITY_PASSWORD_SALT', app.config.get('SECRET_KEY', 'dev-secret-key')),
        
        # Email settings
        'SECURITY_EMAIL_SENDER': app.config.get('MAIL_DEFAULT_SENDER', 'noreply@foreflight-dashboard.com'),
        
        # Custom forms
        'SECURITY_REGISTER_FORM': ExtendedRegisterForm,
        'SECURITY_LOGIN_FORM': ExtendedLoginForm,
    }
    
    # Update app config with security settings
    app.config.update(security_config)
    
    # Initialize Security
    security = Security(app, user_datastore, register_form=ExtendedRegisterForm)
    
    # Create default roles if they don't exist
    with app.app_context():
        create_default_roles(user_datastore)
    
    return security


def create_default_roles(user_datastore):
    """Create default roles for the application."""
    roles = [
        ('admin', 'Administrator - Full access to all features'),
        ('pilot', 'Certified Pilot - Access to all pilot features'),
        ('student', 'Student Pilot - Access to student-specific features'),
        ('instructor', 'Flight Instructor - Can manage student endorsements')
    ]
    
    for role_name, description in roles:
        if not user_datastore.find_role(role_name):
            user_datastore.create_role(name=role_name, description=description)
    
    db.session.commit()


def create_default_admin(app: Flask, user_datastore):
    """Create a default admin user if no users exist."""
    with app.app_context():
        if not user_datastore.find_user(email='admin@foreflight-dashboard.com'):
            admin_role = user_datastore.find_role('admin')
            user_datastore.create_user(
                email='admin@foreflight-dashboard.com',
                password=hashlib.sha256('admin123'.encode()).hexdigest(),
                first_name='Admin',
                last_name='User',
                roles=[admin_role],
                confirmed_at=datetime.now()
            )
            db.session.commit()
            print("Created default admin user: admin@foreflight-dashboard.com / admin123")


def setup_user_directories(app: Flask):
    """Set up user directories for file storage."""
    import os
    
    # Create main uploads directory
    uploads_dir = os.path.join(app.instance_path, 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)
    
    # Create subdirectories
    for subdir in ['logbooks', 'exports', 'backups', 'temp']:
        os.makedirs(os.path.join(uploads_dir, subdir), exist_ok=True)


def get_user_directory(user: User) -> str:
    """Get the directory path for a user's files."""
    import os
    user_dir = user.get_user_directory()
    return os.path.join('uploads', user_dir)


def create_user_directory(user: User):
    """Create a directory for user files."""
    import os
    
    user_path = get_user_directory(user)
    os.makedirs(user_path, exist_ok=True)
    
    # Create subdirectories
    for subdir in ['logbooks', 'exports', 'backups']:
        os.makedirs(os.path.join(user_path, subdir), exist_ok=True)


# Security event handlers
def user_registered_handler(app, user, confirm_token):
    """Handle user registration."""
    # Create user directory
    create_user_directory(user)
    
    # Set default preferences
    default_preferences = {
        'student_pilot': user.student_pilot,
        'timezone': 'UTC',
        'date_format': '%Y-%m-%d',
        'time_format': '%H:%M',
        'theme': 'light',
        'notifications_enabled': True,
        'auto_save_logbooks': True,
        'currency_reminders': True
    }
    user.set_preferences(default_preferences)
    
    # Assign default role based on student pilot status
    user_datastore = create_user_datastore()
    if user.student_pilot:
        role = user_datastore.find_role('student')
    else:
        role = user_datastore.find_role('pilot')
    
    if role:
        user_datastore.add_role_to_user(user, role)
    
    db.session.commit()
    print(f"User {user.email} registered successfully")


def user_confirmed_handler(app, user):
    """Handle user email confirmation."""
    print(f"User {user.email} confirmed their email")


def password_reset_handler(app, user, token):
    """Handle password reset request."""
    print(f"Password reset requested for user {user.email}")


def password_changed_handler(app, user):
    """Handle password change."""
    print(f"Password changed for user {user.email}")


def setup_security_handlers(security):
    """Set up security event handlers."""
    from flask_security.signals import user_registered, user_confirmed, password_reset, password_changed
    
    user_registered.connect(user_registered_handler)
    user_confirmed.connect(user_confirmed_handler)
    password_reset.connect(password_reset_handler)
    password_changed.connect(password_changed_handler)
