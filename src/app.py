"""ForeFlight Logbook Manager web application."""

import csv
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta
from collections import defaultdict
from src.validate_csv import validate_logbook
from src.core.models import RunningTotals
import logging.handlers
import shutil

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure root logger
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create file handler
file_handler = logging.handlers.RotatingFileHandler(
    'logs/foreflight.log',
    maxBytes=1024*1024,  # 1MB
    backupCount=5
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logging.Formatter(
    '%(levelname)s - %(message)s'
))

# Get the root logger and add handlers
root_logger = logging.getLogger()
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)

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
        'pic_time': 0.0
    }
    
    # Sort entries by date in chronological order
    sorted_entries = sorted(entries, key=lambda x: x.date)
    
    # Calculate running totals for each entry
    for entry in sorted_entries:
        # Update running totals
        totals['ground_training'] += float(entry.ground_training) if hasattr(entry, 'ground_training') else 0.0
        totals['asel_time'] += float(entry.total_time) if entry.aircraft.category_class == "ASEL" else 0.0
        totals['day_time'] += float(entry.conditions.day)
        totals['night_time'] += float(entry.conditions.night)
        totals['sim_instrument'] += float(entry.conditions.simulated_instrument)
        totals['dual_received'] += float(entry.dual_received)
        totals['pic_time'] += float(entry.total_time) if entry.pilot_role == 'PIC' else 0.0
        
        # Create RunningTotals instance with rounded values
        entry.running_totals = RunningTotals(**{k: round(v, 1) for k, v in totals.items()})
    
    return sorted_entries

def calculate_30_day_stats(entries):
    """Calculate statistics for the last 30 days."""
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_entries = [e for e in entries if e.date >= thirty_days_ago]
    
    stats = {
        'total_time': sum(float(e.total_time) for e in recent_entries),
        'total_day': sum(float(e.conditions.day) for e in recent_entries),
        'total_night': sum(float(e.conditions.night) for e in recent_entries),
        'total_pic': sum(float(e.total_time) if e.pilot_role == 'PIC' else 0 for e in recent_entries),
        'total_sim_instrument': sum(float(e.conditions.simulated_instrument) for e in recent_entries),
        'total_dual_received': sum(float(e.dual_received) for e in recent_entries),
        'total_takeoffs': sum(e.landings_day + e.landings_night for e in recent_entries),
        'total_landings': sum(e.landings_day + e.landings_night for e in recent_entries)
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
    """Display the main page."""
    return render_template('index.html', entries=[], stats=None, aircraft_stats=None)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and validation."""
    logger.debug("\n=== Starting File Upload Processing ===")
    
    if 'file' not in request.files:
        logger.error("No file part in request")
        flash('No file uploaded')
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        logger.error("No file selected")
        flash('No file selected')
        return redirect(url_for('index'))
    
    if not file.filename.endswith('.csv'):
        logger.error("Invalid file type")
        flash('Only CSV files are allowed')
        return redirect(url_for('index'))
    
    try:
        # Save the file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        logger.debug(f"Saving file to {filepath}")
        file.save(filepath)
        
        # Make a copy of the file for debugging
        debug_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'debug_' + filename)
        shutil.copy2(filepath, debug_filepath)
        logger.debug(f"Created debug copy at {debug_filepath}")
        
        # Read and log the first few lines of the file
        logger.debug("\nFile contents preview:")
        with open(filepath, 'r') as f:
            for i, line in enumerate(f):
                if i < 10:
                    logger.debug(f"Line {i+1}: {line.strip()}")
                else:
                    break
        
        # Validate the logbook
        logger.debug("\n=== Starting Logbook Validation ===")
        entries = validate_logbook(filepath)
        logger.debug(f"\nValidation complete. Found {len(entries)} entries")
        
        if len(entries) == 0:
            logger.error("No valid entries found in the logbook")
            flash('No valid entries found in the logbook. Please check the file format.')
            return redirect(url_for('index'))
        
        # Calculate running totals
        logger.debug("\n=== Calculating Running Totals ===")
        entries = calculate_running_totals(entries)
        
        # Calculate statistics
        logger.debug("\n=== Calculating Statistics ===")
        stats = calculate_30_day_stats(entries)
        aircraft_stats = prepare_aircraft_stats(entries)
        
        # Clean up the uploaded file
        logger.debug(f"\nCleaning up uploaded file: {filepath}")
        os.remove(filepath)
        
        # Log detailed information about what we're passing to the template
        logger.debug("\n=== Template Data ===")
        logger.debug(f"Stats: {stats}")
        logger.debug(f"Aircraft stats: {aircraft_stats}")
        logger.debug(f"Number of entries: {len(entries)}")
        if entries:
            logger.debug("\nFirst entry details:")
            entry = entries[0]
            logger.debug(f"  Date: {entry.date}")
            logger.debug(f"  Route: {entry.departure.identifier} -> {entry.destination.identifier}")
            logger.debug(f"  Aircraft: {entry.aircraft.registration}")
            logger.debug(f"  Total time: {entry.total_time}")
            logger.debug(f"  Day/Night: {entry.conditions.day}/{entry.conditions.night}")
            logger.debug(f"  Landings: Day={entry.landings_day}, Night={entry.landings_night}")
            logger.debug(f"  Running totals: {entry.running_totals}")
        
        try:
            # Show the results
            logger.debug("\n=== Rendering Template ===")
            return render_template('index.html', 
                                entries=entries, 
                                stats=stats, 
                                aircraft_stats=aircraft_stats)
        except Exception as template_error:
            logger.error(f"\nTemplate rendering error: {str(template_error)}", exc_info=True)
            flash('Error rendering results template')
            return redirect(url_for('index'))
    
    except Exception as e:
        logger.error(f"\nError processing file: {str(e)}", exc_info=True)
        flash(f'Error processing file: {str(e)}')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.debug = True
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(host='0.0.0.0', port=5050) 
