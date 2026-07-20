#!/usr/bin/env python3
"""Processar 2105 links com Ollama - COM FEEDBACK EM TEMPO REAL"""

import json
import time
import requests
import sys
from pathlib import Path
from datetime import datetime

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"
INPUT_FILE = Path("dados/links_export.json")
CHECKPOINT_FILE = Path("dados/checkpoint_com_feedback.json")
OUTPUT_FILE = Path("dados/links_categorizado_feedback.json")
CHECKPOINT_INTERVAL = 50

print("\n" + "="*80)
print("PROCESSAMENTO COM FEEDBACK - 2105 LINKS".center(80))
print("="*80 + "\n")

# Carregar dados
print("[1] Carregando links...")
with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

todos_links = data['links']
total = len(todos_links)
print(f"    ✅ {total} links carregados\n")

# Verificar checkpoint anterior
processados_anteriores = []
proximo_indice = 0

if CHECKPOINT_FILE.exists():
    print("[2] Retomando do checkpoint anterior...")
    with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
        checkpoint = json.load(f)
    processados_anteriores = checkpoint.get('resultados', [])
    proximo_indice = checkpoint.get('proximo_indice', 0)
    print(f"    ✅ {len(processados_anteriores)} links já processados")
    print(f"    ✅ Próximo: link #{proximo_indice + 1}\n")
else:
    print("[2] Começando do zero\n")

# Verificar Ollama
print("[3] Verificando Ollama em localhost:11434...")
try:
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    print(f"    ✅ Ollama respondendo (HTTP {response.status_code})\n")
except:
    print("    ❌ ERRO: Ollama não está rodando!")
    print("    Inicie com: ollama serve")
    sys.exit(1)

# Processar
print("[4] Iniciando processamento...\n")
resultados = processados_anteriores.copy()
tempo_inicio = time.time()

try:
    for i in range(proximo_indice, total):
        link = todos_links[i]
        idx = i + 1

        titulo = link.get('titulo') or link['url'][:50]

        prompt = f"""Titulo: {titulo}
URL: {link['url']}

JSON:
{{"cat":"Tec|IA|Edu|Mark|Neg|Sau|Fin|Jur|Auto|Rec|SAP|Tut|Vid|Art|Fer","tags":["t1","t2"],"res":"1-2 frases"}}"""

        try:
            # Processar
            response = requests.post(
                OLLAMA_URL,
                json={"model": MODEL, "prompt": prompt, "stream": False, "temperature": 0.2},
                timeout=300
            )

            if response.status_code != 200:
                print(f"    [{idx}/{total}] ❌ HTTP {response.status_code} - {titulo[:40]}")
                continue

            response_text = response.json()['response'].strip()

            # Extrair JSON
            if "{" in response_text and "}" in response_text:
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

                # Feedback
                pct = (idx * 100) // total
                tempo_decorrido = time.time() - tempo_inicio
                links_por_seg = idx / tempo_decorrido if tempo_decorrido > 0 else 0
                eta_seg = (total - idx) / links_por_seg if links_por_seg > 0 else 0
                eta_min = int(eta_seg / 60)

                # Barra de progresso
                barras = "=" * (pct // 5)
                vazios = "-" * (20 - pct // 5)

                print(f"    [{barras}{vazios}] {pct:3d}% | {idx:4d}/{total} | ETA: {eta_min:3d}min | {titulo[:35]}")

                # Checkpoint
                if idx % CHECKPOINT_INTERVAL == 0:
                    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
                        json.dump({
                            'proximo_indice': idx,
                            'resultados': resultados,
                            'timestamp': datetime.now().isoformat(),
                            'progresso': f"{idx}/{total}"
                        }, f, ensure_ascii=False)
                    print(f"         💾 Checkpoint salvo!")

        except json.JSONDecodeError:
            print(f"    [{idx}/{total}] ⚠️  JSON inválido")
        except requests.Timeout:
            print(f"    [{idx}/{total}] ⏱️  Timeout")
        except Exception as e:
            print(f"    [{idx}/{total}] ❌ Erro: {str(e)[:40]}")

except KeyboardInterrupt:
    print("\n\n❌ INTERROMPIDO PELO USUÁRIO")
    print(f"   Progresso: {len(resultados)}/{total} links")
    sys.exit(0)

# Salvar resultado final
print("\n" + "="*80)
print("PROCESSAMENTO COMPLETO!".center(80))
print("="*80)

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump({
        'total_links': total,
        'processados': len(resultados),
        'timestamp_inicio': datetime.fromtimestamp(tempo_inicio).isoformat(),
        'timestamp_fim': datetime.now().isoformat(),
        'tempo_total_min': (time.time() - tempo_inicio) / 60,
        'resultados': resultados
    }, f, ensure_ascii=False, indent=2)

print(f"\n✅ Processados: {len(resultados)}/{total} ({(len(resultados)*100)//total}%)")
print(f"✅ Tempo total: {(time.time() - tempo_inicio) / 60:.1f} minutos")
print(f"✅ Salvo em: {OUTPUT_FILE}")

# Limpar checkpoint
if CHECKPOINT_FILE.exists():
    CHECKPOINT_FILE.unlink()

print("\n" + "="*80 + "\n")
