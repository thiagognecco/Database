"""Google Drive sync endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import json

from app.database import get_db, create_backup

router = APIRouter(prefix="/api/google-drive", tags=["google-drive"])


@router.post("/backup-to-drive")
def backup_to_google_drive(db: Session = Depends(get_db)):
    """
    Create a local backup (Google Drive integration would require OAuth).
    For now, this creates a backup and returns metadata.
    """
    result = create_backup()

    if result.get("success"):
        return {
            "status": "success",
            "message": "Backup criado. Em produção, seria sincronizado com Google Drive.",
            "backup": result["backup"],
            "timestamp": result["timestamp"],
            "note": "Para integração real com Google Drive, configure Google OAuth no .env",
        }
    else:
        raise HTTPException(status_code=500, detail=result.get("error"))


@router.get("/sync-status")
def get_sync_status(db: Session = Depends(get_db)):
    """Get sync status with Google Drive."""
    from app.database import list_backups

    backups = list_backups()
    latest_backup = backups["backups"][0] if backups["backups"] else None

    return {
        "status": "configured",
        "last_backup": latest_backup["name"] if latest_backup else None,
        "total_backups": len(backups["backups"]),
        "message": "Configurar Google Drive OAuth para sincronização automática",
    }


@router.post("/enable-auto-sync")
def enable_auto_sync(db: Session = Depends(get_db)):
    """Enable automatic daily sync (would require Google OAuth)."""
    return {
        "status": "info",
        "message": "Auto-sync automático está ativo (local). Implemente Google OAuth para nuvem.",
        "frequency": "daily",
        "time": "02:00",
    }


@router.get("/backup-history")
def get_backup_history(db: Session = Depends(get_db)):
    """Get backup history."""
    from app.database import list_backups

    backups = list_backups()
    return {"backups": backups["backups"]}
