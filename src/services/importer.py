"""ForeFlight logbook CSV importer."""

import csv
from datetime import datetime, time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging
import re

import pandas as pd

from .models import Aircraft, Airport, FlightConditions, LogbookEntry

class ForeFlightImporter:
    """Importer for ForeFlight logbook CSV exports."""
    
    def __init__(self, csv_path: str):
        """Initialize the importer.
        
        Args:
            csv_path: Path to the ForeFlight CSV export file
        """
        # Configure logging
        self.logger = logging.getLogger('src.services.importer')
        self.logger.setLevel(logging.DEBUG)
        
        self.csv_path = Path(csv_path)
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        # Read the CSV file in chunks to separate aircraft and flights
        self.aircraft_df = None
        self.flights_df = None
        self._parse_csv()
        
    def _normalize_line(self, line: str) -> str:
        """Normalize a line by removing extra spaces and fixing quotes."""
        # Remove leading/trailing whitespace
        line = line.strip()
        
        # Skip empty lines or lines with just commas
        if not line or all(c in ' ,' for c in line):
            return ''
            
        # Fix triple quotes
        line = line.replace('"""', '"')
        
        # Ensure consistent quoting for fields with commas
        parts = []
        in_quotes = False
        current = []
        
        for char in line:
            if char == '"':
                in_quotes = not in_quotes
                current.append(char)
            elif char == ',' and not in_quotes:
                parts.append(''.join(current).strip())
                current = []
            else:
                current.append(char)
                
        parts.append(''.join(current).strip())
        
        # Clean and rejoin parts
        cleaned_parts = []
        for part in parts:
            part = part.strip()
            if ',' in part and not (part.startswith('"') and part.endswith('"')):
                part = f'"{part}"'
            cleaned_parts.append(part)
            
        return ','.join(cleaned_parts)

    def _should_join_with_previous(self, line: str, prev_line: str) -> bool:
        """Determine if a line should be joined with the previous line."""
        if not line or not prev_line:
            return False
            
        # If the line starts with a space or comma, it's likely a continuation
        if line.startswith(' ') or line.startswith(','):
            return True
            
        # If the previous line ends with an odd number of quotes, this is likely a continuation
        quote_count = prev_line.count('"') - prev_line.count('"""')
        if quote_count % 2 == 1:
            return True
            
        # If the line doesn't start with a typical beginning of a new record
        if not re.match(r'^[A-Za-z0-9"\']', line.lstrip()):
            return True
            
        return False

    def _parse_csv(self):
        """Parse the CSV file into aircraft and flights dataframes."""
        try:
            self.logger.info(f"Starting to parse CSV file: {self.csv_path}")
            
            # Read the entire file
            with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
                content = f.readlines()
            
            # Find section markers
            aircraft_start = None
            flights_start = None
            
            for i, line in enumerate(content):
                if "Aircraft Table" in line:
                    aircraft_start = i
                    self.logger.info(f"Found Aircraft Table at line {i}")
                elif "Flights Table" in line:
                    flights_start = i
                    self.logger.info(f"Found Flights Table at line {i}")
            
            if aircraft_start is None:
                raise ValueError("Could not find Aircraft Table section")
            if flights_start is None:
                raise ValueError("Could not find Flights Table section")
            
            # Extract sections
            aircraft_lines = content[aircraft_start:flights_start]
            flight_lines = content[flights_start:]
            
            # Write sections to temporary files for pandas to read
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as aircraft_file:
                aircraft_file.writelines(aircraft_lines)
                aircraft_path = aircraft_file.name
                
            # For flights, we need to handle the CSV properly
            # First get the header
            header = None
            data_lines = []
            import csv
            import io
            
            # Process flight lines using CSV module
            processed_lines = []
            csv_reader = csv.reader(flight_lines)
            for i, row in enumerate(csv_reader):
                if i == 1:  # Second line is header
                    header = row
                    self.logger.debug(f"Found header row: {header}")
                    processed_lines.append(','.join(f'"{field}"' if ',' in field else field for field in row))
                elif i > 1:  # Data lines
                    processed_lines.append(','.join(f'"{field}"' if ',' in field else field for field in row))
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as flight_file:
                flight_file.write('\n'.join(processed_lines))
                flight_path = flight_file.name
            
            # Log the processed CSV
            self.logger.debug("Processed CSV content:")
            with open(flight_path, 'r') as f:
                for i, line in enumerate(f):
                    if i < 5:  # Log first 5 lines
                        self.logger.debug(f"  Line {i}: {line.strip()}")
            
            # Read aircraft section with pandas
            try:
                self.aircraft_df = pd.read_csv(aircraft_path, skiprows=1)  # Skip "Aircraft Table" row
                self.logger.info(f"Read aircraft DataFrame with shape: {self.aircraft_df.shape}")
            except Exception as e:
                self.logger.error(f"Error reading aircraft section: {str(e)}")
                raise
            
            # Read flights section with pandas
            try:
                # Read the flights data with the correct column names
                self.flights_df = pd.read_csv(
                    flight_path,
                    skiprows=1,  # Skip "Flights Table" row
                    keep_default_na=False,
                    na_values=[''],
                    encoding='utf-8-sig'
                )
                
                self.logger.info(f"Read flights DataFrame with shape: {self.flights_df.shape}")
                self.logger.debug(f"Columns: {list(self.flights_df.columns)}")
                
            except Exception as e:
                self.logger.error(f"Error reading flights section: {str(e)}")
                raise
            
            # Clean up temporary files
            import os
            os.unlink(aircraft_path)
            os.unlink(flight_path)
            
        except Exception as e:
            self.logger.error(f"Error parsing CSV: {str(e)}")
            raise ValueError(f"Error parsing CSV file: {str(e)}")
        
    def _parse_time(self, time_str: str) -> Optional[time]:
        """Parse time string from ForeFlight format."""
        if not time_str:
            return None
        try:
            return datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            return None
            
    def _create_aircraft_dict(self) -> Dict[str, Aircraft]:
        """Create a dictionary of aircraft models from the aircraft table."""
        aircraft_dict = {}
        # Add a default aircraft for empty IDs
        aircraft_dict[''] = Aircraft(
            registration='UNKNOWN',
            type='Unknown',
            category_class='airplane_single_engine_land'
        )
        for _, row in self.aircraft_df.iterrows():
            if row['AircraftID']:  # Only add non-empty aircraft IDs
                gear_type = row['GearType'].lower() if pd.notna(row['GearType']) else "tricycle"
                if "fixed_tailwheel" in gear_type:
                    gear_type = "tailwheel"
                elif "fixed_tricycle" in gear_type:
                    gear_type = "tricycle"
                aircraft_dict[row['AircraftID']] = Aircraft(
                    registration=row['AircraftID'],
                    type=row['TypeCode'],
                    category_class=row['aircraftClass (FAA)'] or "airplane_single_engine_land",
                    gear_type=gear_type
                )
        return aircraft_dict
        
    def _clean_numeric(self, value: str, default: int = 0) -> int:
        """Clean and convert a string to integer, handling invalid values."""
        if pd.isna(value) or not value:
            return default
        if not isinstance(value, str):
            try:
                return int(float(value))
            except (ValueError, TypeError):
                return default
        # Remove any non-numeric characters and quotes
        cleaned = ''.join(c for c in value if c.isdigit() or c == '.')
        try:
            if '.' in cleaned:
                return int(float(cleaned))
            return int(cleaned) if cleaned else default
        except (ValueError, TypeError):
            return default

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

    def import_entries(self) -> List[LogbookEntry]:
        """Import all logbook entries from the CSV.
        
        Returns:
            List of LogbookEntry objects
        
        Raises:
            ValueError: If there are issues parsing the CSV or creating entries
        """
        try:
            entries = []
            aircraft_dict = self._create_aircraft_dict()
            
            self.logger.debug("\n=== CSV Column Headers ===")
            self.logger.debug(f"Available columns: {list(self.flights_df.columns)}")
            
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
                    
                    # Create flight conditions
                    conditions = FlightConditions(
                        day=max(0, total_time - night_time),  # Ensure non-negative
                        night=night_time,
                        actual_instrument=actual_inst,
                        simulated_instrument=sim_inst,
                        cross_country=cross_country
                    )
                    
                    # Determine pilot role and PIC time
                    if pic_time > 0 and dual_received > 0:
                        # Mixed flight with both PIC and dual received time
                        pilot_role = "SPLIT"  # Use SPLIT for mixed role flights
                    elif dual_received > 0:
                        pilot_role = "STUDENT"
                        pic_time = 0  # Students don't log PIC time
                    elif dual_given > 0:
                        pilot_role = "INSTRUCTOR"
                        pic_time = total_time  # Instructors log PIC time
                    elif pic_time > 0:
                        pilot_role = "PIC"
                    elif sic_time > 0:
                        pilot_role = "SIC"
                        pic_time = 0  # SIC doesn't log PIC time
                    else:
                        pilot_role = "PIC"  # Default to PIC if no other role is determined
                        pic_time = total_time  # Set PIC time to total time for PIC flights
                    
                    # If role is PIC and no PIC time specified, use total time
                    if pilot_role == "PIC" and pic_time == 0:
                        pic_time = total_time
                    
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
                        pic_time=pic_time
                    )
                    
                    entries.append(entry)
                    
                except Exception as e:
                    raise ValueError(f"Error processing flight {idx + 1}: {str(e)}")
                
            if not entries:
                raise ValueError("No valid entries found in the logbook")
                
            self.logger.debug(f"\nProcessed {len(entries)} entries")
            
            return entries
            
        except Exception as e:
            raise ValueError(f"Error importing entries: {str(e)}") 