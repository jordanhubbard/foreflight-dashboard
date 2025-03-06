# ForeFlight Logbook Dashboard

This Flask web app reads a ForeFlight logbook CSV file, displays summary statistics, tracks recent flight currency, and flags incomplete or incorrect log entries.

## Features

- Displays **3-month flight currency** (day/night hours, takeoffs/landings).
- Summarizes **hours per aircraft tail number**.
- **Highlights rows with errors** (missing dates, hours, or tail numbers).
- **Lists the first bad entry date for quick lookup in ForeFlight.**

## Installation

1. Clone this repository:
    ```bash
    git clone https://github.com/yourusername/foreflight-logbook-dashboard.git
    cd foreflight-logbook-dashboard
    ```

2. Create a virtual environment (optional but recommended):
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use: venv\Scripts\activate
    ```

3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1. Place your `foreflight_logbook.csv` file in the project root (same folder as `app.py`).
Note that this project creates a sample foreflight_logbook.csv file with a deliberate
error in it to test the validation function of the logbook importer.  You can simply
overwrite this file with your own logbook.

2. Run the app:
    ```bash
    python app.py
    ```

3. Open your browser and visit:
    ```
    http://localhost:5000
    ```

## Sample Data

A sample `foreflight_logbook.csv` is provided for testing.

---

## Sample Flight Row Colors

- **Green:** Solo flights
- **Red:** Dual instruction flights
- **Blue:** Other flights
- **Orange:** Rows with errors (missing data or invalid formats)

---

## License

This project is open-source under the BSD 2 clause License.
