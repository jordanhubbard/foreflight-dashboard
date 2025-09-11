"""Test user management endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.core.auth_models import User


class TestUserEndpoints:
    """Test user-related API endpoints."""

    def test_get_current_user(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test getting current user information."""
        response = client.get("/api/user", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["first_name"] == "Test"
        assert data["last_name"] == "User"

    def test_get_current_user_unauthorized(self, client: TestClient):
        """Test getting current user without authentication."""
        response = client.get("/api/user")
        
        assert response.status_code == 401

    def test_update_user_success(self, client: TestClient, auth_headers: dict):
        """Test successful user update."""
        update_data = {
            "first_name": "Updated",
            "last_name": "Name"
        }
        
        response = client.put("/api/user", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"

    def test_update_user_unauthorized(self, client: TestClient):
        """Test user update without authentication."""
        response = client.put("/api/user", json={"first_name": "Updated"})
        
        assert response.status_code == 401

    def test_update_user_invalid_data(self, client: TestClient, auth_headers: dict):
        """Test user update with invalid data."""
        response = client.put(
            "/api/user", 
            json={"email": "invalid-email"}, 
            headers=auth_headers
        )
        
        # Should either succeed or return validation error
        assert response.status_code in [200, 422]
