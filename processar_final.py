#!/usr/bin/env python3
"""
Processamento final otimizado - versão simples e robusta
"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"
INPUT_FILE = Path("dados/links_export.json")
CHECKPOINT_FILE = Path("dados/checkpoint.json")
OUTPUT_FILE = Path("dados/links_processados_final.json")

print("="*80)
print("PROCESSAMENTO FINAL - " + datetime.now().strftime('%H:%M:%S'))
print("="*80)

# 1. Carregar dados
print("\n1. Carregando dados...")
with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)
todos_links = data['links']
total = len(todos_links)
print(f"   Total de links: {total}")

# 2. Carregar checkpoint
print("\n2. Carregando checkpoint...")
processados = []
proximo = 0

if CHECKPOINT_FILE.exists():
    with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
        ckpt = json.load(f)
    processados = ckpt.get('resultados', [])
    proximo = ckpt.get('proximo', 0)
    print(f"   Checkpoint encontrado: {len(processados)} links processados")
    print(f"   Continuar a partir de link: {proximo + 1}")
else:
    print(f"   Nenhum checkpoint. Começar do zero.")

# 3. Testar OLLAMA
print("\n3. Testando OLLAMA (pode demorar 60+ segundos na primeira carga)...")
try:
    resp = requests.post(
        OLLAMA_URL,
        json={"model": MODEL, "prompt": "test", "stream": False},
        timeout=180
    )
    if resp.status_code == 200:
        print("   OK - OLLAMA respondendo")
    else:
        print(f"   ERRO - Status {resp.status_code}")
        exit(1)
except Exception as e:
    print(f"   ERRO - {e}")
    print("   Certifique-se que OLLAMA está rodando: ollama serve")
    exit(1)

# 4. Processar
print(f"\n4. Iniciando processamento...")
print("="*80 + "\n")

tempo_inicio = time.time()
falhados = []
primeira_tentativa = True

for i in range(proximo, total):
    link = todos_links[i]
    idx = i + 1

    url = link.get('url', 'sem-url')
    if url is None:
        url = 'sem-url'
    titulo = link.get('titulo') or url[:50] or 'link-sem-titulo'

    prompt = f"""Responda APENAS com JSON valido:
{{"cat":"Tech","tags":[],"res":"descricao"}}

Titulo: {titulo[:100]}
URL: {url[:100]}"""

    try:
        timeout_val = 90 if primeira_tentativa else 45
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.35
            },
            timeout=timeout_val
        )
        primeira_tentativa = False

        if resp.status_code == 200:
            texto = resp.json()['response'].strip()

            if "{" in texto and "}" in texto:
                start = texto.find("{")
                end = texto.rfind("}") + 1
                json_str = texto[start:end]

                try:
                    res = json.loads(json_str)
                    processados.append({
                        "id": link['id'],
                        "cat": res.get('cat', 'Other'),
                        "tags": res.get('tags', []),
                        "res": res.get('res', '')
                    })

                    if idx % 10 == 0:
                        pct = (idx * 100) // total
                        tempo_decorrido = time.time() - tempo_inicio
                        vel = idx / tempo_decorrido if tempo_decorrido > 0 else 0
                        eta = (total - idx) / vel / 3600 if vel > 0 else 0
                        print(f"[{idx}/{total}] {pct}% | Velocidade: {vel:.2f} links/s | ETA: {eta:.1f}h")

                    if idx % 100 == 0:
                        with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
                            json.dump({'proximo': idx, 'resultados': processados}, f, ensure_ascii=False)
                        print(f"     Checkpoint salvo!")

                except json.JSONDecodeError:
                    falhados.append((idx, "JSON inválido"))
            else:
                falhados.append((idx, "JSON não encontrado"))
        else:
            falhados.append((idx, f"HTTP {resp.status_code}"))

    except requests.Timeout:
        falhados.append((idx, "Timeout"))
    except Exception as e:
        falhados.append((idx, str(e)[:30]))

# 5. Salvar resultado final
print("\n" + "="*80)
print("PROCESSAMENTO COMPLETO")
print("="*80)

tempo_total = (time.time() - tempo_inicio) / 3600

resultado = {
    'total_links': total,
    'processados': len(processados),
    'falhados': len(falhados),
    'tempo_horas': round(tempo_total, 2),
    'resultados': processados
}

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(resultado, f, ensure_ascii=False, indent=2)

print(f"Total: {total}")
print(f"Processados: {len(processados)}")
print(f"Falhados: {len(falhados)}")
print(f"Tempo: {tempo_total:.2f} horas")
print(f"Salvo em: {OUTPUT_FILE}")
print("="*80)
