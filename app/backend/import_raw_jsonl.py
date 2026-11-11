import argparse
from pathlib import Path

try:
    from app.backend.database import SessionLocal
    from app.backend.ingestion import import_raw_scraper_jsonl
except ModuleNotFoundError:
    from database import SessionLocal
    from ingestion import import_raw_scraper_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa um export JSONL raw do SofaScore Scraper.")
    parser.add_argument("--raw", type=Path, required=True, help="Caminho do JSONL exportado em Original SofaScore data")
    args = parser.parse_args()
    with SessionLocal() as session:
        count = import_raw_scraper_jsonl(session, args.raw)
    print(f"Importação concluída: {count} partida(s) processada(s).")


if __name__ == "__main__":
    main()
