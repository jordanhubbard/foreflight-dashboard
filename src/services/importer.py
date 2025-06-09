"""Importer for ForeFlight logbook CSV exports."""

import pandas as pd
from datetime import datetime, time
from typing import List, Dict, Any
from ..core.models import LogbookEntry, Aircraft, Airport, FlightConditions

class ForeFlightImporter:
    """Importer for ForeFlight logbook CSV exports."""
    
    def __init__(self, csv_path: str):
        """Initialize importer with CSV file path."""
        self.csv_path = csv_path
        self.flights_df = pd.read_csv(csv_path)
        
    def _clean_numeric(self, value) -> int:
        """Clean and convert a value to integer, handling invalid values."""
        if pd.isna(value) or value == '':
            return 0
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            # Remove any non-numeric characters
            cleaned = ''.join(c for c in value if c.isdigit())
            try:
                return int(cleaned) if cleaned else 0
            except (ValueError, TypeError):
                return 0
        return 0

    def _clean_float(self, value, default: float = 0.0) -> float:
        """Clean and convert a value to float, handling invalid values."""
        if pd.isna(value) or value == '':
            return default
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Remove any non-numeric characters except . and -
            cleaned = ''.join(c for c in value if c.isdigit() or c in '.-')
            try:
                return float(cleaned) if cleaned else default
            except (ValueError, TypeError):
                return default
        return default

    def _create_aircraft_dict(self) -> Dict[str, Aircraft]:
        """Create a dictionary of aircraft from the CSV data."""
        aircraft_dict = {}
        
        for _, row in self.flights_df.iterrows():
            if pd.notna(row['AircraftID']):
                aircraft_id = str(row['AircraftID']).strip()
                if aircraft_id not in aircraft_dict:
                    aircraft_dict[aircraft_id] = Aircraft(
                        registration=aircraft_id,
                        type=str(row['Model']) if pd.notna(row['Model']) else 'UNKNOWN',
                        category_class='airplane_single_engine_land',  # Default to ASEL
                        gear_type='tricycle'  # Default to tricycle gear
                    )
        
        return aircraft_dict

    def import_entries(self) -> List[LogbookEntry]:
        """Import all logbook entries from the CSV."""
        try:
            entries = []
            aircraft_dict = self._create_aircraft_dict()
            
            for idx, row in self.flights_df.iterrows():
                try:
                    # Validate required fields
                    if pd.isna(row['Date']):
                        raise ValueError(f"Missing date in flight {idx + 1}")
                    
                    # Create airports
                    departure = Airport(identifier=row['From'].strip() if isinstance(row['From'], str) else None) if pd.notna(row['From']) else None
                    destination = Airport(identifier=row['To'].strip() if isinstance(row['To'], str) else None) if pd.notna(row['To']) else None
                    
                    # Parse times
                    departure_time = self._parse_time(str(row['TimeOut']) if pd.notna(row['TimeOut']) else None)
                    arrival_time = self._parse_time(str(row['TimeIn']) if pd.notna(row['TimeIn']) else None)
                    
                    # Clean numeric values with better error handling
                    total_time = self._clean_float(row['TotalTime'])
                    night_time = self._clean_float(row['Night'])
                    actual_inst = self._clean_float(row['ActualInstrument'])
                    sim_inst = self._clean_float(row['SimulatedInstrument'])
                    cross_country = self._clean_float(row['CrossCountry'])
                    dual_given = self._clean_float(row['DualGiven'])
                    pic_time = self._clean_float(row['PIC'])
                    sic_time = self._clean_float(row['SIC'])
                    dual_received = self._clean_float(row.get('DualReceived', 0.0))
                    solo_time = self._clean_float(row.get('Solo', 0.0))
                    
                    # Determine pilot role
                    if dual_given > 0:
                        pilot_role = "INSTRUCTOR"
                    elif dual_received > 0:
                        pilot_role = "STUDENT"
                    elif pic_time > 0:
                        pilot_role = "PIC"
                    elif sic_time > 0:
                        pilot_role = "SIC"
                    else:
                        pilot_role = "PIC"  # Default to PIC
                    
                    # Create flight conditions
                    conditions = FlightConditions(
                        night=night_time,
                        day=total_time - night_time,
                        actual_instrument=actual_inst,
                        simulated_instrument=sim_inst,
                        cross_country=cross_country
                    )
                    
                    # Create logbook entry
                    entry = LogbookEntry(
                        date=datetime.strptime(str(row['Date']).strip(), "%Y-%m-%d"),
                        departure_time=departure_time or time(0, 0),
                        arrival_time=arrival_time or time(0, 0),
                        total_time=total_time,
                        aircraft=aircraft_dict[str(row['AircraftID']).strip() if pd.notna(row['AircraftID']) else ''],
                        departure=departure,
                        destination=destination,
                        conditions=conditions,
                        pilot_role=pilot_role,
                        landings_day=self._clean_numeric(row['DayLandingsFullStop']),
                        landings_night=self._clean_numeric(row['NightLandingsFullStop']),
                        remarks=f"Distance: {self._clean_float(row.get('Distance', 0.0))}nm\n{str(row['PilotComments']) if pd.notna(row['PilotComments']) else None or str(row['InstructorComments']) if pd.notna(row['InstructorComments']) else None or 'No remarks'}",
                        instructor_comments=str(row['InstructorComments']) if pd.notna(row['InstructorComments']) else None,
                        dual_received=dual_received,
                        pic_time=pic_time,
                        solo_time=solo_time
                    )
                    
                    entries.append(entry)
                    
                except Exception as e:
                    raise ValueError(f"Error processing flight {idx + 1}: {str(e)}")
                
            if not entries:
                raise ValueError("No valid entries found in the logbook")
            
            return entries
            
        except Exception as e:
            raise ValueError(f"Error importing entries: {str(e)}")