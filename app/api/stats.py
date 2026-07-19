"""Statistics and dashboard endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Link
from app.ai_service import get_ai_stats

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/dashboard")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get comprehensive dashboard statistics."""
    total_links = db.query(Link).count()
    total_favoritos = db.query(Link).filter(Link.favorito == True).count()
    total_lidos = db.query(Link).filter(Link.lido == True).count()
    total_nao_lidos = total_links - total_lidos

    # Stats by category
    by_categoria = db.query(
        Link.categoria, func.count(Link.id)
    ).filter(Link.categoria.isnot(None)).group_by(Link.categoria).all()

    # Stats by platform
    by_plataforma = db.query(
        Link.plataforma, func.count(Link.id)
    ).filter(Link.plataforma.isnot(None)).group_by(Link.plataforma).all()

    # Average rating
    avg_rating = db.query(func.avg(Link.rating)).scalar() or 0

    # High rated links (4-5 stars)
    high_rated = db.query(Link).filter(Link.rating >= 4).count()

    return {
        "total_links": total_links,
        "total_favoritos": total_favoritos,
        "total_lidos": total_lidos,
        "total_nao_lidos": total_nao_lidos,
        "avg_rating": float(avg_rating),
        "high_rated": high_rated,
        "by_categoria": [
            {"categoria": cat, "count": count} for cat, count in by_categoria
        ],
        "by_plataforma": [
            {"plataforma": plat, "count": count} for plat, count in by_plataforma
        ],
    }


@router.get("/tags")
def get_all_tags(db: Session = Depends(get_db)):
    """Get all unique tags with count."""
    import json
    from collections import Counter

    all_tags = Counter()
    links = db.query(Link.tags).filter(Link.tags.isnot(None)).all()

    for (tags_json,) in links:
        if tags_json:
            try:
                tags = json.loads(tags_json)
                if isinstance(tags, list):
                    for tag in tags:
                        all_tags[tag] += 1
            except json.JSONDecodeError:
                pass

    return {
        "tags": [
            {"tag": tag, "count": count}
            for tag, count in sorted(all_tags.items(), key=lambda x: x[1], reverse=True)
        ]
    }


@router.get("/top-rated")
def get_top_rated_links(limit: int = 10, db: Session = Depends(get_db)):
    """Get top rated links."""
    links = db.query(Link).filter(Link.rating > 0).order_by(Link.rating.desc()).limit(limit).all()
    return {
        "links": [link.to_dict() for link in links]
    }


@router.get("/ai-usage")
def get_ai_usage_stats():
    """Get AI service usage statistics and cache info."""
    return get_ai_stats()
