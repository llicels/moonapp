# AGENTS.md

## Commands

```bash
# Run the app locally
python app.py

# Run tests
pytest

# Deploy (Render handles this automatically via render.yaml)
```

## Key Facts

- **Entry point**: `app.py` runs the Flask app
- **Production**: Uses `gunicorn --bind 0.0.0.0:$PORT app:app` (see Procfile)
- **Database**: SQLite at `sessions.db` (note: this file is gitignored)
- **Test database**: Tests create temporary databases via `test_db` fixture

## Routes

- `/` - Home page (index.html)
- `/weekly` - Weekly stats page
- `/save` (POST) - Save session
- `/stats` (GET) - Today's stats
- `/weekly-stats` (GET) - Last 7 days stats
- `/sw.js` - Service worker
- `/manifest.json` - PWA manifest

## Testing

Tests use a temporary database fixture. Run with `pytest` (no extra args needed).