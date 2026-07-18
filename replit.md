# Banco de Links

A FastAPI-based link/bookmark manager with AI features powered by Anthropic Claude.

## Stack

- **Backend**: FastAPI + Uvicorn (Python 3.12)
- **Database**: SQLite at `dados/banco.db`
- **Frontend**: Vanilla JS + HTML/CSS served as static files via FastAPI
- **AI**: Anthropic Claude (via `ANTHROPIC_API_KEY` secret)
- **Auth**: Simple PIN-based authentication (default PIN: `1234`, override with `BANCO_LINKS_PIN` secret; PIN changes are persisted to the database)
- **Cloud backup**: GitHub (via `GITHUB_TOKEN` secret + `GITHUB_BACKUP_REPO` env var)

## Running the app

The workflow `Start application` runs:
```
uvicorn app.main:app --host 0.0.0.0 --port 5000
```

The app serves on port 5000 (required for Replit webview). This is controlled by the `BANCO_LINKS_PORT` env var, set to `5000` in the shared environment.

## Key environment variables and secrets

| Variable | Type | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | Replit Secret | AI features (metadata enrichment, etc.) |
| `GITHUB_TOKEN` | Replit Secret | Token pessoal do GitHub (classic) com permissão `repo` |
| `GITHUB_BACKUP_REPO` | Shared env var | Repositório para backups. Pode ser `usuario/repo` ou a URL completa do GitHub |
| `BANCO_LINKS_PORT` | Shared env var | Server port (must be 5000 on Replit) |
| `BANCO_LINKS_PIN` | Replit Secret (optional) | Override PIN (default: `1234`) |

## Backup

- **Local**: automatic daily backups are saved to `dados/backups/`.
- **GitHub**: click the **☁️ Backup GitHub** button in the footer to upload the current SQLite database to the configured repository.
- **Manual download**: backups can also be downloaded from the `dados/backups/` folder.

## Project structure

```
app/
  main.py              # FastAPI app, route registration, startup
  database.py          # SQLAlchemy setup, SQLite, backup logic, config helpers
  models.py            # ORM models (Link, Config)
  schemas.py           # Pydantic schemas
  ai_service.py        # Anthropic Claude integration
  importador.py        # Bulk import logic
  api/
    auth.py            # PIN-based auth (PIN persisted in DB)
    links.py           # CRUD for links
    filters.py         # Category/tag filters
    search.py          # Full-text search
    metadata.py        # AI metadata enrichment
    import_export.py
    stats.py
    sharing.py
    google_drive.py    # Local backup stub (OAuth not implemented)
    github_backup.py   # GitHub cloud backup
  static/
    index.html
    app.js
    styles.css
dados/
  banco.db             # SQLite database
  backups/             # Auto-backup snapshots
```

## User preferences

- Keep existing project structure and stack — do not restructure or migrate.
- Cloud backups use GitHub (not Google Drive) because the user preferred GitHub and the Replit OAuth connectors require a paid plan.
