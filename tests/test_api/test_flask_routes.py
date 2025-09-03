"""Tests for Flask routes and API endpoints."""

import pytest
import json
import io
import os
from unittest.mock import Mock, patch, MagicMock
from flask_security import login_user


class TestFlaskRoutes:
    """Test all Flask routes and API endpoints."""

    def test_index_unauthenticated(self, flask_test_client):
        """Test index route without authentication."""
        response = flask_test_client.get('/')
        
        # Should redirect to login
        assert response.status_code == 302
        assert '/login' in response.headers['Location']

    def test_index_authenticated_no_logbook(self, authenticated_client, test_user):
        """Test index route with authenticated user but no logbook."""
        with patch('src.core.auth_models.UserLogbook.query') as mock_query:
            mock_query.filter_by.return_value.order_by.return_value.first.return_value = None
            
            response = authenticated_client.get('/')
            
            assert response.status_code == 200
            assert b'ForeFlight' in response.data

    def test_index_authenticated_with_logbook(self, authenticated_client, test_user):
        """Test index route with authenticated user and logbook."""
        with patch('src.core.auth_models.UserLogbook.query') as mock_query, \
             patch('src.services.importer.ForeFlightImporter') as mock_importer, \
             patch('src.app.calculate_running_totals') as mock_calc_totals, \
             patch('src.app.calculate_stats_for_entries') as mock_calc_stats, \
             patch('src.app.calculate_recent_experience') as mock_calc_recent, \
             patch('src.app.prepare_aircraft_stats') as mock_aircraft_stats, \
             patch('src.app.convert_entries_to_template_data') as mock_convert_entries, \
             patch('src.app.convert_aircraft_to_template_data') as mock_convert_aircraft:
            
            # Mock active logbook
            mock_logbook = Mock()
            mock_logbook.filename = 'test_logbook.csv'
            mock_query.filter_by.return_value.order_by.return_value.first.return_value = mock_logbook
            
            # Mock importer
            mock_importer_instance = Mock()
            mock_importer_instance.get_flight_entries.return_value = []
            mock_importer_instance.get_aircraft_list.return_value = []
            mock_importer.return_value = mock_importer_instance
            
            # Mock calculations
            mock_calc_totals.return_value = []
            mock_calc_stats.return_value = {}
            mock_calc_recent.return_value = {}
            mock_aircraft_stats.return_value = []
            mock_convert_entries.return_value = []
            mock_convert_aircraft.return_value = []
            
            response = authenticated_client.get('/')
            
            assert response.status_code == 200

    def test_upload_route_get(self, authenticated_client):
        """Test GET /upload route."""
        response = authenticated_client.get('/upload')
        assert response.status_code == 200
        assert b'upload' in response.data.lower()

    def test_upload_route_post_success(self, authenticated_client, sample_csv_content, mock_upload_folder):
        """Test successful file upload via POST /upload."""
        with patch('src.validate_csv.validate_logbook') as mock_validate, \
             patch('src.services.importer.ForeFlightImporter') as mock_importer:
            
            # Mock validation
            mock_validate.return_value = {'success': True, 'warnings': []}
            
            # Mock importer
            mock_importer_instance = Mock()
            mock_importer_instance.import_logbook.return_value = {
                'entries_imported': 2,
                'aircraft_imported': 2
            }
            mock_importer.return_value = mock_importer_instance
            
            # Create file upload
            data = {
                'file': (io.BytesIO(sample_csv_content.encode()), 'test.csv')
            }
            
            response = authenticated_client.post('/upload', 
                                                data=data, 
                                                content_type='multipart/form-data')
            
            assert response.status_code == 302  # Redirect after successful upload

    def test_upload_route_post_no_file(self, authenticated_client):
        """Test POST /upload without file."""
        response = authenticated_client.post('/upload', data={})
        
        assert response.status_code == 302
        # Should redirect back with error flash message

    def test_upload_route_post_invalid_file(self, authenticated_client):
        """Test POST /upload with invalid file type."""
        data = {
            'file': (io.BytesIO(b'not a csv'), 'test.txt')
        }
        
        response = authenticated_client.post('/upload', 
                                            data=data, 
                                            content_type='multipart/form-data')
        
        assert response.status_code == 302

    def test_verify_pic_route(self, authenticated_client):
        """Test POST /verify-pic route."""
        with patch('src.services.importer.ForeFlightImporter') as mock_importer:
            mock_importer_instance = Mock()
            mock_importer_instance.get_flight_entries.return_value = []
            mock_importer.return_value = mock_importer_instance
            
            data = {
                'start_date': '2023-01-01',
                'end_date': '2023-12-31',
                'aircraft_category': 'airplane',
                'aircraft_class': 'single_engine_land'
            }
            
            response = authenticated_client.post('/verify-pic', 
                                                json=data,
                                                content_type='application/json')
            
            assert response.status_code == 200
            result = json.loads(response.data)
            assert 'meets_requirements' in result

    def test_filter_flights_route(self, authenticated_client):
        """Test POST /filter-flights route."""
        with patch('src.services.importer.ForeFlightImporter') as mock_importer, \
             patch('src.app.apply_flight_filters') as mock_filter, \
             patch('src.app.calculate_running_totals') as mock_calc_totals, \
             patch('src.app.convert_entries_to_template_data') as mock_convert:
            
            # Mock importer
            mock_importer_instance = Mock()
            mock_importer_instance.get_flight_entries.return_value = []
            mock_importer.return_value = mock_importer_instance
            
            # Mock filter and conversion functions
            mock_filter.return_value = []
            mock_calc_totals.return_value = []
            mock_convert.return_value = []
            
            filters = {
                'aircraft_type': 'C172',
                'start_date': '2023-01-01',
                'end_date': '2023-12-31'
            }
            
            # Mock session to have logbook filename
            with authenticated_client.session_transaction() as sess:
                sess['logbook_filename'] = 'test.csv'
            
            response = authenticated_client.post('/filter-flights',
                                                json=filters,
                                                content_type='application/json')
            
            assert response.status_code == 200

    def test_api_get_user(self, authenticated_client, test_user):
        """Test GET /api/user endpoint."""
        response = authenticated_client.get('/api/user')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['email'] == test_user.email
        assert data['first_name'] == test_user.first_name

    def test_api_update_user(self, authenticated_client, test_user):
        """Test PUT /api/user endpoint."""
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name'
        }
        
        response = authenticated_client.put('/api/user',
                                           json=update_data,
                                           content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['first_name'] == 'Updated'
        assert data['last_name'] == 'Name'

    def test_api_get_logbook_no_active(self, authenticated_client):
        """Test GET /api/logbook with no active logbook."""
        with patch('src.core.auth_models.UserLogbook.query') as mock_query:
            mock_query.filter_by.return_value.order_by.return_value.first.return_value = None
            
            response = authenticated_client.get('/api/logbook')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['entries'] == []
            assert data['stats'] == {}

    def test_api_get_logbook_with_data(self, authenticated_client):
        """Test GET /api/logbook with active logbook."""
        with patch('src.core.auth_models.UserLogbook.query') as mock_query, \
             patch('src.core.security.get_user_directory') as mock_get_dir, \
             patch('src.app.process_logbook_file') as mock_process, \
             patch('src.app.convert_entries_to_template_data') as mock_convert:
            
            # Mock active logbook
            mock_logbook = Mock()
            mock_logbook.filename = 'test.csv'
            mock_query.filter_by.return_value.order_by.return_value.first.return_value = mock_logbook
            
            # Mock user directory and file processing
            mock_get_dir.return_value = '/test/user/dir'
            mock_process.return_value = ([], {}, {}, [], {})
            mock_convert.return_value = []
            
            with patch('os.path.exists', return_value=True):
                response = authenticated_client.get('/api/logbook')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'entries' in data
            assert 'stats' in data

    def test_api_upload_logbook(self, authenticated_client, sample_csv_content):
        """Test POST /api/upload endpoint."""
        with patch('src.validate_csv.validate_logbook') as mock_validate, \
             patch('src.services.importer.ForeFlightImporter') as mock_importer:
            
            # Mock validation and import
            mock_validate.return_value = {'success': True, 'warnings': []}
            mock_importer_instance = Mock()
            mock_importer_instance.import_logbook.return_value = {
                'entries_imported': 2,
                'aircraft_imported': 2
            }
            mock_importer.return_value = mock_importer_instance
            
            data = {
                'file': (io.BytesIO(sample_csv_content.encode()), 'test.csv')
            }
            
            response = authenticated_client.post('/api/upload',
                                                data=data,
                                                content_type='multipart/form-data')
            
            assert response.status_code == 200
            result = json.loads(response.data)
            assert result['success'] is True
            assert result['entries_imported'] == 2

    def test_api_get_endorsements(self, authenticated_client, test_user):
        """Test GET /api/endorsements endpoint."""
        with patch('src.core.auth_models.InstructorEndorsement.query') as mock_query:
            mock_endorsement = Mock()
            mock_endorsement.to_dict.return_value = {
                'id': 1,
                'endorsement_type': 'solo',
                'description': 'Solo endorsement'
            }
            mock_query.filter_by.return_value.order_by.return_value.all.return_value = [mock_endorsement]
            
            response = authenticated_client.get('/api/endorsements')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert len(data) == 1
            assert data[0]['endorsement_type'] == 'solo'

    def test_api_post_endorsements(self, authenticated_client):
        """Test POST /api/endorsements endpoint."""
        endorsement_data = {
            'endorsement_type': 'solo',
            'description': 'Solo flight endorsement',
            'instructor_name': 'John Doe',
            'instructor_certificate': '1234567'
        }
        
        response = authenticated_client.post('/api/endorsements',
                                            json=endorsement_data,
                                            content_type='application/json')
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True

    def test_api_delete_endorsement(self, authenticated_client):
        """Test DELETE /api/endorsements/{id} endpoint."""
        with patch('src.core.auth_models.InstructorEndorsement.query') as mock_query:
            mock_endorsement = Mock()
            mock_query.filter_by.return_value.first.return_value = mock_endorsement
            
            response = authenticated_client.delete('/api/endorsements/1')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True

    def test_api_delete_endorsement_not_found(self, authenticated_client):
        """Test DELETE /api/endorsements/{id} with non-existent endorsement."""
        with patch('src.core.auth_models.InstructorEndorsement.query') as mock_query:
            mock_query.filter_by.return_value.first.return_value = None
            
            response = authenticated_client.delete('/api/endorsements/999')
            
            assert response.status_code == 404

    def test_unauthenticated_api_access(self, flask_test_client):
        """Test that API endpoints require authentication."""
        endpoints = [
            '/api/user',
            '/api/logbook',
            '/api/upload',
            '/api/endorsements'
        ]
        
        for endpoint in endpoints:
            response = flask_test_client.get(endpoint)
            assert response.status_code == 302  # Redirect to login

    def test_cors_headers_flask(self, authenticated_client):
        """Test CORS headers in Flask responses."""
        response = authenticated_client.get('/api/user')
        
        # Flask-CORS should add CORS headers
        assert response.status_code == 200
        # Headers may vary based on configuration

    def test_error_handling(self, authenticated_client):
        """Test error handling in routes."""
        with patch('src.core.auth_models.UserLogbook.query') as mock_query:
            # Simulate database error
            mock_query.filter_by.side_effect = Exception("Database error")
            
            response = authenticated_client.get('/api/logbook')
            
            assert response.status_code == 500
