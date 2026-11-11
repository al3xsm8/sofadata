from datetime import datetime, timezone
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.backend import models  # noqa: F401
from app.backend.database import Base
from app.backend.main import app
from app.backend.models import Competition, Match, Team, TeamMatchStatistics


@pytest.fixture
def client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        competition = Competition(source_id=17, name="Premier League")
        home = Team(source_id=11, name="Coventry City")
        away = Team(source_id=39, name="Newcastle United")
        match = Match(
            source_id=16363874,
            competition=competition,
            season_source_id=96668,
            home_team=home,
            away_team=away,
            match_date=datetime(2026, 10, 12, 19, 0, tzinfo=timezone.utc),
            status="completed",
            round=6,
            home_goals=4,
            away_goals=1,
            home_half_time_goals=1,
            away_half_time_goals=0,
        )
        match.team_statistics.extend([
            TeamMatchStatistics(team=home, is_home=True, corners=2, half_time_corners=0,
                                shots=9, half_time_shots=2, shots_on_target=6,
                                half_time_shots_on_target=2),
            TeamMatchStatistics(team=away, is_home=False, corners=6, half_time_corners=3,
                                shots=19, half_time_shots=9, shots_on_target=6,
                                half_time_shots_on_target=2),
        ])
        session.add(match)
        session.commit()

    def override_session():
        with Session(engine) as session:
            yield session

    from app.backend.api import get_session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_matches_returns_two_team_rows_and_nullable_cards(client: TestClient) -> None:
    response = client.get("/api/matches")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["home_team"] == "Coventry City"
    assert payload["items"][0]["home_goals"] == 4
    assert len(payload["items"][0]["team_statistics"]) == 2
    home = next(row for row in payload["items"][0]["team_statistics"] if row["is_home"])
    assert home["goals"] == 4
    assert home["cards_total"] is None


def test_list_filters_by_team_and_home_away(client: TestClient) -> None:
    response = client.get("/api/matches", params={"team": "Coventry", "is_home": "true"})
    assert response.status_code == 200
    assert response.json()["total"] == 1

    response = client.get("/api/matches", params={"team": "Coventry", "is_home": "false"})
    assert response.status_code == 200
    assert response.json()["total"] == 0

    opponent = client.get(
        "/api/matches",
        params={"team": "Coventry", "opponent": "Newcastle", "is_home": "true"},
    )
    assert opponent.status_code == 200
    assert opponent.json()["total"] == 1

    missing_team = client.get("/api/matches", params={"team": "No Such Team", "is_home": "true"})
    assert missing_team.status_code == 200
    assert missing_team.json()["total"] == 0


def test_list_filters_by_competition_name(client: TestClient) -> None:
    response = client.get("/api/matches", params={"competition": "Premier"})
    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_list_teams_and_filter_by_team_ids(client: TestClient) -> None:
    teams = client.get("/api/teams")
    assert teams.status_code == 200
    assert {item["name"] for item in teams.json()["items"]} == {"Coventry City", "Newcastle United"}

    home_id = next(item["id"] for item in teams.json()["items"] if item["name"] == "Coventry City")
    away_id = next(item["id"] for item in teams.json()["items"] if item["name"] == "Newcastle United")
    matches = client.get("/api/matches", params={"team_id": home_id, "opponent_id": away_id})
    assert matches.status_code == 200
    assert matches.json()["total"] == 1

    home_only = client.get("/api/matches", params={"team_id": home_id, "is_home": "true"})
    assert home_only.status_code == 200
    assert home_only.json()["total"] == 1

    away_only = client.get("/api/matches", params={"team_id": home_id, "is_home": "false"})
    assert away_only.status_code == 200
    assert away_only.json()["total"] == 0


def test_match_snapshot_is_static_friendly_and_precedes_match_detail_route(client: TestClient) -> None:
    response = client.get("/api/data/matches.json")
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == 1
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["home_team"] == "Coventry City"
    assert payload["items"][0]["analysis"] is None


def test_list_pagination_and_invalid_date_range(client: TestClient) -> None:
    assert client.get("/api/matches", params={"limit": 1, "offset": 1}).json()["items"] == []
    invalid = client.get("/api/matches", params={"from": "2026-10-13", "to": "2026-10-12"})
    assert invalid.status_code == 422


def test_get_match_and_not_found(client: TestClient) -> None:
    found = client.get("/api/matches/1")
    assert found.status_code == 200
    assert found.json()["away_team"] == "Newcastle United"
    missing = client.get("/api/matches/999")
    assert missing.status_code == 404


def test_match_analysis_last_n_averages_and_h2h_scope(client: TestClient) -> None:
    from app.backend.api import get_session

    override = app.dependency_overrides[get_session]
    generator = override()
    session = next(generator)
    try:
        from app.backend.models import Match

        home = session.query(Team).filter_by(source_id=11).one()
        away = session.query(Team).filter_by(source_id=39).one()
        competition = session.query(Competition).filter_by(source_id=17).one()
        previous = Match(
            source_id=20001,
            competition=competition,
            season_source_id=96668,
            home_team=away,
            away_team=home,
            match_date=datetime(2026, 9, 1, tzinfo=timezone.utc),
            status="completed",
            home_goals=0,
            away_goals=2,
        )
        previous.team_statistics.extend([
            TeamMatchStatistics(team=away, is_home=True, corners=4, shots=10, shots_on_target=4),
            TeamMatchStatistics(team=home, is_home=False, corners=3, shots=8, shots_on_target=3),
        ])
        other_season = Match(
            source_id=20002,
            competition=competition,
            season_source_id=76986,
            home_team=home,
            away_team=away,
            match_date=datetime(2025, 3, 1, tzinfo=timezone.utc),
            status="completed",
            home_goals=3,
            away_goals=0,
        )
        session.add_all([previous, other_season])
        session.commit()
    finally:
        generator.close()

    response = client.get("/api/matches/1", params={"window": "season"})
    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["season_source_id"] == 96668
    assert analysis["averages"][0]["matches_used"] == 1
    assert analysis["averages"][0]["goals"] == 2
    assert analysis["head_to_head"]["matches_used"] == 1
    assert analysis["head_to_head"]["home_wins"] == 1
    assert analysis["head_to_head"]["meetings"][0]["home_team"] == "Newcastle United"

    recent = client.get("/api/matches/1", params={"window": "last_n", "n": 1})
    assert recent.status_code == 200
    assert recent.json()["analysis"]["averages"][0]["matches_used"] == 1


def test_match_analysis_with_no_history_returns_empty_averages(client: TestClient) -> None:
    response = client.get("/api/matches/1", params={"window": "season"})
    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert all(team["matches_used"] == 0 for team in analysis["averages"])
    assert all(team["goals"] is None for team in analysis["averages"])
    assert analysis["head_to_head"]["matches_used"] == 0


def test_export_matches_returns_formatted_workbook(client: TestClient) -> None:
    response = client.get("/api/matches/export.xlsx")
    assert response.status_code == 200
    content_type = response.headers["content-type"]
    assert content_type.startswith("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    workbook = load_workbook(BytesIO(response.content), read_only=False, data_only=True)
    sheet = workbook["Banco"]
    assert sheet.max_column == 28
    assert sheet.max_row == 3
    header_row = [cell.value for cell in sheet[1]]
    assert header_row[:4] == ["Data", "Campeonato", "Ord", "Time"]
    assert header_row[7] == "Placar" and header_row[9] == f"Placar 1{chr(0x00ba)}t" and header_row[17] == f"Cart{chr(0x00e3)}o" and header_row[13] == "Gol"
    assert sheet.freeze_panes == "A2"
    assert sheet.auto_filter.ref is not None and sheet.auto_filter.ref.startswith("A1:")
    assert sheet.cell(2, 1).value is not None
    assert sheet.cell(2, 2).value == "Premier League"


def test_export_matches_applies_team_and_opponent_filters(client: TestClient) -> None:
    teams = client.get("/api/teams").json()["items"]
    home_id = next(team["id"] for team in teams if team["name"] == "Coventry City")
    away_id = next(team["id"] for team in teams if team["name"] == "Newcastle United")
    response = client.get(
        "/api/matches/export.xlsx",
        params={"team_id": home_id, "opponent_id": away_id},
    )
    assert response.status_code == 200
    sheet = load_workbook(BytesIO(response.content), data_only=True)["Banco"]
    assert sheet.max_row == 3
    assert [sheet.cell(row, 4).value for row in (2, 3)] == ["Coventry City", "Newcastle United"]
    assert all(sheet.cell(row, 1).value is not None for row in (2, 3))
    assert all(sheet.cell(row, 2).value == "Premier League" for row in (2, 3))


def test_collection_status_is_read_only_and_disabled_by_default(client: TestClient, monkeypatch) -> None:
    monkeypatch.delenv("COLLECTION_ENABLED", raising=False)
    response = client.get("/api/collection/status")
    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert response.json()["interval_minutes"] == 15
    assert response.json()["last_run"]["status"] is None


def test_collection_status_when_history_table_does_not_exist(monkeypatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    def override_session():
        with Session(engine) as session:
            yield session

    from app.backend.api import get_session

    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as test_client:
            response = test_client.get("/api/collection/status")
        assert response.status_code == 200
        assert response.json()["last_run"]["status"] is None
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
