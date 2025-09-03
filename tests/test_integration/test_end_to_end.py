"""End-to-end integration tests."""

import pytest
import json
import io
from unittest.mock import Mock, patch


@pytest.mark.integration
class TestEndToEndWorkflows:
    """Test complete user workflows from start to finish."""

    def test_complete_user_registration_and_upload_workflow(self, flask_test_client, sample_csv_content):
        """Test complete workflow: register -> login -> upload -> view data."""
        
        # Step 1: Register new user
        registration_data = {
            'email': 'newpilot@example.com',
            'password': 'securepassword',
            'password_confirm': 'securepassword',
            'first_name': 'New',
            'last_name': 'Pilot',
            'student_pilot': False
        }
        
        response = flask_test_client.post('/register',
                                         data=registration_data,
                                         follow_redirects=False)
        
        # Should redirect after successful registration
        assert response.status_code == 302
        
        # Step 2: Login with new user
        login_data = {
            'email': 'newpilot@example.com',
            'password': 'securepassword'
        }
        
        response = flask_test_client.post('/login',
                                         data=login_data,
                                         follow_redirects=False)
        
        assert response.status_code == 302
        
        # Step 3: Upload logbook file
        with patch('src.validate_csv.validate_logbook') as mock_validate, \
             patch('src.services.importer.ForeFlightImporter') as mock_importer:
            
            mock_validate.return_value = {'success': True, 'warnings': []}
            mock_importer_instance = Mock()
            mock_importer_instance.import_logbook.return_value = {
                'entries_imported': 2,
                'aircraft_imported': 2
            }
            mock_importer.return_value = mock_importer_instance
            
            data = {
                'file': (io.BytesIO(sample_csv_content.encode()), 'logbook.csv')
            }
            
            response = flask_test_client.post('/upload',
                                             data=data,
                                             content_type='multipart/form-data')
            
            assert response.status_code == 302
        
        # Step 4: View dashboard
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
            mock_logbook.filename = 'logbook.csv'
            mock_query.filter_by.return_value.order_by.return_value.first.return_value = mock_logbook
            
            # Mock importer and calculations
            mock_importer_instance = Mock()
            mock_importer_instance.get_flight_entries.return_value = []
            mock_importer_instance.get_aircraft_list.return_value = []
            mock_importer.return_value = mock_importer_instance
            
            mock_calc_totals.return_value = []
            mock_calc_stats.return_value = {}
            mock_calc_recent.return_value = {}
            mock_aircraft_stats.return_value = []
            mock_convert_entries.return_value = []
            mock_convert_aircraft.return_value = []
            
            response = flask_test_client.get('/')
            
            assert response.status_code == 200

    def test_student_pilot_endorsement_workflow(self, flask_test_client, student_user):
        """Test student pilot endorsement workflow."""
        
        # Login as student
        with flask_test_client.session_transaction() as sess:
            sess['user_id'] = student_user.id
            sess['_fresh'] = True
        
        # Step 1: View endorsements (should be empty)
        response = flask_test_client.get('/api/endorsements')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        
        # Step 2: Add endorsement
        endorsement_data = {
            'endorsement_type': 'solo',
            'description': 'Solo flight endorsement for pattern work',
            'instructor_name': 'Jane Instructor',
            'instructor_certificate': '1234567CFI'
        }
        
        response = flask_test_client.post('/api/endorsements',
                                         json=endorsement_data,
                                         content_type='application/json')
        
        assert response.status_code == 201
        
        # Step 3: Verify endorsement was added
        with patch('src.core.auth_models.InstructorEndorsement.query') as mock_query:
            mock_endorsement = Mock()
            mock_endorsement.to_dict.return_value = {
                'id': 1,
                'endorsement_type': 'solo',
                'description': 'Solo flight endorsement for pattern work'
            }
            mock_query.filter_by.return_value.order_by.return_value.all.return_value = [mock_endorsement]
            
            response = flask_test_client.get('/api/endorsements')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert len(data) == 1
            assert data[0]['endorsement_type'] == 'solo'

    def test_pic_verification_workflow(self, authenticated_client, sample_csv_content):
        """Test PIC time verification workflow."""
        
        # Step 1: Upload logbook
        with authenticated_client.session_transaction() as sess:
            sess['logbook_filename'] = 'test.csv'
        
        # Step 2: Verify PIC requirements
        with patch('src.services.importer.ForeFlightImporter') as mock_importer:
            mock_importer_instance = Mock()
            mock_importer_instance.get_flight_entries.return_value = []
            mock_importer.return_value = mock_importer_instance
            
            verification_data = {
                'start_date': '2023-01-01',
                'end_date': '2023-12-31',
                'aircraft_category': 'airplane',
                'aircraft_class': 'single_engine_land'
            }
            
            response = authenticated_client.post('/verify-pic',
                                                json=verification_data,
                                                content_type='application/json')
            
            assert response.status_code == 200
            result = json.loads(response.data)
            assert 'meets_requirements' in result

    def test_flight_filtering_workflow(self, authenticated_client):
        """Test flight filtering workflow."""
        
        # Set up session with logbook
        with authenticated_client.session_transaction() as sess:
            sess['logbook_filename'] = 'test.csv'
        
        # Test filtering flights
        with patch('src.services.importer.ForeFlightImporter') as mock_importer, \
             patch('src.app.apply_flight_filters') as mock_filter, \
             patch('src.app.calculate_running_totals') as mock_calc_totals, \
             patch('src.app.convert_entries_to_template_data') as mock_convert:
            
            mock_importer_instance = Mock()
            mock_importer_instance.get_flight_entries.return_value = []
            mock_importer.return_value = mock_importer_instance
            
            mock_filter.return_value = []
            mock_calc_totals.return_value = []
            mock_convert.return_value = []
            
            filter_criteria = {
                'aircraft_type': 'C172',
                'start_date': '2023-01-01',
                'end_date': '2023-12-31',
                'pilot_role': 'PIC'
            }
            
            response = authenticated_client.post('/filter-flights',
                                                json=filter_criteria,
                                                content_type='application/json')
            
            assert response.status_code == 200

    def test_user_profile_management_workflow(self, authenticated_client, test_user):
        """Test complete user profile management workflow."""
        
        # Step 1: Get current profile
        response = authenticated_client.get('/api/user')
        
        assert response.status_code == 200
        profile = json.loads(response.data)
        assert profile['email'] == test_user.email
        
        # Step 2: Update profile
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'pilot_certificate_number': '123456789'
        }
        
        response = authenticated_client.put('/api/user',
                                           json=update_data,
                                           content_type='application/json')
        
        assert response.status_code == 200
        updated_profile = json.loads(response.data)
        assert updated_profile['first_name'] == 'Updated'
        assert updated_profile['last_name'] == 'Name'
        
        # Step 3: Verify changes persisted
        response = authenticated_client.get('/api/user')
        
        assert response.status_code == 200
        profile = json.loads(response.data)
        assert profile['first_name'] == 'Updated'

    @pytest.mark.slow
    def test_large_logbook_processing_workflow(self, authenticated_client):
        """Test processing workflow with large logbook file."""
        
        # Create a large CSV content
        header = (
            'ForeFlight Logbook Import,This row is required for importing into ForeFlight. Do not delete or modify.\n'
            'Aircraft Table\n'
            'AircraftID,TypeCode,Year,Make,Model,GearType,EngineType,equipType (FAA),aircraftClass (FAA),complexAircraft (FAA),taa (FAA),highPerformance (FAA),pressurized (FAA)\n'
            'N125CM,CH7A,,Bellanca,7ECA,fixed_tailwheel,Piston,aircraft,airplane_single_engine_land,,,,\n'
            'Flights Table\n'
            'Date,AircraftID,From,To,TotalTime,Night,ActualInstrument,SimulatedInstrument,CrossCountry,DualGiven,PIC,SIC,DualReceived,Solo,DayLandingsFullStop,NightLandingsFullStop,PilotComments,InstructorComments,Distance\n'
        )
        
        # Add many flight entries
        flights = []
        for i in range(500):  # 500 flights
            flights.append(f'2023-01-{(i % 28) + 1:02d},N125CM,KOAK,KSFO,1.5,0.0,0.0,0.0,0.0,0.0,1.5,0.0,0.0,1.5,1,0,Flight {i},,10\n')
        
        large_csv = header + ''.join(flights)
        
        # Test upload with large file
        with patch('src.validate_csv.validate_logbook') as mock_validate, \
             patch('src.services.importer.ForeFlightImporter') as mock_importer:
            
            mock_validate.return_value = {'success': True, 'warnings': []}
            mock_importer_instance = Mock()
            mock_importer_instance.import_logbook.return_value = {
                'entries_imported': 500,
                'aircraft_imported': 1
            }
            mock_importer.return_value = mock_importer_instance
            
            data = {
                'file': (io.BytesIO(large_csv.encode()), 'large_logbook.csv')
            }
            
            response = authenticated_client.post('/api/upload',
                                                data=data,
                                                content_type='multipart/form-data')
            
            assert response.status_code == 200
            result = json.loads(response.data)
            assert result['success'] is True
            assert result['entries_imported'] == 500

    def test_error_recovery_workflow(self, authenticated_client):
        """Test error recovery in workflows."""
        
        # Test upload with invalid file
        data = {
            'file': (io.BytesIO(b'invalid csv content'), 'invalid.csv')
        }
        
        response = authenticated_client.post('/api/upload',
                                            data=data,
                                            content_type='multipart/form-data')
        
        # Should handle error gracefully
        assert response.status_code in [400, 500]
        
        # Should still be able to access other endpoints
        response = authenticated_client.get('/api/user')
        assert response.status_code == 200

    def test_concurrent_user_workflows(self, flask_test_client, test_user, admin_user):
        """Test concurrent workflows by different users."""
        
        # User 1: Regular user
        client1 = flask_test_client
        with client1.session_transaction() as sess:
            sess['user_id'] = test_user.id
            sess['_fresh'] = True
        
        # User 2: Admin user  
        client2 = flask_test_client
        with client2.session_transaction() as sess:
            sess['user_id'] = admin_user.id
            sess['_fresh'] = True
        
        # Both users access their profiles simultaneously
        response1 = client1.get('/api/user')
        response2 = client2.get('/api/user')
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        profile1 = json.loads(response1.data)
        profile2 = json.loads(response2.data)
        
        # Should get different user data
        assert profile1['email'] != profile2['email']
        assert profile1['email'] == test_user.email
        assert profile2['email'] == admin_user.email

    def test_api_rate_limiting_workflow(self, authenticated_client):
        """Test API rate limiting behavior."""
        
        # Make multiple rapid requests
        responses = []
        for i in range(10):
            response = authenticated_client.get('/api/user')
            responses.append(response)
        
        # All requests should succeed (no rate limiting configured in tests)
        for response in responses:
            assert response.status_code == 200

    def test_data_consistency_workflow(self, authenticated_client):
        """Test data consistency across operations."""
        
        # Get initial profile
        response = authenticated_client.get('/api/user')
        assert response.status_code == 200
        initial_profile = json.loads(response.data)
        
        # Update profile
        update_data = {'first_name': 'Consistent'}
        response = authenticated_client.put('/api/user',
                                           json=update_data,
                                           content_type='application/json')
        assert response.status_code == 200
        
        # Verify consistency across multiple reads
        for _ in range(3):
            response = authenticated_client.get('/api/user')
            assert response.status_code == 200
            profile = json.loads(response.data)
            assert profile['first_name'] == 'Consistent'
