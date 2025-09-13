"""
ForeFlight Dashboard - Modern FastAPI Application
Replaces the old Flask application with a clean, modern architecture.
"""

import os
import logging.handlers
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any, Annotated
import tempfile
import shutil
import traceback
from collections import defaultdict
from copy import deepcopy
from functools import lru_cache
import html

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Request, Response, status, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, ValidationError
import uvicorn
from contextlib import nullcontext

# Database imports
from sqlalchemy.orm import Session

# Application imports
from src.core.models import LogbookEntry, Aircraft, Airport, FlightConditions, RunningTotals
from src.core.database import (
    engine, SessionLocal, Base, get_db, init_database,
    User, UserLogbook, InstructorEndorsement, PasswordResetToken
)
from src.core.auth import (
    authenticate_user, create_access_token, get_current_user_from_token,
    create_user, get_password_hash, security, create_default_admin_user,
    session_manager, get_user_from_session
)
from src.services.foreflight_client import ForeFlightClient
from src.services.importer import ForeFlightImporter
from src.core.validation import validate_csv

# Configure logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.handlers.RotatingFileHandler(
            'logs/foreflight.log',
            maxBytes=1024*1024,  # 1MB
            backupCount=5,
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="ForeFlight Dashboard API",
    description="""
    ## ForeFlight Dashboard API
    
    A comprehensive API for managing ForeFlight logbook data, user authentication, and flight statistics.
    
    ### Features
    - **User Authentication**: JWT-based authentication system
    - **Logbook Management**: Upload and process ForeFlight CSV logbooks
    - **Flight Statistics**: Calculate flight time statistics and currency
    - **Aircraft Analytics**: Track time by aircraft and type
    - **Student Pilot Support**: Endorsement tracking and validation
    
    ### Authentication
    Most endpoints require authentication using JWT tokens. Include the token in the Authorization header:
    ```
    Authorization: Bearer <your-jwt-token>
    ```
    
    ### File Uploads
    Logbook files should be in ForeFlight CSV format. The system supports:
    - Flight entries with aircraft, route, and time information
    - Running totals calculation
    - Data validation and error reporting
    
    ### Data Models
    The API uses comprehensive Pydantic models with validation for:
    - Flight entries with time constraints
    - Aircraft information
    - User profiles and preferences
    - Statistical calculations
    """,
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    contact={
        "name": "ForeFlight Dashboard Support",
        "url": "https://github.com/jordanhubbard/foreflight-dashboard",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# Security middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "*.localhost"])

# Enable CORS (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://localhost:5051"] if os.environ.get('ENVIRONMENT') == 'development' else [],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # More permissive headers for API documentation endpoints
    if request.url.path in ["/api/docs", "/api/redoc", "/docs", "/redoc"]:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Allow framing and inline scripts for Swagger UI to work
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
    else:
        # Strict security headers for other endpoints
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    if os.environ.get('ENVIRONMENT') == 'production':
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Database is now configured in src.core.database

# Create upload directory
upload_dir = Path("uploads")
upload_dir.mkdir(exist_ok=True)

# Mount static files for React build
static_path = Path(__file__).parent / "static"
static_path.mkdir(exist_ok=True)

# Mount the dist directory directly for React assets
dist_path = static_path / "dist"
if dist_path.exists():
    app.mount("/assets", StaticFiles(directory=str(dist_path / "assets")), name="assets")
    
# Mount general static files
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Templates for any server-side rendering needed
templates_path = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))

# Security utilities
def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent XSS attacks."""
    if not text:
        return ""
    return html.escape(text.strip())

# Pydantic models for API
class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: 'UserResponse'

class RegisterRequest(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    student_pilot: bool = False
    pilot_certificate_number: Optional[str] = None
class UserCreate(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    student_pilot: bool = False
    pilot_certificate_number: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    student_pilot: bool
    pilot_certificate_number: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class EndorsementCreate(BaseModel):
    start_date: datetime

class EndorsementResponse(BaseModel):
    id: int
    user_id: int
    start_date: datetime
    expiration_date: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True

# Database dependency is imported from src.core.database

# Authentication dependency
async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db_session: Session = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = get_current_user_from_token(credentials, db_session)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    return user

# Optional authentication dependency
async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db_session: Session = Depends(get_db)
) -> Optional[User]:
    """Get current authenticated user (optional)."""
    if not credentials:
        return None
    
    return get_current_user_from_token(credentials, db_session)

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Don't include body in response as it may contain non-serializable data like FormData
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

# Utility functions
def convert_entries_to_template_data(entries: List[LogbookEntry]) -> List[Dict]:
    """Convert LogbookEntry objects to template-friendly dictionaries."""
    template_data = []
    for entry in entries:
        entry_dict = {
            'date': entry.date.isoformat(),
            'aircraft': {
                'registration': entry.aircraft.registration,
                'type': entry.aircraft.type,
                'category_class': entry.aircraft.category_class
            },
            'departure': {
                'identifier': entry.departure.identifier if entry.departure else None
            },
            'destination': {
                'identifier': entry.destination.identifier if entry.destination else None
            },
            'route': f"{entry.departure.identifier if entry.departure else '---'} → {entry.destination.identifier if entry.destination else '---'}",
            'total_time': float(entry.total_time),
            'pic_time': float(entry.pic_time),
            'dual_received': float(entry.dual_received),
            'solo_time': float(entry.solo_time) if entry.solo_time else 0.0,
            'conditions': {
                'day': float(entry.conditions.day),
                'night': float(entry.conditions.night),
                'cross_country': float(entry.conditions.cross_country),
                'simulated_instrument': float(entry.conditions.simulated_instrument),
                'actual_instrument': float(entry.conditions.actual_instrument)
            },
            'landings_day': entry.landings_day,
            'landings_night': entry.landings_night,
            'pilot_role': entry.pilot_role,
            'remarks': entry.remarks,
            'running_totals': {
                'total_time': float(entry.running_totals.total_time) if entry.running_totals else 0.0,
                'pic_time': float(entry.running_totals.pic_time) if entry.running_totals else 0.0,
                'dual_received': float(entry.running_totals.dual_received) if entry.running_totals else 0.0,
                'cross_country': float(entry.running_totals.cross_country) if entry.running_totals else 0.0,
                'day_time': float(entry.running_totals.day_time) if entry.running_totals else 0.0,
                'night_time': float(entry.running_totals.night_time) if entry.running_totals else 0.0,
                'sim_instrument': float(entry.running_totals.sim_instrument) if entry.running_totals else 0.0,
                'asel_time': float(entry.running_totals.asel_time) if entry.running_totals else 0.0,
                'ground_training': float(entry.running_totals.ground_training) if entry.running_totals else 0.0
            },
            'error_explanation': None  # TODO: Add validation error handling
        }
        template_data.append(entry_dict)
    
    return template_data

def calculate_running_totals(entries: List[LogbookEntry]) -> List[LogbookEntry]:
    """Calculate running totals for entries."""
    # Sort entries by date
    sorted_entries = sorted(entries, key=lambda x: x.date)
    
    # Initialize running totals
    running_totals = RunningTotals()
    
    for entry in sorted_entries:
        # Update running totals
        running_totals.total_time += entry.total_time
        running_totals.pic_time += entry.pic_time
        running_totals.dual_received += entry.dual_received
        running_totals.cross_country += entry.conditions.cross_country
        running_totals.day_time += entry.conditions.day
        running_totals.night_time += entry.conditions.night
        running_totals.sim_instrument += entry.conditions.simulated_instrument + entry.conditions.actual_instrument
        
        # Aircraft category specific totals
        if 'ASEL' in entry.aircraft.category_class:
            running_totals.asel_time += entry.total_time
        
        # Assign running totals to entry (create copy to avoid reference issues)
        entry.running_totals = deepcopy(running_totals)
    
    return sorted_entries

@lru_cache(maxsize=128)
def calculate_stats_for_entries_cached(entries_hash: str, entries_count: int) -> Dict:
    """Calculate statistics for a list of entries (cached version)."""
    # This is a cached wrapper - the actual calculation is done by calculate_stats_for_entries
    pass

def calculate_stats_for_entries(entries: List[LogbookEntry]) -> Dict:
    """Calculate statistics for a list of entries."""
    if not entries:
        return {
            'total_time': 0.0,
            'total_hours': 0.0,  # Alias for frontend compatibility
            'total_pic': 0.0,
            'total_dual': 0.0,
            'total_night': 0.0,
            'total_cross_country': 0.0,
            'total_sim_instrument': 0.0,
            'total_landings': 0,
            'total_time_asel': 0.0,
            'total_time_tailwheel': 0.0,
            'total_time_complex': 0.0,
            'total_time_high_performance': 0.0
        }
    
    return {
        'total_time': sum(float(e.total_time) for e in entries),
        'total_hours': sum(float(e.total_time) for e in entries),  # Alias for frontend compatibility
        'total_pic': sum(float(e.pic_time) for e in entries),
        'total_dual': sum(float(e.dual_received) for e in entries),
        'total_night': sum(float(e.conditions.night) for e in entries),
        'total_cross_country': sum(float(e.conditions.cross_country) for e in entries),
        'total_sim_instrument': sum(float(e.conditions.simulated_instrument + e.conditions.actual_instrument) for e in entries),
        'total_landings': sum(e.landings_day + e.landings_night for e in entries),
        'total_time_asel': sum(float(e.total_time) for e in entries if 'ASEL' in e.aircraft.category_class),
        'total_time_tailwheel': 0.0,  # TODO: Implement tailwheel detection
        'total_time_complex': 0.0,    # TODO: Implement complex aircraft detection
        'total_time_high_performance': 0.0  # TODO: Implement high performance detection
    }

# Authentication Routes

@app.post("/api/auth/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    db_session: Session = Depends(get_db)
):
    """Authenticate user and return access token."""
    user = authenticate_user(db_session, login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@app.post("/api/auth/register", response_model=UserResponse)
async def register(
    register_data: RegisterRequest,
    db_session: Session = Depends(get_db)
):
    """Register a new user."""
    user = create_user(
        db=db_session,
        email=register_data.email,
        password=register_data.password,
        first_name=register_data.first_name,
        last_name=register_data.last_name,
        student_pilot=register_data.student_pilot,
        pilot_certificate_number=register_data.pilot_certificate_number
    )
    
    return UserResponse.model_validate(user)

@app.post("/api/auth/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout user (client should discard token)."""
    return {"message": "Successfully logged out"}

# Main Routes

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the React application."""
    # In development mode, return API info instead of serving React
    if os.environ.get('ENVIRONMENT') == 'development':
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>ForeFlight Dashboard API - Development Mode</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
                .container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .api-link {{ display: inline-block; margin: 10px 0; padding: 10px 15px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
                .api-link:hover {{ background: #0056b3; }}
                .dev-info {{ background: #e7f3ff; padding: 15px; border-radius: 4px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 ForeFlight Dashboard API</h1>
                <div class="dev-info">
                    <strong>Development Mode Active</strong><br>
                    FastAPI backend running on port 5051<br>
                    React dev server running on port 3001
                </div>
                <h2>API Documentation</h2>
                <a href="/docs" class="api-link">📚 Interactive API Docs (Swagger)</a><br>
                <a href="/redoc" class="api-link">📖 ReDoc Documentation</a><br>
                <a href="/health" class="api-link">❤️ Health Check</a>
                
                <h2>Frontend Application</h2>
                <a href="http://localhost:3001" class="api-link">🎨 React Frontend (Port 3001)</a>
                
                <h2>Quick Test</h2>
                <p>Test authentication: <code>POST /api/auth/login</code></p>
                <p>Default admin: admin@foreflight-dashboard.com / admin123</p>
            </div>
        </body>
        </html>
        """)
    
    # Production mode: serve built React app
    try:
        index_file = static_path / "dist" / "index.html"
        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return HTMLResponse(content=content)
        else:
            logger.warning(f"React build not found at {index_file}")
            return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>ForeFlight Dashboard</title>
            </head>
            <body>
                <h1>ForeFlight Dashboard</h1>
                <p>React build not found at: <code>{index_file}</code></p>
                <p>Please build the frontend:</p>
                <pre>cd frontend && npm run build</pre>
            </body>
            </html>
            """)
    except Exception as e:
        logger.error(f"Error serving root: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Health check (must be before catch-all route)
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# API Routes

@app.get("/api/user", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user

@app.put("/api/user", response_model=UserResponse)
async def update_user(
    user_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db)
):
    """Update user profile."""
    # Update allowed fields
    if 'first_name' in user_data:
        current_user.first_name = user_data['first_name']
    if 'last_name' in user_data:
        current_user.last_name = user_data['last_name']
    if 'student_pilot' in user_data:
        current_user.student_pilot = user_data['student_pilot']
    if 'pilot_certificate_number' in user_data:
        current_user.pilot_certificate_number = user_data['pilot_certificate_number']
    
    db_session.commit()
    db_session.refresh(current_user)
    
    return current_user

@app.get("/api/logbook")
async def get_logbook_data(
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db),
    limit: int = 100,
    offset: int = 0
):
    """Get logbook data for the current user."""
    try:
        # Get user's active logbook
        active_logbook = (
            db_session.query(UserLogbook)
            .filter_by(user_id=current_user.id, is_active=True)
            .order_by(UserLogbook.uploaded_at.desc())
            .first()
        )
        
        if not active_logbook:
            return {
                "entries": [],
                "stats": {},
                "all_time": {},
                "recent_experience": {},
                "aircraft_stats": [],
                "logbook_filename": None,
                "error_count": 0
            }
        
        # Load and process logbook data
        filepath = upload_dir / active_logbook.filename
        importer = ForeFlightImporter(str(filepath))
        
        entries_objects = importer.get_flight_entries()
        aircraft_objects = importer.get_aircraft_list()
        
        # Calculate running totals
        entries_objects = calculate_running_totals(entries_objects)
        
        # Calculate statistics (use UTC to avoid timezone issues)
        now_utc = datetime.now(timezone.utc)
        current_year_entries = [e for e in entries_objects if e.date.year == now_utc.year]
        recent_entries = [
            e for e in entries_objects 
            if e.date >= now_utc.date() - timedelta(days=30)
        ]
        
        stats = calculate_stats_for_entries(current_year_entries)
        all_time = calculate_stats_for_entries(entries_objects)
        recent_experience = calculate_stats_for_entries(recent_entries)
        
        # Convert to template data
        entries = convert_entries_to_template_data(entries_objects)
        
        return {
            "entries": entries,
            "stats": stats,
            "all_time": all_time,
            "recent_experience": recent_experience,
            "aircraft_stats": [],  # TODO: Implement aircraft stats
            "logbook_filename": active_logbook.filename,
            "error_count": 0,
            "student_pilot": current_user.student_pilot
        }
        
    except Exception as e:
        logger.error(f"Error getting logbook data: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload")
async def upload_logbook(
    file: UploadFile = File(...),
    student_pilot: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db)
):
    """Handle logbook file upload."""
    try:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files are allowed")
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"user_{current_user.id}_{timestamp}_{file.filename}"
        filepath = upload_dir / filename
        
        # Save uploaded file
        with open(filepath, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Update user student pilot status
        if current_user.student_pilot != student_pilot:
            current_user.student_pilot = student_pilot
            db_session.commit()
        
        # Validate the CSV
        try:
            importer = ForeFlightImporter(str(filepath))
            entries = importer.get_flight_entries()
            
            if not entries:
                raise HTTPException(status_code=400, detail="No valid entries found in the logbook file")
            
            # Deactivate previous logbooks
            db_session.query(UserLogbook).filter_by(
                user_id=current_user.id, is_active=True
            ).update({'is_active': False})
            
            # Create new logbook record
            new_logbook = UserLogbook(
                user_id=current_user.id,
                filename=filename,
                original_filename=file.filename,
                uploaded_at=datetime.now(timezone.utc),
                file_size=len(content),
                is_active=True
            )
            db_session.add(new_logbook)
            db_session.commit()
            
            return {"message": "File uploaded successfully", "filename": filename}
            
        except Exception as e:
            # Clean up file on error
            if filepath.exists():
                filepath.unlink()
            raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/endorsements", response_model=List[EndorsementResponse])
async def get_endorsements(
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db)
):
    """Get user's instructor endorsements."""
    endorsements = db_session.query(InstructorEndorsement).filter_by(
        user_id=current_user.id
    ).order_by(InstructorEndorsement.start_date.desc()).all()
    
    return endorsements

@app.post("/api/endorsements", response_model=EndorsementResponse)
async def create_endorsement(
    endorsement_data: EndorsementCreate,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db)
):
    """Create a new instructor endorsement."""
    # Calculate expiration date (90 days from start)
    expiration_date = endorsement_data.start_date + timedelta(days=90)
    
    new_endorsement = InstructorEndorsement(
        user_id=current_user.id,
        start_date=endorsement_data.start_date,
        expiration_date=expiration_date,
        created_at=datetime.now(timezone.utc)
    )
    
    db_session.add(new_endorsement)
    db_session.commit()
    db_session.refresh(new_endorsement)
    
    return new_endorsement

@app.delete("/api/endorsements/{endorsement_id}")
async def delete_endorsement(
    endorsement_id: int,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db)
):
    """Delete an instructor endorsement."""
    endorsement = db_session.query(InstructorEndorsement).filter_by(
        id=endorsement_id, user_id=current_user.id
    ).first()
    
    if not endorsement:
        raise HTTPException(status_code=404, detail="Endorsement not found")
    
    db_session.delete(endorsement)
    db_session.commit()
    
    return {"message": "Endorsement deleted successfully"}

# API Documentation routes
@app.get("/docs", response_class=HTMLResponse)
async def api_docs_redirect():
    """Redirect to API documentation."""
    return RedirectResponse(url="/api/docs", status_code=302)

@app.get("/api-docs", response_class=HTMLResponse) 
async def api_docs_alt():
    """Alternative API documentation endpoint."""
    return RedirectResponse(url="/api/docs", status_code=302)

# Catch-all route for React SPA (must be last!)
@app.get("/{path:path}", response_class=HTMLResponse)
async def serve_spa(path: str):
    """Serve React SPA for all routes (client-side routing)."""
    # Don't serve SPA for API routes - let them return proper 404
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    return await root()

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database and create tables."""
    try:
        # Initialize database tables
        init_database()
        
        # Create default admin user
        db_session = SessionLocal()
        try:
            create_default_admin_user(db_session)
            db_session.commit()
        finally:
            db_session.close()
        
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    port = int(os.environ.get('FASTAPI_PORT', 5051))
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="debug"
    )
