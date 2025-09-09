"""Tests for FastAPI API endpoints."""

import pytest
import io
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, mock_open

from src.main import app


@pytest.fixture
def test_client():
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    user = MagicMock()
    user.id = 1
    user.email = "test@example.com"
    user.first_name = "Test"
    user.last_name = "User"
    user.student_pilot = False
    user.pilot_certificate_number = "1234567"
    user.created_at = datetime.now(timezone.utc)
    return user


@pytest.fixture
def auth_headers():
    """Create authorization headers with valid token."""
    from src.core.auth import create_access_token
    token = create_access_token({"sub": "1"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for testing uploads."""
    return """Date,AircraftID,From,To,Route,TimeOut,TimeIn,TotalTime,PIC,SIC,Night,SoloTime,CrossCountry,NVision,ActualInstrument,SimulatedInstrument,GroundTrainer,DualGiven,DualReceived,ActualInstrumentApproaches,SimulatedInstrumentApproaches,DayTakeoffs,DayLandingsFullStop,NightTakeoffs,NightLandingsFullStop,AllLandings,PilotRole,FlightReview,Checkride,IPC,NVGProficiency,FAR1035935,FAR1351173,PersonRemarks,FlightRemarks
2023-01-01,N12345,KOAK,KSFO,,09:00,10:30,1.5,1.5,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,1,PIC,No,No,No,No,No,No,,Test flight
2023-01-02,N67890,KSFO,KOAK,,14:00,15:30,1.5,0,0,0,1.5,0,0,0,0,0,0,1.5,0,0,1,1,0,0,1,Student,No,No,No,No,No,No,,Training flight"""


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, test_client):
        """Test health check endpoint."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestStaticFileServing:
    """Test static file serving for React app."""

    def test_root_endpoint_serves_react_app(self, test_client):
        """Test that root endpoint serves React app."""
        with patch('pathlib.Path.exists') as mock_exists, \
             patch('builtins.open', mock_open(read_data="<html><body>React App</body></html>")):
            
            mock_exists.return_value = True
            
            response = test_client.get("/")
            
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]

    def test_root_endpoint_fallback_when_no_build(self, test_client):
        """Test fallback when React build doesn't exist."""
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = False
            
            response = test_client.get("/")
            
            assert response.status_code == 200
            assert "ForeFlight Dashboard" in response.text
            assert "React build not found" in response.text

    def test_spa_routing(self, test_client):
        """Test SPA routing serves React app for all routes."""
        with patch('pathlib.Path.exists') as mock_exists, \
             patch('builtins.open', mock_open(read_data="<html><body>React App</body></html>")):
            
            mock_exists.return_value = True
            
            # Test various client-side routes
            for route in ["/dashboard", "/profile", "/upload", "/settings"]:
                response = test_client.get(route)
                assert response.status_code == 200
                assert "text/html" in response.headers["content-type"]


class TestUserEndpoints:
    """Test user-related endpoints."""

    def test_get_current_user_info(self, test_client, mock_user, auth_headers):
        """Test getting current user information."""
        with patch('src.main.get_current_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            response = test_client.get("/api/user", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "test@example.com"
            assert data["first_name"] == "Test"
            assert data["last_name"] == "User"

    def test_get_current_user_unauthorized(self, test_client):
        """Test getting user info without authentication."""
        response = test_client.get("/api/user")
        
        assert response.status_code == 401

    def test_update_user_profile(self, test_client, mock_user, auth_headers):
        """Test updating user profile."""
        with patch('src.main.get_current_user') as mock_get_user, \
             patch('src.main.get_db') as mock_get_db:
            
            mock_get_user.return_value = mock_user
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            
            update_data = {
                "first_name": "Updated",
                "last_name": "Name",
                "student_pilot": True
            }
            
            response = test_client.put("/api/user", 
                                    json=update_data, 
                                    headers=auth_headers)
            
            assert response.status_code == 200
            
            # Verify user was updated
            assert mock_user.first_name == "Updated"
            assert mock_user.last_name == "Name"
            assert mock_user.student_pilot is True


class TestLogbookEndpoints:
    """Test logbook-related endpoints."""

    def test_get_logbook_data_no_logbook(self, test_client, mock_user, auth_headers):
        """Test getting logbook data when user has no logbook."""
        with patch('src.main.get_current_user') as mock_get_user, \
             patch('src.main.SessionLocal') as mock_session_local:
            
            mock_get_user.return_value = mock_user
            mock_session = MagicMock()
            mock_session_local.return_value = mock_session
            
            # Mock no active logbook
            mock_session.query.return_value.filter_by.return_value.order_by.return_value.first.return_value = None
            
            response = test_client.get("/api/logbook", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["entries"] == []
            assert data["logbook_filename"] is None
            assert data["error_count"] == 0

    def test_get_logbook_data_with_logbook(self, test_client, mock_user, auth_headers):
        """Test getting logbook data when user has a logbook."""
        with patch('src.main.get_current_user') as mock_get_user, \
             patch('src.main.SessionLocal') as mock_session_local, \
             patch('src.services.importer.ForeFlightImporter') as mock_importer:
            
            mock_get_user.return_value = mock_user
            mock_session = MagicMock()
            mock_session_local.return_value = mock_session
            
            # Mock active logbook
            mock_logbook = MagicMock()
            mock_logbook.filename = "test_logbook.csv"
            mock_session.query.return_value.filter_by.return_value.order_by.return_value.first.return_value = mock_logbook
            
            # Mock importer
            mock_importer_instance = MagicMock()
            mock_importer_instance.get_flight_entries.return_value = []
            mock_importer_instance.get_aircraft_list.return_value = []
            mock_importer.return_value = mock_importer_instance
            
            response = test_client.get("/api/logbook", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["logbook_filename"] == "test_logbook.csv"
            assert "entries" in data
            assert "stats" in data

    def test_upload_logbook_success(self, test_client, mock_user, auth_headers, sample_csv_content):
        """Test successful logbook upload."""
        with patch('src.main.get_current_user') as mock_get_user, \
             patch('src.main.get_db') as mock_get_db, \
             patch('src.services.importer.ForeFlightImporter') as mock_importer, \
             patch('builtins.open', mock_open()) as mock_file:
            
            mock_get_user.return_value = mock_user
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            
            # Mock successful import
            mock_importer_instance = MagicMock()
            mock_importer_instance.get_flight_entries.return_value = [MagicMock(), MagicMock()]  # 2 entries
            mock_importer.return_value = mock_importer_instance
            
            # Create file upload
            file_data = io.BytesIO(sample_csv_content.encode())
            
            response = test_client.post("/api/upload",
                                      files={"file": ("test.csv", file_data, "text/csv")},
                                      data={"student_pilot": "false"},
                                      headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "File uploaded successfully"
            assert "filename" in data

    def test_upload_logbook_invalid_file_type(self, test_client, mock_user, auth_headers):
        """Test upload with invalid file type."""
        with patch('src.main.get_current_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            file_data = io.BytesIO(b"not a csv file")
            
            response = test_client.post("/api/upload",
                                      files={"file": ("test.txt", file_data, "text/plain")},
                                      headers=auth_headers)
            
            assert response.status_code == 400
            assert "Only CSV files are allowed" in response.json()["detail"]

    def test_upload_logbook_no_entries(self, test_client, mock_user, auth_headers):
        """Test upload with CSV that has no valid entries."""
        with patch('src.main.get_current_user') as mock_get_user, \
             patch('src.main.get_db') as mock_get_db, \
             patch('src.services.importer.ForeFlightImporter') as mock_importer, \
             patch('builtins.open', mock_open()):
            
            mock_get_user.return_value = mock_user
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            
            # Mock empty import
            mock_importer_instance = MagicMock()
            mock_importer_instance.get_flight_entries.return_value = []
            mock_importer.return_value = mock_importer_instance
            
            file_data = io.BytesIO(b"Date,Aircraft\n")  # Empty CSV
            
            response = test_client.post("/api/upload",
                                      files={"file": ("empty.csv", file_data, "text/csv")},
                                      headers=auth_headers)
            
            assert response.status_code == 400
            assert "No valid entries found" in response.json()["detail"]


class TestEndorsementEndpoints:
    """Test endorsement-related endpoints."""

    def test_get_endorsements(self, test_client, mock_user, auth_headers):
        """Test getting user endorsements."""
        with patch('src.main.get_current_user') as mock_get_user, \
             patch('src.main.get_db') as mock_get_db:
            
            mock_get_user.return_value = mock_user
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            
            # Mock endorsements query
            mock_endorsement = MagicMock()
            mock_endorsement.id = 1
            mock_endorsement.user_id = 1
            mock_endorsement.start_date = datetime.now(timezone.utc)
            mock_endorsement.expiration_date = datetime.now(timezone.utc)
            mock_endorsement.created_at = datetime.now(timezone.utc)
            
            mock_db.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = [mock_endorsement]
            
            response = test_client.get("/api/endorsements", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == 1

    def test_create_endorsement(self, test_client, mock_user, auth_headers):
        """Test creating a new endorsement."""
        with patch('src.main.get_current_user') as mock_get_user, \
             patch('src.main.get_db') as mock_get_db:
            
            mock_get_user.return_value = mock_user
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            
            # Mock created endorsement
            mock_endorsement = MagicMock()
            mock_endorsement.id = 1
            mock_endorsement.user_id = 1
            mock_endorsement.start_date = datetime.now(timezone.utc)
            mock_endorsement.expiration_date = datetime.now(timezone.utc)
            mock_endorsement.created_at = datetime.now(timezone.utc)
            
            endorsement_data = {
                "start_date": "2023-01-01T10:00:00Z"
            }
            
            response = test_client.post("/api/endorsements",
                                      json=endorsement_data,
                                      headers=auth_headers)
            
            assert response.status_code == 200

    def test_delete_endorsement(self, test_client, mock_user, auth_headers):
        """Test deleting an endorsement."""
        with patch('src.main.get_current_user') as mock_get_user, \
             patch('src.main.get_db') as mock_get_db:
            
            mock_get_user.return_value = mock_user
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            
            # Mock endorsement exists
            mock_endorsement = MagicMock()
            mock_db.query.return_value.filter_by.return_value.first.return_value = mock_endorsement
            
            response = test_client.delete("/api/endorsements/1", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Endorsement deleted successfully"

    def test_delete_endorsement_not_found(self, test_client, mock_user, auth_headers):
        """Test deleting a non-existent endorsement."""
        with patch('src.main.get_current_user') as mock_get_user, \
             patch('src.main.get_db') as mock_get_db:
            
            mock_get_user.return_value = mock_user
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            
            # Mock endorsement not found
            mock_db.query.return_value.filter_by.return_value.first.return_value = None
            
            response = test_client.delete("/api/endorsements/999", headers=auth_headers)
            
            assert response.status_code == 404
            assert "Endorsement not found" in response.json()["detail"]


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_validation_error_handling(self, test_client):
        """Test validation error handling."""
        # Send invalid JSON to login endpoint
        response = test_client.post("/api/auth/login", json={
            "email": "not-an-email",  # Invalid email format
            "password": ""  # Empty password
        })
        
        assert response.status_code == 422
        assert "detail" in response.json()

    def test_internal_server_error_handling(self, test_client, auth_headers):
        """Test internal server error handling."""
        with patch('src.main.get_current_user') as mock_get_user:
            # Mock an exception
            mock_get_user.side_effect = Exception("Database connection failed")
            
            response = test_client.get("/api/user", headers=auth_headers)
            
            assert response.status_code == 500

    def test_unauthorized_access_to_protected_endpoints(self, test_client):
        """Test unauthorized access to protected endpoints."""
        protected_endpoints = [
            ("/api/user", "GET"),
            ("/api/user", "PUT"),
            ("/api/logbook", "GET"),
            ("/api/upload", "POST"),
            ("/api/endorsements", "GET"),
            ("/api/endorsements", "POST"),
            ("/api/endorsements/1", "DELETE")
        ]
        
        for endpoint, method in protected_endpoints:
            if method == "GET":
                response = test_client.get(endpoint)
            elif method == "PUT":
                response = test_client.put(endpoint, json={})
            elif method == "POST":
                response = test_client.post(endpoint, json={})
            elif method == "DELETE":
                response = test_client.delete(endpoint)
            
            assert response.status_code == 401


class TestAPIDocumentation:
    """Test API documentation endpoints."""

    def test_openapi_schema(self, test_client):
        """Test OpenAPI schema generation."""
        response = test_client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "ForeFlight Dashboard"

    def test_docs_endpoint(self, test_client):
        """Test Swagger UI docs endpoint."""
        response = test_client.get("/docs")
        
        assert response.status_code == 200
        assert "swagger-ui" in response.text.lower()

    def test_redoc_endpoint(self, test_client):
        """Test ReDoc endpoint."""
        response = test_client.get("/redoc")
        
        assert response.status_code == 200
        assert "redoc" in response.text.lower()
