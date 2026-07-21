#!/usr/bin/env python3
"""Traduz APENAS os 877 resumos em inglês que faltam"""

import sys
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models import Link

print("="*80)
print("TRADUÇÃO: Resumos FALTANTES de EN -> PT-BR (877 links)")
print("="*80 + "\n")

# Inicializar Claude
client = Anthropic()

# Conectar banco
db = SessionLocal()

# Pegar links SEM acentos (ainda em inglês)
links_all = db.query(Link).filter(Link.resumo != None, Link.resumo != "").all()
links_en = []

for l in links_all:
    # Detectar se tem acentos (PT-BR)
    tem_acento = any(c in "àáâãäèéêëìíîïòóôõöùúûüçñ" for c in l.resumo.lower())
    if not tem_acento:  # Sem acentos = ainda em inglês
        links_en.append(l)

print(f"Encontrados {len(links_en)} resumos em INGLES para traduzir\n")

if len(links_en) == 0:
    print("Nenhum resumo em inglês encontrado!")
    db.close()
    sys.exit(0)

traduzidos = 0
erros = 0

for i, link in enumerate(links_en, 1):
    try:
        if not link.resumo or len(link.resumo) < 10:
            continue

        sys.stdout.write(f"\r[{i}/{len(links_en)}] Traduzindo ID {link.id}...")
        sys.stdout.flush()

        # Traduzir com Claude Haiku (barato e rápido)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": f"""Traduza APENAS este texto para português brasileiro (PT-BR).
Mantenha o significado exato. Responda APENAS com o texto traduzido, sem explicacoes.

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
            print(f"\n✓ {traduzidos} traduzidos...")

    except Exception as e:
        erros += 1
        print(f"\n✗ Erro ID {link.id}: {str(e)[:50]}")
        continue

db.close()

print("\n\n" + "="*80)
print("RESULTADO FINAL")
print("="*80)
print(f"Traduzidos: {traduzidos}")
print(f"Erros: {erros}")
print(f"Taxa de sucesso: {(traduzidos/(traduzidos+erros)*100) if (traduzidos+erros) > 0 else 0:.1f}%")
print("\nProximo: python migrar_para_postgres.py")
print("="*80)
