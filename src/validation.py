"""Validation utilities for ForeFlight logbook files."""

from typing import Dict, Any
from pathlib import Path
import logging

from .importer import ForeFlightImporter

def validate_csv(csv_path: str) -> Dict[str, Any]:
    """Validate a ForeFlight CSV file and return detailed validation results.
    
    Args:
        csv_path: Path to the CSV file to validate
        
    Returns:
        Dictionary containing validation results with the following structure:
        {
            'success': bool,
            'stage': str,  # Which stage of validation failed
            'error': str,  # Error message if failed
            'details': Dict[str, Any]  # Additional details about the validation
        }
    """
    try:
        # Read raw file contents first
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
            
        lines = content.split('\n')
        result = {
            'success': False,
            'stage': 'initial',
            'error': None,
            'details': {
                'total_lines': len(lines),
                'empty_lines': sum(1 for line in lines if not line.strip()),
                'sample_lines': lines[:5],  # First 5 lines for inspection
                'sections': {
                    'aircraft_table': {'found': False, 'line': None},
                    'flights_table': {'found': False, 'line': None}
                }
            }
        }
        
        # Look for section markers
        for i, line in enumerate(lines):
            if "Aircraft Table" in line:
                result['details']['sections']['aircraft_table'] = {
                    'found': True,
                    'line': i + 1,
                    'content': line
                }
            elif "Flights Table" in line:
                result['details']['sections']['flights_table'] = {
                    'found': True,
                    'line': i + 1,
                    'content': line
                }
        
        # Validate basic structure
        if not result['details']['sections']['aircraft_table']['found']:
            result.update({
                'stage': 'structure',
                'error': 'Missing Aircraft Table section marker'
            })
            return result
            
        if not result['details']['sections']['flights_table']['found']:
            result.update({
                'stage': 'structure',
                'error': 'Missing Flights Table section marker'
            })
            return result
            
        # Try parsing with importer
        try:
            importer = ForeFlightImporter(csv_path)
            
            # Add DataFrame info to results
            if importer.aircraft_df is not None:
                result['details']['aircraft'] = {
                    'rows': len(importer.aircraft_df),
                    'columns': list(importer.aircraft_df.columns),
                    'sample': importer.aircraft_df.head(2).to_dict('records')
                }
                
            if importer.flights_df is not None:
                result['details']['flights'] = {
                    'rows': len(importer.flights_df),
                    'columns': list(importer.flights_df.columns),
                    'sample': importer.flights_df.head(2).to_dict('records')
                }
                
            # Try creating entries
            entries = importer.import_entries()
            result['details']['entries'] = {
                'count': len(entries),
                'sample': [
                    {
                        'date': str(e.date),
                        'aircraft': e.aircraft.registration,
                        'from': e.departure.identifier if e.departure else None,
                        'to': e.destination.identifier if e.destination else None,
                        'total_time': e.total_time
                    }
                    for e in entries[:2]
                ]
            }
            
            result['success'] = True
            result['stage'] = 'complete'
            
        except Exception as e:
            result.update({
                'stage': 'parsing',
                'error': str(e)
            })
            
        return result
        
    except Exception as e:
        return {
            'success': False,
            'stage': 'file_read',
            'error': str(e),
            'details': {}
        } 