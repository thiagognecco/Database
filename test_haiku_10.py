#!/usr/bin/env python3
"""Teste: Categorizar 10 links com Haiku 4.5 (modelo mais barato)"""

import json
import os
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# Carregar 10 links aleatórios
with open("dados/links_export.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

links = data['links'][:10]  # Pega os primeiros 10

print("="*80)
print("TESTE: Categorizar 10 links com Haiku 4.5 (modelo mais barato)")
print("="*80)
print(f"\nLinks para testar: {len(links)}\n")

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

total_input_tokens = 0
total_output_tokens = 0
total_cost = 0

resultados = []

for i, link in enumerate(links, 1):
    titulo = link.get('titulo') or link.get('url', '')[:50]
    resumo = (link.get('resumo') or '')[:200]

    prompt = f"""Categorize este link e gere 3-5 tags relevantes.

Título: {titulo}
URL: {link['url']}
Resumo: {resumo}

Responda APENAS neste formato JSON, sem explicações:
{{
  "categoria": "escolha entre: Tecnologia, IA, Educação, Marketing, Negócios, Saúde, Finanças, Jurídico, Automação, Receita, SAP, Tutorial, Vídeo, Artigo, Ferramenta",
  "tags": ["tag1", "tag2", "tag3"]
}}"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = message.content[0].text

        # Limpar markdown se necessário
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()

        resultado = json.loads(response_text)

        # Calcular custos (Haiku 4.5)
        # Input: $0.80 per 1M tokens
        # Output: $4 per 1M tokens
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens

        input_cost = (input_tokens * 0.80) / 1_000_000
        output_cost = (output_tokens * 4) / 1_000_000
        custo = input_cost + output_cost

        total_input_tokens += input_tokens
        total_output_tokens += output_tokens
        total_cost += custo

        print(f"[{i}/10] OK {titulo[:50]}")
        print(f"        Categoria: {resultado.get('categoria')}")
        print(f"        Tags: {', '.join(resultado.get('tags', []))}")
        print(f"        Custo: ${custo:.6f} (input: {input_tokens}, output: {output_tokens})")
        print()

        resultados.append({
            'link_id': link['id'],
            'categoria': resultado.get('categoria'),
            'tags': resultado.get('tags', []),
            'custo': custo
        })

    except Exception as e:
        print(f"[{i}/10] ERR Erro: {e}\n")

print("="*80)
print("RESULTADO DO TESTE")
print("="*80)
print(f"\nLinks processados: {len(resultados)}/10")
print(f"Total de tokens INPUT: {total_input_tokens}")
print(f"Total de tokens OUTPUT: {total_output_tokens}")
print(f"Total de tokens: {total_input_tokens + total_output_tokens}")
print(f"\nCUSTO TOTAL: ${total_cost:.4f}")

if len(resultados) > 0:
    custo_medio = total_cost / len(resultados)
    print(f"Custo médio por link: ${custo_medio:.6f}")

    custo_2105_estimado = custo_medio * 2105
    print(f"\nESTIMADA para 2105 links: ${custo_2105_estimado:.2f}")
    print("="*80)
