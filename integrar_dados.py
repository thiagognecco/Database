#!/usr/bin/env python3
"""Integra os dados processados do Mistral ao banco de dados"""

import json
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
import sys

sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models import Link

LINKS_EXPORT = Path("dados/links_export.json")
LINKS_PROCESSADOS = Path("dados/links_processados_final.json")

print("="*80)
print("INTEGRANDO DADOS PROCESSADOS AO BANCO DE DADOS")
print("="*80 + "\n")

# 1. Carregar dados
print("1. Carregando arquivos...")
with open(LINKS_EXPORT, 'r', encoding='utf-8') as f:
    links_export = json.load(f)
links_by_id = {link['id']: link for link in links_export['links']}
print(f"   ✓ Links export: {len(links_by_id)} links")

with open(LINKS_PROCESSADOS, 'r', encoding='utf-8') as f:
    dados_processados = json.load(f)
resultados = dados_processados['resultados']
print(f"   ✓ Processados: {len(resultados)} links")

# 2. Conectar ao banco
print("\n2. Conectando ao banco de dados...")
db: Session = SessionLocal()
print("   ✓ Conectado")

# 3. Atualizar links
print("\n3. Atualizando links...")
atualizados = 0
nao_encontrados = 0

for res in resultados:
    link_id = res.get('id')
    categoria = str(res.get('cat', 'Outro'))
    tags_list = res.get('tags', [])
    resumo = res.get('res', '')

    # Converter dict para string se necessário
    if isinstance(resumo, dict):
        resumo = resumo.get('description', '') or str(resumo)
    resumo = str(resumo) if resumo else ''

    # Garantir tags como JSON string
    if isinstance(tags_list, str):
        tags_json = tags_list
    else:
        tags_json = json.dumps(tags_list if isinstance(tags_list, list) else [])

    # Encontrar link no banco
    link = db.query(Link).filter(Link.id == link_id).first()

    if not link:
        export_link = links_by_id.get(link_id)
        if export_link:
            url = export_link['url']
            link = db.query(Link).filter(Link.url == url).first()

    if link:
        link.categoria = categoria
        link.tags = tags_json
        link.resumo = resumo
        link.atualizado_em = datetime.utcnow()
        atualizados += 1

        if atualizados % 100 == 0:
            print(f"   [{atualizados}] Atualizados...")
    else:
        nao_encontrados += 1

try:
    db.commit()
    print(f"\n   ✓ Commit realizado com sucesso!")
except Exception as e:
    print(f"   ✗ Erro ao salvar: {e}")
    db.rollback()
finally:
    db.close()

print("\n" + "="*80)
print("RESULTADO")
print("="*80)
print(f"Total processados: {len(resultados)}")
print(f"Atualizados: {atualizados}")
print(f"Não encontrados: {nao_encontrados}")
print(f"Status: ✅ SUCESSO" if atualizados > 0 else "❌ ERRO")
print("="*80)
