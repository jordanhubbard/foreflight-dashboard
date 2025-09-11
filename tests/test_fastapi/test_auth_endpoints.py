"""Test authentication endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.main import app
from src.core.auth_models import User
from tests.conftest import get_test_db, create_test_user


class TestAuthEndpoints:
    """Test authentication-related API endpoints."""

    def test_login_success(self, client: TestClient, test_user: User):
        """Test successful login."""
        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "testpassword"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "test@example.com"

    def test_login_invalid_credentials(self, client: TestClient):
        """Test login with invalid credentials."""
        response = client.post(
            "/api/auth/login",
            json={"email": "nonexistent@example.com", "password": "wrongpassword"}
        )
        
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    def test_login_malformed_request(self, client: TestClient):
        """Test login with malformed request."""
        response = client.post("/api/auth/login", json={"email": "test@example.com"})
        
        assert response.status_code == 422  # Validation error

    def test_register_success(self, client: TestClient):
        """Test successful user registration."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "newpassword",
                "first_name": "New",
                "last_name": "User"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["first_name"] == "New"
        assert data["last_name"] == "User"

    def test_register_duplicate_email(self, client: TestClient, test_user: User):
        """Test registration with duplicate email."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",  # Already exists
                "password": "newpassword",
                "first_name": "Duplicate",
                "last_name": "User"
            }
        )
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_logout(self, client: TestClient, auth_headers: dict):
        """Test user logout."""
        response = client.post("/api/auth/logout", headers=auth_headers)
        
        assert response.status_code == 200
        assert "successfully logged out" in response.json()["message"].lower()

    def test_logout_without_auth(self, client: TestClient):
        """Test logout without authentication."""
        response = client.post("/api/auth/logout")
        
        assert response.status_code == 401
