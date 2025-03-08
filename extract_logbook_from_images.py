import argparse
import csv
import openai
import os
import json
import base64
from datetime import datetime

def extract_text_from_image(image_path):
    """Uses OpenAI's API to extract text from an image."""
    client = openai.OpenAI()
    with open(image_path, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode("utf-8")
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "Extract structured tabular flight log data from the provided image, maintaining column integrity."},
                {"role": "user", "content": [{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + image_base64}}]}
            ],
            max_tokens=4096
        )
    return response.choices[0].message.content

def parse_table_data(text, year):
    """Parses extracted text into structured table data with improved row detection."""
    rows = []
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    if len(lines) < 2:
        return rows  # Not enough data
    
    # Identify header by looking for the first row with multiple space-separated words
    header = lines[0].split()
    if len(header) < 5:  # If the first row doesn't look like a valid header, check the next row
        header = lines[1].split()
        data_start_index = 2
    else:
        data_start_index = 1
    
    # Ensure consistent column count
    expected_columns = len(header)
    valid_rows = []
    
    for line in lines[data_start_index:]:
        parts = line.split()
        if len(parts) >= expected_columns - 2:  # Allow slight variations in column count
            row = {header[i]: parts[i] if i < len(parts) else "" for i in range(expected_columns)}
            row["Year"] = year  # Ensure Year is always included
            valid_rows.append(row)
    
    return valid_rows

def write_to_csv(output_file, data):
    """Writes structured data to a CSV file, dynamically handling columns."""
    if not data:
        print("No valid data extracted.")
        return
    
    # Filter out unexpected fields
    expected_fields = set(["Year", "Date", "Aircraft Make and Model", "Aircraft Identifier", "Origin Airport", "Destination Airport", "Comments", "Instrument Approaches", "Total Landings", "Single-Engine Hours", "Multi-Engine Hours", "Cross-Country Hours", "Daylight Hours", "Night Hours", "Actual Instrument Hours", "Simulated Instrument Hours", "Ground Trainer Hours", "Dual Instruction Hours Received", "Pilot in Command Hours", "Solo Flight Hours", "Total Duration"])
    
    cleaned_data = []
    for row in data:
        cleaned_row = {key: value for key, value in row.items() if key in expected_fields}
        cleaned_data.append(cleaned_row)
    
    fieldnames = list(expected_fields)
    with open(output_file, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cleaned_data)

def main():
    parser = argparse.ArgumentParser(description="Extract table data from flight log images and save to CSV.")
    parser.add_argument("images", nargs='+', help="Paths to image files.")
    parser.add_argument("--output", default="flight_log.csv", help="Output CSV file name.")
    args = parser.parse_args()

    all_rows = []
    for image_path in args.images:
        print(f"Processing {image_path}...")
        retry_count = 0
        while retry_count < 3:
            extracted_text = extract_text_from_image(image_path)
            year = extracted_text.split("\n")[0].strip()  # Assume the year is the first line
            structured_data = parse_table_data(extracted_text, year)
            if len(structured_data) >= 4:
                all_rows.extend(structured_data)
                break
            else:
                print(f"Warning: Less than 4 rows found in {image_path}, retrying... ({retry_count + 1}/3)")
                retry_count += 1
    
    write_to_csv(args.output, all_rows)
    print(f"Data saved to {args.output}")

if __name__ == "__main__":
    main()
