from flask import Flask, render_template
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

app = Flask(__name__)

LOGBOOK_FILE = 'foreflight_logbook.csv'

def load_flight_data():
    df = pd.read_csv(LOGBOOK_FILE)

    # Locate start of Flights Table
    flight_table_start = None
    for i, row in df.iterrows():
        if row.astype(str).str.contains('Flights Table', case=False, na=False).any():
            flight_table_start = i + 2
            break

    if flight_table_start is None:
        raise ValueError("Could not find 'Flights Table' in the file.")

    flight_data = pd.read_csv(LOGBOOK_FILE, skiprows=flight_table_start)

    flight_data['Date'] = pd.to_datetime(flight_data['Date'], errors='coerce')
    flight_data = flight_data.dropna(subset=['Date'])

    numeric_cols = flight_data.select_dtypes(include=[np.number]).columns
    flight_data[numeric_cols] = flight_data[numeric_cols].fillna(0)

    return flight_data.sort_values('Date')

def calculate_summary(flight_data):
    first_flight = flight_data['Date'].min()
    last_flight = flight_data['Date'].max()

    tail_number_counts = flight_data['AircraftID'].value_counts().reset_index()
    tail_number_counts.columns = ['Tail Number', 'Flights']

    cutoff_date = last_flight - timedelta(days=30)
    recent_flights = flight_data[flight_data['Date'] >= cutoff_date]

    return {
        'first_flight': first_flight,
        'last_flight': last_flight,
        'tail_number_counts': tail_number_counts,
        'solo_hours_last_30': recent_flights['Solo'].sum(),
        'dual_hours_last_30': recent_flights['DualReceived'].sum()
    }

def enhance_flight_data(flight_data):
    running_totals = {
        'TotalTime': 0.0,
        'DayTime': 0.0,
        'Night': 0.0,
        'SimulatedInstrument': 0.0,
        'GroundTraining': 0.0,
        'DualReceived': 0.0,
        'PIC': 0.0,
        'Landings': 0
    }

    enhanced_rows = []
    for _, row in flight_data.iterrows():
        day_time = max(row['TotalTime'] - row['Night'], 0)

        running_totals['TotalTime'] += row['TotalTime']
        running_totals['DayTime'] += day_time
        running_totals['Night'] += row['Night']
        running_totals['SimulatedInstrument'] += row['SimulatedInstrument']
        running_totals['GroundTraining'] += row['GroundTraining']
        running_totals['DualReceived'] += row['DualReceived']
        running_totals['PIC'] += row['PIC']
        running_totals['Landings'] += row['DayLandingsFullStop'] + row['NightLandingsFullStop']

        enhanced_row = row.to_dict()

        for key, value in running_totals.items():
            enhanced_row[f'Running{key}'] = round(value, 1)

        # Highlight if no landings, positive flight time, and no PIC or Dual Received
        if (row['DayLandingsFullStop'] + row['NightLandingsFullStop'] == 0 and 
            row['TotalTime'] > 0 and
            row['PIC'] == 0 and 
            row['DualReceived'] == 0):
            enhanced_row['highlight'] = 'anomaly'
        else:
            enhanced_row['highlight'] = ''

        for key, value in enhanced_row.items():
            if isinstance(value, float):
                enhanced_row[key] = f"{value:.1f}"

        enhanced_rows.append(enhanced_row)

    return enhanced_rows

@app.route('/')
def display_logbook():
    flight_data = load_flight_data()
    summary = calculate_summary(flight_data)
    enhanced_flights = enhance_flight_data(flight_data)

    most_popular_aircraft = summary['tail_number_counts'].iloc[0]['Tail Number']

    return render_template('index.html',
                           summary=summary,
                           flights=enhanced_flights,
                           most_popular_aircraft=most_popular_aircraft)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)
