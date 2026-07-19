"""Filter endpoints for categories and platforms."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
import json

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


@router.get("/tags-count")
def get_tags_count(db: Session = Depends(get_db)):
    """Get tags with count of links in each."""
    links = db.query(Link.tags).filter(Link.tags.isnot(None)).all()

    tag_counts = {}
    for link_tags in links:
        if link_tags[0]:
            try:
                tags = json.loads(link_tags[0]) if isinstance(link_tags[0], str) else link_tags[0]
                if isinstance(tags, list):
                    for tag in tags:
                        if tag:
                            tag_counts[tag] = tag_counts.get(tag, 0) + 1
            except (json.JSONDecodeError, TypeError):
                pass

    # Sort by count descending
    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)

    return {
        "tags": [
            {"name": t[0], "count": t[1]}
            for t in sorted_tags
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
