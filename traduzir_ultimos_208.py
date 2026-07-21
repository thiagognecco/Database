#!/usr/bin/env python3
"""Traduz os últimos 208 resumos em inglês"""

import sys
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models import Link

print("="*80)
print("TRADUCAO FINAL: 208 resumos em INGLES -> PT-BR")
print("="*80 + "\n")

client = Anthropic()
db = SessionLocal()

# Palavras em inglês comuns
english_words = {
    "the", "a", "an", "and", "or", "is", "are", "be", "been",
    "have", "has", "do", "does", "did", "will", "would", "can", "could",
    "should", "may", "might", "must", "for", "to", "of", "in", "on", "at",
    "by", "from", "with", "about", "as", "into", "through", "during",
    "link", "reel", "post", "video", "article", "guide", "tutorial"
}

# Pegar links em inglês
links_all = db.query(Link).filter(Link.resumo != None, Link.resumo != "").all()
links_en = []

for l in links_all:
    texto_lower = l.resumo.lower()
    acentos = sum(1 for c in texto_lower if c in "àáâãäèéêëìíîïòóôõöùúûüçñ")

    if acentos == 0:  # Sem acentos
        palavras = texto_lower.split()
        en_count = sum(1 for p in palavras if p.strip('.,!?;:') in english_words)

        if en_count >= 2:  # Tem palavras em inglês
            links_en.append(l)

print(f"Encontrados {len(links_en)} resumos em INGLES\n")

if len(links_en) == 0:
    print("Nenhum resumo em inglês encontrado!")
    db.close()
    sys.exit(0)

traduzidos = 0
erros = 0

for i, link in enumerate(links_en, 1):
    try:
        sys.stdout.write(f"\r[{i}/{len(links_en)}] ID {link.id}...")
        sys.stdout.flush()

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": f"""Traduza APENAS este texto para portugues brasileiro (PT-BR).
Mantenha o significado exato. Responda APENAS com o texto traduzido, sem explicacoes.

TEXTO:
{link.resumo[:200]}"""
            }]
        )

        resumo_pt = response.content[0].text.strip()
        link.resumo = resumo_pt
        db.commit()
        traduzidos += 1

        if traduzidos % 10 == 0:
            print(f"\n✓ {traduzidos} traduzidos...")

    except Exception as e:
        erros += 1
        print(f"\n✗ ID {link.id}: {str(e)[:40]}")
        continue

db.close()

print("\n\n" + "="*80)
print("RESULTADO FINAL")
print("="*80)
print(f"Traduzidos: {traduzidos}")
print(f"Erros: {erros}")
print(f"Taxa: {(traduzidos/(traduzidos+erros)*100) if (traduzidos+erros) > 0 else 0:.1f}%")
print("\nPROXIMO PASSO: python migrar_para_postgres.py")
print("="*80)
