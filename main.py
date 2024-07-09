# ./main.py
from flask import Flask, request, send_from_directory, jsonify
import csv
from datetime import datetime
import json
import re
import logging
import os

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

TIMESHEET_FILE = 'timesheet.csv'
PROJECTS_FILE = 'projects.csv'

TIME_REGEX = re.compile(r'^([01]\d|2[0-3]):([0-5]\d)$')

@app.route('/')
def index():
    logger.debug("Index route called")
    if app.config.get('TESTING'):
        # This branch will be taken during testing
        return app.send_static_file('index.html')
    else:
        # This branch will be taken in production
        return send_from_directory('.', 'index.html')

@app.route('/projects')
def get_projects():
    logger.debug("Get projects route called")
    try:
        with open(PROJECTS_FILE, 'r') as f:
            reader = csv.DictReader(f)
            projects = list(reader)
        logger.debug(f"Projects loaded: {projects}")
        return json.dumps(projects), 200, {'Content-Type': 'application/json'}
    except Exception as e:
        logger.error(f"Error loading projects: {str(e)}")
        return json.dumps({"error": "Failed to load projects"}), 500, {'Content-Type': 'application/json'}




@app.route('/submit_entry', methods=['POST'])
def submit_entry():
    try:
        app.logger.info(f"Received form data: {request.form}")

        project_id = request.form.get('project')
        date = request.form.get('date')
        start_time = request.form.get('startTime')
        end_time = request.form.get('endTime')
        break_time = request.form.get('break', '0')
        comment = request.form.get('comment', '')

        # Validate required fields
        missing_fields = []
        if not project_id:
            missing_fields.append('project')
        if not date:
            missing_fields.append('date')
        if not start_time:
            missing_fields.append('startTime')
        if not end_time:
            missing_fields.append('endTime')

        if missing_fields:
            return f"Missing required fields: {', '.join(missing_fields)}", 400

        # Validate date format
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return "Invalid date format. Please use YYYY-MM-DD.", 400

        # Validate time format and order
        if not TIME_REGEX.match(start_time) or not TIME_REGEX.match(end_time):
            return "Invalid time format. Please use HH:MM (24-hour format with leading zeros).", 400

        start = datetime.strptime(start_time, '%H:%M').time()
        end = datetime.strptime(end_time, '%H:%M').time()
        if end <= start:
            return "End time must be after start time.", 400

        with open(TIMESHEET_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([project_id, date, start_time, end_time, break_time, comment])

        return "Time entry submitted successfully!"
    except Exception as e:
        app.logger.error(f"Error submitting entry: {str(e)}")
        return f"Error submitting entry: {str(e)}", 500


@app.route('/recent_entries')
def get_recent_entries():
    try:
        with open(TIMESHEET_FILE, 'r') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header row
            entries = list(reader)

        # Sort entries by date and time (most recent first)
        entries.sort(key=lambda x: (x[1], x[2]), reverse=True)

        # Get the 5 most recent entries
        recent_entries = entries[:5]

        # Load project names
        with open(PROJECTS_FILE, 'r') as f:
            projects = {row['project_id']: row['project_name'] for row in csv.DictReader(f)}

        # Format entries with project names and calculate hours
        formatted_entries = []
        for entry in recent_entries:
            project_id, date, start_time, end_time, break_time, comment = entry
            project_name = projects.get(project_id, 'Unknown Project')

            start = datetime.strptime(start_time, '%H:%M')
            end = datetime.strptime(end_time, '%H:%M')
            duration = (end - start).total_seconds() / 3600  # Convert to hours
            duration -= float(break_time) / 60  # Subtract break time (converted to hours)

            formatted_entries.append({
                'project_name': project_name,
                'date': date,
                'start_time': start_time,
                'end_time': end_time,
                'hours': round(duration, 2)
            })

        return jsonify(formatted_entries)
    except Exception as e:
        app.logger.error(f"Error fetching recent entries: {str(e)}")
        return jsonify({"error": "Failed to fetch recent entries"}), 500


if __name__ == '__main__':
    app.run(debug=True)