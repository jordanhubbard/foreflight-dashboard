"""ForeFlight Logbook Manager web application."""

import csv
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from src.validate_csv import validate_logbook
from src.core.models import RunningTotals
import logging.handlers
import shutil

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

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Required for flash messages
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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
    aircraft_stats = defaultdict(lambda: {'count': 0, 'total_time': 0.0, 'registration': '', 'type': ''})
    
    for entry in entries:
        aircraft = entry.aircraft
        key = aircraft.registration
        aircraft_stats[key]['count'] += 1
        aircraft_stats[key]['total_time'] += float(entry.total_time)
        aircraft_stats[key]['registration'] = aircraft.registration
        aircraft_stats[key]['type'] = aircraft.type
    
    # Convert to list and sort by count
    aircraft_list = [
        {
            'registration': stats['registration'],
            'type': stats['type'],
            'count': stats['count'],
            'total_time': stats['total_time']
        }
        for stats in aircraft_stats.values()
    ]
    return sorted(aircraft_list, key=lambda x: x['count'], reverse=True)

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html', entries=None, stats=None, all_time_stats=None, aircraft_stats=None)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and validation."""
    if 'file' not in request.files:
        flash('No file uploaded')
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('index'))
    
    if not file.filename.endswith('.csv'):
        flash('Only CSV files are allowed')
        return redirect(url_for('index'))
    
    try:
        # Save uploaded file
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        file.save(filepath)
        
        # Create debug copy
        debug_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'debug_' + secure_filename(file.filename))
        shutil.copy2(filepath, debug_filepath)
        
        # Validate entries
        entries = validate_logbook(filepath)
        
        # Calculate running totals
        entries = calculate_running_totals(entries)
        
        # Calculate statistics
        stats = calculate_stats_for_entries([e for e in entries if e.date.year == datetime.now().year])
        all_time_stats = calculate_stats_for_entries(entries)
        aircraft_stats = prepare_aircraft_stats(entries)
        
        # Clean up uploaded file
        os.remove(filepath)
        
        return render_template('index.html',
                             entries=entries,
                             stats=stats,
                             all_time_stats=all_time_stats,
                             aircraft_stats=aircraft_stats)
    except Exception as e:
        flash(f'Error processing file: {str(e)}')
        return redirect(url_for('index'))

if __name__ == '__main__':
    # Enable hot reloading
    app.debug = True
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    
    # Run the app
    app.run(host='0.0.0.0', port=5050, debug=True) 
