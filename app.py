from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime, date, timedelta
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
DB_PATH = os.path.join(os.path.dirname(__file__), 'sessions.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            duration INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/weekly')
def weekly():
    return render_template('weekly.html')

@app.route('/save', methods=['POST'])
def save_session():
    data = request.get_json()
    duration = data.get('duration', 25)
    today = date.today().isoformat()
    now = datetime.now().isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        'INSERT INTO sessions (date, duration, created_at) VALUES (?, ?, ?)',
        (today, duration, now)
    )
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'saved'})

@app.route('/stats', methods=['GET'])
def get_stats():
    today = date.today().isoformat()
    
    conn = sqlite3.connect(DB_PATH)
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

@app.route('/weekly-stats', methods=['GET'])
def get_weekly_stats():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    today = date.today()
    week_dates = [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    
    result = []
    for d in week_dates:
        sessions = conn.execute(
            'SELECT SUM(duration) as total FROM sessions WHERE date = ?',
            (d,)
        ).fetchone()
        minutes = sessions['total'] if sessions['total'] else 0
        result.append({
            'date': d,
            'minutes': minutes
        })
    
    conn.close()
    return jsonify(result)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'production') != 'production'
    app.run(host="0.0.0.0", debug=debug, port=port)