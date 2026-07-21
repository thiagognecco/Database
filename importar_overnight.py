#!/usr/bin/env python3
"""Importar resultado do processamento overnight para o banco de dados"""

import json
import sqlite3
from pathlib import Path

INPUT_FILE = Path("dados/links_categorizado_overnight.json")
DB_PATH = Path("dados/banco.db")

print("Carregando resultado do processamento...")

if not INPUT_FILE.exists():
    print(f"ERRO: {INPUT_FILE} não encontrado")
    print("Execute processar_overnight.py primeiro")
    exit(1)

with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

resultados = data['resultados']
print(f"Encontrados {len(resultados)} links processados")

# Conectar ao banco
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Atualizar cada link
updated = 0
for resultado in resultados:
    try:
        cursor.execute("""
            UPDATE links
            SET categoria = ?, tags = ?
            WHERE id = ?
        """, (
            resultado.get('cat', 'Outros'),
            ','.join(resultado.get('tags', [])),
            resultado['link_id']
        ))
        updated += 1
    except Exception as e:
        print(f"Erro ao atualizar link {resultado['link_id']}: {e}")

conn.commit()
conn.close()

print("\n" + "="*60)
print("IMPORTAÇÃO COMPLETA!")
print("="*60)
print(f"Links atualizados: {updated}/{len(resultados)}")
print("="*60)
