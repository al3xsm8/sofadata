from app.backend.collection_worker import run_once


def test_worker_does_not_run_when_disabled(monkeypatch, capsys) -> None:
    monkeypatch.delenv("COLLECTION_ENABLED", raising=False)
    assert run_once() == 0
    assert "desativado" in capsys.readouterr().out
