"""Filter endpoints for categories and platforms."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models import Link
from app.database import get_db

router = APIRouter(prefix="/api/filters", tags=["filters"])


@router.get("/categorias")
def get_categorias(db: Session = Depends(get_db)):
    """Get list of all unique categories."""
    categorias = (
        db.query(Link.categoria)
        .filter(Link.categoria.isnot(None))
        .distinct()
        .all()
    )
    return {"categorias": sorted([c[0] for c in categorias if c[0]])}


@router.get("/plataformas")
def get_plataformas(db: Session = Depends(get_db)):
    """Get list of all unique platforms."""
    plataformas = (
        db.query(Link.plataforma)
        .filter(Link.plataforma.isnot(None))
        .distinct()
        .all()
    )
    return {"plataformas": sorted([p[0] for p in plataformas if p[0]])}
