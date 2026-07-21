#!/usr/bin/env python3
"""Exportar os 10 links testados em Excel"""

import json
import pandas as pd
from pathlib import Path
from anthropic import Anthropic
import os
from dotenv import load_dotenv

load_dotenv()

with open("dados/links_export.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

links = data['links'][:10]

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

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

        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()

        resultado = json.loads(response_text)

        resultados.append({
            'ID': link['id'],
            'Titulo': titulo,
            'URL': link['url'],
            'Categoria Atual': link.get('categoria', ''),
            'Categoria Nova': resultado.get('categoria', ''),
            'Tags Novas': ', '.join(resultado.get('tags', [])),
            'Resumo': resumo
        })

    except Exception as e:
        print(f"Erro no link {i}: {e}")

# Salvar em Excel
df = pd.DataFrame(resultados)
output_file = "teste_10_links.xlsx"
df.to_excel(output_file, index=False, engine='openpyxl')

print(f"\nResultado salvo em: {output_file}")
print(f"\n{df.to_string()}")
