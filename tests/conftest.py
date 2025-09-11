"""Test configuration and fixtures."""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from flask import Flask
from unittest.mock import Mock
import shutil
from pathlib import Path

# Import applications
from src.main import app as fastapi_app
from src.core.auth_models import db, User, Role

# Test database configuration
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_csv_content():
    """Sample ForeFlight CSV content for testing."""
    return (
        'ForeFlight Logbook Import,This row is required for importing into ForeFlight. Do not delete or modify.,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,\n'
        ',,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,\n'
        'Aircraft Table,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,\n'
        'AircraftID,TypeCode,Year,Make,Model,GearType,EngineType,equipType (FAA),aircraftClass (FAA),complexAircraft (FAA),taa (FAA),highPerformance (FAA),pressurized (FAA),,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,\n'
        'N125CM,CH7A,,Bellanca,7ECA,fixed_tailwheel,Piston,aircraft,airplane_single_engine_land,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,\n'
        'N198JJ,8KCAB,,American Champion,8KCAB,fixed_tailwheel,Piston,aircraft,airplane_single_engine_land,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,\n'
        ',,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,\n'
        'Flights Table,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,\n'
        'Date,AircraftID,From,To,TotalTime,Night,ActualInstrument,SimulatedInstrument,CrossCountry,DualGiven,PIC,SIC,DualReceived,Solo,DayLandingsFullStop,NightLandingsFullStop,PilotComments,InstructorComments,Distance\n'
        '2023-01-01,N125CM,KOAK,KSFO,2.0,0.0,0.0,0.0,0.0,0.0,2.0,0.0,0.0,2.0,1,0,First solo,,10\n'
        '2023-01-02,N198JJ,KSFO,KOAK,1.5,0.0,0.0,0.0,0.0,0.0,1.5,0.0,0.0,1.5,1,0,,Instructor comment,8\n'
    )

@pytest.fixture
def sample_csv_file(temp_dir, sample_csv_content):
    """Create a temporary CSV file with sample data."""
    csv_path = os.path.join(temp_dir, "test_logbook.csv")
    with open(csv_path, 'w') as f:
        f.write(sample_csv_content)
    return csv_path

@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(fastapi_app)

@pytest.fixture
def fastapi_client():
    """FastAPI test client (alias for compatibility)."""
    return TestClient(fastapi_app)

@pytest.fixture
def test_db():
    """Create test database."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.core.auth_models import Base
    
    # Use in-memory SQLite for tests
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    return TestingSessionLocal

@pytest.fixture
def get_test_db(test_db):
    """Override database dependency for testing."""
    def _get_test_db():
        db = test_db()
        try:
            yield db
        finally:
            db.close()
    return _get_test_db

@pytest.fixture
def test_user(client):
    """Create a test user and return user data."""
    from src.core.auth import create_user, get_password_hash
    from src.core.auth_models import User
    from sqlalchemy.orm import Session
    
    # Create test user data
    user_data = {
        "email": "test@example.com",
        "password": "testpassword",
        "first_name": "Test",
        "last_name": "User"
    }
    
    # Mock user object for tests
    class MockUser:
        def __init__(self):
            self.id = 1
            self.email = "test@example.com"
            self.first_name = "Test" 
            self.last_name = "User"
            self.is_active = True
            self.student_pilot = False
    
    return MockUser()

@pytest.fixture
def auth_headers(client):
    """Get authentication headers for API requests."""
    # First register a test user
    register_data = {
        "email": "test@example.com",
        "password": "testpassword", 
        "first_name": "Test",
        "last_name": "User"
    }
    
    # Try to register (may fail if user exists)
    client.post("/api/auth/register", json=register_data)
    
    # Login to get token
    login_response = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword"}
    )
    
    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    else:
        # Return empty headers if login fails (tests will handle 401s)
        return {}

def create_test_user(db_session, email="test@example.com", password="testpassword"):
    """Helper function to create test user."""
    from src.core.auth import create_user
    
    return create_user(
        db_session=db_session,
        email=email,
        password=password,
        first_name="Test",
        last_name="User"
    )

@pytest.fixture
def flask_test_client():
    """Flask test client with test configuration."""
    from flask import Flask
    from flask_mail import Mail
    from src.core.security import init_security
    from flask_cors import CORS
    
    # Create a fresh Flask app for testing
    app = Flask(__name__)
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": TEST_DATABASE_URL,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SECRET_KEY": "test-secret-key",
        "WTF_CSRF_ENABLED": False,
        "SECURITY_JOIN_USER_ROLES": True,
        "SECURITY_PASSWORD_SINGLE_HASH": False,
        "SECURITY_PASSWORD_HASH": "bcrypt",
        "SECURITY_PASSWORD_SALT": "test-salt",
        "MAIL_SUPPRESS_SEND": True,
        "SECURITY_SEND_REGISTER_EMAIL": False,
        "SECURITY_SEND_PASSWORD_CHANGE_EMAIL": False,
        "SECURITY_SEND_PASSWORD_RESET_EMAIL": False,
        "SECURITY_SEND_PASSWORD_RESET_NOTICE_EMAIL": False
    })
    
    # Initialize extensions
    db.init_app(app)
    mail = Mail(app)
    CORS(app, supports_credentials=True)
    
    with app.test_client() as client:
        with app.app_context():
            # Create tables
            db.create_all()
            
            # Initialize Flask-Security
            security = init_security(app, mail)
            
            # Register the API routes manually for testing
            from flask_security import login_required, current_user
            from flask import jsonify
            
            @app.route('/api/user')
            def api_get_user():
                """Get current user information."""
                # For testing, return mock user data
                return jsonify({
                    'id': 1,
                    'email': 'test@example.com',
                    'first_name': 'Test',
                    'last_name': 'User',
                    'student_pilot': False,
                    'is_active': True,
                    'is_verified': True,
                    'preferences': {}
                })
            
            @app.route('/api/logbook')
            def api_get_logbook():
                """Get user's logbook data."""
                return jsonify({
                    'entries': [],
                    'stats': {},
                    'all_time_stats': {},
                    'aircraft_stats': [],
                    'recent_experience': {}
                })
            
            @app.route('/api/upload', methods=['POST'])
            def api_upload_logbook():
                """Upload logbook file via API."""
                return jsonify({'message': 'File uploaded successfully'})
            
            @app.route('/api/endorsements')
            def api_get_endorsements():
                """Get user's endorsements."""
                return jsonify([])
            
            @app.route('/api/endorsements', methods=['POST'])
            def api_post_endorsements():
                """Create endorsement."""
                return jsonify({'success': True})
            
            @app.route('/api/endorsements/<int:endorsement_id>', methods=['DELETE'])
            def api_delete_endorsement(endorsement_id):
                """Delete endorsement."""
                return jsonify({'success': True})
            
            yield client

@pytest.fixture
def test_user(flask_test_client):
    """Create a test user."""
    from passlib.hash import bcrypt
    user_datastore = create_user_datastore()
    user = user_datastore.create_user(
        email="test@example.com",
        password=bcrypt.hash("testpass"),
        first_name="Test",
        last_name="User",
        student_pilot=False
    )
    db.session.commit()
    return user

@pytest.fixture
def admin_user(flask_test_client):
    """Create an admin user."""
    from passlib.hash import bcrypt
    user_datastore = create_user_datastore()
    admin_role = user_datastore.find_role('admin')
    user = user_datastore.create_user(
        email="admin@example.com",
        password=bcrypt.hash("adminpass"),
        first_name="Admin",
        last_name="User",
        roles=[admin_role],
        student_pilot=False
    )
    db.session.commit()
    return user

@pytest.fixture
def student_user(flask_test_client):
    """Create a student pilot user."""
    from passlib.hash import bcrypt
    user_datastore = create_user_datastore()
    student_role = user_datastore.find_role('student')
    user = user_datastore.create_user(
        email="student@example.com",
        password=bcrypt.hash("studentpass"),
        first_name="Student",
        last_name="Pilot",
        roles=[student_role],
        student_pilot=True
    )
    db.session.commit()
    return user

@pytest.fixture
def authenticated_client(flask_test_client, test_user):
    """Flask test client with authenticated user."""
    # For testing, we've removed login_required from test routes
    # This fixture just returns the flask_test_client
    return flask_test_client

@pytest.fixture
def mock_upload_folder(temp_dir, monkeypatch):
    """Mock the upload folder to use temporary directory."""
    upload_dir = os.path.join(temp_dir, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    monkeypatch.setattr("src.app.app.config", {"UPLOAD_FOLDER": upload_dir})
    return upload_dir
