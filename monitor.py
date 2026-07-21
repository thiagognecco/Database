#!/usr/bin/env python3
"""Monitor de progresso em tempo real"""

import json
import time
from pathlib import Path

OUTPUT_FILE = Path("dados/links_processado.json")

print("="*80)
print("MONITORANDO PROCESSAMENTO...")
print("="*80 + "\n")

ultima_verificacao = 0
while True:
    if OUTPUT_FILE.exists():
        try:
            with open(OUTPUT_FILE, 'r') as f:
                data = json.load(f)

            processados = data.get('processados', 0)
            total = data.get('total_links', 0)
            custo = data.get('custo_total', 0)
            erros = data.get('erros', 0)

            if processados > 0:
                pct = (processados * 100) // total
                tempo_por_link = 30 if processados == 0 else 30 / processados
                tempo_restante_segundos = (total - processados) * tempo_por_link
                tempo_restante_min = int(tempo_restante_segundos / 60)

                print(f"\r[{processados}/{total}] {pct}% | Custo: ${custo:.2f} | Erros: {erros} | ETA: {tempo_restante_min}min", end='', flush=True)
                ultima_verificacao = processados
        except:
            pass

    time.sleep(2)
