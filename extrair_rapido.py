#!/usr/bin/env python3
"""Extrair links do banco de dados"""

import sqlite3
import json
from pathlib import Path

DB_PATH = Path("dados/banco.db")
OUTPUT_FILE = Path("dados/links_export.json")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("""
    SELECT id, titulo, url, resumo, categoria, plataforma, tema
    FROM links
    ORDER BY id
""")

links = []
for row in cursor.fetchall():
    links.append({
        "id": row[0],
        "titulo": row[1],
        "url": row[2],
        "resumo": row[3],
        "categoria": row[4],
        "plataforma": row[5],
        "tema": row[6]
    })

conn.close()

output = {
    "extraction_date": "2026-07-20",
    "statistics": {"total_links": len(links)},
    "links": links
}

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"Extraído {len(links)} links")
