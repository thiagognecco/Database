#!/usr/bin/env python3
"""Teste com 5 links: Categoria + Tags + Resumo melhorado"""

import json
import os
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

with open("dados/links_export.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

links = data['links'][:5]  # Apenas 5 links

print("="*80)
print("TESTE: 5 links com Haiku 4.5 (categoria + tags + resumo)")
print("="*80)
print(f"\nLinks para testar: {len(links)}\n")

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

total_input_tokens = 0
total_output_tokens = 0
total_cost = 0

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

Responda em JSON puro, sem explicações:
{{
  "categoria": "uma das: Tecnologia, IA, Educacao, Marketing, Negocios, Saude, Financas, Juridico, Automacao, Receita, SAP, Tutorial, Video, Artigo, Ferramenta",
  "tags": ["tag1", "tag2", "tag3"],
  "resumo_novo": "Resumo claro e conciso em 1-2 frases explicando o que eh o link."
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

        print(f"[{i}/5] OK {titulo[:45]}")
        print(f"        Categoria: {resultado.get('categoria')}")
        print(f"        Tags: {', '.join(resultado.get('tags', []))}")
        print(f"        Resumo: {resultado.get('resumo_novo')}")
        print(f"        Custo: ${custo:.6f}")
        print()

        resultados.append({
            'link_id': link['id'],
            'titulo': titulo,
            'url': link['url'],
            'categoria_antiga': link.get('categoria', ''),
            'categoria_nova': resultado.get('categoria'),
            'tags_novas': ', '.join(resultado.get('tags', [])),
            'resumo_novo': resultado.get('resumo_novo'),
            'custo': custo
        })

    except Exception as e:
        print(f"[{i}/5] ERR {str(e)[:50]}\n")

print("="*80)
print("RESULTADO")
print("="*80)
print(f"\nLinks processados: {len(resultados)}/5")
print(f"Total de tokens INPUT: {total_input_tokens}")
print(f"Total de tokens OUTPUT: {total_output_tokens}")
print(f"CUSTO TOTAL: ${total_cost:.4f}")

if len(resultados) > 0:
    custo_medio = total_cost / len(resultados)
    print(f"Custo medio por link: ${custo_medio:.6f}")
    custo_2105_estimado = custo_medio * 2105
    print(f"\nESTIMADA para 2105 links: ${custo_2105_estimado:.2f}")

print("="*80)

# Salvar resultado em JSON
with open("teste_5_resultado.json", 'w', encoding='utf-8') as f:
    json.dump(resultados, f, ensure_ascii=False, indent=2)
print(f"\nResultado salvo em: teste_5_resultado.json")
