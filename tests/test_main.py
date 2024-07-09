# ./tests/test_main.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import mock_open
from io import StringIO
from flask import Flask
from main import app
import json
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture
def mock_csv_files(monkeypatch):
    mock_timesheet = StringIO("project_id,date,start_time,end_time,break,comment\n")
    mock_projects = StringIO("project_id,project_name,hours_procured\n1,Test Project,100\n2,Another Project,200\n")
    mock_index = b"<html><body>Mock Index</body></html>"

    def mock_open_func(filename, mode='r', *args, **kwargs):
        logger.debug(f"Mock open called with filename: {filename}, mode: {mode}")
        if filename == 'timesheet.csv':
            return StringIO() if 'a' in mode else mock_timesheet
        elif filename == 'projects.csv':
            return mock_projects
        logger.warning(f"Unexpected file open: {filename}")
        return mock_open()(filename, mode, *args, **kwargs)

    monkeypatch.setattr('builtins.open', mock_open_func)

    # Mock Flask's send_static_file method
    def mock_send_static_file(self, filename):
        logger.debug(f"Mock send_static_file called with filename: {filename}")
        if filename == 'index.html':
            return mock_index
        return b''

    monkeypatch.setattr(Flask, 'send_static_file', mock_send_static_file)

@pytest.fixture
def client(mock_csv_files):
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_route(client):
    response = client.get('/')
    logger.debug(f"Index route response: {response.data}")
    assert response.status_code == 200
    assert b"Mock Index" in response.data

def test_get_projects(client):
    response = client.get('/projects')
    logger.debug(f"Get projects response: {response.data}")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]['project_id'] == '1'
    assert data[0]['project_name'] == 'Test Project'
    assert data[0]['hours_procured'] == '100'
    assert data[1]['project_id'] == '2'
    assert data[1]['project_name'] == 'Another Project'
    assert data[1]['hours_procured'] == '200'


def test_submit_entry_success(client):
    data = {
        'project': '1',
        'date': datetime.now().strftime('%Y-%m-%d'),
        'startTime': '09:00',
        'endTime': '17:00',
        'break': '60',
        'comment': 'Test entry'
    }
    response = client.post('/submit_entry', data=data)
    assert response.status_code == 200
    assert b"Time entry submitted successfully!" in response.data


def test_submit_entry_missing_fields(client):
    data = {
        'project': '1',
        'date': datetime.now().strftime('%Y-%m-%d'),
        'startTime': '09:00',
        # Missing endTime
        'break': '60',
        'comment': 'Test entry'
    }
    response = client.post('/submit_entry', data=data)
    assert response.status_code == 400
    assert b"Missing required fields: endTime" in response.data


def test_submit_entry_invalid_date(client):
    data = {
        'project': '1',
        'date': 'invalid-date',
        'startTime': '09:00',
        'endTime': '17:00',
        'break': '60',
        'comment': 'Test entry'
    }
    response = client.post('/submit_entry', data=data)
    assert response.status_code == 400
    assert b"Invalid date format" in response.data


def test_submit_entry_invalid_time_order(client):
    data = {
        'project': '1',
        'date': datetime.now().strftime('%Y-%m-%d'),
        'startTime': '17:00',
        'endTime': '09:00',
        'break': '60',
        'comment': 'Test entry'
    }
    response = client.post('/submit_entry', data=data)
    assert response.status_code == 400
    assert b"End time must be after start time" in response.data


def test_submit_entry_invalid_time_format(client):
    data = {
        'project': '1',
        'date': datetime.now().strftime('%Y-%m-%d'),
        'startTime': '9:00',  # Should be 09:00
        'endTime': '17:00',
        'break': '60',
        'comment': 'Test entry'
    }
    response = client.post('/submit_entry', data=data)
    assert response.status_code == 400
    assert b"Invalid time format" in response.data

# This test is now commented out as we decided not to implement future date checking
# def test_submit_entry_future_date(client):
#     future_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
#     data = {
#         'project': '1',
#         'date': future_date,
#         'startTime': '09:00',
#         'endTime': '17:00',
#         'break': '60',
#         'comment': 'Future entry'
#     }
#     response = client.post('/submit_entry', data=data)
#     assert response.status_code == 400
#     assert b"Cannot submit entries for future dates" in response.data