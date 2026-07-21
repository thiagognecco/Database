#!/usr/bin/env python3
"""
Mescla dados processados do JSON com banco de dados existente
- Substitui resumos pobres pelo do Mistral
- Adiciona links novos
- Consolida tudo no banco
"""

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
print("MESCLANDO DADOS PROCESSADOS COM BANCO EXISTENTE")
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

# 3. Mesclar dados
print("\n3. Mesclando dados...")
atualizados = 0
novos = 0
resumos_melhorados = 0

for res in resultados:
    link_id = res.get('id')
    categoria = str(res.get('cat', 'Outro'))
    tags_list = res.get('tags', [])
    resumo_novo = res.get('res', '')

    # Converter dict para string se necessário
    if isinstance(resumo_novo, dict):
        resumo_novo = resumo_novo.get('description', '') or str(resumo_novo)
    resumo_novo = str(resumo_novo) if resumo_novo else ''

    # Garantir tags como JSON string
    if isinstance(tags_list, str):
        tags_json = tags_list
    else:
        tags_json = json.dumps(tags_list if isinstance(tags_list, list) else [])

    # Encontrar link pela URL
    export_link = links_by_id.get(link_id)
    if not export_link:
        continue

    url = export_link['url']
    titulo = export_link.get('titulo', url[:50])

    link = db.query(Link).filter(Link.url == url).first()

    if link:
        # Link já existe - atualizar
        link.categoria = categoria
        link.tags = tags_json

        # Substituir resumo se o antigo é pobre
        resumo_antigo = link.resumo or ""
        if len(resumo_antigo) < 50 and len(resumo_novo) > len(resumo_antigo):
            link.resumo = resumo_novo
            resumos_melhorados += 1
        elif not resumo_antigo:
            link.resumo = resumo_novo

        link.atualizado_em = datetime.utcnow()
        atualizados += 1

        if atualizados % 100 == 0:
            print(f"   [{atualizados}] Atualizados...")

    else:
        # Link novo - inserir
        novo_link = Link(
            url=url,
            titulo=titulo,
            categoria=categoria,
            tags=tags_json,
            resumo=resumo_novo,
            criado_em=datetime.utcnow(),
            atualizado_em=datetime.utcnow()
        )
        db.add(novo_link)
        novos += 1

        if (atualizados + novos) % 100 == 0:
            print(f"   [{atualizados + novos}] Processados...")

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
print(f"Total de resultados: {len(resultados)}")
print(f"Links atualizados: {atualizados}")
print(f"Resumos melhorados: {resumos_melhorados}")
print(f"Links novos adicionados: {novos}")
print(f"Status: ✅ SUCESSO" if atualizados + novos > 0 else "❌ ERRO")
print("="*80)
