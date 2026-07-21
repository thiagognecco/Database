#!/usr/bin/env python3
import sqlite3
from pathlib import Path

db_path = Path("dados/banco.db")
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Amostras de resumos
print("="*80)
print("AMOSTRA DE RESUMOS (verificar idioma)")
print("="*80)

cursor.execute("""
SELECT id, resumo FROM links
WHERE resumo IS NOT NULL AND resumo != ''
LIMIT 10
""")

for id, resumo in cursor.fetchall():
    # Detecção básica
    pt_chars = sum(1 for c in resumo.lower() if c in "àáâãäèéêëìíîïòóôõöùúûüçñ")
    is_pt = pt_chars > 0

    print(f"\nID {id}:")
    idioma = "PT-BR" if is_pt else "INGLES"
    print(f"[{idioma}]: {resumo[:120]}")

conn.close()
print("\n" + "="*80)
