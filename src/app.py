"""ForeFlight Logbook Manager web application."""

import csv
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from src.validate_csv import validate_logbook
from src.core.models import RunningTotals, LogbookEntry, Aircraft, Airport, FlightConditions
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

def convert_entries_to_template_data(entries):
    """Convert LogbookEntry objects to template-friendly dictionaries."""
    logger.info(f"Converting {len(entries)} entries to template data")
    
    # Entries come in chronological order (oldest first) with running totals calculated
    # We need to reverse them for display (newest first) while preserving running totals
    template_entries = []
    for i, entry in enumerate(entries):
        try:
            # Get the full nested dictionary for HTML template access
            entry_dict = entry.to_dict()
            
            # Debug: Log the first few entries' running totals before conversion
            if i < 3:
                logger.info(f"Entry {i}: Original entry.running_totals object = {entry.running_totals}")
                logger.info(f"Entry {i}: entry_dict running_totals = {entry_dict.get('running_totals')}")
            
            # Add flattened properties for JavaScript compatibility
            entry_dict.update({
                # Flattened versions for JavaScript
                'id': f"entry-{i+1}",
                'date': entry_dict['date'].split('T')[0],  # Date only
                'route': f"{entry_dict['departure']['identifier'] if entry_dict['departure'] else '---'} → {entry_dict['destination']['identifier'] if entry_dict['destination'] else '---'}",
                'aircraft': entry_dict['aircraft']['registration'],
                'total': entry_dict['total_time'],
                'day': entry_dict['conditions']['day'],
                'night': entry_dict['conditions']['night'],
                'ldg': entry_dict['landings_day'] + entry_dict['landings_night'],
                'role': entry_dict['pilot_role'],
                'pic': entry_dict['pic_time'],
                'dual': entry_dict['dual_received'],
                'xc': entry_dict['conditions']['cross_country'],  # Individual flight XC for filtering
                'night_time': entry_dict['conditions']['night'],  # Individual flight night for filtering
                'solo_time': entry_dict.get('solo_time', 0),
                'dual_rcvd': entry_dict['dual_received'],
                'sim_inst': entry_dict['conditions']['simulated_instrument'],
                'pic_time': entry_dict['pic_time'],
                # Running totals for the accumulated columns
                'ground': entry_dict['running_totals']['ground_training'] if entry_dict.get('running_totals') else 0,
                'asel': entry_dict['running_totals']['asel_time'] if entry_dict.get('running_totals') else 0,
                'xc_total': entry_dict['running_totals']['cross_country'] if entry_dict.get('running_totals') else 0,
                'day_time': entry_dict['running_totals']['day_time'] if entry_dict.get('running_totals') else 0,
                'night_total': entry_dict['running_totals']['night_time'] if entry_dict.get('running_totals') else 0,
                'sim_inst_total': entry_dict['running_totals']['sim_instrument'] if entry_dict.get('running_totals') else 0,
                'dual_rcvd_total': entry_dict['running_totals']['dual_received'] if entry_dict.get('running_totals') else 0,
                'pic_time_total': entry_dict['running_totals']['pic_time'] if entry_dict.get('running_totals') else 0
            })
            
            # Debug: Log running totals for first few entries after conversion
            if i < 3:
                logger.info(f"Entry {i}: Final flattened running totals:")
                logger.info(f"  ground: {entry_dict['ground']}")
                logger.info(f"  asel: {entry_dict['asel']}")
                logger.info(f"  xc_total: {entry_dict['xc_total']}")
                logger.info(f"  day_time: {entry_dict['day_time']}")
                logger.info(f"  night_total: {entry_dict['night_total']}")
                logger.info(f"  sim_inst_total: {entry_dict['sim_inst_total']}")
                logger.info(f"  dual_rcvd_total: {entry_dict['dual_rcvd_total']}")
                logger.info(f"  pic_time_total: {entry_dict['pic_time_total']}")
            
            # Ensure running_totals is properly structured for template
            if not entry_dict.get('running_totals'):
                entry_dict['running_totals'] = {
                    'ground_training': 0.0,
                    'asel_time': 0.0, 
                    'day_time': 0.0,
                    'night_time': 0.0,
                    'sim_instrument': 0.0,
                    'dual_received': 0.0,
                    'pic_time': 0.0,
                    'cross_country': 0.0
                }
            template_entries.append(entry_dict)
        except Exception as e:
            logger.error(f"Error converting entry {i} to dict: {str(e)}")
            continue
    
    # Reverse the order so most recent flights appear first
    # Running totals are already calculated correctly in chronological order
    template_entries.reverse()
    logger.info(f"Successfully converted {len(template_entries)} entries to template data (reversed for display)")
    return template_entries

def convert_aircraft_to_template_data(aircraft_list):
    """Convert Aircraft objects to template-friendly dictionaries."""
    return [aircraft.to_dict() for aircraft in aircraft_list]

# Initialize the database only if it doesn't exist
def init_db_if_needed():
    """Initialize the database only if it doesn't exist."""
    if not os.path.exists('endorsements.db'):
        init_db()

def calculate_running_totals(entries):
    """Calculate running totals for each entry."""
    logger.info(f"Calculating running totals for {len(entries)} entries")
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
    for i, entry in enumerate(sorted_entries):
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
        
        # Debug: Log first few entries
        if i < 3:
            logger.info(f"Entry {i} ({entry.date.strftime('%Y-%m-%d')}): set running_totals = {entry.running_totals}")
    
    logger.info(f"Finished calculating running totals")
    return sorted_entries

def calculate_30_day_stats(entries):
    """Calculate statistics for the last 30 days."""
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_entries = [e for e in entries if e.date >= thirty_days_ago]
    return calculate_stats_for_entries(recent_entries)

def calculate_recent_experience(entries):
    """Calculate statistics for the last 30 days."""
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    # Filter entries for the last 30 days
    recent_entries = [e for e in entries if e.date >= thirty_days_ago]
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
        'total_time_tailwheel': sum(float(e.total_time) for e in entries if e.aircraft.gear_type == "fixed_tailwheel"),
        'total_time_tricycle': sum(float(e.total_time) for e in entries if e.aircraft.gear_type == "fixed_tricycle"),
        'total_time_asel': sum(float(e.total_time) for e in entries if e.aircraft.category_class == "airplane_single_engine_land"),
        'total_time_complex': sum(float(e.total_time) for e in entries if getattr(e.aircraft, 'complex_aircraft', False)),
        'total_time_high_performance': sum(float(e.total_time) for e in entries if getattr(e.aircraft, 'high_performance', False)),
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
    
    # Initialize default values
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
            
            # Work with objects for business logic
            entries_objects = importer.get_flight_entries()
            aircraft_objects = importer.get_aircraft_list()
            
            # Calculate running totals on objects
            entries_objects = calculate_running_totals(entries_objects)
            
            # Calculate statistics from objects
            stats = calculate_stats_for_entries([e for e in entries_objects if e.date.year == datetime.now().year])
            all_time = calculate_stats_for_entries(entries_objects)
            recent_experience = calculate_recent_experience(entries_objects)
            aircraft_stats = prepare_aircraft_stats(entries_objects)
            
            # Convert to template-friendly data
            entries = convert_entries_to_template_data(entries_objects)
            aircraft_list = convert_aircraft_to_template_data(aircraft_objects)
            
            # Get endorsements if student pilot
            if is_student_pilot:
                try:
                    endorsements = get_all_endorsements()
                    endorsements_dict = [e.to_dict() for e in endorsements]
                except Exception as e:
                    logger.warning(f"Could not load endorsements: {str(e)}")
                    endorsements_dict = []
            
            logger.info(f"Successfully prepared {len(entries)} entries for template rendering")
            
        except Exception as e:
            logger.error(f"Failed to reload uploaded logbook: {str(e)}", exc_info=True)
            flash(f'Failed to reload uploaded logbook: {str(e)}')
    
    return render_template('index.html', 
                         entries=entries,  # Now always dictionaries
                         stats=stats,
                         all_time_stats=all_time,
                         aircraft_stats=aircraft_stats,
                         aircraft_list=aircraft_list,  # Now always dictionaries
                         endorsements=endorsements_dict,
                         now=datetime.now().isoformat(),
                         current_year=datetime.now().year,
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
        
        # Work with objects for business logic
        entries_objects = importer.get_flight_entries()
        aircraft_objects = importer.get_aircraft_list()
        logger.info(f"Parsed {len(entries_objects)} flights and {len(aircraft_objects)} aircraft")
        
        if not entries_objects:
            logger.warning("No entries found in logbook")
            flash('No valid entries found in the logbook file')
            return redirect(url_for('index'))
        
        # Calculate running totals on objects
        logger.info("Calculating running totals")
        entries_objects = calculate_running_totals(entries_objects)
        
        # Calculate statistics from objects
        logger.info("Calculating statistics")
        stats = calculate_stats_for_entries([e for e in entries_objects if e.date.year == datetime.now().year])
        all_time = calculate_stats_for_entries(entries_objects)
        recent_experience = calculate_recent_experience(entries_objects)
        # Calculate aircraft statistics from entries
        aircraft_stats = prepare_aircraft_stats(entries_objects)
        
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

@app.route('/filter-flights', methods=['POST'])
def filter_flights():
    """Filter flights based on criteria and return rendered table HTML."""
    try:
        # Get filter criteria from request
        filters = request.get_json()
        logger.info(f"Received filter request: {filters}")
        
        # Get the logbook filename from session
        filename = session.get('logbook_filename')
        if not filename:
            return jsonify({'error': 'No logbook data found. Please upload a CSV file first.'}), 400
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'Logbook file not found. Please upload a CSV file again.'}), 400
        
        # Use ForeFlightImporter for MVC-compliant model access
        from src.services.importer import ForeFlightImporter
        importer = ForeFlightImporter(filepath)
        entries_objects = importer.get_flight_entries()
        
        if not entries_objects:
            return jsonify({'error': 'No valid entries found in logbook.'}), 400
        
        # Apply filters
        filtered_entries = apply_flight_filters(entries_objects, filters)
        logger.info(f"Filtered {len(entries_objects)} entries down to {len(filtered_entries)}")
        
        # Calculate running totals for filtered entries
        filtered_entries = calculate_running_totals(filtered_entries)
        
        # Convert to template data
        template_entries = convert_entries_to_template_data(filtered_entries)
        
        # Render just the table body HTML
        from flask import render_template_string
        table_html = render_template_string('''
            {% for entry in entries %}
            <tr id="entry-{{ loop.index }}" class="{% if entry['error_explanation'] %}has-error{% endif %}">
                <td class="flight-date">
                    <span class="disclosure-triangle" data-target="flight-details-{{ loop.index }}">▶</span>
                    {{ entry['date'].split('T')[0] if 'T' in entry['date'] else entry['date'] }}
                </td>
                <td class="route">{{ entry['departure']['identifier'] if entry['departure'] else '---' }} → {{ entry['destination']['identifier'] if entry['destination'] else '---' }}</td>
                <td>{{ entry['aircraft']['registration'] }}</td>
                <td>{{ "%.1f"|format(entry['total_time']) }}</td>
                <td>{{ "%.1f"|format(entry['conditions']['day']) }}/{{ "%.1f"|format(entry['conditions']['night']) }}</td>
                <td>{{ entry['landings_day'] + entry['landings_night'] }}</td>
                <td class="{% if entry['pilot_role'] == 'SPLIT' %}split-role-text{% endif %}">{{ entry['pilot_role'] }}</td>
                <td>{{ "%.1f"|format(entry['pic_time']) }}</td>
                <td>{{ "%.1f"|format(entry['dual_received']) }}</td>
                <td>
                    {% if entry['error_explanation'] %}
                    <span class="badge bg-danger" data-bs-toggle="tooltip" title="{{ entry['error_explanation'] }}">
                        Invalid
                    </span>
                    {% endif %}
                    {% if entry['conditions']['cross_country'] > 0 %}
                    <span class="badge badge-xc" data-bs-toggle="tooltip" title="Cross-country flight">
                        <i class="fas fa-plane"></i> XC
                    </span>
                    {% endif %}
                    {% if entry['conditions']['night'] > 0 %}
                    <span class="badge badge-night" data-bs-toggle="tooltip" title="Night flight">
                        <i class="fas fa-moon"></i> Night
                    </span>
                    {% endif %}
                    {% if entry['pic_time'] > 0 and entry['dual_received'] == 0 %}
                    <span class="badge badge-solo" data-bs-toggle="tooltip" title="Solo flight">
                        <i class="fas fa-user"></i> Solo
                    </span>
                    {% endif %}
                    {% if entry['dual_received']|float > 0 %}
                    <span class="badge badge-dual" data-bs-toggle="tooltip" title="Dual instruction received">
                        <i class="fas fa-users"></i> Dual
                    </span>
                    {% endif %}
                </td>
                <td class="text-end running-total">{{ "%.1f"|format(entry['running_totals']['ground_training']) if entry['running_totals']['ground_training'] else "0.0" }}</td>
                <td class="text-end running-total">{{ "%.1f"|format(entry['running_totals']['asel_time']) }}</td>
                <td class="text-end running-total">{{ "%.1f"|format(entry['running_totals']['cross_country']) if entry['running_totals']['cross_country'] else "0.0" }}</td>
                <td class="text-end running-total">{{ "%.1f"|format(entry['running_totals']['day_time']) }}</td>
                <td class="text-end running-total">{{ "%.1f"|format(entry['running_totals']['night_time']) }}</td>
                <td class="text-end running-total">{{ "%.1f"|format(entry['running_totals']['sim_instrument']) }}</td>
                <td class="text-end running-total">{{ "%.1f"|format(entry['running_totals']['dual_received']) }}</td>
                <td class="text-end running-total">{{ "%.1f"|format(entry['running_totals']['pic_time']) }}</td>
                <td class="d-none solo-time">{{ entry['solo_time'] }}</td>
                <td class="d-none xc-time">{{ entry['conditions']['cross_country'] }}</td>
                <td class="d-none instrument-time">{{ entry['conditions']['simulated_instrument'] + entry['conditions']['actual_instrument'] }}</td>
            </tr>
            <tr class="details-row">
                <td colspan="100%" id="flight-details-{{ loop.index }}">
                    <div class="details-grid">
                        <div class="detail-item">
                            <span class="detail-label">Aircraft Details</span>
                            <span class="detail-value">Registration: {{ entry['aircraft']['registration'] }}
Type: {{ entry['aircraft']['type'] }}
Category/Class: {{ entry['aircraft']['category_class'] }}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Route Information</span>
                            <span class="detail-value">Departure: {{ entry['departure']['identifier'] if entry['departure'] else 'N/A' }}
Destination: {{ entry['destination']['identifier'] if entry['destination'] else 'N/A' }}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Flight Times</span>
                            <span class="detail-value">Total: {{ entry['total_time'] }}
Day: {{ entry['conditions']['day'] }}
Night: {{ entry['conditions']['night'] }}
PIC: {{ entry['pic_time'] }}
Dual Received: {{ entry['dual_received'] }}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Landings</span>
                            <span class="detail-value">Day: {{ entry['landings_day'] }}
Night: {{ entry['landings_night'] }}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Running Totals</span>
                            <span class="detail-value">Ground: {{ entry['running_totals']['ground_training'] if entry['running_totals']['ground_training'] else "0.0" }}
ASEL: {{ entry['running_totals']['asel_time'] }}
Cross Country: {{ entry['running_totals']['cross_country'] if entry['running_totals']['cross_country'] else "0.0" }}
Day: {{ entry['running_totals']['day_time'] }}
Night: {{ entry['running_totals']['night_time'] }}
Sim Instrument: {{ entry['running_totals']['sim_instrument'] }}
Dual Received: {{ entry['running_totals']['dual_received'] }}
PIC: {{ entry['running_totals']['pic_time'] }}</span>
                        </div>
                        {% if entry['remarks'] %}
                        <div class="detail-item">
                            <span class="detail-label">Remarks</span>
                            <span class="detail-value">{{ entry['remarks'] }}</span>
                        </div>
                        {% endif %}
                    </div>
                </td>
            </tr>
            {% endfor %}
        ''', entries=template_entries)
        
        return jsonify({
            'success': True,
            'table_html': table_html,
            'total_entries': len(template_entries),
            'original_total': len(entries_objects)
        })
        
    except Exception as e:
        logger.error(f"Error filtering flights: {str(e)}")
        return jsonify({'error': f'Error filtering flights: {str(e)}'}), 500

def apply_flight_filters(entries, filters):
    """Apply flight filters based on the specified criteria."""
    logger.info(f"Applying filters: {filters}")
    
    if not filters or filters.get('all', True):
        logger.info("All filter selected or no filters, returning all entries")
        return entries
    
    filtered_entries = []
    
    for i, entry in enumerate(entries):
        include_entry = False
        
        # Primary filters (mutually exclusive) - determine base set
        pic_time = float(entry.pic_time)
        dual_received = float(entry.dual_received)
        
        # Check if any primary filters are selected
        primary_filters_selected = filters.get('pic', False) or filters.get('dual', False) or filters.get('solo', False)
        
        if primary_filters_selected:
            # PIC filter: flights where pilot was PIC
            if filters.get('pic', False) and pic_time > 0:
                include_entry = True
            
            # Dual filter: flights where dual instruction was received
            elif filters.get('dual', False) and dual_received > 0:
                include_entry = True
            
            # Solo filter: flights where pilot was PIC but no dual received
            elif filters.get('solo', False) and pic_time > 0 and dual_received == 0:
                include_entry = True
        else:
            # No primary filters selected, include all entries for modifier filtering
            include_entry = True
        
        # Apply modifier filters (these are additional requirements)
        if include_entry:
            # Night filter: must have night time
            if filters.get('night', False):
                night_time = float(entry.conditions.night)
                if night_time <= 0:
                    include_entry = False
                    logger.debug(f"Entry {i} excluded by night filter: night_time={night_time}")
            
            # Cross-country filter: must have cross-country time
            if filters.get('xc', False):
                xc_time = float(entry.conditions.cross_country)
                if xc_time <= 0:
                    include_entry = False
                    logger.debug(f"Entry {i} excluded by XC filter: xc_time={xc_time}")
            
            # Instrument filter: must have simulated or actual instrument time
            if filters.get('instrument', False):
                sim_instrument = float(entry.conditions.simulated_instrument)
                actual_instrument = float(entry.conditions.actual_instrument)
                instrument_time = sim_instrument + actual_instrument
                if instrument_time <= 0:
                    include_entry = False
                    logger.debug(f"Entry {i} excluded by instrument filter: sim={sim_instrument}, actual={actual_instrument}, total={instrument_time}")
        
        if include_entry:
            filtered_entries.append(entry)
            logger.debug(f"Entry {i} included: PIC={pic_time}, Dual={dual_received}, Night={float(entry.conditions.night)}, XC={float(entry.conditions.cross_country)}, Instrument={float(entry.conditions.simulated_instrument) + float(entry.conditions.actual_instrument)}")
    
    logger.info(f"Filtered {len(entries)} entries down to {len(filtered_entries)}")
    return filtered_entries

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
    parser.add_argument('--port', type=int, default=8081, help='Port to bind to')
    args = parser.parse_args()
    
    # Run the app
    app.run(host=args.host, port=args.port, debug=True)
