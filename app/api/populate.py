"""Populate tags in links database"""
import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models import Link
from app.database import get_db

router = APIRouter(prefix="/api/populate", tags=["populate"])


@router.post("/tags")
def populate_tags(db: Session = Depends(get_db)):
    """Populate tags in all links based on categoria, tema, and content analysis"""
    links = db.query(Link).all()
    updated = 0

    for link in links:
        tags = []

        # Add categoria as tag
        if link.categoria:
            tag = link.categoria.lower().strip().replace(' ', '-')
            if tag and tag not in tags:
                tags.append(tag)

        # Add tema as tag
        if link.tema:
            tag = link.tema.lower().strip().replace(' ', '-')
            if tag and tag not in tags:
                tags.append(tag)

        # Add platform as tag
        if link.plataforma:
            tag = link.plataforma.lower().strip().replace(' ', '-')
            if tag and tag not in tags:
                tags.append(tag)

        # Analyze resumo for common tags
        if link.resumo:
            resumo_lower = link.resumo.lower()
            keywords = {
                'tutorial': ['tutorial', 'guia', 'como fazer', 'passo a passo'],
                'video': ['vídeo', 'video', 'youtube', 'assistir'],
                'artigo': ['artigo', 'post', 'publicação', 'medium'],
                'documentacao': ['documentação', 'documentation', 'docs', 'referência'],
                'codigo': ['código', 'code', 'exemplo', 'github'],
                'leitura': ['ler', 'reading', 'read', 'artigo longo'],
            }

            for tag_name, keywords_list in keywords.items():
                if any(kw in resumo_lower for kw in keywords_list):
                    if tag_name not in tags:
                        tags.append(tag_name)

        # Always add 'importante' tag to favorite links
        if link.favorito:
            if 'importante' not in tags:
                tags.append('importante')

        # Always add 'nao-lido' for unread links
        if not link.lido:
            if 'nao-lido' not in tags:
                tags.append('nao-lido')

        # Convert to JSON and save
        if tags:
            link.tags = json.dumps(tags)
            updated += 1

    db.commit()

    return {
        "status": "success",
        "message": f"✅ Atualizado: {updated} links com tags",
        "total_links": len(links),
        "updated": updated,
    }


@router.get("/tags/example")
def get_tags_example(db: Session = Depends(get_db)):
    """Get examples of links with populated tags"""
    examples = db.query(Link).filter(Link.tags != "").limit(5).all()

    return {
        "examples": [
            {
                "id": link.id,
                "titulo": link.titulo,
                "categoria": link.categoria,
                "tema": link.tema,
                "tags": json.loads(link.tags) if link.tags else [],
            }
            for link in examples
        ]
    }
