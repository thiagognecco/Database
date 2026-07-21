#!/usr/bin/env python3
"""Traduz resumos em inglês para PT-BR usando Claude API"""

import sys
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models import Link

print("="*80)
print("TRADUÇÃO: Resumos de EN -> PT-BR")
print("="*80 + "\n")

# Inicializar Claude
client = Anthropic()

# Conectar banco
db = SessionLocal()

# Pegar links com resumo em inglês
links = db.query(Link).all()
links_en = [l for l in links if l.resumo and any(c.isupper() for c in l.resumo[:50])]

print(f"Encontrados {len(links_en)} resumos para traduzir\n")

traduzidos = 0
erros = 0

for i, link in enumerate(links_en, 1):
    try:
        if not link.resumo or len(link.resumo) < 10:
            continue

        # Traduzir com Claude
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": f"""Traduza APENAS este texto para português brasileiro (PT-BR).
Mantenha o significado exato. Responda APENAS com o texto traduzido, sem explicações.

TEXTO:
{link.resumo[:200]}"""
            }]
        )

        resumo_pt = response.content[0].text.strip()

        # Atualizar
        link.resumo = resumo_pt
        db.commit()
        traduzidos += 1

        if traduzidos % 10 == 0:
            print(f"[{i}/{len(links_en)}] {traduzidos} traduzidos...")

    except Exception as e:
        print(f"Erro no link {link.id}: {str(e)[:50]}")
        erros += 1
        continue

db.close()

print("\n" + "="*80)
print("✅ TRADUÇÃO COMPLETA!")
print("="*80)
print(f"Traduzidos: {traduzidos}")
print(f"Erros: {erros}")
print("\nProximo: python migrar_para_postgres.py")
print("="*80)
