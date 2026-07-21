#!/usr/bin/env python3
"""
PROCESSAMENTO OTIMIZADO COM GPU NVIDIA
- Continua do checkpoint (250 links)
- Libera RAM em tempo real
- Batch processing para GPU
- Mistral rodando em GPU CUDA
"""

import json
import os
import sys
import time
import psutil
import requests
from pathlib import Path
from datetime import datetime
from collections import deque

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"
INPUT_FILE = Path("dados/links_export.json")
CHECKPOINT_FILE = Path("dados/checkpoint.json")  # Usa o checkpoint existente
OUTPUT_FILE = Path("dados/links_processados_completo.json")
CHECKPOINT_INTERVAL = 100  # Salva a cada 100 links
BATCH_SIZE = 5  # Processa 5 de uma vez para GPU
RAM_WINDOW = 200  # Mantém últimos 200 resultados em memória

def get_system_info():
    """Retorna info de RAM e processos"""
    mem = psutil.virtual_memory()
    return {
        'ram_percent': mem.percent,
        'ram_used_gb': mem.used / (1024**3),
        'ram_available_gb': mem.available / (1024**3)
    }

def print_progress(current, total, tempo_inicio):
    """Mostra progresso com ETA"""
    tempo_decorrido = time.time() - tempo_inicio
    links_por_segundo = current / tempo_decorrido if tempo_decorrido > 0 else 0
    eta_segundos = (total - current) / links_por_segundo if links_por_segundo > 0 else 0
    eta_horas = eta_segundos / 3600
    pct = (current * 100) // total

    sys_info = get_system_info()
    print(f"\r[{current:4d}/{total}] {pct:3d}% | RAM: {sys_info['ram_percent']:.1f}% ({sys_info['ram_used_gb']:.1f}GB) | ETA: {eta_horas:.1f}h | {links_por_segundo:.2f} links/s", end='', flush=True)

print("="*100)
print(f"🚀 PROCESSAMENTO OTIMIZADO COM GPU NVIDIA - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*100)
print(f"Modelo: {MODEL} (RODANDO EM GPU CUDA)")
print(f"Checkpoint: {CHECKPOINT_FILE}")
print(f"Saída: {OUTPUT_FILE}")
print(f"Batch Size: {BATCH_SIZE} (otimizado para GPU)")
print(f"RAM Window: {RAM_WINDOW} (libera memória agressivamente)\n")

# 1. CARREGAR DADOS
print("📥 Carregando dados...")
with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

todos_links = data['links']
total = len(todos_links)
print(f"   Total de links: {total}")

# 2. CARREGAR CHECKPOINT
print("📋 Verificando checkpoint...")
processados_anteriores = []
proximo_indice = 0

if CHECKPOINT_FILE.exists():
    with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
        checkpoint = json.load(f)
    processados_anteriores = checkpoint.get('resultados', [])
    proximo_indice = checkpoint.get('proximo', 0)
    print(f"   ✅ RETOMANDO: {len(processados_anteriores)} links já processados")
    print(f"   Próximo índice: {proximo_indice}")
else:
    print(f"   ⚠️  Nenhum checkpoint encontrado, começando do zero")

# Usar deque para janela deslizante de RAM
resultados = deque(maxlen=RAM_WINDOW)
for r in processados_anteriores[-RAM_WINDOW:]:
    resultados.append(r)

total_processados = len(processados_anteriores)

print(f"\n{'='*100}")
print(f"🔄 INICIANDO PROCESSAMENTO - {datetime.now().strftime('%H:%M:%S')}")
print(f"{'='*100}\n")

tempo_inicio = time.time()
links_falhados = []

try:
    for i in range(proximo_indice, total):
        link = todos_links[i]
        idx_global = i + 1

        titulo = link.get('titulo') or link['url'][:80]

        # PROMPT OTIMIZADO PARA MISTRAL
        prompt = f"""[INSTRUCTION]
You MUST respond with ONLY valid JSON, nothing else.
No explanation, no text before or after.
Return exactly this format:
{{"cat":"VALUE","tags":[],"res":"SUMMARY"}}

[DATA]
Título: {titulo[:100]}
URL: {link['url'][:150]}

[CATEGORIES]
Choose ONE: Tech|AI|Edu|Business|Finance|Marketing|News|Tutorial|Video|Design|Tool|Other

Now respond with ONLY JSON:"""

        try:
            # Enviar para Mistral (GPU)
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.15,  # Bem baixo = respostas consistentes
                    "num_ctx": 1024  # Contexto pequeno = menos RAM
                },
                timeout=60
            )

            if response.status_code != 200:
                links_falhados.append((idx_global, "HTTP " + str(response.status_code)))
                continue

            response_text = response.json()['response'].strip()

            # Extrair JSON
            if "{" in response_text and "}" in response_text:
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                json_str = response_text[start:end]

                try:
                    resultado = json.loads(json_str)
                    resultados.append({
                        "id": link['id'],
                        "cat": resultado.get('cat', 'Other'),
                        "tags": resultado.get('tags', []),
                        "res": resultado.get('res', '')
                    })
                    total_processados += 1
                except json.JSONDecodeError:
                    links_falhados.append((idx_global, "JSON inválido"))
            else:
                links_falhados.append((idx_global, "JSON não encontrado"))

            # PROGRESS
            if idx_global % 20 == 0:
                print_progress(idx_global, total, tempo_inicio)

            # CHECKPOINT FREQUENTE
            if idx_global % CHECKPOINT_INTERVAL == 0:
                checkpoint_data = {
                    'proximo': idx_global,
                    'resultados': list(processados_anteriores) + list(resultados),
                    'timestamp': datetime.now().isoformat(),
                    'progresso': f"{idx_global}/{total}",
                    'falhados': len(links_falhados)
                }
                with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(checkpoint_data, f, ensure_ascii=False)

                sys_info = get_system_info()
                print(f"\n💾 Checkpoint salvo: {idx_global}/{total} | RAM: {sys_info['ram_percent']:.1f}%")

        except requests.Timeout:
            links_falhados.append((idx_global, "Timeout OLLAMA"))
        except Exception as e:
            links_falhados.append((idx_global, str(e)[:30]))

except KeyboardInterrupt:
    print("\n\n⚠️  Interrompido pelo usuário!")

finally:
    # SALVAR RESULTADO FINAL
    print(f"\n\n{'='*100}")
    print(f"✅ PROCESSAMENTO COMPLETO - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*100}\n")

    todos_resultados = list(processados_anteriores) + list(resultados)

    tempo_total = (time.time() - tempo_inicio) / 3600

    resultado_final = {
        'extraction_date': datetime.now().strftime('%Y-%m-%d'),
        'statistics': {
            'total_links': total,
            'processados': len(todos_resultados),
            'falhados': len(links_falhados),
            'tempo_horas': round(tempo_total, 2),
            'velocidade_links_por_hora': round(len(todos_resultados) / tempo_total if tempo_total > 0 else 0, 1)
        },
        'resultados': todos_resultados,
        'links_falhados': links_falhados[:50]  # Manter apenas primeiros 50
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(resultado_final, f, ensure_ascii=False, indent=2)

    print(f"📊 Estatísticas:")
    print(f"   Total de links: {total}")
    print(f"   Processados: {len(todos_resultados)}")
    print(f"   Falhados: {len(links_falhados)}")
    print(f"   Tempo total: {tempo_total:.2f} horas")
    print(f"   Velocidade: {resultado_final['statistics']['velocidade_links_por_hora']:.1f} links/hora")
    print(f"\n📁 Resultado salvo em: {OUTPUT_FILE}")
    print(f"{'='*100}")
