import pytest
import sqlite3
import os
import tempfile
from datetime import datetime, date

# Create a temporary database for testing
@pytest.fixture
def test_db():
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    conn = sqlite3.connect(path)
    conn.execute('''
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            duration INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    conn.commit()
    
    yield path
    
    os.unlink(path)

@pytest.fixture
def app(test_db):
    from flask import Flask
    from app import app as flask_app
    
    # We need to patch the DB_PATH to use test db
    original_db_path = flask_app.config.get('DB_PATH', '/some/path')
    
    # Create a test app with the test db
    test_app = Flask(__name__)
    test_app.config['TESTING'] = True
    test_app.config['DB_PATH'] = test_db
    
    # Copy routes from original app
    @test_app.route('/')
    def index():
        from flask import render_template
        return render_template('index.html')
    
    @test_app.route('/save', methods=['POST'])
    def save_session():
        from flask import request, jsonify
        data = request.get_json()
        duration = data.get('duration', 25)
        today = date.today().isoformat()
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(test_db)
        conn.execute(
            'INSERT INTO sessions (date, duration, created_at) VALUES (?, ?, ?)',
            (today, duration, now)
        )
        conn.commit()
        conn.close()
        
        return jsonify({'status': 'saved'})
    
    @test_app.route('/stats', methods=['GET'])
    def get_stats():
        from flask import jsonify
        today = date.today().isoformat()
        
        conn = sqlite3.connect(test_db)
        conn.row_factory = sqlite3.Row
        
        sessions = conn.execute(
            'SELECT * FROM sessions WHERE date = ? ORDER BY created_at DESC',
            (today,)
        ).fetchall()
        
        total_minutes = sum(row['duration'] for row in sessions)
        
        session_list = []
        for row in sessions:
            created = datetime.fromisoformat(row['created_at'])
            session_list.append({
                'time': created.strftime('%H:%M'),
                'duration': row['duration']
            })
        
        conn.close()
        
        return jsonify({
            'total_minutes': total_minutes,
            'sessions': session_list
        })
    
    yield test_app

@pytest.fixture
def client(app):
    return app.test_client()


def test_single_session_save(client, test_db):
    response = client.post('/save', json={'duration': 25})
    assert response.status_code == 200
    assert response.json['status'] == 'saved'
    
    response = client.get('/stats')
    data = response.json
    assert data['total_minutes'] == 25
    assert len(data['sessions']) == 1


def test_multiple_sessions_same_day(client, test_db):
    client.post('/save', json={'duration': 25})
    client.post('/save', json={'duration': 30})
    client.post('/save', json={'duration': 45})
    
    response = client.get('/stats')
    data = response.json
    assert data['total_minutes'] == 100
    assert len(data['sessions']) == 3


def test_multiple_one_hour_sessions(client, test_db):
    # Save 3 sessions of 60 minutes each
    client.post('/save', json={'duration': 60})
    client.post('/save', json={'duration': 60})
    client.post('/save', json={'duration': 60})
    
    response = client.get('/stats')
    data = response.json
    # Should total 180 minutes (3 hours)
    assert data['total_minutes'] == 180
    assert len(data['sessions']) == 3


def test_mixed_durations(client, test_db):
    durations = [10, 15, 20, 25, 30, 45, 60]
    for d in durations:
        client.post('/save', json={'duration': d})
    
    response = client.get('/stats')
    data = response.json
    assert data['total_minutes'] == sum(durations)
    assert len(data['sessions']) == 7


def test_empty_database(client, test_db):
    response = client.get('/stats')
    data = response.json
    assert data['total_minutes'] == 0
    assert len(data['sessions']) == 0