"""FastAPI application for the ForeFlight Logbook Manager."""

from datetime import datetime, timedelta
from typing import List, Optional, Annotated
from pathlib import Path
import tempfile
import shutil
import traceback
import logging

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from src.core.models import LogbookEntry
from src.services.foreflight_client import ForeFlightClient
from src.services.importer import ForeFlightImporter
from src.core.validation import validate_csv
from src.core.account_manager import AccountManager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ForeFlight Logbook Manager",
    description="API for managing ForeFlight logbook entries",
    version="0.1.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = Path(__file__).parent.parent / "static"
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Mount templates directory
templates_path = Path(__file__).parent.parent / "templates"
templates_path.mkdir(exist_ok=True)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed messages."""
    error_messages = []
    for error in exc.errors():
        location = " -> ".join(str(loc) for loc in error["loc"])
        message = f"Error in {location}: {error['msg']}"
        error_messages.append(message)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "Validation Error",
            "details": error_messages
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions with detailed messages."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": str(exc),
            "details": traceback.format_exc().split('\n')
        }
    )

async def get_foreflight_client() -> ForeFlightClient:
    """Get a ForeFlight API client instance."""
    try:
        return ForeFlightClient()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Serve the main page."""
    index_path = templates_path / "index.html"
    if index_path.exists():
        return index_path.read_text()
    else:
        logger.error(f"Template not found: {index_path}")
        raise HTTPException(status_code=404, detail="Template not found")

@app.post("/upload", status_code=status.HTTP_200_OK)
async def upload_logbook(file: Annotated[UploadFile, File(...)]):
    """Handle logbook file upload."""
    logger.info(f"Received file upload: {file.filename}")
    
    if not file.filename.lower().endswith('.csv'):
        logger.warning(f"Invalid file type: {file.filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload a CSV file"
        )

    temp_path = None
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_path = temp_file.name
            logger.info(f"Saved uploaded file to temporary location: {temp_path}")

        # Validate the CSV file first
        logger.info("Starting CSV validation")
        validation_result = validate_csv(temp_path)
        logger.info(f"Validation result: {validation_result}")
        
        if not validation_result['success']:
            logger.warning(f"Validation failed: {validation_result['error']}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": validation_result['error'],
                    "details": validation_result.get('details', {})
                }
            )

        # Import the logbook
        try:
            logger.info("Starting logbook import")
            importer = ForeFlightImporter(temp_path)
            entries = importer.import_entries()
            logger.info(f"Successfully imported {len(entries)} entries")
            
        except ValidationError as e:
            logger.error(f"Validation error during import: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "Validation Error",
                    "details": [
                        f"Error in {' -> '.join(str(loc) for loc in err['loc'])}: {err['msg']}"
                        for err in e.errors()
                    ]
                }
            )
        except ValueError as e:
            logger.error(f"Value error during import: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error during import: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

        if not entries:
            logger.warning("No entries found in logbook")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid entries found in the logbook file"
            )

        # Calculate statistics
        logger.info("Calculating statistics")
        total_time = sum(entry.total_time for entry in entries)
        pic_time = sum(entry.pic_time for entry in entries)
        dual_received = sum(entry.dual_received for entry in entries)
        
        # Get date range
        dates = [entry.date for entry in entries]
        date_range = {
            "start": min(dates).date().isoformat() if dates else None,
            "end": max(dates).date().isoformat() if dates else None
        }
        
        # Get aircraft types and hours
        aircraft_types = {}
        for entry in entries:
            ac_type = entry.aircraft.type
            aircraft_types[ac_type] = aircraft_types.get(ac_type, 0) + entry.total_time

        # Calculate recent activity (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_entries = [entry for entry in entries if entry.date >= thirty_days_ago]
        recent_activity = {
            "total_time": round(sum(entry.total_time for entry in recent_entries), 1),
            "pic_time": round(sum(entry.pic_time for entry in recent_entries), 1),
            "night_time": round(sum(entry.conditions.night for entry in recent_entries), 1),
            "sim_instrument": round(sum(entry.conditions.simulated_instrument for entry in recent_entries), 1),
            "dual_received": round(sum(entry.dual_received for entry in recent_entries), 1),
            "flight_count": len(recent_entries)
        }

        # Prepare detailed flight data
        logger.info("Preparing flight data")
        flight_data = []
        aircraft_summary = {}

        for entry in entries:
            # Track aircraft usage
            registration = entry.aircraft.registration
            if registration not in aircraft_summary:
                aircraft_summary[registration] = {
                    "flights": 0,
                    "total_time": 0,
                    "type": entry.aircraft.type
                }
            aircraft_summary[registration]["flights"] += 1
            aircraft_summary[registration]["total_time"] += entry.total_time

            # Format flight data
            entry.validate_entry()  # Run validation for this entry
            flight_data.append({
                "date": entry.date.date().isoformat(),
                "aircraft": entry.aircraft.registration,
                "type": entry.aircraft.type,
                "from": entry.departure.identifier if entry.departure else "---",
                "to": entry.destination.identifier if entry.destination else "---",
                "total_time": entry.total_time,
                "pilot_role": entry.pilot_role,
                "landings": entry.landings_day + entry.landings_night,
                "night": entry.conditions.night,
                "instrument": entry.conditions.actual_instrument + entry.conditions.simulated_instrument,
                "cross_country": entry.conditions.cross_country,
                "remarks": entry.remarks or "",
                "has_errors": bool(entry.error_explanation),
                "error_explanation": entry.error_explanation
            })

        # Sort flight data by date (newest first)
        flight_data.sort(key=lambda x: x["date"], reverse=True)

        # Sort aircraft summary by number of flights
        aircraft_summary = {
            k: v for k, v in sorted(
                aircraft_summary.items(),
                key=lambda item: item[1]["flights"],
                reverse=True
            )
        }

        logger.info("Successfully processed logbook data")
        return {
            "success": True,
            "entries_count": len(entries),
            "statistics": {
                "total_time": round(total_time, 1),
                "pic_time": round(pic_time, 1),
                "dual_received": round(dual_received, 1),
                "date_range": date_range,
                "aircraft_types": {k: round(v, 1) for k, v in aircraft_types.items()},
                "recent_activity": recent_activity
            },
            "flight_data": flight_data,
            "aircraft_summary": aircraft_summary
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in upload handler: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        # Clean up temporary file
        if temp_path and Path(temp_path).exists():
            try:
                Path(temp_path).unlink()
                logger.info(f"Cleaned up temporary file: {temp_path}")
            except Exception as e:
                logger.error(f"Error cleaning up temporary file {temp_path}: {e}")
        file.file.close()

@app.get("/entries", response_model=List[LogbookEntry])
async def get_entries(
    client: Annotated[ForeFlightClient, Depends(get_foreflight_client)],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Get logbook entries with optional date filtering."""
    try:
        return client.get_logbook_entries(start_date, end_date)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/entries", response_model=LogbookEntry, status_code=status.HTTP_201_CREATED)
async def create_entry(
    entry: LogbookEntry,
    client: Annotated[ForeFlightClient, Depends(get_foreflight_client)]
):
    """Create a new logbook entry."""
    try:
        return client.add_logbook_entry(entry)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.put("/entries/{entry_id}", response_model=LogbookEntry)
async def update_entry(
    entry_id: str,
    entry: LogbookEntry,
    client: Annotated[ForeFlightClient, Depends(get_foreflight_client)]
):
    """Update an existing logbook entry."""
    entry.id = entry_id
    try:
        return client.update_logbook_entry(entry)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: str,
    client: Annotated[ForeFlightClient, Depends(get_foreflight_client)]
):
    """Delete a logbook entry."""
    try:
        client.delete_logbook_entry(entry_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Account Management API Endpoints
@app.post("/api/admin/accounts/create-from-file")
async def create_accounts_from_file(
    file_path: str = "test-accounts.json",
    request: Request = None
):
    """Create accounts from a JSON file.
    
    This endpoint is for administrative use to create test or production accounts
    from a JSON file containing account definitions.
    """
    try:
        # Import Flask app to get the application context
        from src.app import app as flask_app
        
        with flask_app.app_context():
            # Ensure database tables exist
            from src.core.auth_models import db
            from src.core.security import create_user_datastore
            
            db.create_all()
            
            # Create default roles if they don't exist
            user_datastore = create_user_datastore()
            roles = [
                ('admin', 'Administrator - Full access to all features'),
                ('pilot', 'Certified Pilot - Access to all pilot features'),
                ('student', 'Student Pilot - Access to student-specific features'),
                ('instructor', 'Flight Instructor - Can manage student endorsements')
            ]
            
            for role_name, description in roles:
                if not user_datastore.find_role(role_name):
                    user_datastore.create_role(name=role_name, description=description)
            
            db.session.commit()
            
            # Create accounts from JSON
            manager = AccountManager(flask_app)
            
            # Validate the JSON file first
            if not manager.validate_accounts_json(file_path):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Account validation failed. Please check the JSON file."
                )
            
            created_users = manager.create_accounts_from_json(file_path)
            
            # Return summary
            user_summaries = []
            for user in created_users:
                user_summaries.append({
                    "email": user.email,
                    "name": f"{user.first_name} {user.last_name}",
                    "roles": [role.name for role in user.roles],
                    "student_pilot": user.student_pilot,
                    "created": True
                })
            
            return {
                "success": True,
                "message": f"Successfully created {len(created_users)} accounts",
                "accounts": user_summaries
            }
            
    except Exception as e:
        logger.error(f"Error creating accounts from file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating accounts: {str(e)}"
        )


@app.post("/api/admin/accounts/validate-file")
async def validate_accounts_file(file_path: str = "test-accounts.json"):
    """Validate account definitions in a JSON file.
    
    This endpoint validates the structure and content of an accounts JSON file
    without actually creating the accounts.
    """
    try:
        from src.core.account_manager import validate_accounts_file
        
        if validate_accounts_file(file_path):
            return {
                "success": True,
                "message": "All account definitions are valid",
                "file_path": file_path
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Some account definitions are invalid"
            )
            
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account file not found: {file_path}"
        )
    except Exception as e:
        logger.error(f"Error validating accounts file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating accounts file: {str(e)}"
        ) 