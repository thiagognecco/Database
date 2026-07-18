"""Simple PIN-based authentication."""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json
import os

from app.database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Simple in-memory session store
_sessions = {}
SESSION_TIMEOUT = timedelta(hours=24)


def _get_default_pin():
    """Get PIN from environment or use default."""
    return os.getenv("BANCO_LINKS_PIN", "1234")


@router.post("/login")
def login(pin: str, db: Session = Depends(get_db)):
    """Login with PIN."""
    correct_pin = _get_default_pin()

    if pin != correct_pin:
        raise HTTPException(status_code=401, detail="PIN incorreto")

    # Generate session token
    import secrets
    session_token = secrets.token_urlsafe(32)
    _sessions[session_token] = {
        "created_at": datetime.now(),
        "pin": pin,
    }

    return {
        "session_token": session_token,
        "message": "Login successful",
        "user": "admin",
    }


@router.post("/logout")
def logout(session_token: str = None):
    """Logout."""
    if session_token and session_token in _sessions:
        del _sessions[session_token]

    return {"message": "Logged out"}


@router.get("/status")
def auth_status(session_token: str = None):
    """Check auth status."""
    if not session_token or session_token not in _sessions:
        return {"authenticated": False, "message": "Not logged in"}

    session = _sessions[session_token]
    created_at = session["created_at"]
    if datetime.now() - created_at > SESSION_TIMEOUT:
        del _sessions[session_token]
        return {"authenticated": False, "message": "Session expired"}

    return {
        "authenticated": True,
        "user": "admin",
        "created_at": created_at.isoformat(),
    }


def require_auth(session_token: str = None):
    """Dependency for requiring authentication."""
    if not session_token or session_token not in _sessions:
        raise HTTPException(status_code=401, detail="Unauthorized")

    session = _sessions[session_token]
    if datetime.now() - session["created_at"] > SESSION_TIMEOUT:
        del _sessions[session_token]
        raise HTTPException(status_code=401, detail="Session expired")

    return session_token


@router.post("/change-pin")
def change_pin(old_pin: str, new_pin: str, db: Session = Depends(get_db)):
    """Change PIN."""
    correct_pin = _get_default_pin()

    if old_pin != correct_pin:
        raise HTTPException(status_code=401, detail="PIN atual incorreto")

    if len(new_pin) < 4:
        raise HTTPException(status_code=400, detail="PIN deve ter pelo menos 4 dígitos")

    # In production, persist this securely
    return {
        "message": "PIN updated (local only - implemente persistência)",
        "warning": "Defina BANCO_LINKS_PIN na variável de ambiente para persistir",
    }
