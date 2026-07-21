#!/usr/bin/env python3
"""Processar 2105 links com Haiku 4.5"""

import json
import os
import sqlite3
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

with open("dados/links_export.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

links = data['links']

print("="*80)
print(f"PROCESSANDO {len(links)} LINKS COM HAIKU 4.5")
print("="*80)
print(f"Custo estimado: ~$1.40")
print(f"Tempo estimado: 30-40 minutos")
print(f"Início: {datetime.now().strftime('%H:%M:%S')}")
print("="*80 + "\n")

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

total_input_tokens = 0
total_output_tokens = 0
total_cost = 0
processados = 0
erros = 0

resultados = []

for i, link in enumerate(links, 1):
    titulo = link.get('titulo') or link.get('url', '')[:80]
    resumo_atual = (link.get('resumo') or '')[:150]

    prompt = f"""Analise este link e forneça:
1. Melhor categoria
2. 3-5 tags relevantes
3. Resumo melhorado (1-2 frases claras em português)

Título: {titulo}
URL: {link['url']}
Resumo atual: {resumo_atual}

Responda em JSON puro:
{{
  "categoria": "uma das: Tecnologia, IA, Educacao, Marketing, Negocios, Saude, Financas, Juridico, Automacao, Receita, SAP, Tutorial, Video, Artigo, Ferramenta",
  "tags": ["tag1", "tag2", "tag3"],
  "resumo_novo": "Resumo de 1-2 frases."
}}"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = message.content[0].text

        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()

        resultado = json.loads(response_text)

        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens
        input_cost = (input_tokens * 0.80) / 1_000_000
        output_cost = (output_tokens * 4) / 1_000_000
        custo = input_cost + output_cost

        total_input_tokens += input_tokens
        total_output_tokens += output_tokens
        total_cost += custo
        processados += 1

        resultados.append({
            'link_id': link['id'],
            'categoria_nova': resultado.get('categoria'),
            'tags_novas': resultado.get('tags', []),
            'resumo_novo': resultado.get('resumo_novo')
        })

        if i % 100 == 0 or i == len(links):
            pct = (i * 100) // len(links)
            print(f"[{i}/{len(links)}] {pct}% - Custo até agora: ${total_cost:.2f}")

    except Exception as e:
        erros += 1
        print(f"[{i}] ERRO: {str(e)[:50]}")

print("\n" + "="*80)
print("RESULTADO DO PROCESSAMENTO")
print("="*80)
print(f"Processados: {processados}/{len(links)}")
print(f"Erros: {erros}")
print(f"Total de tokens: {total_input_tokens + total_output_tokens}")
print(f"CUSTO TOTAL: ${total_cost:.4f}")
print(f"Tempo final: {datetime.now().strftime('%H:%M:%S')}")
print("="*80)

# Salvar JSON
with open("dados/links_processado.json", 'w', encoding='utf-8') as f:
    json.dump({
        'processing_date': datetime.now().isoformat(),
        'total_links': len(links),
        'processados': processados,
        'erros': erros,
        'custo_total': total_cost,
        'results': resultados
    }, f, ensure_ascii=False, indent=2)

print(f"\nSalvo em: dados/links_processado.json")
