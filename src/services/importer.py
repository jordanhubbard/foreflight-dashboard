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
                
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as flight_file:
                flight_file.writelines(flight_lines)
                flight_path = flight_file.name
            
            # Read aircraft section with pandas
            try:
                self.aircraft_df = pd.read_csv(aircraft_path, skiprows=1)  # Skip "Aircraft Table" row
                self.logger.info(f"Read aircraft DataFrame with shape: {self.aircraft_df.shape}")
            except Exception as e:
                self.logger.error(f"Error reading aircraft section: {str(e)}")
                raise
            
            # Read flights section with pandas, handling empty fields and quotes
            try:
                self.flights_df = pd.read_csv(
                    flight_path,
                    skiprows=1,  # Skip "Flights Table" row
                    keep_default_na=False,  # Don't convert empty strings to NaN
                    quoting=csv.QUOTE_MINIMAL,  # Handle quotes properly
                    escapechar='\\',  # Handle escaped characters
                    encoding='utf-8-sig',  # Handle UTF-8 with BOM
                    dtype={'InstructorName': str},  # Ensure instructor names are read as strings
                    na_values=[],  # Don't treat any values as NA
                    na_filter=False  # Don't filter NA values
                )
                self.logger.info(f"Read flights DataFrame with shape: {self.flights_df.shape}")
                
                # Debug: Check DataFrame columns and sample data
                self.logger.debug("\nFlights DataFrame Info:")
                self.logger.debug(f"Columns: {list(self.flights_df.columns)}")
                self.logger.debug("\nSample of first 5 rows with all columns:")
                sample = self.flights_df.head(5)
                for idx, row in sample.iterrows():
                    self.logger.debug(f"\nRow {idx} - All columns:")
                    for col in self.flights_df.columns:
                        val = row[col]
                        self.logger.debug(f"  {col}: {val!r} (type: {type(val)}, repr: {repr(val)})")
                
                # Debug: Check instructor names and dual received
                if 'InstructorName' in self.flights_df.columns:
                    self.logger.debug("\nSample of instructor names and dual received from flights DataFrame:")
                    sample = self.flights_df.head(10)  # Look at first 10 rows
                    for idx, row in sample.iterrows():
                        instructor = row.get('InstructorName', '')
                        dual = self._clean_float(row.get('DualReceived', 0.0))
                        self.logger.debug(f"\nProcessing row {idx}:")
                        self.logger.debug(f"  Raw instructor: {instructor!r}")
                        self.logger.debug(f"  Raw instructor type: {type(instructor)}")
                        self.logger.debug(f"  Raw instructor repr: {repr(instructor)}")
                        self.logger.debug(f"  Raw dual received: {row.get('DualReceived', 0.0)!r}")
                        self.logger.debug(f"  Cleaned dual received: {dual}")
                        
                        # Try cleaning the instructor name
                        cleaned_name = self._clean_instructor_name(instructor)
                        self.logger.debug(f"  Cleaned instructor name: {cleaned_name!r}")
                else:
                    self.logger.warning("No InstructorName column found in flights DataFrame")
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
                aircraft_dict[row['AircraftID']] = Aircraft(
                    registration=row['AircraftID'],
                    type=row['TypeCode'],
                    category_class=row['aircraftClass (FAA)'] or "airplane_single_engine_land"
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

    def _clean_instructor_name(self, raw_name):
        """Clean instructor name from raw format."""
        if not raw_name or pd.isna(raw_name):
            return None
        
        # Handle format: "Name;Instructor;email"
        if ';' in raw_name:
            parts = raw_name.split(';')
            if len(parts) >= 1:
                return parts[0].strip()
        
        return raw_name.strip()

    def _process_instructor_stats(self):
        """Process instructor statistics from the flights DataFrame."""
        instructor_stats = {}
        
        # Log the column names to verify we have InstructorName
        self.logger.debug(f"DataFrame columns: {self.flights_df.columns.tolist()}")
        
        if 'InstructorName' not in self.flights_df.columns:
            self.logger.warning("InstructorName column not found in DataFrame")
            return []
        
        # Log the first few rows of instructor names
        self.logger.debug("First 5 rows of instructor names:")
        for idx, row in self.flights_df.head().iterrows():
            self.logger.debug(f"Row {idx} - Raw instructor name: {row.get('InstructorName', 'NOT FOUND')}")
        
        for _, row in self.flights_df.iterrows():
            dual_received = row.get('DualReceived', 0.0)
            raw_instructor_name = row.get('InstructorName')
            
            self.logger.debug(f"Processing row - Dual received: {dual_received}, Raw instructor name: {raw_instructor_name!r}")
            
            if dual_received > 0:
                instructor_name = self._clean_instructor_name(raw_instructor_name)
                self.logger.debug(f"  Cleaned instructor name: {instructor_name!r}")
                
                if instructor_name:
                    if instructor_name not in instructor_stats:
                        instructor_stats[instructor_name] = {
                            'name': instructor_name,
                            'num_flights': 0,
                            'dual_received': 0.0,
                            'last_flight': None
                        }
                    
                    instructor_stats[instructor_name]['num_flights'] += 1
                    instructor_stats[instructor_name]['dual_received'] += dual_received
                    
                    flight_date = row.get('Date')
                    if flight_date and (
                        not instructor_stats[instructor_name]['last_flight'] or 
                        flight_date > instructor_stats[instructor_name]['last_flight']
                    ):
                        instructor_stats[instructor_name]['last_flight'] = flight_date
        
        # Convert to list and sort by number of flights
        stats_list = list(instructor_stats.values())
        stats_list.sort(key=lambda x: x['num_flights'], reverse=True)
        
        self.logger.debug(f"Final instructor stats ({len(stats_list)} instructors):")
        for stat in stats_list:
            self.logger.debug(f"  {stat['name']}: {stat['num_flights']} flights, {stat['dual_received']} hours")
        
        return stats_list

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
            
            # Log a few rows of instructor names for debugging
            if 'InstructorName' in self.flights_df.columns:
                self.logger.debug("\n=== Sample Instructor Names ===")
                sample_rows = self.flights_df.head(5)
                for idx, row in sample_rows.iterrows():
                    instructor_name = row.get('InstructorName', 'NOT FOUND')
                    dual_received = row.get('DualReceived', 0.0)
                    self.logger.debug(f"Row {idx}:")
                    self.logger.debug(f"  Raw InstructorName: {instructor_name!r}")
                    cleaned_name = self._clean_instructor_name(instructor_name)
                    self.logger.debug(f"  Cleaned InstructorName: {cleaned_name!r}")
                    self.logger.debug(f"  DualReceived: {dual_received}")
            else:
                self.logger.debug("No InstructorName column found in CSV")
            
            for idx, row in self.flights_df.iterrows():
                try:
                    # Log instructor-related fields for debugging
                    self.logger.debug(f"\nProcessing row {idx}:")
                    instructor_name_raw = row.get('InstructorName', '')  # Changed from 'NOT FOUND' to ''
                    self.logger.debug(f"Raw InstructorName from CSV: {instructor_name_raw!r}")
                    instructor_name = self._clean_instructor_name(instructor_name_raw)
                    self.logger.debug(f"Cleaned InstructorName: {instructor_name!r}")
                    dual_received = self._clean_float(row.get('DualReceived', 0.0))
                    self.logger.debug(f"DualReceived: {dual_received}")
                    
                    # Only use instructor name if there is dual received time
                    if dual_received <= 0:
                        instructor_name = None
                        self.logger.debug("No dual received time, setting instructor_name to None")
                    
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
                    
                    # Create flight conditions
                    conditions = FlightConditions(
                        day=max(0, total_time - night_time),  # Ensure non-negative
                        night=night_time,
                        actual_instrument=actual_inst,
                        simulated_instrument=sim_inst,
                        cross_country=cross_country
                    )
                    
                    # Determine pilot role
                    if dual_received > 0:
                        pilot_role = "STUDENT"  # Changed from "Dual Received" to "STUDENT"
                    elif dual_given > 0:
                        pilot_role = "INSTRUCTOR"  # Changed from "Dual Given" to "INSTRUCTOR"
                    elif pic_time > 0:
                        pilot_role = "PIC"
                    elif sic_time > 0:
                        pilot_role = "SIC"
                    else:
                        pilot_role = "Unknown"
                    
                    self.logger.debug(f"Pilot role determined as: {pilot_role}")
                    
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
                        remarks=str(row['PilotComments']) if pd.notna(row['PilotComments']) else None,
                        instructor_name=instructor_name,
                        instructor_comments=str(row['InstructorComments']) if pd.notna(row['InstructorComments']) else None,
                        dual_received=dual_received
                    )
                    
                    self.logger.debug(f"Created entry with instructor_name: {entry.instructor_name!r}")
                    entries.append(entry)
                    
                except Exception as e:
                    raise ValueError(f"Error processing flight {idx + 1}: {str(e)}")
                
            if not entries:
                raise ValueError("No valid entries found in the logbook")
                
            self.logger.debug(f"\nProcessed {len(entries)} entries")
            instructor_entries = [e for e in entries if e.instructor_name]
            self.logger.debug(f"Found {len(instructor_entries)} entries with instructor names:")
            for entry in instructor_entries:
                self.logger.debug(f"  Date: {entry.date}, Instructor: {entry.instructor_name!r}, Dual: {entry.dual_received}")
            
            return entries
            
        except Exception as e:
            raise ValueError(f"Error importing entries: {str(e)}")

    def _parse_csv_file(self, file_path):
        """Parse the CSV file and return a list of flight entries."""
        entries = []
        with open(file_path, 'r') as f:
            # Skip to the Flights Table
            for line in f:
                if 'Flights Table' in line:
                    break
            
            # Read the header line
            header = next(f).strip().split(',')
            self.logger.debug(f"CSV columns: {header}")
            
            # Find the index of the InstructorName column
            instructor_name_idx = None
            for i, col in enumerate(header):
                if col == 'InstructorName':
                    instructor_name_idx = i
                    break
            
            if instructor_name_idx is None:
                self.logger.warning("InstructorName column not found in CSV")
            else:
                self.logger.debug(f"InstructorName column found at index {instructor_name_idx}")
            
            # Read the first few rows to check instructor names
            sample_rows = []
            for _ in range(5):
                try:
                    row = next(f)
                    sample_rows.append(row)
                except StopIteration:
                    break
            
            self.logger.debug("Sample rows instructor names:")
            for row in sample_rows:
                values = row.strip().split(',')
                if instructor_name_idx is not None and instructor_name_idx < len(values):
                    self.logger.debug(f"Raw instructor name: {values[instructor_name_idx]}")
            
            # Reset file pointer to after header
            f.seek(0)
            for line in f:
                if 'Flights Table' in line:
                    break
            next(f)  # Skip header line again
            
            # Process all rows including the sample rows we read
            all_rows = sample_rows + f.readlines()
            for row in all_rows:
                values = row.strip().split(',')
                if len(values) < len(header):
                    continue
                    
                entry = {}
                for i, col in enumerate(header):
                    if i < len(values):
                        entry[col] = values[i]
                
                if instructor_name_idx is not None and instructor_name_idx < len(values):
                    raw_instructor = values[instructor_name_idx]
                    self.logger.debug(f"Processing instructor name: {raw_instructor}")
                
                # Convert the entry to a FlightEntry object
                flight_entry = self._create_flight_entry(entry)
                if flight_entry:
                    entries.append(flight_entry)
        
        return entries 