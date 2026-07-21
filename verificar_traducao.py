#!/usr/bin/env python3
import sqlite3
from pathlib import Path

db_path = Path("dados/banco.db")
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Contar resumos
cursor.execute("""
SELECT
  COUNT(*) as total,
  SUM(CASE WHEN resumo IS NULL OR resumo = '' THEN 1 ELSE 0 END) as sem_resumo
FROM links
""")

result = cursor.fetchone()
total, sem = result if result else (0, 0)
com_resumo = total - sem if total else 0

print("="*80)
print("VERIFICAÇÃO DO BANCO DE DADOS")
print("="*80)
print(f"Total de links: {total}")
print(f"Com resumo: {com_resumo}")
print(f"Sem resumo: {sem}")

# Mostrar alguns resumos
print("\n=== PRIMEIROS 5 RESUMOS ===")
cursor.execute("SELECT id, resumo FROM links WHERE resumo IS NOT NULL LIMIT 5")
for id, resumo in cursor.fetchall():
    preview = resumo[:80] if resumo else "(vazio)"
    lang = "PT-BR" if any(c in "àáâãäåèéêëìíîïòóôõöùúûüçñ" for c in resumo.lower()) else "EN?"
    print(f"ID {id} [{lang}]: {preview}...")

conn.close()
print("\n" + "="*80)
