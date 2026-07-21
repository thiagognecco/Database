#!/usr/bin/env python3
"""Processar 2105 links com checkpoint a cada 100"""

import json
import os
import sys
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Force flush output
sys.stdout.flush = lambda: None

with open("dados/links_export.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

links = data['links']

print("="*80, flush=True)
print(f"PROCESSANDO {len(links)} LINKS", flush=True)
print("="*80, flush=True)

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

total_cost = 0
processados = 0
erros = 0
resultados = []

for i, link in enumerate(links, 1):
    titulo = link.get('titulo') or link.get('url', '')[:80]
    resumo_atual = (link.get('resumo') or '')[:150]

    prompt = f"""Analise este link:
Título: {titulo}
URL: {link['url']}
Resumo: {resumo_atual}

JSON:
{{"categoria": "Tecnologia|IA|Educacao|Marketing|Negocios|Saude|Financas|Juridico|Automacao|Receita|SAP|Tutorial|Video|Artigo|Ferramenta", "tags": ["tag1", "tag2", "tag3"], "resumo_novo": "1-2 frases"}}"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1].replace("json\n", "").strip()

        resultado = json.loads(response_text)

        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens
        custo = ((input_tokens * 0.80) + (output_tokens * 4)) / 1_000_000

        total_cost += custo
        processados += 1

        resultados.append({
            'link_id': link['id'],
            'categoria': resultado.get('categoria'),
            'tags': resultado.get('tags', []),
            'resumo': resultado.get('resumo_novo')
        })

        if i % 10 == 0:
            print(f"[{i}/{len(links)}] Custo: ${total_cost:.2f}", flush=True)

        if i % 100 == 0:
            with open("dados/links_processado.json", 'w', encoding='utf-8') as f:
                json.dump({
                    'processados': processados,
                    'total': len(links),
                    'custo': total_cost,
                    'erros': erros,
                    'results': resultados
                }, f, ensure_ascii=False)

    except Exception as e:
        erros += 1
        if i % 50 == 0:
            print(f"[{i}] Erro: {str(e)[:30]}", flush=True)

# Salvar final
with open("dados/links_processado.json", 'w', encoding='utf-8') as f:
    json.dump({
        'processados': processados,
        'total': len(links),
        'custo': total_cost,
        'erros': erros,
        'results': resultados,
        'concluido': True
    }, f, ensure_ascii=False)

print(f"\nCONCLUIDO: {processados}/{len(links)} | Custo: ${total_cost:.2f}", flush=True)
