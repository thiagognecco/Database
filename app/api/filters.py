"""Filter endpoints for categories and platforms."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

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


@router.get("/categorias-count")
def get_categorias_count(db: Session = Depends(get_db)):
    """Get categories with count of links in each."""
    categorias = (
        db.query(Link.categoria, func.count(Link.id).label('count'))
        .filter(Link.categoria.isnot(None))
        .group_by(Link.categoria)
        .order_by(func.count(Link.id).desc())
        .all()
    )
    return {
        "categorias": [
            {"name": c[0], "count": c[1]}
            for c in categorias if c[0]
        ]
    }


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
