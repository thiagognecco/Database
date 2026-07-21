#!/usr/bin/env python3
"""Versão rápida - inicia direto sem verificação"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"
INPUT_FILE = Path("dados/links_export.json")
OUTPUT_FILE = Path("dados/links_categorizado_overnight.json")

print("="*80)
print(f"PROCESSAMENTO RÁPIDO - {datetime.now().strftime('%H:%M:%S')}")
print("="*80)

# Carregar dados
with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

todos_links = data['links']
total = len(todos_links)
print(f"Total de links: {total}\n")

resultados = []
tempo_inicio = time.time()

for i in range(min(2, total)):  # Processar só 2 para testar
    link = todos_links[i]
    idx = i + 1
    titulo = link.get('titulo') or link['url'][:50]

    print(f"[{idx}] Processando: {titulo[:40]}...", flush=True)

    prompt = f"""Titulo: {titulo}
URL: {link['url']}

JSON:
{{"cat":"Tec","tags":["web"],"res":"link importante"}}"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False, "temperature": 0.2},
            timeout=300
        )

        if response.status_code == 200:
            resultado = json.loads(response.json()['response'].strip())
            resultados.append({"link_id": link['id'], "cat": resultado.get('cat'), "tags": resultado.get('tags', [])})
            print(f"     OK - Categoria: {resultado.get('cat')}")
        else:
            print(f"     ERRO HTTP {response.status_code}")

    except Exception as e:
        print(f"     ERRO: {str(e)[:50]}")

print(f"\nProcessados: {len(resultados)}/2")
print("="*80)
