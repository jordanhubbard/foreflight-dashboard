from flask import Flask, render_template
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

app = Flask(__name__)

LOGBOOK_FILE = 'foreflight_logbook.csv'

def load_flight_data():
    df = pd.read_csv(LOGBOOK_FILE)
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

def calculate_fill_rates(flight_data):
    total_rows = len(flight_data)
    return {col: (flight_data[col].notna().sum() / total_rows) * 100 for col in flight_data.columns}

def detect_anomalies(flight_data, threshold=3.0):
    anomalies = {}
    for column in flight_data.select_dtypes(include=[np.number]).columns:
        mean = flight_data[column].mean()
        std_dev = flight_data[column].std()
        if pd.isna(mean) or pd.isna(std_dev) or std_dev == 0:
            continue
        outliers = flight_data[(flight_data[column] < mean - threshold * std_dev) |
                               (flight_data[column] > mean + threshold * std_dev)]
        if not outliers.empty:
            anomalies[column] = {"mean": mean, "std_dev": std_dev, "outliers": outliers}
    return anomalies

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

def enhance_flight_data(flight_data, anomalies):
    running_totals = {col: 0.0 for col in ['DualReceived', 'Night', 'SimulatedInstrument', 'PIC', 'DayLandingsFullStop', 'NightLandingsFullStop']}
    anomaly_rows = set()
    for column_data in anomalies.values():
        anomaly_rows.update(column_data['outliers'].index)

    enhanced_rows = []
    for idx, row in flight_data.iterrows():
        for key in running_totals:
            running_totals[key] += row.get(key, 0)
        enhanced_row = row.to_dict()
        for key, value in running_totals.items():
            enhanced_row[f'Running{key}'] = value
        enhanced_row['is_anomaly'] = idx in anomaly_rows
        for key, value in enhanced_row.items():
            if isinstance(value, float):
                enhanced_row[key] = f"{value:.1f}"
        enhanced_rows.append(enhanced_row)
    return enhanced_rows

@app.route('/')
def display_logbook():
    flight_data = load_flight_data()
    fill_rates = calculate_fill_rates(flight_data)
    anomalies = detect_anomalies(flight_data)
    summary = calculate_summary(flight_data)
    enhanced_flights = enhance_flight_data(flight_data, anomalies)

    most_popular_aircraft = summary['tail_number_counts'].iloc[0]['Tail Number']
    return render_template('index.html',
                           summary=summary,
                           flights=enhanced_flights,
                           most_popular_aircraft=most_popular_aircraft,
                           fill_rates=fill_rates,
                           anomalies=anomalies)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
