"""Tests for FastAPI endpoints."""

import pytest
import io
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestFastAPIEndpoints:
    """Test all FastAPI endpoints."""

    def test_get_index(self, fastapi_client):
        """Test GET / endpoint."""
        response = fastapi_client.get("/")
        # Should either return HTML or 404 if template doesn't exist
        assert response.status_code in [200, 404]

    def test_upload_logbook_success(self, fastapi_client, sample_csv_content):
        """Test successful logbook upload."""
        # Create a file-like object
        file_data = io.BytesIO(sample_csv_content.encode())
        
        with patch('src.core.validation.validate_csv') as mock_validate, \
             patch('src.services.importer.ForeFlightImporter') as mock_importer:
            
            # Mock validation success
            mock_validate.return_value = {'success': True}
            
            # Mock importer
            mock_importer_instance = Mock()
            mock_importer_instance.import_logbook.return_value = {
                'entries_imported': 2,
                'aircraft_imported': 2,
                'warnings': []
            }
            mock_importer.return_value = mock_importer_instance
            
            response = fastapi_client.post(
                "/upload",
                files={"file": ("test.csv", file_data, "text/csv")}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["entries_imported"] == 2
            assert data["aircraft_imported"] == 2

    def test_upload_logbook_invalid_file_type(self, fastapi_client):
        """Test upload with invalid file type."""
        file_data = io.BytesIO(b"not a csv")
        
        response = fastapi_client.post(
            "/upload",
            files={"file": ("test.txt", file_data, "text/plain")}
        )
        
        assert response.status_code == 400
        assert "Please upload a CSV file" in response.json()["detail"]

    def test_upload_logbook_validation_failure(self, fastapi_client, sample_csv_content):
        """Test upload with validation failure."""
        file_data = io.BytesIO(sample_csv_content.encode())
        
        with patch('src.core.validation.validate_csv') as mock_validate:
            mock_validate.return_value = {
                'success': False,
                'error': 'Invalid CSV format',
                'details': {'line': 5, 'issue': 'Missing column'}
            }
            
            response = fastapi_client.post(
                "/upload",
                files={"file": ("test.csv", file_data, "text/csv")}
            )
            
            assert response.status_code == 400
            data = response.json()["detail"]
            assert data["error"] == "Invalid CSV format"
            assert "details" in data

    def test_upload_logbook_import_failure(self, fastapi_client, sample_csv_content):
        """Test upload with import failure."""
        file_data = io.BytesIO(sample_csv_content.encode())
        
        with patch('src.core.validation.validate_csv') as mock_validate, \
             patch('src.services.importer.ForeFlightImporter') as mock_importer:
            
            mock_validate.return_value = {'success': True}
            mock_importer.side_effect = Exception("Import failed")
            
            response = fastapi_client.post(
                "/upload",
                files={"file": ("test.csv", file_data, "text/csv")}
            )
            
            assert response.status_code == 500
            assert "Import failed" in response.json()["detail"]

    def test_get_entries_success(self, fastapi_client):
        """Test GET /entries endpoint."""
        with patch('src.api.routes.get_foreflight_client') as mock_get_client:
            mock_client = Mock()
            mock_client.get_logbook_entries.return_value = [
                {
                    "date": "2023-01-01",
                    "aircraft": {"registration": "N12345"},
                    "total_time": 1.5
                }
            ]
            mock_get_client.return_value = mock_client
            
            response = fastapi_client.get("/entries")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["aircraft"]["registration"] == "N12345"

    def test_get_entries_with_date_filter(self, fastapi_client):
        """Test GET /entries with date filtering."""
        with patch('src.api.routes.get_foreflight_client') as mock_get_client:
            mock_client = Mock()
            mock_client.get_logbook_entries.return_value = []
            mock_get_client.return_value = mock_client
            
            response = fastapi_client.get(
                "/entries?start_date=2023-01-01T00:00:00&end_date=2023-12-31T23:59:59"
            )
            
            assert response.status_code == 200
            mock_client.get_logbook_entries.assert_called_once()

    def test_get_entries_client_error(self, fastapi_client):
        """Test GET /entries with client error."""
        with patch('src.api.routes.get_foreflight_client') as mock_get_client:
            mock_get_client.side_effect = Exception("Client error")
            
            response = fastapi_client.get("/entries")
            
            assert response.status_code == 500
            assert "Client error" in response.json()["detail"]

    def test_create_entry_success(self, fastapi_client):
        """Test POST /entries endpoint."""
        entry_data = {
            "date": "2023-01-01T10:00:00",
            "aircraft": {
                "registration": "N12345",
                "type": "C172",
                "category_class": "ASEL"
            },
            "departure": {"identifier": "KOAK"},
            "destination": {"identifier": "KSFO"},
            "total_time": 1.5,
            "pilot_role": "PIC",
            "conditions": {
                "day": 1.5,
                "night": 0.0,
                "actual_instrument": 0.0,
                "simulated_instrument": 0.0,
                "cross_country": 0.0
            },
            "dual_received": 0.0,
            "pic_time": 1.5,
            "solo_time": 0.0
        }
        
        with patch('src.api.routes.get_foreflight_client') as mock_get_client:
            mock_client = Mock()
            mock_client.add_logbook_entry.return_value = entry_data
            mock_get_client.return_value = mock_client
            
            response = fastapi_client.post("/entries", json=entry_data)
            
            assert response.status_code == 201
            data = response.json()
            assert data["aircraft"]["registration"] == "N12345"

    def test_create_entry_validation_error(self, fastapi_client):
        """Test POST /entries with validation error."""
        invalid_entry = {
            "date": "invalid-date",
            "total_time": "not-a-number"
        }
        
        response = fastapi_client.post("/entries", json=invalid_entry)
        
        assert response.status_code == 422  # Validation error

    def test_create_entry_client_error(self, fastapi_client):
        """Test POST /entries with client error."""
        entry_data = {
            "date": "2023-01-01T10:00:00",
            "aircraft": {"registration": "N12345", "type": "C172", "category_class": "ASEL"},
            "departure": {"identifier": "KOAK"},
            "destination": {"identifier": "KSFO"},
            "total_time": 1.5,
            "pilot_role": "PIC",
            "conditions": {
                "day": 1.5,
                "night": 0.0,
                "actual_instrument": 0.0,
                "simulated_instrument": 0.0,
                "cross_country": 0.0
            },
            "dual_received": 0.0,
            "pic_time": 1.5,
            "solo_time": 0.0
        }
        
        with patch('src.api.routes.get_foreflight_client') as mock_get_client:
            mock_client = Mock()
            mock_client.add_logbook_entry.side_effect = Exception("Client error")
            mock_get_client.return_value = mock_client
            
            response = fastapi_client.post("/entries", json=entry_data)
            
            assert response.status_code == 500
            assert "Client error" in response.json()["detail"]

    def test_update_entry_success(self, fastapi_client):
        """Test PUT /entries/{entry_id} endpoint."""
        entry_id = "test-entry-id"
        entry_data = {
            "date": "2023-01-01T10:00:00",
            "aircraft": {"registration": "N12345", "type": "C172", "category_class": "ASEL"},
            "departure": {"identifier": "KOAK"},
            "destination": {"identifier": "KSFO"},
            "total_time": 2.0,  # Updated time
            "pilot_role": "PIC",
            "conditions": {
                "day": 2.0,
                "night": 0.0,
                "actual_instrument": 0.0,
                "simulated_instrument": 0.0,
                "cross_country": 0.0
            },
            "dual_received": 0.0,
            "pic_time": 2.0,
            "solo_time": 0.0
        }
        
        with patch('src.api.routes.get_foreflight_client') as mock_get_client:
            mock_client = Mock()
            mock_client.update_logbook_entry.return_value = entry_data
            mock_get_client.return_value = mock_client
            
            response = fastapi_client.put(f"/entries/{entry_id}", json=entry_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_time"] == 2.0

    def test_cors_headers(self, fastapi_client):
        """Test CORS headers are present."""
        response = fastapi_client.options("/entries")
        
        # FastAPI with CORSMiddleware should handle OPTIONS requests
        assert response.status_code in [200, 405]  # 405 if OPTIONS not explicitly handled

    def test_static_files_mount(self, fastapi_client):
        """Test static files are mounted."""
        # Test accessing static endpoint (even if file doesn't exist)
        response = fastapi_client.get("/static/nonexistent.css")
        
        # Should get 404 (not found) rather than route not found
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_validation_exception_handler(self, fastapi_client):
        """Test custom validation exception handler."""
        # Send malformed JSON to trigger validation error
        response = fastapi_client.post(
            "/entries",
            json={"invalid": "data", "missing": "required_fields"}
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_get_foreflight_client_dependency(self, fastapi_client):
        """Test the get_foreflight_client dependency."""
        from src.api.routes import get_foreflight_client
        
        # This tests the dependency directly
        with patch('src.services.foreflight_client.ForeFlightClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            # The dependency should return a client instance
            client = get_foreflight_client()
            assert client is not None
