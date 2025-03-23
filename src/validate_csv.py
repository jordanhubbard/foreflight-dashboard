"""Script to validate ForeFlight logbook CSV entries."""

import csv
from datetime import datetime, time
from .core.models import LogbookEntry, Aircraft, Airport, FlightConditions

def parse_time(time_str):
    """Parse time string in HH:MM format."""
    if not time_str:
        return None
    try:
        return datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        return None

def parse_float(value, default=0.0):
    """Parse float value, handling invalid values."""
    if not value:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def parse_int(value, default=0):
    """Parse integer value, handling invalid values."""
    if not value:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default

def determine_pilot_role(row):
    """Determine pilot role based on flight data."""
    if parse_float(row.get('DualGiven', 0)) > 0:
        return "INSTRUCTOR"
    if parse_float(row.get('DualReceived', 0)) > 0:
        return "STUDENT"
    if parse_float(row.get('PIC', 0)) > 0:
        return "PIC"
    if parse_float(row.get('SIC', 0)) > 0:
        return "SIC"
    return "PIC"  # Default to PIC if no other role is clear

def validate_logbook(csv_path):
    """Validate all entries in the logbook CSV file."""
    with open(csv_path, 'r') as f:
        content = f.readlines()

    # Find the Aircraft and Flights tables
    aircraft_start = flights_start = -1
    for i, line in enumerate(content):
        if line.strip().startswith('AircraftID,'):
            aircraft_start = i
        elif line.strip().startswith('Date,'):
            flights_start = i
            break

    if aircraft_start == -1 or flights_start == -1:
        raise ValueError("Invalid CSV format - missing required tables")

    # Process Aircraft Table
    aircraft_headers = content[aircraft_start].strip().split(',')
    aircraft_data = {}

    for line in content[aircraft_start + 1:flights_start]:
        if not line.strip():
            continue

        row = dict(zip(aircraft_headers, line.strip().split(',')))
        aircraft_data[row['AircraftID']] = {
            'type': row.get('Model', 'UNKNOWN'),
            'category_class': 'airplane_single_engine_land',  # Default to ASEL
            'gear_type': row.get('GearType', 'fixed_tricycle')
        }

    # Process Flights Table
    flight_headers = content[flights_start].strip().split(',')
    entries = []
    row_count = 0
    error_count = 0

    for line in content[flights_start + 1:]:
        if not line.strip():
            continue

        row_count += 1
        try:
            row = dict(zip(flight_headers, line.strip().split(',')))

            if not row.get('Date'):
                error_count += 1
                continue

            aircraft_id = row.get('AircraftID') or "UNKNOWN"
            aircraft_info = aircraft_data.get(aircraft_id, {
                'type': 'UNKNOWN',
                'category_class': 'airplane_single_engine_land',
                'gear_type': 'fixed_tricycle'
            })

            total_time = parse_float(row.get('TotalTime', 0))
            night_landings = parse_int(row.get('NightLandingsFullStop', 0))

            entry = LogbookEntry(
                date=datetime.strptime(row['Date'], "%Y-%m-%d"),
                departure_time=parse_time(row.get('TimeOut')) or parse_time("00:00"),
                arrival_time=parse_time(row.get('TimeIn')) or parse_time("00:00"),
                total_time=total_time,
                pic_time=parse_float(row.get('PIC', 0)),
                aircraft=Aircraft(
                    registration=aircraft_id,
                    type=aircraft_info['type'],
                    category_class=aircraft_info['category_class'],
                    gear_type="tailwheel" if "fixed_tailwheel" in aircraft_info['gear_type'] else "tricycle"
                ),
                departure=Airport(identifier=row.get('From', '')),
                destination=Airport(identifier=row.get('To', '')),
                conditions=FlightConditions(
                    night=parse_float(row.get('Night', 0)),
                    day=total_time - parse_float(row.get('Night', 0)),
                    actual_instrument=parse_float(row.get('ActualInstrument', 0)),
                    simulated_instrument=parse_float(row.get('SimulatedInstrument', 0)),
                    cross_country=parse_float(row.get('CrossCountry', 0))
                ),
                pilot_role=determine_pilot_role(row),
                landings_day=parse_int(row.get('DayLandingsFullStop', 0)),
                landings_night=night_landings,
                remarks=f"Distance: {parse_float(row.get('Distance', '0.0'))}nm\n{row.get('PilotComments') or row.get('InstructorComments') or 'No remarks'}",
                dual_received=parse_float(row.get('DualReceived', 0)),
                ground_training=parse_float(row.get('GroundTraining', 0))
            )

            # Validate the entry but always add it to entries
            entry.validate_entry()
            entries.append(entry)

        except Exception as e:
            error_count += 1
            continue

    return entries

if __name__ == "__main__":
    csv_path = "tests/logbook.csv"
    print("Validating logbook entries...")
    entries = validate_logbook(csv_path)
    print("\nValidation complete.")
    print(f"Processed {len(entries)} entries.") 