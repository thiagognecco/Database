#!/usr/bin/env python3
"""
Migra dados do SQLite para PostgreSQL no Railway
"""

import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json
from datetime import datetime

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

from app.models import Base, Link, Config

print("="*80)
print("MIGRACAO: SQLite -> PostgreSQL")
print("="*80 + "\n")

# Connection strings
SQLITE_URL = "sqlite:///dados/banco.db"
POSTGRES_URL = "postgresql://postgres:YZJGFupkhYxnmcsqwaiYkMLZTgSaORBa@tokaido.proxy.rlwy.net:52228/railway"

print("1. Conectando ao SQLite (origem)...")
try:
    sqlite_engine = create_engine(SQLITE_URL)
    sqlite_session = sessionmaker(bind=sqlite_engine)()
    print("   [OK] SQLite conectado")
except Exception as e:
    print(f"   [ERRO] {e}")
    sys.exit(1)

print("\n2. Conectando ao PostgreSQL (destino)...")
try:
    pg_engine = create_engine(POSTGRES_URL)
    pg_engine.connect()
    print("   [OK] PostgreSQL conectado")
except Exception as e:
    print(f"   [ERRO] {e}")
    print("   Verifique a DATABASE_URL!")
    sys.exit(1)

print("\n3. Criando tabelas no PostgreSQL...")
try:
    Base.metadata.create_all(bind=pg_engine)
    print("   [OK] Tabelas criadas")
except Exception as e:
    print(f"   [ERRO] {e}")
    sys.exit(1)

print("\n4. Copiando dados...")
try:
    PGSession = sessionmaker(bind=pg_engine)
    pg_session = PGSession()

    # Copiar Links
    links = sqlite_session.query(Link).all()
    print(f"   Copiando {len(links)} links...")

    for link in links:
        novo_link = Link(
            id=link.id,
            url=link.url,
            titulo=link.titulo,
            resumo=link.resumo,
            autor=link.autor,
            data=link.data,
            plataforma=link.plataforma,
            categoria=link.categoria,
            tema=link.tema,
            confiabilidade=link.confiabilidade,
            bot=link.bot,
            favorito=link.favorito,
            tags=link.tags,
            rating=link.rating,
            lido=link.lido,
            criado_em=link.criado_em,
            atualizado_em=link.atualizado_em,
        )
        pg_session.merge(novo_link)

    pg_session.commit()
    print(f"   [OK] {len(links)} links copiados")

    # Copiar Configs
    configs = sqlite_session.query(Config).all()
    print(f"   Copiando {len(configs)} configs...")

    for config in configs:
        nova_config = Config(
            chave=config.chave,
            valor=config.valor,
            atualizado_em=config.atualizado_em,
        )
        pg_session.merge(nova_config)

    pg_session.commit()
    print(f"   [OK] {len(configs)} configs copiadas")

except Exception as e:
    print(f"   [ERRO] {e}")
    pg_session.rollback()
    sys.exit(1)
finally:
    pg_session.close()
    sqlite_session.close()

print("\n" + "="*80)
print("MIGRACAO COMPLETA!")
print("="*80)
print(f"\nDados migrados com sucesso!")
print("Próximo passo: Atualizar DATABASE_URL no Railway e fazer deploy")
print("\n" + "="*80)
