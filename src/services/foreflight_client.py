"""ForeFlight API client for accessing logbook data."""

import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from src.core.config import FOREFLIGHT_API_KEY, FOREFLIGHT_API_SECRET, FOREFLIGHT_API_BASE_URL
from src.core.models import LogbookEntry, Aircraft

class ForeFlightClient:
    """Client for interacting with the ForeFlight API."""
    
    def __init__(self, csv_file_path: Optional[str] = None, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """Initialize the ForeFlight client.
        
        Args:
            csv_file_path: Path to CSV file for local data (used for testing)
            api_key: ForeFlight API key (optional, defaults to environment variable)
            api_secret: ForeFlight API secret (optional, defaults to environment variable)
        """
        self.csv_file_path = csv_file_path
        self.api_key = api_key or FOREFLIGHT_API_KEY
        self.api_secret = api_secret or FOREFLIGHT_API_SECRET
        self.base_url = FOREFLIGHT_API_BASE_URL.rstrip('/') if FOREFLIGHT_API_BASE_URL else None
        
        # If CSV file is provided, use local data mode
        if self.csv_file_path:
            from src.services.importer import ForeFlightImporter
            self.importer = ForeFlightImporter(self.csv_file_path)
            self.logbook_entries = self.importer.get_flight_entries()
            self.aircraft_list = self.importer.get_aircraft_list()
        else:
            # API mode - require credentials
            if not self.api_key or not self.api_secret:
                raise ValueError("ForeFlight API credentials not provided")
            self.importer = None
            self.logbook_entries = []
            self.aircraft_list = []
            
        self.session = requests.Session()
        self.session.auth = (self.api_key, self.api_secret)
        
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make a request to the ForeFlight API.
        
        Args:
            method: HTTP method to use
            endpoint: API endpoint to call
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            Dict containing the API response
            
        Raises:
            requests.exceptions.RequestException: If the request fails
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
        
    def get_logbook_entries(self, start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> List[LogbookEntry]:
        """Retrieve logbook entries from ForeFlight API or local data.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            List of LogbookEntry objects
        """
        # If using local data (CSV file)
        if self.csv_file_path:
            entries = self.logbook_entries
            
            # Apply date filtering if provided
            if start_date or end_date:
                filtered_entries = []
                for entry in entries:
                    entry_date = entry.date
                    if start_date and entry_date < start_date:
                        continue
                    if end_date and entry_date > end_date:
                        continue
                    filtered_entries.append(entry)
                return filtered_entries
            
            return entries
        
        # API mode
        params = {}
        if start_date:
            params['start_date'] = start_date.isoformat()
        if end_date:
            params['end_date'] = end_date.isoformat()
            
        response = self._make_request('GET', '/logbook/entries', params=params)
        return [LogbookEntry(**entry) for entry in response.get('entries', [])]
        
    def add_logbook_entry(self, entry: LogbookEntry) -> LogbookEntry:
        """Add a new logbook entry to ForeFlight or local data.
        
        Args:
            entry: LogbookEntry object to add
            
        Returns:
            Updated LogbookEntry object with server-assigned ID
        """
        # If using local data (CSV file)
        if self.csv_file_path:
            self.logbook_entries.append(entry)
            return entry
        
        # API mode
        response = self._make_request('POST', '/logbook/entries',
                                    json=entry.model_dump(exclude={'id'}))
        return LogbookEntry(**response)
        
    def update_logbook_entry(self, entry: LogbookEntry) -> LogbookEntry:
        """Update an existing logbook entry in ForeFlight.
        
        Args:
            entry: LogbookEntry object to update
            
        Returns:
            Updated LogbookEntry object
            
        Raises:
            ValueError: If the entry has no ID
        """
        if not entry.id:
            raise ValueError("Cannot update entry without ID")
            
        response = self._make_request('PUT', f'/logbook/entries/{entry.id}',
                                    json=entry.model_dump(exclude={'id'}))
        return LogbookEntry(**response)
        
    def delete_logbook_entry(self, entry_id: str) -> bool:
        """Delete a logbook entry from ForeFlight.
        
        Args:
            entry_id: ID of the entry to delete
            
        Returns:
            True if deleted successfully
        """
        self._make_request('DELETE', f'/logbook/entries/{entry_id}')
        return True
        
    def get_aircraft_list(self) -> List[Aircraft]:
        """Retrieve aircraft list from ForeFlight.
        
        Returns:
            List of Aircraft objects
        """
        response = self._make_request('GET', '/aircraft')
        return [Aircraft(**aircraft) for aircraft in response.get('aircraft', [])]
        
    def get_statistics(self) -> Dict:
        """Get flight statistics.
        
        Returns:
            Dictionary containing flight statistics
        """
        # For now, return empty stats - would normally call API
        return {
            'total_flights': 0,
            'total_hours': 0.0,
            'pic_hours': 0.0,
            'cross_country_hours': 0.0,
            'instrument_hours': 0.0,
            'night_hours': 0.0
        }
        
    def get_recent_flights(self, days: int = 30) -> List[LogbookEntry]:
        """Get recent flights within specified days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of recent LogbookEntry objects
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        return self.get_logbook_entries(start_date, end_date) 