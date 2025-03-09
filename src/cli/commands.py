"""Command-line interface for the ForeFlight Logbook Manager."""

import click
import uvicorn
from pathlib import Path
import json
from datetime import datetime
import sys
from typing import Dict, Any, List

from .importer import ForeFlightImporter
from .api import app
from .validation import validate_csv

@click.group()
def cli():
    """ForeFlight Logbook Manager CLI."""
    pass

@click.command()
@click.option('--host', default='127.0.0.1', help='Host to bind to')
@click.option('--port', default=8000, help='Port to bind to')
@click.option('--reload', is_flag=True, help='Enable auto-reload')
def serve(host: str, port: int, reload: bool):
    """Start the web API server."""
    uvicorn.run(
        "src.api:app",
        host=host,
        port=port,
        reload=reload
    )

@click.command()
def init():
    """Initialize the application configuration."""
    env_file = Path('.env')
    if not env_file.exists():
        env_content = """# ForeFlight API Configuration
FOREFLIGHT_API_KEY=your_api_key_here
FOREFLIGHT_API_SECRET=your_api_secret_here
FOREFLIGHT_API_BASE_URL=https://api.foreflight.com/

# Database Configuration
DATABASE_URL=sqlite:///logbook.db

# Logging Configuration
LOG_LEVEL=INFO
"""
        env_file.write_text(env_content)
        click.echo("Created .env file with default configuration")
    else:
        click.echo(".env file already exists")

    # Create logs directory
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    click.echo("Created logs directory")

@click.command()
@click.argument('csv_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output JSON file path')
def import_csv(csv_file: str, output: str):
    """Import a ForeFlight logbook CSV file.
    
    CSV_FILE: Path to the ForeFlight logbook export CSV file
    """
    try:
        importer = ForeFlightImporter(csv_file)
        entries = importer.import_entries()
        
        # Convert entries to JSON
        entries_json = [entry.model_dump() for entry in entries]
        
        # If output file specified, write to file
        if output:
            output_path = Path(output)
            output_path.write_text(json.dumps(entries_json, indent=2, default=str))
            click.echo(f"Imported {len(entries)} entries to {output}")
        else:
            # Print summary to console
            click.echo(f"Successfully imported {len(entries)} entries")
            click.echo("\nSummary:")
            
            # Calculate some basic statistics
            total_time = sum(entry.total_time for entry in entries)
            pic_time = sum(entry.total_time for entry in entries if entry.pilot_role == "PIC")
            dual_received = sum(entry.total_time for entry in entries if entry.pilot_role == "Dual Received")
            
            click.echo(f"Total flight time: {total_time:.1f} hours")
            click.echo(f"PIC time: {pic_time:.1f} hours")
            click.echo(f"Dual received: {dual_received:.1f} hours")
            
            # Show date range
            dates = [entry.date for entry in entries]
            if dates:
                click.echo(f"Date range: {min(dates).date()} to {max(dates).date()}")
            
            # Show aircraft types
            aircraft_types = set(entry.aircraft.type for entry in entries)
            click.echo("\nAircraft types:")
            for ac_type in sorted(aircraft_types):
                type_time = sum(e.total_time for e in entries if e.aircraft.type == ac_type)
                click.echo(f"  {ac_type}: {type_time:.1f} hours")
                
    except Exception as e:
        click.echo(f"Error importing CSV: {str(e)}", err=True)
        raise click.Abort()

@click.command()
@click.argument('csv_path', type=click.Path(exists=True))
def validate(csv_path):
    """Validate a ForeFlight CSV file and show detailed results."""
    result = validate_csv(csv_path)
    
    # Print results in a readable format
    click.echo("\nForeFlight CSV Validation Results")
    click.echo("=" * 40)
    
    click.echo(f"\nStatus: {'✓ Success' if result['success'] else '✗ Failed'}")
    click.echo(f"Stage: {result['stage']}")
    
    if result['error']:
        click.echo(f"\nError: {result['error']}")
    
    if result['details']:
        click.echo("\nDetails:")
        click.echo(f"- Total lines: {result['details']['total_lines']}")
        click.echo(f"- Empty lines: {result['details']['empty_lines']}")
        
        click.echo("\nFirst few lines:")
        for i, line in enumerate(result['details']['sample_lines'], 1):
            click.echo(f"{i}: {line}")
        
        click.echo("\nSections:")
        for section, info in result['details']['sections'].items():
            status = "✓" if info['found'] else "✗"
            line_info = f"(line {info['line']})" if info['found'] else ""
            click.echo(f"- {status} {section} {line_info}")
        
        if 'aircraft' in result['details']:
            click.echo("\nAircraft Data:")
            click.echo(f"- Rows: {result['details']['aircraft']['rows']}")
            click.echo(f"- Columns: {', '.join(result['details']['aircraft']['columns'])}")
            click.echo("- Sample data:")
            for row in result['details']['aircraft']['sample']:
                click.echo(f"  {row}")
        
        if 'flights' in result['details']:
            click.echo("\nFlights Data:")
            click.echo(f"- Rows: {result['details']['flights']['rows']}")
            click.echo(f"- Columns: {', '.join(result['details']['flights']['columns'])}")
            click.echo("- Sample data:")
            for row in result['details']['flights']['sample']:
                click.echo(f"  {row}")
        
        if 'entries' in result['details']:
            click.echo("\nProcessed Entries:")
            click.echo(f"- Total entries: {result['details']['entries']['count']}")
            click.echo("- Sample entries:")
            for entry in result['details']['entries']['sample']:
                click.echo(f"  {entry}")
    
    sys.exit(0 if result['success'] else 1)

cli.add_command(serve)
cli.add_command(init)
cli.add_command(import_csv)
cli.add_command(validate)

if __name__ == '__main__':
    cli() 