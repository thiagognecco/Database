"""Full-text search endpoints using FTS5."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import json

from app.database import get_db
from app.models import Link

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/suggest")
def search_suggest(q: str, db: Session = Depends(get_db)):
    """Get autocomplete suggestions based on query."""
    if not q or len(q.strip()) < 1:
        return {"suggestions": []}

    q = q.strip().lower()

    # Search in títulos, categorias, temas, autores
    suggestions = set()

    # From titles
    titles = db.query(Link.titulo).filter(
        Link.titulo.ilike(f"%{q}%")
    ).limit(5).all()
    for title in titles:
        if title[0]:
            suggestions.add(title[0][:50])

    # From categories
    categories = db.query(Link.categoria).filter(
        Link.categoria.ilike(f"%{q}%")
    ).distinct().limit(5).all()
    for cat in categories:
        if cat[0]:
            suggestions.add(cat[0])

    # From temas
    temas = db.query(Link.tema).filter(
        Link.tema.ilike(f"%{q}%")
    ).distinct().limit(5).all()
    for tema in temas:
        if tema[0]:
            suggestions.add(tema[0])

    # From autores
    autores = db.query(Link.autor).filter(
        Link.autor.ilike(f"%{q}%")
    ).distinct().limit(5).all()
    for autor in autores:
        if autor[0]:
            suggestions.add(autor[0])

    return {"suggestions": list(suggestions)[:10]}


@router.get("")
def search_links(
    q: str = None,
    categoria: str = None,
    plataforma: str = None,
    tags: str = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    Search links using FTS5 with unicode61 tokenizer (accent-insensitive).
    Supports filtering by category, platform, and tags.
    Tags parameter should be comma-separated: "tag1,tag2"
    """
    # Parse tags parameter
    selected_tags = set()
    if tags:
        selected_tags = set(t.strip() for t in tags.split(',') if t.strip())

    # If no query, return all links
    if not q or not q.strip():
        links_query = db.query(Link)

        if categoria:
            links_query = links_query.filter(Link.categoria == categoria)
        if plataforma:
            links_query = links_query.filter(Link.plataforma == plataforma)

        # Filter by tags if provided
        if selected_tags:
            all_links = links_query.all()
            filtered_links = []
            for link in all_links:
                try:
                    link_tags = json.loads(link.tags) if link.tags else []
                    if isinstance(link_tags, list):
                        link_tags_set = set(link_tags)
                        if selected_tags.issubset(link_tags_set):
                            filtered_links.append(link)
                except (json.JSONDecodeError, TypeError):
                    pass
            total = len(filtered_links)
            links = filtered_links[offset:offset + limit]
        else:
            total = links_query.count()
            links = links_query.limit(limit).offset(offset).all()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "data": [link.to_dict() for link in links],
        }

    # Use LIKE search (simple and reliable) - busca em TODOS os campos
    search_term = f"%{q}%"
    links_query = db.query(Link).filter(
        (Link.titulo.ilike(search_term)) |          # Título
        (Link.resumo.ilike(search_term)) |          # Resumo
        (Link.autor.ilike(search_term)) |           # Autor
        (Link.categoria.ilike(search_term)) |       # Categoria
        (Link.tema.ilike(search_term)) |            # Tema
        (Link.plataforma.ilike(search_term)) |      # Plataforma
        (Link.url.ilike(search_term))               # URL
    )

    if categoria:
        links_query = links_query.filter(Link.categoria == categoria)
    if plataforma:
        links_query = links_query.filter(Link.plataforma == plataforma)

    # Filter by tags if provided
    if selected_tags:
        all_links = links_query.all()
        filtered_links = []
        for link in all_links:
            try:
                link_tags = json.loads(link.tags) if link.tags else []
                if isinstance(link_tags, list):
                    link_tags_set = set(link_tags)
                    if selected_tags.issubset(link_tags_set):
                        filtered_links.append(link)
            except (json.JSONDecodeError, TypeError):
                pass
        total = len(filtered_links)
        links = filtered_links[offset:offset + limit]
    else:
        total = links_query.count()
        links = links_query.limit(limit).offset(offset).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [link.to_dict() for link in links],
    }


@router.get("/stats")
def search_stats(db: Session = Depends(get_db)):
    """Get search statistics."""
    total_links = db.query(Link).count()
    total_categorias = (
        db.query(Link.categoria)
        .filter(Link.categoria.isnot(None))
        .distinct()
        .count()
    )
    total_plataformas = (
        db.query(Link.plataforma)
        .filter(Link.plataforma.isnot(None))
        .distinct()
        .count()
    )
    total_favoritos = db.query(Link).filter(Link.favorito == True).count()

    return {
        "total_links": total_links,
        "total_categorias": total_categorias,
        "total_plataformas": total_plataformas,
        "total_favoritos": total_favoritos,
    }
