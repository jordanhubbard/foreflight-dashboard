"""Tests for FastAPI JWT authentication system."""

import pytest
import jwt
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.main import app
from src.core.auth import (
    create_access_token, verify_token, authenticate_user, 
    create_user, get_password_hash, verify_password,
    SECRET_KEY, ALGORITHM
)
from src.core.auth_models import User, Role


@pytest.fixture
def test_client():
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def test_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "first_name": "Test",
        "last_name": "User",
        "student_pilot": False
    }


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return MagicMock()


class TestJWTAuthentication:
    """Test JWT authentication functionality."""

    def test_create_access_token(self):
        """Test JWT token creation."""
        data = {"sub": "123", "email": "test@example.com"}
        token = create_access_token(data)
        
        # Verify token can be decoded
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "123"
        assert payload["email"] == "test@example.com"
        assert "exp" in payload

    def test_create_access_token_with_expiration(self):
        """Test JWT token creation with custom expiration."""
        data = {"sub": "123"}
        expires_delta = timedelta(minutes=60)
        token = create_access_token(data, expires_delta)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_time = datetime.now(timezone.utc) + expires_delta
        
        # Allow 5 second tolerance
        assert abs((exp_time - expected_time).total_seconds()) < 5

    def test_verify_token_valid(self):
        """Test token verification with valid token."""
        data = {"sub": "123", "email": "test@example.com"}
        token = create_access_token(data)
        
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "123"
        assert payload["email"] == "test@example.com"

    def test_verify_token_invalid(self):
        """Test token verification with invalid token."""
        invalid_token = "invalid.token.here"
        payload = verify_token(invalid_token)
        assert payload is None

    def test_verify_token_expired(self):
        """Test token verification with expired token."""
        data = {"sub": "123"}
        expired_token = jwt.encode(
            {**data, "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
            SECRET_KEY,
            algorithm=ALGORITHM
        )
        
        payload = verify_token(expired_token)
        assert payload is None

    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False

    def test_authenticate_user_success(self, mock_db_session):
        """Test successful user authentication."""
        # Create mock user
        mock_user = MagicMock(spec=User)
        mock_user.email = "test@example.com"
        mock_user.password = get_password_hash("testpassword123")
        mock_user.active = True
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        user = authenticate_user(mock_db_session, "test@example.com", "testpassword123")
        assert user == mock_user

    def test_authenticate_user_not_found(self, mock_db_session):
        """Test authentication with non-existent user."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        user = authenticate_user(mock_db_session, "nonexistent@example.com", "password")
        assert user is None

    def test_authenticate_user_wrong_password(self, mock_db_session):
        """Test authentication with wrong password."""
        mock_user = MagicMock(spec=User)
        mock_user.email = "test@example.com"
        mock_user.password = get_password_hash("correctpassword")
        mock_user.active = True
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        user = authenticate_user(mock_db_session, "test@example.com", "wrongpassword")
        assert user is None

    def test_authenticate_user_inactive(self, mock_db_session):
        """Test authentication with inactive user."""
        mock_user = MagicMock(spec=User)
        mock_user.email = "test@example.com"
        mock_user.password = get_password_hash("testpassword123")
        mock_user.active = False
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        user = authenticate_user(mock_db_session, "test@example.com", "testpassword123")
        assert user is None


class TestAuthenticationEndpoints:
    """Test FastAPI authentication endpoints."""

    def test_login_success(self, test_client, mock_db_session):
        """Test successful login."""
        with patch('src.main.get_db') as mock_get_db, \
             patch('src.main.authenticate_user') as mock_auth:
            
            mock_get_db.return_value = mock_db_session
            
            # Mock successful authentication
            mock_user = MagicMock()
            mock_user.id = 1
            mock_user.email = "test@example.com"
            mock_user.first_name = "Test"
            mock_user.last_name = "User"
            mock_user.student_pilot = False
            mock_user.created_at = datetime.now(timezone.utc)
            mock_auth.return_value = mock_user
            
            response = test_client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "testpassword123"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert data["user"]["email"] == "test@example.com"

    def test_login_invalid_credentials(self, test_client, mock_db_session):
        """Test login with invalid credentials."""
        with patch('src.main.get_db') as mock_get_db, \
             patch('src.main.authenticate_user') as mock_auth:
            
            mock_get_db.return_value = mock_db_session
            mock_auth.return_value = None  # Authentication failed
            
            response = test_client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "wrongpassword"
            })
            
            assert response.status_code == 401
            assert "Incorrect email or password" in response.json()["detail"]

    def test_login_missing_data(self, test_client):
        """Test login with missing data."""
        response = test_client.post("/api/auth/login", json={
            "email": "test@example.com"
            # Missing password
        })
        
        assert response.status_code == 422

    def test_register_success(self, test_client, mock_db_session):
        """Test successful user registration."""
        with patch('src.main.get_db') as mock_get_db, \
             patch('src.main.create_user') as mock_create:
            
            mock_get_db.return_value = mock_db_session
            
            # Mock successful user creation
            mock_user = MagicMock()
            mock_user.id = 1
            mock_user.email = "newuser@example.com"
            mock_user.first_name = "New"
            mock_user.last_name = "User"
            mock_user.student_pilot = False
            mock_user.created_at = datetime.now(timezone.utc)
            mock_create.return_value = mock_user
            
            response = test_client.post("/api/auth/register", json={
                "email": "newuser@example.com",
                "password": "newpassword123",
                "first_name": "New",
                "last_name": "User",
                "student_pilot": False
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "newuser@example.com"
            assert data["first_name"] == "New"

    def test_register_duplicate_email(self, test_client, mock_db_session):
        """Test registration with duplicate email."""
        with patch('src.main.get_db') as mock_get_db, \
             patch('src.main.create_user') as mock_create:
            
            mock_get_db.return_value = mock_db_session
            
            # Mock user creation failure (duplicate email)
            from fastapi import HTTPException
            mock_create.side_effect = HTTPException(status_code=400, detail="Email already registered")
            
            response = test_client.post("/api/auth/register", json={
                "email": "existing@example.com",
                "password": "password123",
                "first_name": "Test",
                "last_name": "User"
            })
            
            assert response.status_code == 400

    def test_logout(self, test_client):
        """Test logout endpoint."""
        response = test_client.post("/api/auth/logout")
        
        assert response.status_code == 200
        assert response.json()["message"] == "Successfully logged out"

    def test_protected_endpoint_without_token(self, test_client):
        """Test accessing protected endpoint without token."""
        response = test_client.get("/api/user")
        
        assert response.status_code == 401

    def test_protected_endpoint_with_invalid_token(self, test_client):
        """Test accessing protected endpoint with invalid token."""
        response = test_client.get("/api/user", headers={
            "Authorization": "Bearer invalid.token.here"
        })
        
        assert response.status_code == 401

    def test_protected_endpoint_with_valid_token(self, test_client, mock_db_session):
        """Test accessing protected endpoint with valid token."""
        with patch('src.main.get_db') as mock_get_db, \
             patch('src.main.get_current_user_from_token') as mock_get_user:
            
            mock_get_db.return_value = mock_db_session
            
            # Mock user from token
            mock_user = MagicMock()
            mock_user.id = 1
            mock_user.email = "test@example.com"
            mock_user.first_name = "Test"
            mock_user.last_name = "User"
            mock_user.student_pilot = False
            mock_user.created_at = datetime.now(timezone.utc)
            mock_get_user.return_value = mock_user
            
            # Create valid token
            token = create_access_token({"sub": "1"})
            
            response = test_client.get("/api/user", headers={
                "Authorization": f"Bearer {token}"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "test@example.com"


class TestUserCreation:
    """Test user creation functionality."""

    def test_create_user_success(self, mock_db_session):
        """Test successful user creation."""
        # Mock database operations
        mock_db_session.query.return_value.filter.return_value.first.return_value = None  # No existing user
        
        user = create_user(
            db=mock_db_session,
            email="newuser@example.com",
            password="password123",
            first_name="New",
            last_name="User",
            student_pilot=True
        )
        
        assert user.email == "newuser@example.com"
        assert user.first_name == "New"
        assert user.last_name == "User"
        assert user.student_pilot is True
        assert user.active is True
        
        # Verify password is hashed
        assert user.password != "password123"
        assert verify_password("password123", user.password)

    def test_create_user_duplicate_email(self, mock_db_session):
        """Test user creation with duplicate email."""
        # Mock existing user
        existing_user = MagicMock()
        mock_db_session.query.return_value.filter.return_value.first.return_value = existing_user
        
        with pytest.raises(Exception):  # Should raise HTTPException
            create_user(
                db=mock_db_session,
                email="existing@example.com",
                password="password123",
                first_name="Test",
                last_name="User"
            )


class TestTokenValidation:
    """Test token validation and user retrieval."""

    def test_get_current_user_from_valid_token(self, mock_db_session):
        """Test getting user from valid token."""
        from fastapi.security import HTTPAuthorizationCredentials
        from src.main import get_current_user_from_token
        
        # Create mock user
        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.active = True
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Create valid token
        token = create_access_token({"sub": "1"})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        
        user = get_current_user_from_token(credentials, mock_db_session)
        assert user == mock_user

    def test_get_current_user_from_invalid_token(self, mock_db_session):
        """Test getting user from invalid token."""
        from fastapi.security import HTTPAuthorizationCredentials
        from src.main import get_current_user_from_token
        
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid.token")
        
        user = get_current_user_from_token(credentials, mock_db_session)
        assert user is None

    def test_get_current_user_no_credentials(self, mock_db_session):
        """Test getting user with no credentials."""
        from src.main import get_current_user_from_token
        
        user = get_current_user_from_token(None, mock_db_session)
        assert user is None
