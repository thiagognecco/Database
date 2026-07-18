"""GitHub backup endpoints.

Uses a personal access token stored in the GITHUB_TOKEN Replit Secret.
Backs up the SQLite database to a file in a user-configured repository.
"""
import os
import base64
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import get_db, DB_PATH

router = APIRouter(prefix="/api/github", tags=["github"])

GITHUB_API = "https://api.github.com"
REPO_ENV_VAR = "GITHUB_BACKUP_REPO"  # e.g. "username/repo-name"


def _get_token():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise HTTPException(status_code=503, detail="GITHUB_TOKEN não configurado nos Secrets")
    return token


def _get_repo():
    repo = os.getenv(REPO_ENV_VAR)
    if not repo:
        raise HTTPException(
            status_code=503,
            detail=f"{REPO_ENV_VAR} não configurado. Defina no formato 'usuario/repo'.",
        )
    return repo


@router.get("/status")
def github_status():
    """Check whether GitHub backup is configured."""
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv(REPO_ENV_VAR)
    return {
        "configured": bool(token and repo),
        "repo": repo,
        "missing": [
            "GITHUB_TOKEN" if not token else None,
            REPO_ENV_VAR if not repo else None,
        ],
    }


@router.post("/backup")
def backup_to_github(db: Session = Depends(get_db)):
    """Upload the current SQLite database to a GitHub repository."""
    token = _get_token()
    repo = _get_repo()

    if not DB_PATH.exists():
        raise HTTPException(status_code=500, detail="Banco de dados não encontrado")

    db_bytes = DB_PATH.read_bytes()
    content_b64 = base64.b64encode(db_bytes).decode()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = f"backups/banco_links_{timestamp}.db"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Check if file already exists (unlikely with timestamp)
    sha = None
    with httpx.Client() as client:
        check_resp = client.get(
            f"{GITHUB_API}/repos/{repo}/contents/{path}",
            headers=headers,
        )
        if check_resp.status_code == 200:
            sha = check_resp.json().get("sha")

        body = {
            "message": f"Backup automático do Banco de Links - {timestamp}",
            "content": content_b64,
        }
        if sha:
            body["sha"] = sha

        put_resp = client.put(
            f"{GITHUB_API}/repos/{repo}/contents/{path}",
            headers=headers,
            json=body,
        )

    if put_resp.status_code not in (200, 201):
        try:
            detail = put_resp.json()
        except Exception:
            detail = put_resp.text
        raise HTTPException(
            status_code=502,
            detail=f"GitHub API error: {put_resp.status_code} - {detail}",
        )

    data = put_resp.json()
    return {
        "status": "success",
        "message": "Backup enviado para o GitHub",
        "repo": repo,
        "path": path,
        "url": data.get("content", {}).get("html_url"),
        "timestamp": timestamp,
        "size": len(db_bytes),
    }


@router.get("/history")
def github_history():
    """List recent backup commits on the repository."""
    token = _get_token()
    repo = _get_repo()

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    with httpx.Client() as client:
        resp = client.get(
            f"{GITHUB_API}/repos/{repo}/commits",
            headers=headers,
            params={"path": "backups", "per_page": 10},
        )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"GitHub API error: {resp.status_code} - {resp.text}",
        )

    commits = resp.json()
    return {
        "repo": repo,
        "commits": [
            {
                "sha": c["sha"],
                "message": c["commit"]["message"],
                "date": c["commit"]["committer"]["date"],
                "url": c["html_url"],
            }
            for c in commits
        ],
    }
