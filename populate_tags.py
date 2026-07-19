#!/usr/bin/env python3
"""Populate tags in database based on categoria, tema, and plataforma"""
import json
import sys
sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.models import Link

db = SessionLocal()

# Get all links without tags
links = db.query(Link).filter(
    (Link.tags == "") | (Link.tags.isnot(None))
).all()

total = len(links)
updated = 0

for link in links:
    tags = []

    # Add categoria as tag
    if link.categoria:
        tags.append(link.categoria.lower().replace(' ', '-'))

    # Add tema as tag
    if link.tema:
        tema_tag = link.tema.lower().replace(' ', '-')
        if tema_tag not in tags:
            tags.append(tema_tag)

    # Add platform as tag
    if link.plataforma:
        plat_tag = link.plataforma.lower().replace(' ', '-')
        if plat_tag not in tags:
            tags.append(plat_tag)

    # Add common tags based on content
    if link.resumo:
        resumo_lower = link.resumo.lower()
        if 'tutorial' in resumo_lower:
            if 'tutorial' not in tags:
                tags.append('tutorial')
        if 'video' in resumo_lower or link.plataforma == 'YouTube':
            if 'video' not in tags:
                tags.append('video')
        if 'artigo' in resumo_lower or link.plataforma == 'Medium':
            if 'artigo' not in tags:
                tags.append('artigo')
        if 'documentação' in resumo_lower or 'documentation' in resumo_lower:
            if 'documentacao' not in tags:
                tags.append('documentacao')

    # Always add 'importante' tag to favorite links
    if link.favorito:
        if 'importante' not in tags:
            tags.append('importante')

    # Convert to JSON
    if tags:
        link.tags = json.dumps(tags)
        updated += 1

# Save
db.commit()
print(f"✅ Atualizado: {updated} links com tags")
print(f"Total processado: {total} links")

# Show some examples
examples = db.query(Link).filter(Link.tags != "").limit(3).all()
print("\n📋 Exemplos:")
for link in examples:
    print(f"- {link.titulo[:40]}: {link.tags[:60]}")
