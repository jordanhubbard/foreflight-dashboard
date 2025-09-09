"""Integration tests for FastAPI application."""

import pytest
import io
import tempfile
import os
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.main import app
from src.core.auth import create_access_token


@pytest.fixture
def test_client():
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_logbook_csv():
    """Sample logbook CSV content."""
    return """Date,AircraftID,From,To,Route,TimeOut,TimeIn,TotalTime,PIC,SIC,Night,SoloTime,CrossCountry,NVision,ActualInstrument,SimulatedInstrument,GroundTrainer,DualGiven,DualReceived,ActualInstrumentApproaches,SimulatedInstrumentApproaches,DayTakeoffs,DayLandingsFullStop,NightTakeoffs,NightLandingsFullStop,AllLandings,PilotRole,FlightReview,Checkride,IPC,NVGProficiency,FAR1035935,FAR1351173,PersonRemarks,FlightRemarks
2023-01-01,N12345,KOAK,KSFO,,09:00,10:30,1.5,1.5,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,1,PIC,No,No,No,No,No,No,,First flight of the year
2023-01-15,N12345,KSFO,KPAO,,14:00,15:00,1.0,1.0,0,0,0,50,0,0,0,0,0,0,0,0,1,1,0,0,1,PIC,No,No,No,No,No,No,,Cross country flight
2023-02-01,N67890,KPAO,KHAF,,10:00,11:30,1.5,0,0,0,1.5,0,0,0,0,0,0,1.5,0,0,1,1,0,0,1,Student,No,No,No,No,No,No,,Training with instructor"""


class TestCompleteUserWorkflow:
    """Test complete user workflows from registration to logbook analysis."""

    def test_complete_user_registration_and_logbook_workflow(self, test_client, sample_logbook_csv):
        """Test complete workflow: register -> login -> upload -> view data."""
        
        with patch('src.main.get_db') as mock_get_db, \
             patch('src.main.create_user') as mock_create_user, \
             patch('src.main.authenticate_user') as mock_auth_user, \
             patch('src.main.SessionLocal') as mock_session_local, \
             patch('src.services.importer.ForeFlightImporter') as mock_importer, \
             patch('builtins.open') as mock_open_file:
            
            # Setup mocks
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_session_local.return_value = mock_db
            
            # Step 1: Register new user
            mock_user = MagicMock()
            mock_user.id = 1
            mock_user.email = "newpilot@example.com"
            mock_user.first_name = "New"
            mock_user.last_name = "Pilot"
            mock_user.student_pilot = False
            mock_user.created_at = datetime.now(timezone.utc)
            mock_create_user.return_value = mock_user
            
            registration_response = test_client.post("/api/auth/register", json={
                "email": "newpilot@example.com",
                "password": "securepassword123",
                "first_name": "New",
                "last_name": "Pilot",
                "student_pilot": False
            })
            
            assert registration_response.status_code == 200
            assert registration_response.json()["email"] == "newpilot@example.com"
            
            # Step 2: Login with new user
            mock_auth_user.return_value = mock_user
            
            login_response = test_client.post("/api/auth/login", json={
                "email": "newpilot@example.com",
                "password": "securepassword123"
            })
            
            assert login_response.status_code == 200
            login_data = login_response.json()
            assert "access_token" in login_data
            assert login_data["token_type"] == "bearer"
            
            # Extract token for subsequent requests
            token = login_data["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Step 3: Get user profile
            with patch('src.main.get_current_user') as mock_get_current_user:
                mock_get_current_user.return_value = mock_user
                
                profile_response = test_client.get("/api/user", headers=headers)
                
                assert profile_response.status_code == 200
                profile_data = profile_response.json()
                assert profile_data["email"] == "newpilot@example.com"
                assert profile_data["first_name"] == "New"
            
            # Step 4: Upload logbook file
            with patch('src.main.get_current_user') as mock_get_current_user:
                mock_get_current_user.return_value = mock_user
                
                # Mock successful file processing
                mock_importer_instance = MagicMock()
                mock_entries = [MagicMock(), MagicMock(), MagicMock()]  # 3 entries
                mock_importer_instance.get_flight_entries.return_value = mock_entries
                mock_importer.return_value = mock_importer_instance
                
                # Mock logbook creation
                mock_logbook = MagicMock()
                mock_logbook.filename = "test_logbook.csv"
                
                file_data = io.BytesIO(sample_logbook_csv.encode())
                
                upload_response = test_client.post("/api/upload",
                                                 files={"file": ("logbook.csv", file_data, "text/csv")},
                                                 data={"student_pilot": "false"},
                                                 headers=headers)
                
                assert upload_response.status_code == 200
                upload_data = upload_response.json()
                assert upload_data["message"] == "File uploaded successfully"
            
            # Step 5: View logbook data
            with patch('src.main.get_current_user') as mock_get_current_user:
                mock_get_current_user.return_value = mock_user
                
                # Mock active logbook
                mock_logbook = MagicMock()
                mock_logbook.filename = "test_logbook.csv"
                mock_db.query.return_value.filter_by.return_value.order_by.return_value.first.return_value = mock_logbook
                
                # Mock importer for logbook data
                mock_importer_instance.get_flight_entries.return_value = mock_entries
                mock_importer_instance.get_aircraft_list.return_value = []
                
                logbook_response = test_client.get("/api/logbook", headers=headers)
                
                assert logbook_response.status_code == 200
                logbook_data = logbook_response.json()
                assert logbook_data["logbook_filename"] == "test_logbook.csv"
                assert "entries" in logbook_data
                assert "stats" in logbook_data

    def test_student_pilot_endorsement_workflow(self, test_client):
        """Test student pilot endorsement management workflow."""
        
        with patch('src.main.get_db') as mock_get_db, \
             patch('src.main.get_current_user') as mock_get_current_user:
            
            # Setup student pilot user
            mock_user = MagicMock()
            mock_user.id = 1
            mock_user.email = "student@example.com"
            mock_user.student_pilot = True
            mock_get_current_user.return_value = mock_user
            
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            
            token = create_access_token({"sub": "1"})
            headers = {"Authorization": f"Bearer {token}"}
            
            # Step 1: Check initial endorsements (should be empty)
            mock_db.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = []
            
            endorsements_response = test_client.get("/api/endorsements", headers=headers)
            
            assert endorsements_response.status_code == 200
            assert len(endorsements_response.json()) == 0
            
            # Step 2: Create new endorsement
            mock_endorsement = MagicMock()
            mock_endorsement.id = 1
            mock_endorsement.user_id = 1
            mock_endorsement.start_date = datetime.now(timezone.utc)
            mock_endorsement.expiration_date = datetime.now(timezone.utc)
            mock_endorsement.created_at = datetime.now(timezone.utc)
            
            create_response = test_client.post("/api/endorsements", 
                                             json={"start_date": "2023-01-01T10:00:00Z"},
                                             headers=headers)
            
            assert create_response.status_code == 200
            
            # Step 3: View updated endorsements list
            mock_db.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = [mock_endorsement]
            
            updated_endorsements_response = test_client.get("/api/endorsements", headers=headers)
            
            assert updated_endorsements_response.status_code == 200
            endorsements = updated_endorsements_response.json()
            assert len(endorsements) == 1
            
            # Step 4: Delete endorsement
            mock_db.query.return_value.filter_by.return_value.first.return_value = mock_endorsement
            
            delete_response = test_client.delete("/api/endorsements/1", headers=headers)
            
            assert delete_response.status_code == 200
            assert delete_response.json()["message"] == "Endorsement deleted successfully"

    def test_profile_management_workflow(self, test_client):
        """Test user profile management workflow."""
        
        with patch('src.main.get_db') as mock_get_db, \
             patch('src.main.get_current_user') as mock_get_current_user:
            
            # Setup user
            mock_user = MagicMock()
            mock_user.id = 1
            mock_user.email = "pilot@example.com"
            mock_user.first_name = "John"
            mock_user.last_name = "Doe"
            mock_user.student_pilot = False
            mock_user.pilot_certificate_number = None
            mock_get_current_user.return_value = mock_user
            
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            
            token = create_access_token({"sub": "1"})
            headers = {"Authorization": f"Bearer {token}"}
            
            # Step 1: Get initial profile
            profile_response = test_client.get("/api/user", headers=headers)
            
            assert profile_response.status_code == 200
            profile = profile_response.json()
            assert profile["first_name"] == "John"
            assert profile["student_pilot"] is False
            
            # Step 2: Update profile
            update_data = {
                "first_name": "Jonathan",
                "student_pilot": True,
                "pilot_certificate_number": "1234567890"
            }
            
            update_response = test_client.put("/api/user", 
                                            json=update_data,
                                            headers=headers)
            
            assert update_response.status_code == 200
            
            # Verify updates were applied
            assert mock_user.first_name == "Jonathan"
            assert mock_user.student_pilot is True
            assert mock_user.pilot_certificate_number == "1234567890"


class TestErrorRecoveryWorkflows:
    """Test error recovery and edge case workflows."""

    def test_invalid_logbook_upload_recovery(self, test_client):
        """Test recovery from invalid logbook upload."""
        
        with patch('src.main.get_db') as mock_get_db, \
             patch('src.main.get_current_user') as mock_get_current_user:
            
            mock_user = MagicMock()
            mock_user.id = 1
            mock_get_current_user.return_value = mock_user
            
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            
            token = create_access_token({"sub": "1"})
            headers = {"Authorization": f"Bearer {token}"}
            
            # Step 1: Try to upload invalid file type
            invalid_file = io.BytesIO(b"This is not a CSV file")
            
            response = test_client.post("/api/upload",
                                      files={"file": ("invalid.txt", invalid_file, "text/plain")},
                                      headers=headers)
            
            assert response.status_code == 400
            assert "Only CSV files are allowed" in response.json()["detail"]
            
            # Step 2: Try to upload empty CSV
            with patch('src.services.importer.ForeFlightImporter') as mock_importer:
                mock_importer_instance = MagicMock()
                mock_importer_instance.get_flight_entries.return_value = []  # No entries
                mock_importer.return_value = mock_importer_instance
                
                empty_csv = io.BytesIO(b"Date,Aircraft\n")  # Header only
                
                response = test_client.post("/api/upload",
                                          files={"file": ("empty.csv", empty_csv, "text/csv")},
                                          headers=headers)
                
                assert response.status_code == 400
                assert "No valid entries found" in response.json()["detail"]
            
            # Step 3: Upload valid CSV (recovery)
            with patch('src.services.importer.ForeFlightImporter') as mock_importer, \
                 patch('builtins.open'):
                
                mock_importer_instance = MagicMock()
                mock_importer_instance.get_flight_entries.return_value = [MagicMock()]  # Valid entry
                mock_importer.return_value = mock_importer_instance
                
                valid_csv = io.BytesIO(b"Date,AircraftID,TotalTime\n2023-01-01,N12345,1.5\n")
                
                response = test_client.post("/api/upload",
                                          files={"file": ("valid.csv", valid_csv, "text/csv")},
                                          headers=headers)
                
                assert response.status_code == 200
                assert response.json()["message"] == "File uploaded successfully"

    def test_authentication_token_expiry_workflow(self, test_client):
        """Test handling of expired authentication tokens."""
        
        # Create expired token
        from src.core.auth import SECRET_KEY, ALGORITHM
        import jwt
        from datetime import timedelta
        
        expired_payload = {
            "sub": "1",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1)  # Expired
        }
        expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)
        headers = {"Authorization": f"Bearer {expired_token}"}
        
        # Try to access protected endpoint with expired token
        response = test_client.get("/api/user", headers=headers)
        
        assert response.status_code == 401
        
        # Login again to get new token
        with patch('src.main.get_db') as mock_get_db, \
             patch('src.main.authenticate_user') as mock_auth_user:
            
            mock_user = MagicMock()
            mock_user.id = 1
            mock_user.email = "test@example.com"
            mock_auth_user.return_value = mock_user
            
            login_response = test_client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "password123"
            })
            
            assert login_response.status_code == 200
            new_token = login_response.json()["access_token"]
            
            # Use new token to access protected endpoint
            new_headers = {"Authorization": f"Bearer {new_token}"}
            
            with patch('src.main.get_current_user') as mock_get_current_user:
                mock_get_current_user.return_value = mock_user
                
                response = test_client.get("/api/user", headers=new_headers)
                
                assert response.status_code == 200


class TestConcurrentUserWorkflows:
    """Test concurrent user operations."""

    def test_multiple_users_different_logbooks(self, test_client):
        """Test multiple users with different logbooks."""
        
        with patch('src.main.get_db') as mock_get_db, \
             patch('src.main.SessionLocal') as mock_session_local, \
             patch('src.main.get_current_user') as mock_get_current_user:
            
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_session_local.return_value = mock_db
            
            # User 1
            user1 = MagicMock()
            user1.id = 1
            user1.email = "pilot1@example.com"
            
            # User 2  
            user2 = MagicMock()
            user2.id = 2
            user2.email = "pilot2@example.com"
            
            token1 = create_access_token({"sub": "1"})
            token2 = create_access_token({"sub": "2"})
            
            headers1 = {"Authorization": f"Bearer {token1}"}
            headers2 = {"Authorization": f"Bearer {token2}"}
            
            # Mock different logbooks for each user
            def mock_get_current_user_side_effect(*args, **kwargs):
                # This is a simplified mock - in reality, we'd need to check the token
                if "1" in str(args) or "1" in str(kwargs):
                    return user1
                return user2
            
            mock_get_current_user.side_effect = lambda: user1  # Simplified for test
            
            # User 1 gets their logbook
            logbook1 = MagicMock()
            logbook1.filename = "user1_logbook.csv"
            logbook1.user_id = 1
            
            mock_db.query.return_value.filter_by.return_value.order_by.return_value.first.return_value = logbook1
            
            with patch('src.services.importer.ForeFlightImporter') as mock_importer:
                mock_importer_instance = MagicMock()
                mock_importer_instance.get_flight_entries.return_value = [MagicMock()]  # 1 entry
                mock_importer_instance.get_aircraft_list.return_value = []
                mock_importer.return_value = mock_importer_instance
                
                response1 = test_client.get("/api/logbook", headers=headers1)
                
                assert response1.status_code == 200
                data1 = response1.json()
                assert data1["logbook_filename"] == "user1_logbook.csv"
            
            # User 2 gets their logbook (different data)
            mock_get_current_user.side_effect = lambda: user2
            
            logbook2 = MagicMock()
            logbook2.filename = "user2_logbook.csv"
            logbook2.user_id = 2
            
            mock_db.query.return_value.filter_by.return_value.order_by.return_value.first.return_value = logbook2
            
            with patch('src.services.importer.ForeFlightImporter') as mock_importer:
                mock_importer_instance = MagicMock()
                mock_importer_instance.get_flight_entries.return_value = [MagicMock(), MagicMock()]  # 2 entries
                mock_importer_instance.get_aircraft_list.return_value = []
                mock_importer.return_value = mock_importer_instance
                
                response2 = test_client.get("/api/logbook", headers=headers2)
                
                assert response2.status_code == 200
                data2 = response2.json()
                assert data2["logbook_filename"] == "user2_logbook.csv"
            
            # Verify users get different data
            assert data1["logbook_filename"] != data2["logbook_filename"]


class TestDataConsistencyWorkflows:
    """Test data consistency across operations."""

    def test_logbook_update_consistency(self, test_client):
        """Test consistency when updating logbook data."""
        
        with patch('src.main.get_db') as mock_get_db, \
             patch('src.main.SessionLocal') as mock_session_local, \
             patch('src.main.get_current_user') as mock_get_current_user:
            
            mock_user = MagicMock()
            mock_user.id = 1
            mock_user.student_pilot = False
            mock_get_current_user.return_value = mock_user
            
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_session_local.return_value = mock_db
            
            token = create_access_token({"sub": "1"})
            headers = {"Authorization": f"Bearer {token}"}
            
            # Step 1: Upload first logbook
            with patch('src.services.importer.ForeFlightImporter') as mock_importer, \
                 patch('builtins.open'):
                
                mock_importer_instance = MagicMock()
                mock_importer_instance.get_flight_entries.return_value = [MagicMock()]
                mock_importer.return_value = mock_importer_instance
                
                # Mock deactivating old logbooks
                mock_db.query.return_value.filter_by.return_value.update.return_value = None
                
                file1 = io.BytesIO(b"Date,AircraftID,TotalTime\n2023-01-01,N12345,1.5\n")
                
                response1 = test_client.post("/api/upload",
                                           files={"file": ("logbook1.csv", file1, "text/csv")},
                                           headers=headers)
                
                assert response1.status_code == 200
            
            # Step 2: Upload second logbook (should deactivate first)
            with patch('src.services.importer.ForeFlightImporter') as mock_importer, \
                 patch('builtins.open'):
                
                mock_importer_instance = MagicMock()
                mock_importer_instance.get_flight_entries.return_value = [MagicMock(), MagicMock()]
                mock_importer.return_value = mock_importer_instance
                
                file2 = io.BytesIO(b"Date,AircraftID,TotalTime\n2023-01-01,N12345,1.5\n2023-01-02,N67890,2.0\n")
                
                response2 = test_client.post("/api/upload",
                                           files={"file": ("logbook2.csv", file2, "text/csv")},
                                           headers=headers)
                
                assert response2.status_code == 200
            
            # Step 3: Verify only latest logbook is active
            latest_logbook = MagicMock()
            latest_logbook.filename = "logbook2.csv"
            latest_logbook.is_active = True
            
            mock_db.query.return_value.filter_by.return_value.order_by.return_value.first.return_value = latest_logbook
            
            with patch('src.services.importer.ForeFlightImporter') as mock_importer:
                mock_importer_instance = MagicMock()
                mock_importer_instance.get_flight_entries.return_value = [MagicMock(), MagicMock()]
                mock_importer_instance.get_aircraft_list.return_value = []
                mock_importer.return_value = mock_importer_instance
                
                response3 = test_client.get("/api/logbook", headers=headers)
                
                assert response3.status_code == 200
                data = response3.json()
                assert "logbook2" in data["logbook_filename"]
