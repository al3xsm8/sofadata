import argparse
from pathlib import Path

try:
    from app.backend.database import SessionLocal
    from app.backend.ingestion import import_jsonl
except ModuleNotFoundError:
    from database import SessionLocal
    from ingestion import import_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa exportações locais JSONL do SofaScore Scraper.")
    parser.add_argument("--events", type=Path, required=True, help="JSONL normalizado do dataset events")
    parser.add_argument("--slices", type=Path, required=True, help="JSONL de fatias exportadas no schema raw")
    args = parser.parse_args()
    with SessionLocal() as session:
        count = import_jsonl(session, args.events, args.slices)
    print(f"Importação concluída: {count} partida(s).")


if __name__ == "__main__":
    main()
