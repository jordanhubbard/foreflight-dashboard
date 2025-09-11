"""Test endorsement management endpoints."""

import pytest
from fastapi.testclient import TestClient
from datetime import date
from src.core.auth_models import User


class TestEndorsementEndpoints:
    """Test endorsement-related API endpoints."""

    def test_get_endorsements(self, client: TestClient, auth_headers: dict):
        """Test getting user endorsements."""
        response = client.get("/api/endorsements", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_endorsements_unauthorized(self, client: TestClient):
        """Test getting endorsements without authentication."""
        response = client.get("/api/endorsements")
        
        assert response.status_code == 401

    def test_create_endorsement(self, client: TestClient, auth_headers: dict):
        """Test creating a new endorsement."""
        endorsement_data = {
            "endorsement_type": "BFR",
            "date_given": str(date.today()),
            "expiration_date": str(date.today().replace(year=date.today().year + 2)),
            "instructor_name": "John Doe",
            "instructor_certificate": "CFI123456",
            "notes": "Biennial Flight Review completed successfully"
        }
        
        response = client.post(
            "/api/endorsements", 
            json=endorsement_data, 
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["endorsement_type"] == "BFR"
        assert data["instructor_name"] == "John Doe"

    def test_create_endorsement_invalid_data(self, client: TestClient, auth_headers: dict):
        """Test creating endorsement with invalid data."""
        endorsement_data = {
            "endorsement_type": "",  # Invalid empty type
            "date_given": "invalid-date"
        }
        
        response = client.post(
            "/api/endorsements", 
            json=endorsement_data, 
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error

    def test_create_endorsement_unauthorized(self, client: TestClient):
        """Test creating endorsement without authentication."""
        endorsement_data = {
            "endorsement_type": "BFR",
            "date_given": str(date.today())
        }
        
        response = client.post("/api/endorsements", json=endorsement_data)
        
        assert response.status_code == 401

    def test_delete_endorsement(self, client: TestClient, auth_headers: dict):
        """Test deleting an endorsement."""
        # First create an endorsement
        endorsement_data = {
            "endorsement_type": "BFR",
            "date_given": str(date.today()),
            "instructor_name": "John Doe",
            "instructor_certificate": "CFI123456"
        }
        
        create_response = client.post(
            "/api/endorsements", 
            json=endorsement_data, 
            headers=auth_headers
        )
        
        if create_response.status_code == 200:
            endorsement_id = create_response.json()["id"]
            
            # Now delete it
            delete_response = client.delete(
                f"/api/endorsements/{endorsement_id}", 
                headers=auth_headers
            )
            
            assert delete_response.status_code == 200
            assert "deleted successfully" in delete_response.json()["message"]

    def test_delete_nonexistent_endorsement(self, client: TestClient, auth_headers: dict):
        """Test deleting a non-existent endorsement."""
        response = client.delete("/api/endorsements/99999", headers=auth_headers)
        
        assert response.status_code == 404

    def test_delete_endorsement_unauthorized(self, client: TestClient):
        """Test deleting endorsement without authentication."""
        response = client.delete("/api/endorsements/1")
        
        assert response.status_code == 401
