#!/usr/bin/env python
"""Script para regenerar resumos de todos os links em português."""
import asyncio
from app.database import get_db, init_db
from app.models import Link
from app.ai_service import generate_summary_with_ai
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def regenerate_all_summaries():
    """Regenerar resumos de todos os links."""
    init_db()
    db = next(get_db())

    links = db.query(Link).all()
    total = len(links)
    updated = 0

    logger.info(f"Regenerando {total} resumos...")

    for i, link in enumerate(links, 1):
        if not link.titulo:
            continue

        try:
            new_resumo = await generate_summary_with_ai(link.titulo, link.url)
            if new_resumo and new_resumo != link.resumo:
                link.resumo = new_resumo
                db.commit()
                updated += 1

                if i % 10 == 0:
                    logger.info(f"Progresso: {i}/{total} ({updated} atualizados)")
        except Exception as e:
            logger.error(f"Erro ao regenerar resumo de {link.url}: {e}")
            continue

    logger.info(f"✅ Concluído! {updated}/{total} resumos atualizados para português")
    db.close()

if __name__ == "__main__":
    asyncio.run(regenerate_all_summaries())
