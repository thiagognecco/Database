"""Database setup and management."""
import os
import sqlite3
from pathlib import Path
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base

# Usar PostgreSQL Railway como padrão, fallback para SQLite local
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:YZJGFupkhYxnmcsqwaiYkMLZTgSaORBa@tokaido.proxy.rlwy.net:52228/railway"
)

# Se DATABASE_URL começa com postgresql, usa PostgreSQL
if DATABASE_URL.startswith("postgresql"):
    engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
else:
    # Fallback para SQLite local (desenvolvimento)
    DADOS_DIR = Path(__file__).parent.parent / "dados"
    DADOS_DIR.mkdir(exist_ok=True)
    DB_PATH = DADOS_DIR / "banco.db"
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency for FastAPI to get DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_config(db, chave: str, default: str = None) -> str:
    """Get a config value from the database."""
    from app.models import Config
    row = db.query(Config).filter(Config.chave == chave).first()
    return row.valor if row else default


def set_config(db, chave: str, valor: str) -> None:
    """Set or update a config value in the database."""
    from app.models import Config
    from datetime import datetime
    row = db.query(Config).filter(Config.chave == chave).first()
    if row:
        row.valor = valor
        row.atualizado_em = datetime.utcnow()
    else:
        db.add(Config(chave=chave, valor=valor))
    db.commit()


def init_db():
    """Initialize database: create tables and FTS5 virtual table (SQLite only)."""
    # Create regular tables
    Base.metadata.create_all(bind=engine)

    # FTS5 is SQLite only - skip for PostgreSQL
    if not DATABASE_URL.startswith("postgresql"):
        # Create FTS5 virtual table for full-text search (SQLite)
        with engine.begin() as conn:
            # Drop if exists (for dev)
            try:
                conn.execute(text("DROP TABLE IF EXISTS links_fts"))
            except:
                pass

            # Create FTS5 table with unicode61 tokenizer
            conn.execute(text("""
                CREATE VIRTUAL TABLE links_fts USING fts5(
                    id UNINDEXED,
                    titulo,
                    resumo,
                    autor,
                    categoria,
                    tema,
                    tokenize = 'unicode61 remove_diacritics 2'
                )
            """))

        # Create trigger to sync FTS5 on INSERT
        try:
            conn.execute(text("""
                CREATE TRIGGER links_ai AFTER INSERT ON links BEGIN
                  INSERT INTO links_fts(id, titulo, resumo, autor, categoria, tema)
                  VALUES (new.id, new.titulo, new.resumo, new.autor, new.categoria, new.tema);
                END
            """))
        except:
            pass

        # Create trigger to sync FTS5 on UPDATE
        try:
            conn.execute(text("""
                CREATE TRIGGER links_au AFTER UPDATE ON links BEGIN
                  DELETE FROM links_fts WHERE id = old.id;
                  INSERT INTO links_fts(id, titulo, resumo, autor, categoria, tema)
                  VALUES (new.id, new.titulo, new.resumo, new.autor, new.categoria, new.tema);
                END
            """))
        except:
            pass

        # Create trigger to sync FTS5 on DELETE
        try:
            conn.execute(text("""
                CREATE TRIGGER links_ad AFTER DELETE ON links BEGIN
                  DELETE FROM links_fts WHERE id = old.id;
                END
            """))
        except:
            pass

        conn.commit()

        # Populate FTS5 with existing links if any
        try:
            from app.models import Link
            db = SessionLocal()
            links = db.query(Link).all()
            db.close()

            if links:
                for link in links:
                    try:
                        conn.execute(text("""
                            INSERT INTO links_fts(id, titulo, resumo, autor, categoria, tema)
                            VALUES (:id, :titulo, :resumo, :autor, :categoria, :tema)
                        """), {
                            "id": link.id,
                            "titulo": link.titulo or '',
                            "resumo": link.resumo or '',
                            "autor": link.autor or '',
                            "categoria": link.categoria or '',
                            "tema": link.tema or ''
                        })
                    except:
                        pass
                conn.commit()
        except:
            pass


def sanitize_fts_query(query: str) -> str:
    """Sanitize FTS5 query to prevent injection and DoS attacks."""
    import re

    query = query.strip()
    if not query:
        return ""

    # Remove dangerous FTS5 operators and limit query size
    query = re.sub(r'[{}()*&|^~\[\]"]+', ' ', query)
    query = re.sub(r'\s+', ' ', query)  # collapse whitespace

    # Limit to 200 chars
    if len(query) > 200:
        query = query[:200]

    return query.strip()


def search_fts(query: str, limit: int = 50, offset: int = 0):
    """
    Search using FTS5 with unicode61 tokenizer (ignores accents).
    Returns (results, total_count).
    """
    # Sanitize query first
    query = sanitize_fts_query(query)
    if not query:
        return [], 0

    try:
        with engine.begin() as conn:
            # Search query
            result = conn.execute(text("""
                SELECT id FROM links_fts
                WHERE links_fts MATCH :query
                LIMIT :limit OFFSET :offset
            """), {"query": query, "limit": limit, "offset": offset})

            ids = [row[0] for row in result.fetchall()]

            # Count total
            count_result = conn.execute(text("""
                SELECT COUNT(*) FROM links_fts
                WHERE links_fts MATCH :query
            """), {"query": query})

            total = count_result.scalar()

        # Fetch full link objects
        if ids:
            db = SessionLocal()
            try:
                from app.models import Link
                links = db.query(Link).filter(Link.id.in_(ids)).all()
                # Sort by order of appearance in search (preserve FTS5 relevance)
                id_order = {id_: idx for idx, id_ in enumerate(ids)}
                links.sort(key=lambda l: id_order.get(l.id, float('inf')))
                return [link.to_dict() for link in links], total
            finally:
                db.close()

        return [], total
    except Exception as e:
        import logging
        logging.error(f"FTS5 search error: {e}")
        return [], 0


def create_backup():
    """Create a timestamped backup of the database."""
    from shutil import copy
    from datetime import datetime

    backup_dir = DADOS_DIR / "backups"
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"banco_{timestamp}.db"

    try:
        copy(DB_PATH, backup_path)
        return {"backup": str(backup_path), "timestamp": timestamp, "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}


def restore_backup(backup_path: str):
    """Restore database from a backup."""
    from shutil import copy
    from pathlib import Path

    backup = Path(backup_path)
    if not backup.exists():
        return {"error": "Backup não encontrado", "success": False}

    try:
        copy(backup, DB_PATH)
        return {"message": "Backup restaurado com sucesso", "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}


def list_backups():
    """List all available backups."""
    backup_dir = DADOS_DIR / "backups"
    if not backup_dir.exists():
        return {"backups": []}

    backups = sorted(backup_dir.glob("banco_*.db"), reverse=True)
    return {
        "backups": [
            {"path": str(b), "name": b.name, "size": b.stat().st_size}
            for b in backups[:10]  # Last 10
        ]
    }


def setup_auto_backup():
    """Schedule daily backup at 2:00 AM."""
    from datetime import datetime, time
    import threading

    def backup_loop():
        while True:
            now = datetime.now()
            # Run backup at 2:00 AM
            if now.hour == 2 and now.minute == 0:
                create_backup()
                # Sleep until next day to avoid multiple backups
                import time as time_module
                time_module.sleep(3600)  # 1 hour
            import time as time_module
            time_module.sleep(60)  # Check every minute

    thread = threading.Thread(target=backup_loop, daemon=True)
    thread.start()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at: {DB_PATH}")
