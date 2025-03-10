"""Script to validate ForeFlight logbook CSV entries."""

import csv
from datetime import datetime, time
from .core.models import LogbookEntry, Aircraft, Airport, FlightConditions
import logging

logger = logging.getLogger(__name__)

def parse_time(time_str):
    """Parse time string in HH:MM format."""
    if not time_str:
        return None
    try:
        return datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        return None

def parse_float(value):
    """Parse float value, returning 0.0 if invalid."""
    try:
        return float(value) if value else 0.0
    except ValueError:
        return 0.0

def parse_int(value):
    """Parse integer value, returning 0 if invalid."""
    try:
        return int(value) if value else 0
    except ValueError:
        return 0

def determine_pilot_role(row):
    """Determine the pilot role based on flight times."""
    pic_time = parse_float(row.get('PIC', 0))
    solo_time = parse_float(row.get('Solo', 0))
    dual_time = parse_float(row.get('DualReceived', 0))
    
    if pic_time > 0 or solo_time > 0:
        return 'PIC'
    elif dual_time > 0:
        return 'STUDENT'
    return 'PIC'  # Default to PIC if no role can be determined

def validate_logbook(csv_path):
    """Validate all entries in the logbook CSV file."""
    logger.debug("\n" + "="*80)
    logger.debug("STARTING LOGBOOK VALIDATION")
    logger.debug("="*80)
    logger.debug(f"\nReading file: {csv_path}")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        content = f.readlines()
    
    # Find Aircraft Table and Flights Table sections
    aircraft_start = -1
    flights_start = -1
    
    for i, line in enumerate(content):
        if line.strip().startswith('Aircraft Table'):
            aircraft_start = i
        elif line.strip().startswith('Flights Table'):
            flights_start = i
            break
    
    if aircraft_start == -1:
        logger.error("Aircraft Table not found in file")
        return []
    
    if flights_start == -1:
        logger.error("Flights Table not found in file")
        return []
    
    logger.debug(f"Found Aircraft Table at line {aircraft_start}")
    logger.debug(f"Found Flights Table at line {flights_start}")
    
    # Process Aircraft Table
    aircraft_data = {}
    aircraft_headers = content[aircraft_start + 1].strip().split(',')
    logger.debug(f"Aircraft headers: {aircraft_headers}")
    
    for line in content[aircraft_start + 2:flights_start]:
        if not line.strip() or not any(line.strip().split(',')):
            continue
        
        row = dict(zip(aircraft_headers, line.strip().split(',')))
        if row.get('AircraftID'):
            aircraft_data[row['AircraftID']] = {
                'type': row.get('Model', 'UNKNOWN'),
                'make': row.get('Make', 'UNKNOWN')
            }
            logger.debug(f"Found aircraft: {row['AircraftID']} - {row.get('Model', 'UNKNOWN')}")
    
    logger.debug(f"\nTotal aircraft found: {len(aircraft_data)}")
    
    # Process Flights Table
    flight_headers = content[flights_start + 1].strip().split(',')
    logger.debug(f"\nFlight headers: {flight_headers}")
    
    entries = []
    row_count = 0
    error_count = 0
    
    for line in content[flights_start + 2:]:
        if not line.strip() or not any(line.strip().split(',')):
            continue
        
        row_count += 1
        try:
            row = dict(zip(flight_headers, line.strip().split(',')))
            
            if not row.get('Date'):
                logger.debug(f"Skipping row {row_count} - no date")
                continue
            
            aircraft_id = row.get('AircraftID') or "UNKNOWN"
            aircraft_info = aircraft_data.get(aircraft_id, {'type': 'UNKNOWN', 'make': 'UNKNOWN'})
            
            logger.debug(f"\nProcessing flight {row_count}:")
            logger.debug(f"  Date: {row.get('Date')}")
            logger.debug(f"  Aircraft: {aircraft_id}")
            logger.debug(f"  Route: {row.get('From')} -> {row.get('To')}")
            
            # Create entry
            total_time = parse_float(row.get('TotalTime'))
            night_time = parse_float(row.get('Night', 0))
            night_landings = parse_int(row.get('NightLandingsFullStop', 0))
            
            if night_landings > 0 and night_time == 0:
                night_time = min(night_landings * 0.3, total_time)
                logger.debug(f"  Estimated night time from landings: {night_time}")
            
            day_time = max(0.0, total_time - night_time)
            
            logger.debug(f"  Times:")
            logger.debug(f"    Total: {total_time}")
            logger.debug(f"    Day: {day_time}")
            logger.debug(f"    Night: {night_time}")
            
            entry = LogbookEntry(
                date=datetime.strptime(row['Date'], "%Y-%m-%d"),
                departure_time=parse_time(row.get('TimeOut')) or parse_time("00:00"),
                arrival_time=parse_time(row.get('TimeIn')) or parse_time("00:00"),
                total_time=total_time,
                pic_time=parse_float(row.get('PIC', 0)),
                aircraft=Aircraft(
                    registration=aircraft_id,
                    type=aircraft_info['type'],
                    category_class="ASEL"  # Default to ASEL
                ),
                departure=Airport(identifier=row.get('From', '')),
                destination=Airport(identifier=row.get('To', '')),
                conditions=FlightConditions(
                    day=day_time,
                    night=night_time,
                    actual_instrument=parse_float(row.get('ActualInstrument', 0)),
                    simulated_instrument=parse_float(row.get('SimulatedInstrument', 0)),
                    cross_country=parse_float(row.get('CrossCountry', 0))
                ),
                pilot_role=determine_pilot_role(row),
                landings_day=parse_int(row.get('DayLandingsFullStop', 0)),
                landings_night=night_landings,
                remarks=row.get('PilotComments') or row.get('InstructorComments') or "No remarks",
                dual_received=parse_float(row.get('DualReceived', 0))
            )
            
            # Validate the entry
            entry.validate_entry()
            entries.append(entry)
            logger.debug("  Entry processed successfully")
            
            # Print validation results
            if entry.error_explanation:
                error_count += 1
                logger.debug(f"  Validation issues:")
                logger.debug(f"    {entry.error_explanation}")
            else:
                logger.debug("  Entry valid")
            
        except Exception as e:
            error_count += 1
            logger.error(f"\nError processing entry for {row.get('Date', 'UNKNOWN DATE')}:")
            logger.error(f"  {str(e)}")
            continue
    
    logger.debug("\n=== Validation Summary ===")
    logger.debug(f"Total rows processed: {row_count}")
    logger.debug(f"Valid entries: {len(entries)}")
    logger.debug(f"Entries with errors: {error_count}")
    
    return entries

if __name__ == "__main__":
    csv_path = "tests/logbook.csv"
    print("Validating logbook entries...")
    entries = validate_logbook(csv_path)
    print("\nValidation complete.")
    print(f"Processed {len(entries)} entries.") 