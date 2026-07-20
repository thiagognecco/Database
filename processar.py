#!/usr/bin/env python3
import json, time, requests, sys
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

OLLAMA = "http://localhost:11434/api/generate"
MODEL = "mistral"
INPUT = Path("dados/links_export.json")
CHECKPOINT = Path("dados/checkpoint.json")
OUTPUT = Path("dados/resultado.json")

print("\n" + "="*70)
print("PROCESSAMENTO - 2105 LINKS COM FEEDBACK")
print("="*70 + "\n")

# Carregar
with open(INPUT, 'r', encoding='utf-8') as f:
    todos = json.load(f)['links']

total = len(todos)
print(f"[CARREGADO] {total} links\n")

# Checkpoint?
resultados = []
inicio = 0
if CHECKPOINT.exists():
    cp = json.load(open(CHECKPOINT, 'r', encoding='utf-8'))
    resultados = cp.get('resultados', [])
    inicio = cp.get('proximo', 0)
    print(f"[RETOMANDO] {len(resultados)} já processados\n")

t_inicio = time.time()

for i in range(inicio, total):
    link = todos[i]
    idx = i + 1
    titulo = link.get('titulo') or link['url'][:40]

    try:
        resp = requests.post(OLLAMA, json={
            "model": MODEL,
            "prompt": f"Titulo: {titulo}\nURL: {link['url']}\n\nJSON: {{\"cat\":\"Tec|IA|Edu\",\"tags\":[],\"res\":\"\"}}",
            "stream": False
        }, timeout=300)

        if resp.status_code == 200:
            txt = resp.json()['response'].strip()
            if "{" in txt:
                s = txt.find("{")
                e = txt.rfind("}") + 1
                res = json.loads(txt[s:e])
                resultados.append({
                    "id": link['id'],
                    "cat": res.get('cat', 'Outro'),
                    "tags": res.get('tags', []),
                    "res": res.get('res', '')
                })

                # Feedback
                pct = (idx * 100) // total
                tempo = time.time() - t_inicio
                vel = idx / tempo if tempo > 0 else 0
                eta = (total - idx) / vel if vel > 0 else 0

                barra = "=" * (pct // 5) + "-" * (20 - pct // 5)
                print(f"[{barra}] {pct:3d}% | {idx:4d}/{total} | {int(eta/60):3d}min | {titulo[:30]}")

                # Checkpoint
                if idx % 50 == 0:
                    json.dump({"proximo": idx, "resultados": resultados}, open(CHECKPOINT, 'w', encoding='utf-8'))
                    print(f"     >>> CHECKPOINT SALVO! <<<\n")
    except Exception as e:
        print(f"[ERRO {idx}] {str(e)[:40]}")

# Final
print("\n" + "="*70)
print(f"CONCLUIDO! {len(resultados)}/{total} links")
print(f"Tempo: {(time.time()-t_inicio)/60:.1f} minutos")
print("="*70 + "\n")

json.dump({
    "total": total,
    "processados": len(resultados),
    "tempo_min": (time.time()-t_inicio)/60,
    "resultados": resultados
}, open(OUTPUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

print(f"Salvo em: {OUTPUT}\n")

if CHECKPOINT.exists():
    CHECKPOINT.unlink()
