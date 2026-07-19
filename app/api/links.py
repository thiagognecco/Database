"""CRUD endpoints for links."""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import asyncio

from app.models import Link
from app.database import get_db
from app.schemas import LinkCreate, LinkUpdate
from app.ai_service import categorize_link, generate_summary_with_ai

router = APIRouter(prefix="/api/links", tags=["links"])


@router.get("")
def list_links(
    categoria: Optional[str] = None,
    plataforma: Optional[str] = None,
    favorito: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List all links with optional filters."""
    query = db.query(Link)

    if categoria:
        query = query.filter(Link.categoria == categoria)

    if plataforma:
        query = query.filter(Link.plataforma == plataforma)

    if favorito is not None:
        query = query.filter(Link.favorito == favorito)

    total = query.count()
    links = query.limit(limit).offset(offset).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [link.to_dict() for link in links],
    }


@router.get("/{link_id:int}")
def get_link(link_id: int, db: Session = Depends(get_db)):
    """Get a specific link by ID."""
    link = db.query(Link).filter(Link.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Not found")

    return link.to_dict()


@router.post("")
async def create_link(link: LinkCreate, db: Session = Depends(get_db)):
    """Create a new link with AI-powered auto-categorization and summary generation."""
    # Check if URL already exists
    existing = db.query(Link).filter(Link.url == link.url).first()
    if existing:
        raise HTTPException(status_code=400, detail="URL já existe")

    # Parse date if provided
    link_data = None
    if link.data:
        try:
            link_data = datetime.fromisoformat(link.data)
        except ValueError:
            raise HTTPException(status_code=400, detail="Data em formato ISO inválido")

    # Use AI to auto-categorize if not provided
    categoria = link.categoria
    tema = link.tema
    confiabilidade = link.confiabilidade

    if not categoria or not tema:
        try:
            ai_result = await categorize_link(link.url, link.titulo or "", link.resumo or "")
            if not categoria:
                categoria = ai_result.get("categoria")
            if not tema:
                tema = ai_result.get("tema")
            if not confiabilidade:
                confiabilidade = ai_result.get("confiabilidade")
        except Exception as e:
            import logging
            logging.warning(f"AI categorization failed: {e}")

    # Generate summary with AI if not provided
    resumo = link.resumo
    if not resumo and link.titulo:
        try:
            resumo = await generate_summary_with_ai(link.titulo, link.url)
        except Exception as e:
            import logging
            logging.warning(f"AI summary generation failed: {e}")

    new_link = Link(
        url=link.url,
        titulo=link.titulo,
        resumo=resumo,
        autor=link.autor,
        data=link_data,
        plataforma=link.plataforma,
        categoria=categoria,
        tema=tema,
        confiabilidade=confiabilidade,
        bot=link.bot,
    )

    db.add(new_link)
    db.commit()
    db.refresh(new_link)

    return new_link.to_dict()


@router.put("/{link_id:int}")
def update_link(link_id: int, link_data: LinkUpdate, db: Session = Depends(get_db)):
    """Update a link."""
    link = db.query(Link).filter(Link.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link não encontrado")

    if link_data.titulo is not None:
        link.titulo = link_data.titulo
    if link_data.resumo is not None:
        link.resumo = link_data.resumo
    if link_data.autor is not None:
        link.autor = link_data.autor
    if link_data.data is not None:
        try:
            link.data = datetime.fromisoformat(link_data.data)
        except ValueError:
            raise HTTPException(status_code=400, detail="Data em formato ISO inválido")
    if link_data.plataforma is not None:
        link.plataforma = link_data.plataforma
    if link_data.categoria is not None:
        link.categoria = link_data.categoria
    if link_data.tema is not None:
        link.tema = link_data.tema
    if link_data.confiabilidade is not None:
        link.confiabilidade = link_data.confiabilidade

    link.atualizado_em = datetime.utcnow()
    db.commit()
    db.refresh(link)

    return link.to_dict()


@router.delete("/{link_id:int}")
def delete_link(link_id: int, db: Session = Depends(get_db)):
    """Delete a link."""
    link = db.query(Link).filter(Link.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Not found")

    db.delete(link)
    db.commit()

    return {"message": "Link deleted"}


@router.post("/{link_id:int}/favorite")
def toggle_favorite(link_id: int, db: Session = Depends(get_db)):
    """Toggle favorite status of a link."""
    link = db.query(Link).filter(Link.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link não encontrado")

    link.favorito = not link.favorito
    link.atualizado_em = datetime.utcnow()
    db.commit()
    db.refresh(link)
    return link.to_dict()


@router.post("/{link_id:int}/analyze-with-ai")
async def analyze_link_with_ai(link_id: int, db: Session = Depends(get_db)):
    """Analyze and enhance a link with AI (auto-categorize and generate summary)."""
    link = db.query(Link).filter(Link.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link não encontrado")

    try:
        # Auto-categorize
        ai_result = await categorize_link(link.url, link.titulo or "", link.resumo or "")
        link.categoria = ai_result.get("categoria")
        link.tema = ai_result.get("tema")
        link.confiabilidade = ai_result.get("confiabilidade")

        # Generate summary if empty
        if not link.resumo and link.titulo:
            link.resumo = await generate_summary_with_ai(link.titulo, link.url)

        link.atualizado_em = datetime.utcnow()
        db.commit()
        db.refresh(link)

        return {
            "message": "Link analisado com sucesso",
            "link": link.to_dict()
        }

    except Exception as e:
        import logging
        logging.error(f"AI analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Erro ao analisar link com IA")

    return {"favorito": link.favorito}


@router.get("/favoritos")
def get_favoritos(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    """Get all favorite links."""
    total = db.query(Link).filter(Link.favorito == True).count()
    links = (
        db.query(Link)
        .filter(Link.favorito == True)
        .limit(limit)
        .offset(offset)
        .all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [link.to_dict() for link in links],
    }


@router.post("/{link_id:int}/rating")
def set_rating(link_id: int, rating: int, db: Session = Depends(get_db)):
    """Set link rating (0-5 stars)."""
    link = db.query(Link).filter(Link.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Not found")

    if rating < 0 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating deve estar entre 0 e 5")

    link.rating = rating
    link.atualizado_em = datetime.utcnow()
    db.commit()
    db.refresh(link)

    return {"rating": link.rating}


@router.post("/{link_id:int}/mark-read")
def mark_as_read(link_id: int, lido: bool = True, db: Session = Depends(get_db)):
    """Mark link as read or unread."""
    link = db.query(Link).filter(Link.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Not found")

    link.lido = lido
    link.atualizado_em = datetime.utcnow()
    db.commit()
    db.refresh(link)

    return {"lido": link.lido}


@router.post("/{link_id:int}/tags")
def set_tags(link_id: int, tags: list, db: Session = Depends(get_db)):
    """Set tags for a link."""
    import json
    link = db.query(Link).filter(Link.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Not found")

    link.tags = json.dumps(tags)
    link.atualizado_em = datetime.utcnow()
    db.commit()
    db.refresh(link)

    return {"tags": tags}
