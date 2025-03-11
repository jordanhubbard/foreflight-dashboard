"""Data models for the ForeFlight Logbook Manager."""

from datetime import datetime, time, timezone
from typing import Optional, List, Dict, Annotated
from pydantic import BaseModel, Field, validator, ConfigDict, model_validator

class Airport(BaseModel):
    """Airport information."""
    identifier: Optional[str] = None
    name: Optional[str] = None
    
    model_config = ConfigDict(
        title="Airport",
        description="Airport information"
    )

    def __bool__(self):
        """Return True if the airport has an identifier."""
        return bool(self.identifier)

class Aircraft(BaseModel):
    """Aircraft information."""
    registration: str
    type: str
    category_class: str
    
    model_config = ConfigDict(
        title="Aircraft",
        description="Aircraft information"
    )
    
class FlightConditions(BaseModel):
    """Flight conditions information."""
    day: float = 0.0
    night: float = 0.0
    actual_instrument: float = 0.0
    simulated_instrument: float = 0.0
    cross_country: float = 0.0
    
    model_config = ConfigDict(
        title="FlightConditions",
        description="Flight conditions information"
    )
    
class RunningTotals(BaseModel):
    """Running totals for logbook entries."""
    ground_training: float = 0.0
    asel_time: float = 0.0
    day_time: float = 0.0
    night_time: float = 0.0
    sim_instrument: float = 0.0
    dual_received: float = 0.0
    pic_time: float = 0.0
    
    model_config = ConfigDict(
        title="RunningTotals",
        description="Running totals for logbook entries"
    )

class LogbookEntry(BaseModel):
    """Main logbook entry model."""
    id: Optional[str] = None
    date: datetime
    departure_time: Optional[time] = None
    arrival_time: Optional[time] = None
    total_time: float
    
    # Aircraft information
    aircraft: Aircraft
    
    # Airport information
    departure: Optional[Airport] = None
    destination: Optional[Airport] = None
    alternate: Optional[Airport] = None
    
    # Flight conditions
    conditions: FlightConditions
    
    # Additional fields
    remarks: Optional[str] = None
    pilot_role: str = "PIC"
    dual_received: float = 0.0
    pic_time: float = 0.0
    solo_time: float = 0.0
    ground_training: float = 0.0
    landings_day: int = 0
    landings_night: int = 0
    instructor_name: Optional[str] = None
    instructor_comments: Optional[str] = None
    
    # Running totals
    running_totals: Optional[RunningTotals] = None
    
    # Validation error explanation
    error_explanation: Optional[str] = None
    
    model_config = ConfigDict(
        title="LogbookEntry",
        description="Main logbook entry model",
        json_schema_extra={
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
                "error_explanation": None
            }
        }
    )

    @model_validator(mode='after')
    def validate_date_not_future(self) -> 'LogbookEntry':
        """Validate that the date is not in the future using UTC."""
        current_utc = datetime.now(timezone.utc)
        if self.date.replace(tzinfo=timezone.utc) > current_utc:
            raise ValueError("Flight date cannot be in the future")
        return self

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
        valid_roles = ["PIC", "SIC", "STUDENT", "INSTRUCTOR", "SPLIT"]
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
            
        # Check that total time matches PIC time plus dual received time
        if self.total_time > 0:
            # If role is PIC and no PIC time is set, use total time
            if self.pilot_role == "PIC" and self.pic_time == 0:
                self.pic_time = self.total_time
            
            total_accounted_time = self.dual_received + self.pic_time
            
            if abs(total_accounted_time - self.total_time) > 0.1:  # Allow 0.1 hour difference for rounding
                issues.append(f"Total time ({self.total_time:.1f}) should equal sum of PIC time ({self.pic_time:.1f}) and dual received time ({self.dual_received:.1f})")

        # Check that cross-country time has sufficient distance
        if self.conditions.cross_country > 0:
            # Get distance from ForeFlight CSV
            distance = float(self.remarks.split('Distance: ')[1].split('nm')[0]) if 'Distance: ' in self.remarks else 0.0
            if distance < 50:
                issues.append(f"Cross-country time logged ({self.conditions.cross_country}) but flight distance ({distance}nm) is less than 50nm")

        # Set error explanation if issues were found
        if issues:
            self.error_explanation = "; ".join(issues)
        else:
            self.error_explanation = None 