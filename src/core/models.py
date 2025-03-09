"""Data models for the ForeFlight Logbook Manager."""

from datetime import datetime, time, timezone
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, validator

class Airport(BaseModel):
    """Airport information."""
    identifier: Optional[str] = Field(None, description="Airport identifier (ICAO/IATA)")
    name: Optional[str] = Field(None, description="Airport name")

    def __bool__(self):
        """Return True if the airport has an identifier."""
        return bool(self.identifier)

class Aircraft(BaseModel):
    """Aircraft information."""
    registration: str = Field(..., description="Aircraft registration number")
    type: str = Field(..., description="Aircraft type designator")
    category_class: str = Field(..., description="Category/class of aircraft")
    
class FlightConditions(BaseModel):
    """Flight conditions information."""
    day: float = Field(0.0, description="Day flight time")
    night: float = Field(0.0, description="Night flight time")
    actual_instrument: float = Field(0.0, description="Actual instrument time")
    simulated_instrument: float = Field(0.0, description="Simulated instrument time")
    cross_country: float = Field(0.0, description="Cross-country time")
    
class RunningTotals(BaseModel):
    """Running totals for logbook entries."""
    ground_training: float = Field(0.0, description="Total ground training time")
    asel_time: float = Field(0.0, description="Total ASEL time")
    day_time: float = Field(0.0, description="Total day time")
    night_time: float = Field(0.0, description="Total night time")
    sim_instrument: float = Field(0.0, description="Total simulated instrument time")
    dual_received: float = Field(0.0, description="Total dual received time")
    pic_time: float = Field(0.0, description="Total PIC time")

class LogbookEntry(BaseModel):
    """Main logbook entry model."""
    id: Optional[str] = Field(None, description="Entry ID")
    date: datetime = Field(..., description="Date of flight")
    departure_time: Optional[time] = Field(None, description="Departure time")
    arrival_time: Optional[time] = Field(None, description="Arrival time")
    total_time: float = Field(..., description="Total flight time")
    
    # Aircraft information
    aircraft: Aircraft
    
    # Airport information
    departure: Optional[Airport] = Field(None, description="Departure airport")
    destination: Optional[Airport] = Field(None, description="Destination airport")
    alternate: Optional[Airport] = None
    
    # Flight conditions
    conditions: FlightConditions
    
    # Additional fields
    remarks: Optional[str] = Field(None, description="Flight remarks")
    pilot_role: str = Field("PIC", description="Pilot role")
    dual_received: float = Field(0.0, description="Dual instruction received")
    solo_time: float = Field(0.0, description="Solo flight time")
    ground_training: float = Field(0.0, description="Ground training time")
    landings_day: int = Field(0, description="Number of day landings")
    landings_night: int = Field(0, description="Number of night landings")
    
    # Running totals
    running_totals: Optional[RunningTotals] = None
    
    # Validation error explanation
    error_explanation: Optional[str] = Field(None, description="Explanation of any validation errors in the entry")

    @validator('date')
    def validate_date(cls, v):
        """Validate that the date is not in the future using UTC."""
        current_utc = datetime.now(timezone.utc)
        if v.replace(tzinfo=timezone.utc) > current_utc:
            raise ValueError("Flight date cannot be in the future")
        return v

    def validate_entry(self) -> None:
        """Validate the entry and set error explanation if issues are found."""
        issues = []
        
        # Check for missing airports
        if not self.departure or not self.departure.identifier:
            issues.append("Missing departure airport")
        if not self.destination or not self.destination.identifier:
            issues.append("Missing destination airport")
            
        # Validate aircraft registration (tail number)
        if not self.aircraft or not self.aircraft.registration:
            issues.append("Missing aircraft registration")
        elif not self.aircraft.registration.startswith(('N', 'C-', 'G-')):  # US, Canadian, or UK registrations
            issues.append(f"Invalid aircraft registration format: {self.aircraft.registration}")
            
        # Validate pilot role
        valid_roles = ["PIC", "SIC", "STUDENT", "Dual Given"]
        if self.pilot_role not in valid_roles:
            issues.append(f"Invalid pilot role (must be one of: {', '.join(valid_roles)})")
            
        # Check for implausibly short flight time
        if 0 < self.total_time < 0.3:
            issues.append(f"Flight time of {self.total_time} hours seems implausibly short (less than 18 minutes)")
            
        # Check flight conditions consistency only if conditions are provided
        total_condition_time = (
            self.conditions.day +
            self.conditions.night
        )
        if total_condition_time > 0 and abs(total_condition_time - self.total_time) > 0.1:
            issues.append(f"Day ({self.conditions.day}) + night ({self.conditions.night}) time ({total_condition_time}) does not match total time ({self.total_time})")
            
        # Check instrument time consistency
        total_instrument = (
            self.conditions.actual_instrument +
            self.conditions.simulated_instrument
        )
        if total_instrument > self.total_time:
            issues.append(f"Total instrument time ({total_instrument}) exceeds flight time ({self.total_time})")

        # Check dual received time consistency
        if self.dual_received > self.total_time:
            issues.append(f"Dual received time ({self.dual_received}) exceeds flight time ({self.total_time})")
            
        # Check that total time is accounted for in PIC, dual received, or solo time
        if self.total_time > 0:
            is_pic = self.pilot_role == "PIC"
            total_accounted_time = (
                self.total_time if is_pic else 0.0) + self.dual_received + self.solo_time
            if total_accounted_time < 0.1:  # Using 0.1 to account for floating point precision
                issues.append("Flight has total time but no PIC, dual received, or solo time recorded")
            
        # Set error explanation if issues were found
        if issues:
            self.error_explanation = "; ".join(issues)
        else:
            self.error_explanation = None

    @validator('arrival_time')
    def validate_times(cls, v, values):
        """Validate that arrival time is after departure time, accounting for flights crossing midnight."""
        if 'departure_time' in values:
            dt = values['departure_time']
            # If arrival time is before departure time, assume flight crossed midnight
            if v < dt:
                # Verify the total time makes sense for a flight crossing midnight
                if 'total_time' in values:
                    # Calculate time difference accounting for midnight crossing
                    hours_diff = (24 - dt.hour + v.hour) + (v.minute - dt.minute) / 60
                    # Allow some rounding difference (0.2 hours = 12 minutes)
                    if abs(hours_diff - values['total_time']) > 0.2:
                        raise ValueError("Arrival and departure times don't match total time")
            else:
                # For same-day flights, verify total time roughly matches time difference
                if 'total_time' in values:
                    hours_diff = (v.hour - dt.hour) + (v.minute - dt.minute) / 60
                    if abs(hours_diff - values['total_time']) > 0.2:
                        raise ValueError("Arrival and departure times don't match total time")
        return v

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "date": "2023-11-01T14:00:00Z",
                "departure_time": "14:00:00",
                "arrival_time": "16:30:00",
                "total_time": 2.5,
                "aircraft": {
                    "registration": "N12345",
                    "type": "C172",
                    "category_class": "ASEL"
                },
                "departure": {
                    "identifier": "KBOS",
                    "name": "Boston Logan International"
                },
                "destination": {
                    "identifier": "KJFK",
                    "name": "John F Kennedy International"
                },
                "conditions": {
                    "day": 2.5,
                    "night": 0.0,
                    "actual_instrument": 0.5,
                    "simulated_instrument": 0.0,
                    "cross_country": 2.5
                },
                "pilot_role": "PIC",
                "landings_day": 1,
                "landings_night": 0,
                "dual_received": 0.0,
                "remarks": "Cross country flight BOS-JFK",
                "error_explanation": None  # This will only be populated for entries with issues
            }
        } 