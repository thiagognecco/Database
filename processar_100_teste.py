#!/usr/bin/env python3
"""Teste com 100 links. Se funcionar, faz batches de 100 em 100."""

import json
import os
import sys
import time
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

with open("dados/links_export.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

todos_links = data['links']

# BATCHES DE 100
batch_size = 100
num_batches = (len(todos_links) + batch_size - 1) // batch_size

print(f"Total: {len(todos_links)} links")
print(f"Batches: {num_batches} x {batch_size}\n")

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

todos_resultados = []
custo_total = 0

for batch_num in range(num_batches):
    start_idx = batch_num * batch_size
    end_idx = min(start_idx + batch_size, len(todos_links))
    batch_links = todos_links[start_idx:end_idx]

    print(f"\n=== BATCH {batch_num + 1}/{num_batches} ({start_idx + 1}-{end_idx}) ===\n")

    batch_custo = 0

    for i, link in enumerate(batch_links):
        idx_global = start_idx + i + 1
        titulo = link.get('titulo') or link['url'][:50]

        prompt = f"""Titulo: {titulo}
URL: {link['url']}

JSON:
{{"cat":"Tec|IA|Edu|Mark|Neg|Sau|Fin|Jur|Auto|Rec|SAP|Tut|Vid|Art|Fer","tags":["t1","t2"],"res":"1-2 frases"}}"""

        try:
            # Barra
            pct = (idx_global * 100) // len(todos_links)
            barras = "=" * (pct // 5) + "-" * (20 - pct // 5)

            sys.stdout.write(f"\r[{barras}] {pct}% ({idx_global}/{len(todos_links)}) | {titulo[:25]}")
            sys.stdout.flush()

            # Processar
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text.strip()
            if "```" in response_text:
                response_text = response_text.split("```")[1].replace("json", "").strip()

            resultado = json.loads(response_text)

            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens
            custo = ((input_tokens * 0.80) + (output_tokens * 4)) / 1_000_000

            batch_custo += custo
            custo_total += custo

            todos_resultados.append({
                "link_id": link['id'],
                "cat": resultado.get('cat'),
                "tags": resultado.get('tags', []),
                "res": resultado.get('res')
            })

        except Exception as e:
            sys.stdout.write(f"\nERRO {idx_global}: {str(e)[:40]}\n")
            sys.stdout.flush()

    print(f"\nBatch custo: ${batch_custo:.2f}")

# Salvar resultado
with open("dados/links_categorizado_final.json", 'w', encoding='utf-8') as f:
    json.dump({
        "total_links": len(todos_links),
        "processados": len(todos_resultados),
        "custo_total": custo_total,
        "resultados": todos_resultados
    }, f, ensure_ascii=False)

print(f"\n\n{'='*60}")
print(f"CONCLUIDO!")
print(f"Processados: {len(todos_resultados)}/{len(todos_links)}")
print(f"Custo total: ${custo_total:.2f}")
print(f"Salvo em: dados/links_categorizado_final.json")
print(f"{'='*60}")
