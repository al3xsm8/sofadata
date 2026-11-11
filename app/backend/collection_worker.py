"""Separate scheduled worker for importing local JSONL exports (no upstream network calls)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

try:
    from app.backend.database import Base, SessionLocal, engine
    from app.backend.ingestion import import_jsonl
    from app.backend.models import CollectionRun
except ModuleNotFoundError:
    from database import Base, SessionLocal, engine
    from ingestion import import_jsonl
    from models import CollectionRun


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _configured_path(key: str, default: str) -> Path:
    value = Path(os.getenv(key, default))
    return value if value.is_absolute() else (_project_root() / value).resolve()


def run_once() -> int:
    """Import configured local exports once; safe to invoke periodically from Task Scheduler."""
    enabled = os.getenv("COLLECTION_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        print("Agendador desativado (COLLECTION_ENABLED=false).")
        return 0

    Base.metadata.create_all(engine)
    events_file = _configured_path("COLLECTION_EVENTS_FILE", "data/evento-16363874.jsonl")
    slices_file = _configured_path("COLLECTION_SLICES_FILE", "data/fatias-16363874.jsonl")
    started = datetime.now(timezone.utc)

    with SessionLocal() as session:
        # PostgreSQL advisory lock prevents overlapping Task Scheduler invocations.
        if engine.dialect.name == "postgresql":
            acquired = session.execute(text("SELECT pg_try_advisory_lock(684229117)")).scalar_one()
            if not acquired:
                print("Outra execução do importador já está em andamento.")
                return 0
        run = CollectionRun(started_at=started, status="running")
        session.add(run)
        session.commit()
        try:
            count = import_jsonl(session, events_file, slices_file)
            run.finished_at = datetime.now(timezone.utc)
            run.status = "succeeded"
            run.imported_count = count
            session.commit()
            print(f"Importação agendada concluída: {count} partida(s).")
            return 0
        except Exception as exc:
            session.rollback()
            failed = session.get(CollectionRun, run.id)
            if failed is not None:
                failed.finished_at = datetime.now(timezone.utc)
                failed.status = "failed"
                failed.error_message = f"{type(exc).__name__}: {exc}"[:1000]
                session.commit()
            print(f"Falha na importação agendada: {type(exc).__name__}: {exc}")
            return 1
        finally:
            if engine.dialect.name == "postgresql" and session.is_active:
                session.execute(text("SELECT pg_advisory_unlock(684229117)"))
                session.commit()


if __name__ == "__main__":
    raise SystemExit(run_once())
