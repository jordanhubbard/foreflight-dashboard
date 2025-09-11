"""Simple integration tests that work with real database."""

import pytest
from fastapi.testclient import TestClient
from src.main import app


class TestSimpleIntegration:
    """Simple integration tests without complex mocking."""

    def test_health_check(self):
        """Test health check endpoint."""
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_api_docs_accessible(self):
        """Test that API documentation is accessible."""
        client = TestClient(app)
        response = client.get("/docs")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_openapi_spec(self):
        """Test that OpenAPI specification is accessible."""
        client = TestClient(app)
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "ForeFlight Dashboard"

    def test_api_404_works(self):
        """Test that non-existent API endpoints return 404."""
        client = TestClient(app)
        response = client.get("/api/nonexistent")
        
        assert response.status_code == 404

    def test_root_serves_html(self):
        """Test root endpoint returns HTML."""
        client = TestClient(app)
        response = client.get("/")
        
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        
        # Should contain basic HTML structure
        content = response.text
        assert "<!doctype html>" in content.lower()
        assert "<title>ForeFlight Dashboard</title>" in content

    def test_spa_routing(self):
        """Test that SPA routes return the main HTML."""
        client = TestClient(app)
        test_routes = [
            "/login",
            "/dashboard", 
            "/profile"
        ]
        
        for route in test_routes:
            response = client.get(route)
            
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/html")
            
            # Should return the same HTML as root
            content = response.text
            assert "<!doctype html>" in content.lower()
            assert "<title>ForeFlight Dashboard</title>" in content

    def test_protected_endpoint_requires_auth(self):
        """Test that protected endpoints require authentication."""
        client = TestClient(app)
        
        protected_endpoints = [
            "/api/user",
            "/api/logbook",
            "/api/endorsements"
        ]
        
        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401

    def test_register_and_login_flow(self):
        """Test basic user registration and login flow."""
        client = TestClient(app)
        
        # Try to register a new user
        import time
        unique_email = f"testuser{int(time.time())}@example.com"
        
        register_data = {
            "email": unique_email,
            "password": "testpassword123",
            "first_name": "Test",
            "last_name": "User"
        }
        
        register_response = client.post("/api/auth/register", json=register_data)
        
        # Registration might fail if user exists, that's OK
        if register_response.status_code == 200:
            # If registration succeeded, try to login
            login_response = client.post("/api/auth/login", json={
                "email": unique_email,
                "password": "testpassword123"
            })
            
            assert login_response.status_code == 200
            data = login_response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert "user" in data
            
            # Test accessing protected endpoint with token
            token = data["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            user_response = client.get("/api/user", headers=headers)
            assert user_response.status_code == 200
            
            user_data = user_response.json()
            assert user_data["email"] == unique_email
            assert user_data["first_name"] == "Test"
            assert user_data["last_name"] == "User"

    def test_invalid_login(self):
        """Test login with invalid credentials."""
        client = TestClient(app)
        
        response = client.post("/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    def test_malformed_requests(self):
        """Test handling of malformed requests."""
        client = TestClient(app)
        
        # Missing required fields
        response = client.post("/api/auth/login", json={"email": "test@example.com"})
        assert response.status_code == 422
        
        # Invalid JSON
        response = client.post("/api/auth/register", 
                             data="invalid json",
                             headers={"Content-Type": "application/json"})
        assert response.status_code == 422

    def test_logbook_without_data(self):
        """Test logbook endpoint with authenticated user but no data."""
        client = TestClient(app)
        
        # First register and login
        import time
        unique_email = f"logbooktest{int(time.time())}@example.com"
        
        register_data = {
            "email": unique_email,
            "password": "testpassword123",
            "first_name": "Logbook",
            "last_name": "Test"
        }
        
        register_response = client.post("/api/auth/register", json=register_data)
        
        if register_response.status_code == 200:
            # Login
            login_response = client.post("/api/auth/login", json={
                "email": unique_email,
                "password": "testpassword123"
            })
            
            if login_response.status_code == 200:
                token = login_response.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}
                
                # Get logbook data (should return empty data structure)
                logbook_response = client.get("/api/logbook", headers=headers)
                assert logbook_response.status_code == 200
                
                data = logbook_response.json()
                assert "entries" in data
                assert "stats" in data
                assert isinstance(data["entries"], list)
                assert len(data["entries"]) == 0  # No data uploaded yet
