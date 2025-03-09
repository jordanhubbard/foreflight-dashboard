"""Tests for the core models."""

from datetime import datetime, time
import pytest
from src.core.models import LogbookEntry, Aircraft, Airport, FlightConditions

def create_valid_entry():
    """Create a valid logbook entry for testing."""
    return LogbookEntry(
        date=datetime.now(),
        total_time=1.5,
        aircraft=Aircraft(
            registration="N12345",
            type="C172",
            category_class="ASEL"
        ),
        departure=Airport(identifier="KBOS"),
        destination=Airport(identifier="KJFK"),
        conditions=FlightConditions(
            day=1.5,
            night=0.0,
            actual_instrument=0.0,
            simulated_instrument=0.0,
            cross_country=0.0
        ),
        pilot_role="PIC",
        dual_received=0.0,
        solo_time=0.0
    )

def test_valid_entry():
    """Test that a valid entry passes validation."""
    entry = create_valid_entry()
    entry.validate_entry()
    assert entry.error_explanation is None

def test_aircraft_registration():
    """Test validation of aircraft registration (tail number)."""
    # Test missing aircraft
    entry = create_valid_entry()
    entry.aircraft = None
    entry.validate_entry()
    assert "Missing aircraft registration" in entry.error_explanation

    # Test missing registration
    entry = create_valid_entry()
    entry.aircraft.registration = ""
    entry.validate_entry()
    assert "Missing aircraft registration" in entry.error_explanation

    # Test valid US registration
    entry = create_valid_entry()
    entry.aircraft.registration = "N12345"
    entry.validate_entry()
    assert entry.error_explanation is None

    # Test valid Canadian registration
    entry = create_valid_entry()
    entry.aircraft.registration = "C-FABC"
    entry.validate_entry()
    assert entry.error_explanation is None

    # Test valid UK registration
    entry = create_valid_entry()
    entry.aircraft.registration = "G-ABCD"
    entry.validate_entry()
    assert entry.error_explanation is None

    # Test invalid format
    entry = create_valid_entry()
    entry.aircraft.registration = "XX-1234"
    entry.validate_entry()
    assert "Invalid aircraft registration format" in entry.error_explanation

def test_missing_airports():
    """Test validation of missing airports."""
    # Test missing departure
    entry = create_valid_entry()
    entry.departure = None
    entry.validate_entry()
    assert "Missing departure airport" in entry.error_explanation

    # Test missing destination
    entry = create_valid_entry()
    entry.destination = None
    entry.validate_entry()
    assert "Missing destination airport" in entry.error_explanation

    # Test both missing
    entry = create_valid_entry()
    entry.departure = None
    entry.destination = None
    entry.validate_entry()
    assert all(x in entry.error_explanation for x in ["Missing departure airport", "Missing destination airport"])

def test_invalid_pilot_role():
    """Test validation of pilot role."""
    entry = create_valid_entry()
    entry.pilot_role = "INVALID"
    entry.validate_entry()
    assert "Invalid pilot role" in entry.error_explanation

def test_implausibly_short_flight():
    """Test validation of implausibly short flight times."""
    # Test exactly 0.3 hours (should pass)
    entry = create_valid_entry()
    entry.total_time = 0.3
    entry.conditions.day = 0.3
    entry.validate_entry()
    assert entry.error_explanation is None

    # Test less than 0.3 hours (should fail)
    entry = create_valid_entry()
    entry.total_time = 0.2
    entry.conditions.day = 0.2
    entry.validate_entry()
    assert "implausibly short" in entry.error_explanation

    # Test 0 hours (should pass - might be ground training)
    entry = create_valid_entry()
    entry.total_time = 0.0
    entry.conditions.day = 0.0
    entry.validate_entry()
    assert entry.error_explanation is None

def test_day_night_consistency():
    """Test validation of day/night time consistency."""
    entry = create_valid_entry()
    entry.total_time = 2.0
    entry.conditions.day = 1.0
    entry.conditions.night = 0.5
    entry.validate_entry()
    assert "does not match total time" in entry.error_explanation

def test_instrument_time_consistency():
    """Test validation of instrument time consistency."""
    entry = create_valid_entry()
    entry.total_time = 1.0
    entry.conditions.actual_instrument = 0.8
    entry.conditions.simulated_instrument = 0.3
    entry.validate_entry()
    assert "exceeds flight time" in entry.error_explanation

def test_dual_received_consistency():
    """Test validation of dual received time consistency."""
    entry = create_valid_entry()
    entry.total_time = 1.0
    entry.dual_received = 1.5
    entry.validate_entry()
    assert "exceeds flight time" in entry.error_explanation

def test_time_accountability():
    """Test validation of time accountability (PIC/dual/solo)."""
    # Test PIC time
    entry = create_valid_entry()
    entry.total_time = 1.0
    entry.conditions.day = 1.0
    entry.pilot_role = "PIC"
    entry.validate_entry()
    assert entry.error_explanation is None

    # Test dual received time
    entry = create_valid_entry()
    entry.total_time = 1.0
    entry.conditions.day = 1.0
    entry.pilot_role = "STUDENT"
    entry.dual_received = 1.0
    entry.validate_entry()
    assert entry.error_explanation is None

    # Test solo time
    entry = create_valid_entry()
    entry.total_time = 1.0
    entry.conditions.day = 1.0
    entry.pilot_role = "STUDENT"
    entry.solo_time = 1.0
    entry.validate_entry()
    assert entry.error_explanation is None

    # Test missing accountability
    entry = create_valid_entry()
    entry.total_time = 1.0
    entry.conditions.day = 1.0
    entry.pilot_role = "STUDENT"
    entry.dual_received = 0.0
    entry.solo_time = 0.0
    entry.validate_entry()
    assert "no PIC, dual received, or solo time recorded" in entry.error_explanation

def test_future_date():
    """Test validation of future dates."""
    entry = create_valid_entry()
    with pytest.raises(ValueError, match="Flight date cannot be in the future"):
        entry.date = datetime(2025, 1, 1)
        entry.validate_entry()

def test_arrival_departure_times():
    """Test validation of arrival and departure times."""
    entry = create_valid_entry()
    
    # Test normal same-day flight
    entry.departure_time = time(14, 0)  # 2:00 PM
    entry.arrival_time = time(15, 30)   # 3:30 PM
    entry.total_time = 1.5
    entry.validate_entry()
    assert entry.error_explanation is None

    # Test midnight crossing
    entry.departure_time = time(23, 0)  # 11:00 PM
    entry.arrival_time = time(1, 0)     # 1:00 AM
    entry.total_time = 2.0
    entry.validate_entry()
    assert entry.error_explanation is None

    # Test mismatched times
    with pytest.raises(ValueError, match="don't match total time"):
        entry.departure_time = time(14, 0)  # 2:00 PM
        entry.arrival_time = time(18, 0)    # 6:00 PM
        entry.total_time = 2.0  # Should be 4.0
        entry.validate_entry() 