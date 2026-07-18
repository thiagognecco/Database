# Banco de Links

A FastAPI-based link/bookmark manager with AI features powered by Anthropic Claude.

## Stack

- **Backend**: FastAPI + Uvicorn (Python 3.12)
- **Database**: SQLite at `dados/banco.db`
- **Frontend**: Vanilla JS + HTML/CSS served as static files via FastAPI
- **AI**: Anthropic Claude (via `ANTHROPIC_API_KEY` secret)
- **Auth**: Simple PIN-based authentication (default PIN: `1234`, override with `BANCO_LINKS_PIN` env var)

## Running the app

The workflow `Start application` runs:
```
uvicorn app.main:app --host 0.0.0.0 --port 5000
```

The app serves on port 5000 (required for Replit webview). This is controlled by the `BANCO_LINKS_PORT` env var, set to `5000` in the shared environment.

## Key environment variables

| Variable | Where | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | Replit Secret | AI features (metadata enrichment, etc.) |
| `BANCO_LINKS_PORT` | Shared env var | Server port (must be 5000 on Replit) |
| `BANCO_LINKS_PIN` | Replit Secret (optional) | Login PIN (default: `1234`) |

## Project structure

```
app/
  main.py          # FastAPI app, route registration, startup
  database.py      # SQLAlchemy setup, SQLite, backup logic
  models.py        # ORM models
  schemas.py       # Pydantic schemas
  ai_service.py    # Anthropic Claude integration
  importador.py    # Bulk import logic
  api/
    auth.py        # PIN-based auth
    links.py       # CRUD for links
    filters.py     # Category/tag filters
    search.py      # Full-text search
    metadata.py    # AI metadata enrichment
    import_export.py
    stats.py
    sharing.py
    google_drive.py  # Backup (OAuth not implemented yet)
  static/
    index.html
    app.js
    styles.css
dados/
  banco.db         # SQLite database
  backups/         # Auto-backup snapshots
```

## User preferences

- Keep existing project structure and stack — do not restructure or migrate.
