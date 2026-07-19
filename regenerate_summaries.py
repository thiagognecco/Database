#!/usr/bin/env python
"""Script para regenerar resumos de todos os links em português."""
import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import get_db, init_db
from app.models import Link
from app.ai_service import generate_summary_with_ai
from app.ai_cache import rate_limiter
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

async def regenerate_all_summaries():
    """Regenerar resumos de todos os links."""
    rate_limiter.call_times = []  # Reset rate limiter for this script
    rate_limiter.max_calls = 100  # Increase limit for batch processing
    rate_limiter.window_seconds = 60
    init_db()
    db = next(get_db())

    links = db.query(Link).all()
    total = len(links)
    updated = 0
    skipped = 0

    logger.info(f"🚀 Regenerando {total} resumos em português...\n")

    for i, link in enumerate(links, 1):
        if not link.titulo:
            skipped += 1
            continue

        try:
            new_resumo = await generate_summary_with_ai(link.titulo, link.url)
            if new_resumo and new_resumo != link.resumo:
                old = link.resumo[:50] if link.resumo else "vazio"
                link.resumo = new_resumo
                db.commit()
                updated += 1

                if updated % 10 == 0:
                    logger.info(f"✅ {updated} resumos atualizados | Progresso: {i}/{total}")
        except Exception as e:
            logger.error(f"❌ Erro ao regenerar {link.titulo[:30]}: {str(e)[:60]}")
            continue

    logger.info(f"\n{'='*60}")
    logger.info(f"✅ CONCLUÍDO!")
    logger.info(f"{'='*60}")
    logger.info(f"Total processado: {total}")
    logger.info(f"Atualizados: {updated}")
    logger.info(f"Pulados (sem título): {skipped}")
    logger.info(f"{'='*60}\n")

    db.close()

if __name__ == "__main__":
    asyncio.run(regenerate_all_summaries())
