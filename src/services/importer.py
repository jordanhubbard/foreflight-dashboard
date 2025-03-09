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
        self.csv_path = Path(csv_path)
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        # Configure logging
        logging.basicConfig(level=logging.DEBUG)
        
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
            logging.info(f"Starting to parse CSV file: {self.csv_path}")
            
            # Read the entire file and normalize line endings
            with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
                
            # Normalize line endings
            content = content.replace('\r\n', '\n').replace('\r', '\n')
            
            # Split into lines
            raw_lines = content.split('\n')
            logging.info(f"Read {len(raw_lines)} raw lines from file")
            
            # Process lines with better joining logic
            processed_lines = []
            current_line = None
            
            for line in raw_lines:
                line = line.strip()
                
                if not line:  # Skip empty lines
                    continue
                    
                if current_line is None:
                    current_line = line
                elif self._should_join_with_previous(line, current_line):
                    # Join with a space to preserve formatting
                    current_line = f"{current_line} {line}"
                else:
                    # Process the current line
                    normalized = self._normalize_line(current_line)
                    if normalized:
                        processed_lines.append(normalized)
                    current_line = line
            
            # Don't forget the last line
            if current_line:
                normalized = self._normalize_line(current_line)
                if normalized:
                    processed_lines.append(normalized)
            
            logging.info(f"Processed into {len(processed_lines)} normalized lines")
            
            # Find section markers
            aircraft_start = None
            flights_start = None
            
            for i, line in enumerate(processed_lines):
                if "Aircraft Table" in line:
                    aircraft_start = i
                    logging.info(f"Found Aircraft Table at line {i}")
                elif "Flights Table" in line:
                    flights_start = i
                    logging.info(f"Found Flights Table at line {i}")
            
            if aircraft_start is None:
                raise ValueError("Could not find Aircraft Table section")
            if flights_start is None:
                raise ValueError("Could not find Flights Table section")
            
            # Extract and parse aircraft section
            aircraft_lines = processed_lines[aircraft_start + 1:flights_start]
            logging.info(f"Extracted {len(aircraft_lines)} aircraft lines")
            
            # Find aircraft headers
            aircraft_headers = None
            aircraft_data = []
            
            for line in aircraft_lines:
                if not aircraft_headers:
                    # Look for header line containing typical aircraft columns
                    if any(keyword in line.lower() for keyword in ['aircraft', 'id', 'type', 'make', 'model']):
                        try:
                            headers = list(csv.reader([line]))[0]
                            headers = [h.strip() for h in headers if h.strip()]
                            if headers:
                                aircraft_headers = headers
                                logging.info(f"Found aircraft headers: {headers}")
                                continue
                        except Exception as e:
                            logging.warning(f"Error parsing potential header line: {line}")
                            logging.warning(f"Error details: {str(e)}")
                else:
                    try:
                        row = list(csv.reader([line]))[0]
                        if len(row) >= len(aircraft_headers):
                            aircraft_data.append(dict(zip(aircraft_headers, row)))
                    except Exception as e:
                        logging.warning(f"Error parsing aircraft data line: {line}")
                        logging.warning(f"Error details: {str(e)}")
            
            if not aircraft_headers:
                raise ValueError("Could not find valid aircraft headers")
            
            if not aircraft_data:
                raise ValueError("No valid aircraft data found")
            
            # Extract and parse flights section
            flight_lines = processed_lines[flights_start + 1:]
            logging.info(f"Extracted {len(flight_lines)} flight lines")
            
            # Find flight headers
            flight_headers = None
            flight_data = []
            
            for line in flight_lines:
                if not flight_headers:
                    # Look for header line containing typical flight columns
                    if any(keyword in line for keyword in ['Date', 'Aircraft', 'From', 'To']):
                        try:
                            headers = list(csv.reader([line]))[0]
                            headers = [h.strip() for h in headers if h.strip()]
                            if headers:
                                flight_headers = headers
                                logging.info(f"Found flight headers: {headers}")
                                continue
                        except Exception as e:
                            logging.warning(f"Error parsing potential flight header line: {line}")
                            logging.warning(f"Error details: {str(e)}")
                else:
                    try:
                        row = list(csv.reader([line]))[0]
                        if len(row) >= len(flight_headers):
                            flight_data.append(dict(zip(flight_headers, row)))
                    except Exception as e:
                        logging.warning(f"Error parsing flight data line: {line}")
                        logging.warning(f"Error details: {str(e)}")
            
            if not flight_headers:
                raise ValueError("Could not find valid flight headers")
            
            if not flight_data:
                raise ValueError("No valid flight data found")
            
            # Convert to pandas DataFrames
            self.aircraft_df = pd.DataFrame(aircraft_data)
            self.flights_df = pd.DataFrame(flight_data)
            
            logging.info("Successfully created DataFrames")
            logging.info(f"Aircraft DataFrame shape: {self.aircraft_df.shape}")
            logging.info(f"Flight DataFrame shape: {self.flights_df.shape}")
            
        except Exception as e:
            logging.error(f"Error parsing CSV: {str(e)}")
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
                    dual_received = self._clean_float(row['DualReceived'])
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
                        pilot_role = "Dual Received"
                    elif dual_given > 0:
                        pilot_role = "Dual Given"
                    elif pic_time > 0:
                        pilot_role = "PIC"
                    elif sic_time > 0:
                        pilot_role = "SIC"
                    else:
                        pilot_role = "Unknown"
                    
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
                        remarks=str(row['PilotComments']) if pd.notna(row['PilotComments']) else None
                    )
                    
                    entries.append(entry)
                    
                except Exception as e:
                    raise ValueError(f"Error processing flight {idx + 1}: {str(e)}")
                
            if not entries:
                raise ValueError("No valid entries found in the logbook")
                
            return entries
            
        except Exception as e:
            raise ValueError(f"Error importing entries: {str(e)}") 