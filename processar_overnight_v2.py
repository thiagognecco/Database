#!/usr/bin/env python3
"""Versão v2 - Prompt otimizado para forçar JSON do Mistral"""

import json
import os
import sys
import time
import requests
from pathlib import Path
from datetime import datetime

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"
INPUT_FILE = Path("dados/links_export.json")
CHECKPOINT_FILE = Path("dados/checkpoint_overnight.json")
OUTPUT_FILE = Path("dados/links_categorizado_overnight.json")
CHECKPOINT_INTERVAL = 50

print("="*80)
print(f"PROCESSAMENTO OVERNIGHT v2 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)
print(f"Modelo: {MODEL} (LOCAL)")
print(f"Arquivo de saída: {OUTPUT_FILE}\n")

# Carregar dados
with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

todos_links = data['links']
total = len(todos_links)

# Verificar checkpoint
processados_anteriores = []
proximo_indice = 0

if CHECKPOINT_FILE.exists():
    with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
        checkpoint = json.load(f)
    processados_anteriores = checkpoint.get('resultados', [])
    proximo_indice = checkpoint.get('proximo_indice', 0)
    print(f"RETOMANDO: {len(processados_anteriores)} links já processados\n")
else:
    print("Começando do zero\n")

resultados = processados_anteriores.copy()
tempo_inicio = time.time()

for i in range(proximo_indice, total):
    link = todos_links[i]
    idx_global = i + 1

    titulo = link.get('titulo') or link['url'][:80]

    # PROMPT OTIMIZADO - Força JSON
    prompt = f"""[INSTRUCTION]
You MUST respond with ONLY valid JSON, nothing else.
Do not explain, do not add text before or after.
Return exactly this format:
{{"cat":"VALUE","tags":["tag1","tag2"],"res":"SUMMARY"}}

[DATA]
Title: {titulo}
URL: {link['url']}

[CATEGORIES]
cat must be ONE of: Tec|IA|Edu|Mark|Neg|Sau|Fin|Jur|Auto|Rec|SAP|Tut|Vid|Art|Fer

Now respond with ONLY the JSON object:"""

    try:
        # Enviar para Mistral
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.1,  # Mais baixo = mais consistente
            },
            timeout=300
        )

        if response.status_code != 200:
            print(f"[{idx_global}/{total}] ERRO HTTP {response.status_code}")
            continue

        response_text = response.json()['response'].strip()

        # Tentar extrair JSON da resposta
        if "{" in response_text and "}" in response_text:
            # Extrair entre as primeiras { e última }
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            json_str = response_text[start:end]

            resultado = json.loads(json_str)

            resultados.append({
                "link_id": link['id'],
                "cat": resultado.get('cat', 'Outro'),
                "tags": resultado.get('tags', []),
                "res": resultado.get('res', '')
            })

            # Progress
            if idx_global % 10 == 0:
                tempo_decorrido = time.time() - tempo_inicio
                links_por_segundo = idx_global / tempo_decorrido if tempo_decorrido > 0 else 0
                eta_segundos = (total - idx_global) / links_por_segundo if links_por_segundo > 0 else 0
                eta_horas = eta_segundos / 3600
                pct = (idx_global * 100) // total
                print(f"[{idx_global}/{total}] {pct}% | ETA: {eta_horas:.1f}h | {titulo[:30]}")

            # Checkpoint
            if idx_global % CHECKPOINT_INTERVAL == 0:
                with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
                    json.dump({
                        'proximo_indice': idx_global,
                        'resultados': resultados,
                        'timestamp': datetime.now().isoformat(),
                        'progresso': f"{idx_global}/{total}"
                    }, f, ensure_ascii=False)

        else:
            print(f"[{idx_global}] ERRO JSON NAO ENCONTRADO")

    except json.JSONDecodeError as e:
        print(f"[{idx_global}] ERRO JSON: {str(e)[:30]}")
    except requests.Timeout:
        print(f"[{idx_global}] TIMEOUT")
    except Exception as e:
        print(f"[{idx_global}] ERRO: {str(e)[:30]}")

# Salvar resultado final
print("\n" + "="*80)
print("PROCESSAMENTO COMPLETO")
print("="*80)

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump({
        'total_links': total,
        'processados': len(resultados),
        'timestamp_inicio': datetime.fromtimestamp(tempo_inicio).isoformat(),
        'timestamp_fim': datetime.now().isoformat(),
        'tempo_total_horas': (time.time() - tempo_inicio) / 3600,
        'resultados': resultados
    }, f, ensure_ascii=False, indent=2)

print(f"Processados: {len(resultados)}/{total}")
print(f"Tempo total: {(time.time() - tempo_inicio) / 3600:.1f} horas")
print(f"Salvo em: {OUTPUT_FILE}")

# Limpar checkpoint
if CHECKPOINT_FILE.exists():
    CHECKPOINT_FILE.unlink()

print("="*80)
