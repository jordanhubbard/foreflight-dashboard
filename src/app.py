"""ForeFlight Logbook Manager web application."""

import csv
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from src.validate_csv import validate_logbook
from src.core.models import RunningTotals
from src.db import init_db, add_endorsement, get_all_endorsements, delete_endorsement, verify_pic_endorsements
import logging.handlers
import shutil
import time

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure root logger
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

# Get the root logger
logger = logging.getLogger(__name__)

# Ensure all loggers are set to DEBUG level and have the same handlers
root_logger = logging.getLogger()
for name in logging.root.manager.loggerDict:
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)
    # Remove any existing handlers
    log.handlers = []
    # Add the same handlers as the root logger
    for handler in root_logger.handlers:
        log.addHandler(handler)

# Create Flask app with default template folder structure
# Flask will look for templates in the 'templates' directory inside the application package
import os
app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.secret_key = 'your-secret-key-here'  # Required for flash messages
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize the database only if it doesn't exist
def init_db_if_needed():
    """Initialize the database only if it doesn't exist."""
    if not os.path.exists('endorsements.db'):
        init_db()

def calculate_running_totals(entries):
    """Calculate running totals for each entry."""
    totals = {
        'ground_training': 0.0,
        'asel_time': 0.0,
        'day_time': 0.0,
        'night_time': 0.0,
        'sim_instrument': 0.0,
        'dual_received': 0.0,
        'pic_time': 0.0,
        'cross_country': 0.0
    }
    
    # Sort entries by date in chronological order
    sorted_entries = sorted(entries, key=lambda x: x.date)
    
    # Calculate running totals for each entry
    for entry in sorted_entries:
        # Update running totals
        totals['ground_training'] += float(entry.ground_training)
        totals['asel_time'] += float(entry.total_time) if entry.aircraft.category_class == "airplane_single_engine_land" else 0.0
        totals['day_time'] += float(entry.conditions.day)
        totals['night_time'] += float(entry.conditions.night)
        totals['sim_instrument'] += float(entry.conditions.simulated_instrument)
        totals['dual_received'] += float(entry.dual_received)
        totals['pic_time'] += float(entry.pic_time)
        totals['cross_country'] += float(entry.conditions.cross_country)
        
        # Create RunningTotals instance with rounded values
        entry.running_totals = RunningTotals(**{k: round(v, 1) for k, v in totals.items()})
    
    return sorted_entries

def calculate_30_day_stats(entries):
    """Calculate statistics for the last 30 days."""
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_entries = [e for e in entries if e.date >= thirty_days_ago]
    return calculate_stats_for_entries(recent_entries)

def calculate_recent_experience(entries):
    """Calculate statistics for the last 2 calendar months."""
    today = datetime.now()
    # Get the first day of the current month
    first_day_current = today.replace(day=1)
    # Get the first day of the previous month
    if first_day_current.month == 1:
        first_day_previous = first_day_current.replace(year=first_day_current.year - 1, month=12)
    else:
        first_day_previous = first_day_current.replace(month=first_day_current.month - 1)
    
    # Filter entries for the last 2 calendar months
    recent_entries = [e for e in entries if e.date >= first_day_previous]
    return calculate_stats_for_entries(recent_entries)

def calculate_year_stats(entries):
    """Calculate statistics for the last year."""
    one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)
    recent_entries = [e for e in entries if e.date.replace(tzinfo=timezone.utc) >= one_year_ago]
    return calculate_stats_for_entries(recent_entries)

def calculate_all_time_stats(entries):
    """Calculate statistics for all entries."""
    return calculate_stats_for_entries(entries)

def calculate_stats_for_entries(entries):
    """Calculate statistics for the given entries."""
    stats = {
        'total_time': sum(float(e.total_time) for e in entries),
        'total_time_tailwheel': sum(float(e.total_time) for e in entries if e.aircraft.gear_type == "tailwheel"),
        'total_time_tricycle': sum(float(e.total_time) for e in entries if e.aircraft.gear_type == "tricycle"),
        'total_time_asel': sum(float(e.total_time) for e in entries if e.aircraft.category_class == "airplane_single_engine_land"),
        'total_time_amel': sum(float(e.total_time) for e in entries if e.aircraft.category_class == "airplane_multi_engine_land"),
        'total_time_ases': sum(float(e.total_time) for e in entries if e.aircraft.category_class == "airplane_single_engine_sea"),
        'total_time_ames': sum(float(e.total_time) for e in entries if e.aircraft.category_class == "airplane_multi_engine_sea"),
        'total_time_helo': sum(float(e.total_time) for e in entries if e.aircraft.category_class == "rotorcraft_helicopter"),
        'total_time_gyro': sum(float(e.total_time) for e in entries if e.aircraft.category_class == "rotorcraft_gyroplane"),
        'total_time_glider': sum(float(e.total_time) for e in entries if e.aircraft.category_class == "glider"),
        'total_day': sum(float(e.conditions.day) for e in entries),
        'total_night': sum(float(e.conditions.night) for e in entries),
        'total_pic': sum(float(e.pic_time) for e in entries),
        'total_sim_instrument': sum(float(e.conditions.simulated_instrument) for e in entries),
        'total_dual_received': sum(float(e.dual_received) for e in entries),
        'total_ground_training': sum(float(e.ground_training) for e in entries),
        'total_takeoffs': sum(e.landings_day + e.landings_night for e in entries),
        'total_landings': sum(e.landings_day + e.landings_night for e in entries),
        'total_cross_country': sum(float(e.conditions.cross_country) for e in entries)
    }
    return stats

def prepare_aircraft_stats(entries):
    """Prepare aircraft statistics for display."""
    aircraft_stats = defaultdict(lambda: {
        'count': 0,
        'total_time': 0.0,
        'solo_time': 0.0,
        'dual_time': 0.0,
        'registration': '',
        'type': ''
    })
    
    for entry in entries:
        aircraft = entry.aircraft
        key = aircraft.registration
        aircraft_stats[key]['count'] += 1
        aircraft_stats[key]['total_time'] += float(entry.total_time)
        # Track solo time (PIC without dual received) and dual time separately
        if entry.dual_received > 0:
            aircraft_stats[key]['dual_time'] += float(entry.total_time)
        else:
            aircraft_stats[key]['solo_time'] += float(entry.total_time)
        aircraft_stats[key]['registration'] = aircraft.registration
        aircraft_stats[key]['type'] = aircraft.type
    
    # Convert to list and sort by count
    aircraft_list = [
        {
            'registration': stats['registration'],
            'type': stats['type'],
            'count': stats['count'],
            'total_time': stats['total_time'],
            'solo_time': stats['solo_time'],
            'dual_time': stats['dual_time']
        }
        for stats in aircraft_stats.values()
    ]
    return sorted(aircraft_list, key=lambda x: x['count'], reverse=True)

@app.route('/')
def index():
    """Render the main page."""
    init_db_if_needed()
    
    # Check if a logbook was uploaded in this session
    logbook_filename = session.get('logbook_filename')
    is_student_pilot = session.get('is_student_pilot', False)
    
    entries = []
    stats = {}
    all_time_stats = {}
    aircraft_stats = []
    aircraft_list = []
    endorsements_dict = []
    recent_experience = {}
    all_time = {}
    error_count = 0
    
    if logbook_filename:
        try:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], logbook_filename)
            from src.services.importer import ForeFlightImporter
            importer = ForeFlightImporter(filepath)
            entries = importer.get_flight_entries()
            aircraft_list = [a.to_dict() for a in importer.get_aircraft_list()]
            entries = calculate_running_totals(entries)
            stats = calculate_stats_for_entries([e for e in entries if e.date.year == datetime.now().year])
            all_time = calculate_stats_for_entries(entries)
            recent_experience = calculate_recent_experience(entries)
            aircraft_stats = aircraft_list
            # Get endorsements if student pilot
            if is_student_pilot:
                try:
                    endorsements = get_all_endorsements()
                    endorsements_dict = [e.to_dict() for e in endorsements]
                except Exception as e:
                    logger.warning(f"Could not load endorsements: {str(e)}")
                    endorsements_dict = []
            # Do not delete the uploaded file or clear session here; keep for future reloads
            # File is kept in uploads/ for future reloads
            pass
        except Exception as e:
            logger.error(f"Failed to reload uploaded logbook: {str(e)}", exc_info=True)
            flash(f'Failed to reload uploaded logbook: {str(e)}')
    
    return render_template('index.html', 
                         entries=[entry.to_dict() for entry in entries],
                         stats=stats,
                         all_time_stats=all_time,
                         aircraft_stats=aircraft_stats,
                         aircraft_list=aircraft_list,
                         endorsements=endorsements_dict,
                         now=datetime.now().isoformat(),
                         is_student_pilot=is_student_pilot,
                         error_count=error_count,
                         recent_experience=recent_experience,
                         all_time=all_time
    )

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and validation."""
    logger.info("Starting file upload process")
    
    if 'file' not in request.files:
        logger.warning("No file part in request")
        flash('No file uploaded')
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        logger.warning("No selected file")
        flash('No file selected')
        return redirect(url_for('index'))
    
    if not file.filename.endswith('.csv'):
        logger.warning(f"Invalid file type: {file.filename}")
        flash('Only CSV files are allowed')
        return redirect(url_for('index'))
    
    try:
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        logger.info(f"Saved uploaded file to {filepath}")
        
        # Store filename and student pilot state in session for persistence
        session['logbook_filename'] = filename
        session['is_student_pilot'] = request.form.get('student_pilot') == 'on'
        
        # Create debug copy
        debug_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'debug_' + filename)
        shutil.copy2(filepath, debug_filepath)
        logger.info(f"Created debug copy at {debug_filepath}")
        
        # Use ForeFlightImporter for MVC-compliant model access
        logger.info("Parsing uploaded logbook using ForeFlightImporter")
        from src.services.importer import ForeFlightImporter
        importer = ForeFlightImporter(filepath)
        entries = importer.get_flight_entries()
        aircraft_list = importer.get_aircraft_list()
        logger.info(f"Parsed {len(entries)} flights and {len(aircraft_list)} aircraft")
        
        if not entries:
            logger.warning("No entries found in logbook")
            flash('No valid entries found in the logbook file')
            return redirect(url_for('index'))
        
        # Calculate running totals
        logger.info("Calculating running totals")
        entries = calculate_running_totals(entries)
        
        # Calculate statistics
        logger.info("Calculating statistics")
        stats = calculate_stats_for_entries([e for e in entries if e.date.year == datetime.now().year])
        all_time = calculate_stats_for_entries(entries)
        recent_experience = calculate_recent_experience(entries)
        # aircraft_stats can now be a direct pass-through of aircraft_list, or can be calculated from aircraft_list
        aircraft_stats = aircraft_list
        
        # Get student pilot status from form
        is_student_pilot = request.form.get('student_pilot') == 'on'
        
        # Get endorsements only if student pilot
        endorsements = []
        if is_student_pilot:
            try:
                init_db_if_needed()
                endorsements = get_all_endorsements()
                endorsements_dict = [e.to_dict() for e in endorsements]
            except Exception as e:
                logger.warning(f"Could not load endorsements: {str(e)}")
                endorsements_dict = []
        else:
            endorsements_dict = []
        
        # Do not delete the uploaded file; keep it in uploads/ for future reloads

        # Redirect to index so session-based persistence is used
        return redirect(url_for('index'))
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        flash(f'Error validating logbook: {str(e)}')
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        flash(f'Error processing file: {str(e)}')
        return redirect(url_for('index'))

@app.route('/endorsements/add', methods=['POST'])
def add_endorsement_route():
    """Add a new endorsement."""
    try:
        # Check if student pilot
        if not request.args.get('student_pilot', 'false').lower() == 'true':
            flash('Endorsements are only available for student pilots')
            return redirect(url_for('index'))
            
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
        endorsement = add_endorsement(start_date)
        flash('Endorsement added successfully')
    except Exception as e:
        flash(f'Error adding endorsement: {str(e)}')
    return redirect(url_for('index'))

@app.route('/endorsements/delete/<int:endorsement_id>', methods=['POST'])
def delete_endorsement_route(endorsement_id):
    """Delete an endorsement."""
    try:
        # Check if student pilot
        if not request.args.get('student_pilot', 'false').lower() == 'true':
            flash('Endorsements are only available for student pilots')
            return redirect(url_for('index'))
            
        if delete_endorsement(endorsement_id):
            flash('Endorsement deleted successfully')
        else:
            flash('Endorsement not found')
    except Exception as e:
        flash(f'Error deleting endorsement: {str(e)}')
    return redirect(url_for('index'))

@app.route('/verify-pic', methods=['POST'])
def verify_pic():
    """Verify PIC endorsements for all entries."""
    try:
        # Check if student pilot
        if not request.args.get('student_pilot', 'false').lower() == 'true':
            return jsonify({'error': 'Endorsement verification is only available for student pilots'}), 403
            
        data = request.get_json()
        if not data or 'entries' not in data:
            return jsonify({'error': 'No entries provided'}), 400
            
        entries = []
        for entry_data in data['entries']:
            try:
                # Convert the dictionary back to a LogbookEntry object
                entry = LogbookEntry(
                    date=datetime.fromisoformat(entry_data['date']),
                    departure_time=time.fromisoformat(entry_data['departure_time']) if entry_data.get('departure_time') else None,
                    arrival_time=time.fromisoformat(entry_data['arrival_time']) if entry_data.get('arrival_time') else None,
                    total_time=entry_data['total_time'],
                    aircraft=Aircraft(**entry_data['aircraft']),
                    departure=Airport(**entry_data['departure']) if entry_data.get('departure') else None,
                    destination=Airport(**entry_data['destination']) if entry_data.get('destination') else None,
                    conditions=FlightConditions(**entry_data['conditions']),
                    remarks=entry_data.get('remarks'),
                    pilot_role=entry_data['pilot_role'],
                    dual_received=entry_data['dual_received'],
                    pic_time=entry_data['pic_time'],
                    solo_time=entry_data.get('solo_time', 0.0),
                    ground_training=entry_data.get('ground_training', 0.0),
                    landings_day=entry_data['landings_day'],
                    landings_night=entry_data['landings_night']
                )
                entries.append(entry)
            except Exception as e:
                logger.error(f"Error converting entry: {str(e)}")
                continue
                
        results = verify_pic_endorsements(entries)
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Error verifying PIC endorsements: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Enable hot reloading
    app.debug = True
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='ForeFlight Dashboard Flask App')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5050, help='Port to bind to')
    args = parser.parse_args()
    
    # Run the app
    app.run(host=args.host, port=args.port, debug=True)
