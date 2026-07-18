---
name: GitHub backup
description: Why cloud backup uses a manual GitHub token instead of Replit OAuth connectors.
---

# GitHub backup

**Rule:** Use a user-supplied GitHub personal access token (stored in `GITHUB_TOKEN` Replit Secret) for cloud backups, not the Replit GitHub OAuth connector.

**Why:** The user reported that both the Google Drive and GitHub OAuth connectors in the Replit mission UI prompted for a paid plan upgrade. The user wanted a free alternative, so the app uses a classic GitHub PAT with `repo` scope.

**How to apply:**
- Read `GITHUB_TOKEN` from secrets and `GITHUB_BACKUP_REPO` from env vars.
- Accept `usuario/repo` or a full GitHub URL; normalize to `usuario/repo` before calling the GitHub API.
- Upload the SQLite database (`dados/banco.db`) to `backups/banco_links_YYYYMMDD_HHMMSS.db` in the configured repo.
- Expose a status endpoint (`/api/github/status`) and a backup endpoint (`/api/github/backup`) and wire a button in the UI footer.
- Relevant files: `app/api/github_backup.py`, `app/main.py`, `app/static/index.html`, `app/static/app.js`.
