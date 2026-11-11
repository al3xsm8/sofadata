from datetime import datetime, timezone

import pytest
import json
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.backend import models  # noqa: F401
from app.backend.database import Base
from app.backend.models import Competition, Match, Team, TeamMatchStatistics
from app.backend.ingestion import import_event, import_jsonl, import_raw_scraper_jsonl


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


def test_insert_and_query_match_with_two_team_rows(session: Session) -> None:
    competition = Competition(source_id=17, name="Premier League", country="England")
    home = Team(source_id=11, name="Coventry City")
    away = Team(source_id=39, name="Newcastle United")
    match = Match(
        source_id=16363874,
        competition=competition,
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
        TeamMatchStatistics(team=home, is_home=True, corners=2, shots=9, shots_on_target=6, cards_total=1),
        TeamMatchStatistics(team=away, is_home=False, corners=6, shots=19, shots_on_target=6, cards_total=1),
    ])
    session.add(match)
    session.commit()

    saved = session.scalar(select(Match).where(Match.source_id == 16363874))
    assert saved is not None
    assert saved.home_team.name == "Coventry City"
    assert saved.away_team.name == "Newcastle United"
    assert saved.home_goals == 4 and saved.away_goals == 1
    assert len(saved.team_statistics) == 2
    assert {row.is_home for row in saved.team_statistics} == {True, False}


def test_source_match_id_prevents_duplicate_match(session: Session) -> None:
    home = Team(source_id=11, name="Home")
    away = Team(source_id=39, name="Away")
    session.add_all([home, away])
    session.flush()
    date = datetime(2026, 10, 12, 19, 0, tzinfo=timezone.utc)
    session.add(Match(source_id=123, home_team=home, away_team=away, match_date=date))
    session.commit()

    session.add(Match(source_id=123, home_team=home, away_team=away, match_date=date))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_unique_team_statistics_per_match(session: Session) -> None:
    home = Team(source_id=11, name="Home")
    away = Team(source_id=39, name="Away")
    match = Match(
        source_id=123,
        home_team=home,
        away_team=away,
        match_date=datetime(2026, 10, 12, 19, 0, tzinfo=timezone.utc),
    )
    session.add(match)
    session.flush()
    session.add(TeamMatchStatistics(match=match, team=home, is_home=True))
    session.commit()

    session.add(TeamMatchStatistics(match=match, team=home, is_home=True))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def _sample_event() -> dict:
    return {
        "id": 16363874,
        "tournament_id": 17,
        "start_utc": "2026-10-12T19:00:00Z",
        "status": {"class": "completed"},
        "stage": {"id": 17, "name": "Premier League"},
        "round": {"number": 6},
        "participants": {
            "home": {"id": 11, "name": "Coventry City"},
            "away": {"id": 39, "name": "Newcastle United"},
        },
        "score": {"home": 4, "away": 1, "half_time": {"home": 1, "away": 0}},
    }


def _sample_slices(include_cards: bool = True) -> dict:
    def period(name: str, home: int, away: int, home_yellow: int, away_yellow: int,
               home_red: int = 0, away_red: int = 0) -> dict:
        statistics_items = [
            {"key": "cornerKicks", "homeValue": home, "awayValue": away},
            {"key": "totalShotsOnGoal", "homeValue": home + 7, "awayValue": away + 13},
            {"key": "shotsOnGoal", "homeValue": 6, "awayValue": 6},
        ]
        if include_cards:
            statistics_items.append({"key": "yellowCards", "homeValue": home_yellow, "awayValue": away_yellow})
            statistics_items.append({"key": "redCards", "homeValue": home_red, "awayValue": away_red})
        return {
            "period": name,
            "groups": [{"statisticsItems": statistics_items}],
        }
    return {
        "statistics": {"statistics": [
            period("ALL", 2, 6, 2, 1, 1, 0),
            period("1ST", 0, 3, 1, 0, 0, 0),
            period("2ND", 2, 3, 1, 1, 1, 0),
        ]},
        "incidents": {"incidents": []},
    }


def test_normalize_event_statistics_cards_and_repeat_import(session: Session) -> None:
    event = _sample_event()
    slices = _sample_slices()

    import_event(session, event, slices)
    session.commit()
    import_event(session, event, slices)
    session.commit()

    matches = session.query(Match).filter_by(source_id=16363874).all()
    assert len(matches) == 1
    assert len(matches[0].team_statistics) == 2
    by_side = {row.is_home: row for row in matches[0].team_statistics}
    assert by_side[True].corners == 2
    assert by_side[True].half_time_corners == 0
    assert by_side[True].cards_total == 3
    assert by_side[True].half_time_cards_total == 1
    assert by_side[True].second_half_cards_total == 2
    assert by_side[False].cards_total == 1
    assert by_side[False].half_time_cards_total == 0
    assert by_side[False].second_half_cards_total == 1


def test_missing_statistics_remain_null(session: Session) -> None:
    import_event(session, _sample_event(), _sample_slices(include_cards=False))
    session.commit()
    rows = session.query(TeamMatchStatistics).all()
    assert len(rows) == 2
    assert all(row.corners == 2 or row.corners == 6 for row in rows)
    assert all(row.cards_total is None for row in rows)


def test_partial_card_statistics_remain_null(session: Session) -> None:
    slices = _sample_slices()
    for period in slices["statistics"]["statistics"]:
        for group in period["groups"]:
            group["statisticsItems"] = [
                item for item in group["statisticsItems"] if item.get("key") != "redCards"
            ]
    import_event(session, _sample_event(), slices)
    session.commit()
    assert all(row.cards_total is None for row in session.query(TeamMatchStatistics).all())


def test_import_jsonl_uses_real_raw_slice_shape_and_tournament_id(session: Session, tmp_path) -> None:
    events_path = tmp_path / "events.jsonl"
    slices_path = tmp_path / "slices.jsonl"
    events_path.write_text(json.dumps(_sample_event()) + "\n", encoding="utf-8")
    slices = _sample_slices()
    rows = [
        {"event_id": 16363874, "key": key, "sub": "", "payload": payload}
        for key, payload in slices.items()
    ]
    slices_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    assert import_jsonl(session, events_path, slices_path) == 1
    match = session.query(Match).filter_by(source_id=16363874).one()
    assert match.competition.source_id == 17
    assert session.query(Competition).filter_by(source_id=1).count() == 0
    assert len(match.team_statistics) == 2


def test_reimport_without_optional_stat_preserves_previous_value(session: Session) -> None:
    import_event(session, _sample_event(), _sample_slices())
    session.commit()
    home = session.query(Team).filter_by(source_id=11).one()
    row = session.query(TeamMatchStatistics).filter_by(team_id=home.id).one()
    row.corners = 99
    session.commit()

    slices = _sample_slices(include_cards=False)
    for period in slices["statistics"]["statistics"]:
        for group in period["groups"]:
            group["statisticsItems"] = [
                item for item in group["statisticsItems"] if item.get("key") != "cornerKicks"
            ]
    import_event(session, _sample_event(), slices)
    session.commit()
    row = session.query(TeamMatchStatistics).filter_by(team_id=home.id).one()
    assert row.corners == 99

    import_event(session, _sample_event(), {})
    session.commit()
    row = session.query(TeamMatchStatistics).filter_by(team_id=home.id).one()
    assert row.corners == 99


def test_import_jsonl_rolls_back_on_invalid_event(session: Session, tmp_path) -> None:
    events_path = tmp_path / "events.jsonl"
    slices_path = tmp_path / "slices.jsonl"
    events_path.write_text(json.dumps({"id": 456}) + "\n", encoding="utf-8")
    slices_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="start_utc"):
        import_jsonl(session, events_path, slices_path)
    assert session.query(Match).count() == 0
    assert session.query(Team).count() == 0


def test_import_raw_scraper_export_with_event_and_statistics(session: Session, tmp_path) -> None:
    raw_path = tmp_path / "uefa-raw.jsonl"
    event = {
        "id": 777001,
        "startTimestamp": 1792000000,
        "status": {"type": "finished"},
        "roundInfo": {"round": 1},
        "tournament": {"uniqueTournament": {"id": 999, "name": "UEFA Champions League"}},
        "season": {"id": 1234},
        "homeTeam": {"id": 101, "name": "Home UCL"},
        "awayTeam": {"id": 202, "name": "Away UCL"},
        "homeScore": {"normaltime": 2, "period1": 1},
        "awayScore": {"normaltime": 1, "period1": 0},
    }
    stats = {"statistics": [
        {"period": period, "groups": [{"statisticsItems": [
            {"key": "cornerKicks", "homeValue": home, "awayValue": away},
            {"key": "totalShotsOnGoal", "homeValue": home + 4, "awayValue": away + 3},
            {"key": "shotsOnGoal", "homeValue": home + 2, "awayValue": away + 1},
            {"key": "yellowCards", "homeValue": 1, "awayValue": 2},
            {"key": "redCards", "homeValue": 0, "awayValue": 0},
        ]}]} for period, home, away in (("ALL", 5, 3), ("1ST", 2, 1), ("2ND", 3, 2))
    ]}
    raw_path.write_text("".join(json.dumps(row) + "\n" for row in (
        {"event_id": 777001, "key": "event", "payload": event},
        {"event_id": 777001, "key": "statistics", "payload": stats},
    )), encoding="utf-8")

    assert import_raw_scraper_jsonl(session, raw_path) == 1
    match = session.query(Match).filter_by(source_id=777001).one()
    home = next(row for row in match.team_statistics if row.is_home)
    assert match.competition.name == "UEFA Champions League"
    assert match.home_goals == 2 and match.away_goals == 1
    assert home.corners == 5 and home.half_time_corners == 2 and home.second_half_corners == 3
    assert home.cards_total == 1 and home.half_time_cards_total == 1
