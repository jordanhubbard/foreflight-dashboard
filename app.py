from flask import Flask, render_template
import pandas as pd
from datetime import datetime, timedelta
import os

app = Flask(__name__)

def load_logbook_data():
    try:
        df = pd.read_csv('foreflight_logbook.csv')

        if df.empty:
            print("Warning: The logbook CSV is empty.")
            return pd.DataFrame()  # Safe empty DataFrame

        # Ensure Date is datetime
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

        # Convert numeric fields to numbers, replacing bad values with 0
        numeric_columns = ['TotalTime', 'Day', 'Night', 'Takeoffs', 'Landings', 'DualGiven', 'DualReceived', 'Solo']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        return df

    except FileNotFoundError:
        print("Error: foreflight_logbook.csv not found.")
        return pd.DataFrame()

    except pd.errors.EmptyDataError:
        print("Error: foreflight_logbook.csv is empty.")
        return pd.DataFrame()

    except pd.errors.ParserError:
        print("Error: foreflight_logbook.csv could not be parsed.")
        return pd.DataFrame()

    except Exception as e:
        print(f"Unexpected error while loading logbook data: {e}")
        return pd.DataFrame()

def validate_row(row):
    errors = []

    required_fields = ['Date', 'AircraftID', 'TotalTime', 'Takeoffs', 'Landings']
    for field in required_fields:
        if pd.isna(row[field]) or str(row[field]).strip() == '':
            errors.append(f"Missing {field}")

    numeric_fields = ['TotalTime', 'Day', 'Night', 'Takeoffs', 'Landings', 'DualGiven', 'DualReceived', 'Solo']
    for field in numeric_fields:
        try:
            if pd.notna(row[field]):
                float(row[field])
        except ValueError:
            errors.append(f"Invalid number in {field}")

    if pd.isna(row['Date']):
        errors.append("Invalid Date")

    return errors

def calculate_currency(df):
    recent_flights = df[df['Date'] >= datetime.now() - timedelta(days=90)]
    return {
        'day_hours': recent_flights['Day'].sum(),
        'night_hours': recent_flights['Night'].sum(),
        'takeoffs': recent_flights['Takeoffs'].sum(),
        'landings': recent_flights['Landings'].sum()
    }

def hours_per_aircraft(df):
    return df.groupby('AircraftID')['TotalTime'].sum().reset_index()

@app.route('/')
def index():
    df = load_logbook_data()
    df['Errors'] = df.apply(validate_row, axis=1)
    df['HasErrors'] = df['Errors'].apply(lambda x: len(x) > 0)

    bad_entries = df[df['HasErrors']]
    num_bad_entries = len(bad_entries)
    first_bad_entry_date = bad_entries['Date'].min() if num_bad_entries > 0 else None

    currency = calculate_currency(df)
    hours_by_aircraft = hours_per_aircraft(df)

    def flight_type(row):
        if row['Solo'] > 0:
            return 'solo'
        elif row['DualReceived'] > 0 or row['DualGiven'] > 0:
            return 'dual'
        return 'other'

    df['FlightType'] = df.apply(flight_type, axis=1)

    return render_template('index.html', 
                           currency=currency,
                           hours_by_aircraft=hours_by_aircraft.to_dict('records'),
                           flights=df.to_dict('records'),
                           num_bad_entries=num_bad_entries,
                           first_bad_entry_date=first_bad_entry_date)

if __name__ == '__main__':
    app.run(debug=True)
