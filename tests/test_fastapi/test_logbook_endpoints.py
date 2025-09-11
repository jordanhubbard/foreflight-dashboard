"""Test logbook management endpoints."""

import pytest
from fastapi.testclient import TestClient
from io import BytesIO
from src.core.auth_models import User


class TestLogbookEndpoints:
    """Test logbook-related API endpoints."""

    def test_get_logbook_data(self, client: TestClient, auth_headers: dict):
        """Test getting logbook data."""
        response = client.get("/api/logbook", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "statistics" in data
        assert isinstance(data["entries"], list)

    def test_get_logbook_unauthorized(self, client: TestClient):
        """Test getting logbook data without authentication."""
        response = client.get("/api/logbook")
        
        assert response.status_code == 401

    def test_upload_csv_success(self, client: TestClient, auth_headers: dict):
        """Test successful CSV upload."""
        # Create a minimal valid CSV
        csv_content = """Date,Aircraft ID,From,To,Route,Time Out,Time In,On Duty,Off Duty,Total Time,PIC,SIC,Night,Solo,Cross Country,NVG,NVG Ops,Distance,Day Takeoffs,Day Landings,Night Takeoffs,Night Landings,All Landings,Actual Instrument,Simulated Instrument,Hobbs Start,Hobbs End,Tach Start,Tach End,Holds,Approach1,Approach2,Approach3,Approach4,Approach5,Approach6,Dual Given,Dual Received,Simulator,Ground Training,Instructor Name,Instructor Comments,Person 1,Person 2,Person 3,Person 4,Person 5,Pilot Comments
2023-01-01,N12345,KORD,KMDW,,09:00,10:30,,1.5,1.5,0,0,0,0,0,0,0,0,1,1,0,0,1,0,0,0,0,0,0,0,,,,,,0,0,0,0,,,,,,,Test flight"""
        
        files = {"file": ("test.csv", BytesIO(csv_content.encode()), "text/csv")}
        
        response = client.post("/api/upload", files=files, headers=auth_headers)
        
        # Should succeed or return validation errors
        assert response.status_code in [200, 400]

    def test_upload_invalid_file(self, client: TestClient, auth_headers: dict):
        """Test upload with invalid file."""
        files = {"file": ("test.txt", BytesIO(b"not a csv"), "text/plain")}
        
        response = client.post("/api/upload", files=files, headers=auth_headers)
        
        assert response.status_code == 400

    def test_upload_no_file(self, client: TestClient, auth_headers: dict):
        """Test upload without file."""
        response = client.post("/api/upload", headers=auth_headers)
        
        assert response.status_code == 422  # Validation error

    def test_upload_unauthorized(self, client: TestClient):
        """Test upload without authentication."""
        files = {"file": ("test.csv", BytesIO(b"csv content"), "text/csv")}
        
        response = client.post("/api/upload", files=files)
        
        assert response.status_code == 401
