from flask import Flask, render_template, request, jsonify, send_from_directory
import sqlite3
from datetime import datetime, date, timedelta
import os

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
DB_PATH = os.path.join(os.path.dirname(__file__), 'sessions.db')

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

def get_db_connection():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL')
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        raise

def init_db():
    try:
        with get_db_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    duration INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json', mimetype='application/json')

@app.route('/weekly')
def weekly():
    return render_template('weekly.html')

@app.route('/save', methods=['POST'])
def save_session():
    try:
        data = request.get_json()
        duration = data.get('duration', 25)
        session_id = data.get('session_id')
        today = date.today().isoformat()
        now = datetime.now().isoformat()

        if not isinstance(duration, int) or duration <= 0:
            return jsonify({'status': 'error', 'message': 'invalid_duration'}), 400

        with get_db_connection() as conn:
            if session_id:
                cursor = conn.execute(
                    'UPDATE sessions SET duration = ? WHERE id = ?',
                    (duration, session_id)
                )
                if cursor.rowcount == 0:
                    return jsonify({'status': 'error', 'message': 'session_not_found'}), 404
            else:
                cursor = conn.execute(
                    'INSERT INTO sessions (date, duration, created_at) VALUES (?, ?, ?)',
                    (today, duration, now)
                )
                session_id = cursor.lastrowid

            conn.commit()
            return jsonify({'status': 'saved', 'session_id': session_id})

    except sqlite3.OperationalError as e:
        if 'locked' in str(e).lower():
            return jsonify({'status': 'error', 'message': 'database_locked'}), 503
        return jsonify({'status': 'error', 'message': 'database_error'}), 500
    except Exception:
        return jsonify({'status': 'error', 'message': 'server_error'}), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    today = date.today().isoformat()

    try:
        with get_db_connection() as conn:
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

            return jsonify({
                'total_minutes': total_minutes,
                'sessions': session_list
            })

    except sqlite3.OperationalError:
        return jsonify({'total_minutes': 0, 'sessions': []}), 200

@app.route('/weekly-stats', methods=['GET'])
def get_weekly_stats():
    try:
        with get_db_connection() as conn:
            today = date.today()
            start_date = (today - timedelta(days=6)).isoformat()
            end_date = today.isoformat()

            rows = conn.execute(
                'SELECT date, SUM(duration) as total FROM sessions WHERE date BETWEEN ? AND ? GROUP BY date',
                (start_date, end_date)
            ).fetchall()

            stats_map = {row['date']: row['total'] for row in rows}

            result = []
            for i in range(6, -1, -1):
                d = (today - timedelta(days=i)).isoformat()
                result.append({
                    'date': d,
                    'minutes': stats_map.get(d, 0)
                })

            return jsonify(result)

    except sqlite3.OperationalError:
        today = date.today()
        return jsonify([{'date': (today - timedelta(days=i)).isoformat(), 'minutes': 0} for i in range(6, -1, -1)]), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'production') != 'production'
    app.run(host="0.0.0.0", debug=debug, port=port)