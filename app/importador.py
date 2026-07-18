"""CSV importer with robust parsing."""
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Tuple
from sqlalchemy.orm import Session

from app.models import Link
from app.database import SessionLocal, DB_PATH


def parse_data_brasileira(data_str: str) -> datetime | None:
    """Parse DD/MM/AAAA format to datetime. Returns None if invalid."""
    if not data_str or not isinstance(data_str, str):
        return None

    data_str = data_str.strip()
    if not data_str:
        return None

    try:
        return datetime.strptime(data_str, "%d/%m/%Y")
    except ValueError:
        return None


def importar_csv(
    caminho_csv: str | Path,
    db: Session | None = None,
) -> dict:
    """
    Import CSV to database.

    Args:
        caminho_csv: Path to CSV file
        db: SQLAlchemy session (if None, creates temp session)

    Returns:
        {
            "success": bool,
            "imported": int,
            "duplicates": int,
            "errors": List[str],
            "ignored_duplicates": List[str]
        }
    """
    caminho = Path(caminho_csv)
    if not caminho.exists():
        return {
            "success": False,
            "imported": 0,
            "duplicates": 0,
            "errors": [f"Arquivo não encontrado: {caminho}"],
            "ignored_duplicates": [],
        }

    result = {
        "success": True,
        "imported": 0,
        "duplicates": 0,
        "errors": [],
        "ignored_duplicates": [],
    }

    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        urls_vistas = set()
        header_visto = False

        with open(caminho, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for linha_num, row in enumerate(reader, start=2):  # Start at 2 (after header)
                # Skip empty rows
                if not any(row.values()):
                    continue

                # Skip header rows (if repeated in middle)
                if row.get("LINK", "").upper() == "LINK":
                    continue

                # Extract fields
                url = row.get("LINK", "").strip()
                if not url:
                    result["errors"].append(f"Linha {linha_num}: URL vazia")
                    continue

                # Check for duplicates
                if url in urls_vistas:
                    result["duplicates"] += 1
                    result["ignored_duplicates"].append(url)
                    continue

                urls_vistas.add(url)

                # Check if already in DB
                existing = db.query(Link).filter(Link.url == url).first()
                if existing:
                    result["duplicates"] += 1
                    result["ignored_duplicates"].append(url)
                    continue

                # Parse date
                data_str = row.get("Data", "").strip()
                data = parse_data_brasileira(data_str) if data_str else None

                # Parse bot field
                bot_str = row.get("Bot", "").strip().lower()
                bot = bot_str in ("sim", "true", "1", "yes")

                try:
                    link = Link(
                        url=url,
                        titulo=row.get("Título", "").strip() or None,
                        resumo=row.get("Resumo (20 palavras)", "").strip() or None,
                        autor=row.get("Autor", "").strip() or None,
                        data=data,
                        plataforma=row.get("Plataforma", "").strip() or None,
                        categoria=row.get("Categoria", "").strip() or None,
                        tema=row.get("Tema", "").strip() or None,
                        confiabilidade=row.get("Confiabilidade", "Média").strip() or "Média",
                        bot=bot,
                    )
                    db.add(link)
                    result["imported"] += 1

                except Exception as e:
                    result["errors"].append(f"Linha {linha_num}: {str(e)}")

        db.commit()

    except Exception as e:
        result["success"] = False
        result["errors"].append(f"Erro ao processar CSV: {str(e)}")
        db.rollback()

    finally:
        if close_db:
            db.close()

    return result


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Uso: python importar.py <caminho_csv>")
        sys.exit(1)

    csv_path = sys.argv[1]
    result = importar_csv(csv_path)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["success"]:
        sys.exit(1)
