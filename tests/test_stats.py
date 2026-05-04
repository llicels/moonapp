import pytest
import sqlite3
import os
import tempfile
from datetime import datetime, date, timedelta
from app import app as flask_app

@pytest.fixture
def client(monkeypatch):
    # Create a temporary database file
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Monkeypatch the DB_PATH in the app module
    import app
    monkeypatch.setattr(app, "DB_PATH", db_path)
    
    # Initialize the database
    app.init_db()
    
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)
    for suffix in ['-shm', '-wal']:
        if os.path.exists(db_path + suffix):
            os.unlink(db_path + suffix)

def test_single_session_save(client):
    response = client.post('/save', json={'duration': 25})
    assert response.status_code == 200
    assert response.json['status'] == 'saved'
    
    response = client.get('/stats')
    data = response.json
    assert data['total_minutes'] == 25
    assert len(data['sessions']) == 1

def test_multiple_sessions_same_day(client):
    client.post('/save', json={'duration': 25})
    client.post('/save', json={'duration': 30})
    client.post('/save', json={'duration': 45})
    
    response = client.get('/stats')
    data = response.json
    assert data['total_minutes'] == 100
    assert len(data['sessions']) == 3

def test_invalid_duration(client):
    response = client.post('/save', json={'duration': 0})
    assert response.status_code == 400
    
    response = client.post('/save', json={'duration': -5})
    assert response.status_code == 400

def test_weekly_stats(client):
    # Save sessions for today and yesterday
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    
    # We need to manually insert into DB to simulate different dates
    import app
    with app.get_db_connection() as conn:
        conn.execute('INSERT INTO sessions (date, duration, created_at) VALUES (?, ?, ?)',
                     (today, 30, datetime.now().isoformat()))
        conn.execute('INSERT INTO sessions (date, duration, created_at) VALUES (?, ?, ?)',
                     (yesterday, 45, (datetime.now() - timedelta(days=1)).isoformat()))
        conn.commit()
    
    response = client.get('/weekly-stats')
    assert response.status_code == 200
    data = response.json
    assert len(data) == 7
    
    # Check today's stats (last element)
    assert data[-1]['minutes'] == 30
    # Check yesterday's stats (second to last element)
    assert data[-2]['minutes'] == 45

def test_empty_database(client):
    response = client.get('/stats')
    data = response.json
    assert data['total_minutes'] == 0
    assert len(data['sessions']) == 0
    
    response = client.get('/weekly-stats')
    data = response.json
    assert len(data) == 7
    for day in data:
        assert day['minutes'] == 0

def test_session_update(client):
    # Create a session
    response = client.post('/save', json={'duration': 25})
    session_id = response.json['session_id']
    
    # Update the same session
    response = client.post('/save', json={'duration': 40, 'session_id': session_id})
    assert response.status_code == 200
    assert response.json['status'] == 'saved'
    
    # Verify total minutes is now 40, not 25+40
    response = client.get('/stats')
    assert response.json['total_minutes'] == 40
    assert len(response.json['sessions']) == 1

def test_stats_only_for_today(client):
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    
    import app
    with app.get_db_connection() as conn:
        # Session from yesterday
        conn.execute('INSERT INTO sessions (date, duration, created_at) VALUES (?, ?, ?)',
                     (yesterday, 60, (datetime.now() - timedelta(days=1)).isoformat()))
        # Session from today
        conn.execute('INSERT INTO sessions (date, duration, created_at) VALUES (?, ?, ?)',
                     (today, 30, datetime.now().isoformat()))
        conn.commit()
    
    # Verify today's stats only show today's 30 mins
    response = client.get('/stats')
    assert response.json['total_minutes'] == 30
    assert len(response.json['sessions']) == 1
    assert response.json['sessions'][0]['duration'] == 30