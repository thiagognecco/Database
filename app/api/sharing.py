"""Sharing and collections endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import json
import secrets

from app.database import get_db
from app.models import Link

router = APIRouter(prefix="/api/sharing", tags=["sharing"])

# In-memory storage for share codes (in production, use database)
_share_codes = {}


@router.post("/create-share")
def create_share(categoria: str = None, tags: list = None, db: Session = Depends(get_db)):
    """Create a shareable collection."""
    query = db.query(Link)

    if categoria:
        query = query.filter(Link.categoria == categoria)

    if tags:
        import json
        # Filter links that have any of the tags
        links = query.all()
        filtered_links = []
        for link in links:
            if link.tags:
                link_tags = json.loads(link.tags)
                if any(tag in link_tags for tag in tags):
                    filtered_links.append(link)
        links = filtered_links
    else:
        links = query.all()

    # Generate share code
    share_code = secrets.token_urlsafe(16)
    _share_codes[share_code] = {
        "links": [link.to_dict() for link in links],
        "created_at": datetime.now().isoformat(),
        "categoria": categoria,
        "tags": tags,
    }

    return {
        "share_code": share_code,
        "count": len(links),
        "share_url": f"/share/{share_code}",
    }


@router.get("/share/{share_code}")
def get_shared_collection(share_code: str, db: Session = Depends(get_db)):
    """Get a shared collection."""
    if share_code not in _share_codes:
        raise HTTPException(status_code=404, detail="Collection not found")

    return _share_codes[share_code]


@router.post("/collections")
def create_collection(name: str, link_ids: list, db: Session = Depends(get_db)):
    """Create a named collection."""
    links = db.query(Link).filter(Link.id.in_(link_ids)).all()

    return {
        "name": name,
        "count": len(links),
        "links": [link.to_dict() for link in links],
        "created_at": datetime.now().isoformat(),
    }


@router.get("/advanced-search")
def advanced_search(
    query: str = None,
    and_tags: list = None,
    or_tags: list = None,
    not_tags: list = None,
    min_rating: int = 0,
    only_read: bool = False,
    db: Session = Depends(get_db),
):
    """Advanced search with AND/OR/NOT operators and filters."""
    import json

    results = db.query(Link)

    # Text search
    if query:
        search_term = f"%{query}%"
        results = results.filter(
            (Link.titulo.ilike(search_term))
            | (Link.resumo.ilike(search_term))
            | (Link.autor.ilike(search_term))
        )

    # Tag filters
    if and_tags or or_tags or not_tags:
        all_links = results.all()
        filtered = []

        for link in all_links:
            link_tags = []
            if link.tags:
                try:
                    link_tags = json.loads(link.tags)
                except:
                    pass

            # AND: all tags must be present
            if and_tags and not all(tag in link_tags for tag in and_tags):
                continue

            # OR: at least one tag must be present
            if or_tags and not any(tag in link_tags for tag in or_tags):
                continue

            # NOT: none of these tags
            if not_tags and any(tag in link_tags for tag in not_tags):
                continue

            filtered.append(link)

        results = filtered
    else:
        results = results.all()

    # Rating filter
    if min_rating > 0:
        results = [link for link in results if link.rating >= min_rating]

    # Read status
    if only_read:
        results = [link for link in results if link.lido]

    return {
        "count": len(results),
        "data": [link.to_dict() for link in results],
    }
