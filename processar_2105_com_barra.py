#!/usr/bin/env python3
"""Processar 2105 com barra de progresso em tempo real"""

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

links = data['links']
total = len(links)

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

total_cost = 0
processados = 0
tempo_inicio = time.time()

print(f"Processando {total} links...\n")

for i, link in enumerate(links):
    idx = i + 1

    titulo = link.get('titulo') or link['url'][:50]

    prompt = f"""Titulo: {titulo}
URL: {link['url']}

Responda APENAS JSON:
{{"cat":"Tec ou IA ou Edu ou Mark ou Neg ou Sau ou Fin ou Jur ou Auto ou Rec ou SAP ou Tut ou Vid ou Art ou Fer","tags":["t1","t2"],"res":"1-2 frases"}}"""

    try:
        # Barra de progresso ANTES do processamento
        pct = (idx * 100) // total
        barras_cheias = (pct // 5)
        barras_vazias = 20 - barras_cheias
        barra = "=" * barras_cheias + "-" * barras_vazias

        tempo_decorrido = time.time() - tempo_inicio
        tempo_por_link = tempo_decorrido / idx if idx > 0 else 0
        tempo_restante = (total - idx) * tempo_por_link
        eta_min = int(tempo_restante / 60)

        # Print com \r para atualizar na mesma linha
        sys.stdout.write(f"\r[{barra}] {pct}% ({idx}/{total}) | ${total_cost:.2f} | ETA: {eta_min}m | {titulo[:30]}")
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

        json.loads(response_text)  # Validar JSON

        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens
        custo = ((input_tokens * 0.80) + (output_tokens * 4)) / 1_000_000
        total_cost += custo
        processados += 1

    except Exception as e:
        # Mostrar erro na próxima linha (não sobrescreve barra)
        sys.stdout.write(f"\nERRO no link {idx}: {str(e)[:50]}\n")
        sys.stdout.flush()

# Final
print(f"\n\nCONCLUIDO!")
print(f"Processados: {processados}/{total}")
print(f"Custo total: ${total_cost:.2f}")

# Salvar resultado
with open("dados/links_processado_final.json", 'w') as f:
    json.dump({
        "processados": processados,
        "total": total,
        "custo": total_cost,
        "timestamp": time.time()
    }, f)

print(f"Salvo em: dados/links_processado_final.json")
