from flask import Flask, render_template, request
import pandas as pd
import io

app = Flask(__name__)

def process_logbook(file):
    """ Read and process the uploaded logbook CSV file """
    df = pd.read_csv(file)

    # Ensure Date column is properly formatted
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

    # Summary information
    first_flight = df['Date'].min()
    last_flight = df['Date'].max()

    # Count flights per Tail Number
    tail_number_counts = df['AircraftID'].value_counts().reset_index()
    tail_number_counts.columns = ['Tail Number', 'Flights']

    most_popular_aircraft = tail_number_counts.iloc[0]['Tail Number'] if not tail_number_counts.empty else None

    # Calculate running totals
    df['RunningTotalTime'] = df['TotalTime'].cumsum()
    df['RunningDayTime'] = df['TotalTime'].cumsum() - df['Night'].cumsum()
    df['RunningNight'] = df['Night'].cumsum()
    df['RunningSimulatedInstrument'] = df['SimulatedInstrument'].cumsum()
    df['RunningGroundTraining'] = df['GroundTraining'].cumsum()
    df['RunningDualReceived'] = df['DualReceived'].cumsum()
    df['RunningPIC'] = df['PIC'].cumsum()
    df['RunningLandings'] = df['Landings'].cumsum()

    # Convert dataframe to list of dicts for rendering
    flights = df.to_dict(orient='records')

    return {
        'first_flight': first_flight,
        'last_flight': last_flight,
        'tail_number_counts': tail_number_counts,
        'most_popular_aircraft': most_popular_aircraft
    }, flights

@app.route('/', methods=['GET', 'POST'])
def index():
    summary = {}
    flights = []

    if request.method == 'POST' and 'file' in request.files:
        file = request.files['file']
        if file.filename.endswith('.csv'):
            summary, flights = process_logbook(io.StringIO(file.stream.read().decode('utf-8')))

    return render_template('index.html', summary=summary, flights=flights)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)
