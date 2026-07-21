#!/usr/bin/env python3
"""Teste otimizado: 10 links, prompt enxuto"""

import json
import os
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

with open("dados/links_export.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

links = data['links'][:10]

print("="*60)
print(f"TESTE OTIMIZADO: {len(links)} links")
print("="*60 + "\n")

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

total_cost = 0
resultados = []

for i, link in enumerate(links, 1):
    # Prompt MUITO enxuto - sem explicacoes
    titulo = link.get('titulo') or link['url'][:50]

    prompt = f"""Titulo: {titulo}
URL: {link['url']}

Responda APENAS JSON:
{{"cat":"Tec ou IA ou Edu ou Mark ou Neg ou Sau ou Fin ou Jur ou Auto ou Rec ou SAP ou Tut ou Vid ou Art ou Fer","tags":["t1","t2"],"res":"1-2 frases"}}"""

    try:
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
        total_cost += custo

        print(f"[{i}] {titulo[:40]}")
        print(f"    Cat: {resultado.get('cat')}")
        print(f"    Res: {resultado.get('res')}")
        print(f"    Tokens IN/OUT: {input_tokens}/{output_tokens} | Custo: ${custo:.6f}\n")

        resultados.append(resultado)

    except Exception as e:
        print(f"[{i}] ERRO: {str(e)[:40]}\n")

print("="*60)
print(f"CUSTO TOTAL 10 links: ${total_cost:.4f}")
print(f"Média por link: ${total_cost/len(resultados):.6f}")
print(f"Estimado 2105 links: ${(total_cost/len(resultados))*2105:.2f}")
print("="*60)

with open("teste_otimizado_10.json", 'w') as f:
    json.dump({"custo": total_cost, "links": len(resultados), "resultados": resultados}, f)
