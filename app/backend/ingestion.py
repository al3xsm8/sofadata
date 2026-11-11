"""Normalize locally exported SofaScore JSONL and persist it to the application database."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

try:
    from app.backend.models import Competition, Match, Team, TeamMatchStatistics
except ModuleNotFoundError:
    from models import Competition, Match, Team, TeamMatchStatistics


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSON inválido em {path}, linha {line_number}: {exc.msg}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"Registro inválido em {path}, linha {line_number}: esperado um objeto JSON")
            records.append(record)
    return records


def _as_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _result(home: int | None, away: int | None) -> str | None:
    if home is None or away is None:
        return None
    return "Vitoria" if home > away else "Derrota" if home < away else "Empate"


def _find_statistic(payload: dict[str, Any], period_name: str, key: str) -> tuple[int | None, int | None]:
    periods = payload.get("statistics")
    if not isinstance(periods, list):
        return None, None
    period = next(
        (item for item in periods if isinstance(item, dict) and item.get("period") == period_name),
        None,
    )
    if not isinstance(period, dict):
        return None, None
    for group in period.get("groups", []):
        if not isinstance(group, dict):
            continue
        for item in group.get("statisticsItems", []):
            if isinstance(item, dict) and item.get("key") == key:
                return _as_int(item.get("homeValue")), _as_int(item.get("awayValue"))
    return None, None


def _get_team(session: Session, participant: dict[str, Any]) -> Team:
    source_id = _as_int(participant.get("id"))
    name = participant.get("name")
    if source_id is None or not isinstance(name, str) or not name.strip():
        raise ValueError("Participante sem ID ou nome válido na exportação normalizada")
    team = session.scalar(select(Team).where(Team.source_id == source_id))
    if team is None:
        team = Team(source_id=source_id, name=name)
        session.add(team)
    else:
        team.name = name
    return team


def _get_competition(session: Session, source_id: int | None, name: str | None) -> Competition | None:
    if source_id is None:
        return None
    competition = session.scalar(select(Competition).where(Competition.source_id == source_id))
    if competition is None:
        if not name:
            return None
        competition = Competition(source_id=source_id, name=name)
        session.add(competition)
    elif name:
        competition.name = name
    return competition


def import_event(session: Session, event: dict[str, Any], slices: dict[str, Any]) -> Match:
    """Upsert one match and its two team-statistics rows by source IDs."""
    source_id = _as_int(event.get("id"))
    start_utc = event.get("start_utc")
    if source_id is None or not isinstance(start_utc, str):
        raise ValueError("Evento precisa conter id inteiro e start_utc ISO-8601")
    match_date = datetime.fromisoformat(start_utc.replace("Z", "+00:00"))
    if match_date.tzinfo is None:
        raise ValueError("start_utc precisa incluir fuso horário")
    match_date = match_date.astimezone(timezone.utc)

    participants = event.get("participants") or {}
    home_data, away_data = participants.get("home"), participants.get("away")
    if not isinstance(home_data, dict) or not isinstance(away_data, dict):
        raise ValueError("Evento precisa conter participantes home e away")
    home_team = _get_team(session, home_data)
    away_team = _get_team(session, away_data)

    stage = event.get("stage") or {}
    competition = _get_competition(session, _as_int(event.get("tournament_id")), stage.get("name"))
    score = event.get("score") or {}
    half_time = score.get("half_time") or {}
    round_data = event.get("round") or {}
    status = event.get("status") or {}

    match = session.scalar(select(Match).where(Match.source_id == source_id))
    if match is None:
        match = Match(source_id=source_id, home_team=home_team, away_team=away_team, match_date=match_date)
        session.add(match)
    match.competition = competition
    match.season_source_id = _as_int(event.get("season_id"))
    match.home_team = home_team
    match.away_team = away_team
    match.match_date = match_date
    match.status = status.get("class") if isinstance(status, dict) else None
    match.round = _as_int(round_data.get("number"))
    match.home_goals = _as_int(score.get("home"))
    match.away_goals = _as_int(score.get("away"))
    match.home_half_time_goals = _as_int(half_time.get("home"))
    match.away_half_time_goals = _as_int(half_time.get("away"))
    home_second_half = (
        match.home_goals - match.home_half_time_goals
        if match.status == "completed" and match.home_goals is not None and match.home_half_time_goals is not None
        else None
    )
    away_second_half = (
        match.away_goals - match.away_half_time_goals
        if match.status == "completed" and match.away_goals is not None and match.away_half_time_goals is not None
        else None
    )
    if home_second_half is not None and away_second_half is not None:
        match.home_second_half_goals = home_second_half
        match.away_second_half_goals = away_second_half
    match.home_result = _result(match.home_goals, match.away_goals)
    match.home_half_time_result = _result(match.home_half_time_goals, match.away_half_time_goals)
    match.home_second_half_result = _result(home_second_half, away_second_half)
    match.last_updated_at = datetime.now(timezone.utc)
    session.flush()

    statistics_payload = slices.get("statistics")
    stat_values: dict[bool, dict[str, int | None]] = {True: {}, False: {}}
    mappings = {
        "corners": "cornerKicks",
        "shots": "totalShotsOnGoal",
        "shots_on_target": "shotsOnGoal",
    }
    for field, key in mappings.items():
        home_all, away_all = _find_statistic(statistics_payload or {}, "ALL", key)
        home_half, away_half = _find_statistic(statistics_payload or {}, "1ST", key)
        home_second, away_second = _find_statistic(statistics_payload or {}, "2ND", key)
        stat_values[True][field] = home_all
        stat_values[False][field] = away_all
        stat_values[True][f"half_time_{field}"] = home_half
        stat_values[False][f"half_time_{field}"] = away_half
        stat_values[True][f"second_half_{field}"] = home_second
        stat_values[False][f"second_half_{field}"] = away_second

    # The source reports yellow and red cards as separate team totals for each
    # period. Only sum when both are present so a partial response is not
    # mistaken for a complete card count.
    for period_name, field in (
        ("ALL", "cards_total"),
        ("1ST", "half_time_cards_total"),
        ("2ND", "second_half_cards_total"),
    ):
        home_yellow, away_yellow = _find_statistic(statistics_payload or {}, period_name, "yellowCards")
        home_red, away_red = _find_statistic(statistics_payload or {}, period_name, "redCards")
        for is_home, yellow, red in (
            (True, home_yellow, home_red),
            (False, away_yellow, away_red),
        ):
            stat_values[is_home][field] = yellow + red if yellow is not None and red is not None else None

    for is_home, team in ((True, home_team), (False, away_team)):
        row = session.scalar(
            select(TeamMatchStatistics).where(
                TeamMatchStatistics.match_id == match.id,
                TeamMatchStatistics.team_id == team.id,
            )
        )
        if row is None:
            row = TeamMatchStatistics(match=match, team=team, is_home=is_home)
            session.add(row)
        row.is_home = is_home
        for field, value in stat_values[is_home].items():
            if value is not None or getattr(row, field) is None:
                setattr(row, field, value)
        row.updated_at = datetime.now(timezone.utc)
    return match


def import_jsonl(session: Session, events_path: Path, slices_path: Path) -> int:
    try:
        event_records = read_jsonl(events_path)
        slice_records = read_jsonl(slices_path)
        slices_by_event: dict[int, dict[str, Any]] = {}
        for record in slice_records:
            event_id = _as_int(record.get("event_id", record.get("owner_id")))
            key = record.get("key")
            if event_id is not None and isinstance(key, str):
                slices_by_event.setdefault(event_id, {})[key] = record.get("payload")
        for event in event_records:
            event_id = _as_int(event.get("id"))
            if event_id is None:
                raise ValueError("Exportação events contém registro sem id inteiro")
            import_event(session, event, slices_by_event.get(event_id, {}))
        session.commit()
        return len(event_records)
    except Exception:
        session.rollback()
        raise


def import_raw_scraper_jsonl(session: Session, raw_path: Path) -> int:
    """Import original-data JSONL exports produced by the local scraper platform."""
    try:
        events: dict[int, dict[str, Any]] = {}
        slices: dict[int, dict[str, Any]] = {}
        for record in read_jsonl(raw_path):
            event_id = _as_int(record.get("event_id"))
            key = record.get("key")
            payload = record.get("payload")
            if event_id is None or not isinstance(key, str) or not isinstance(payload, dict):
                raise ValueError("Registro raw precisa conter event_id, key e payload objeto")
            if key == "event":
                events[event_id] = payload
            elif key == "statistics":
                slices.setdefault(event_id, {})["statistics"] = payload

        if not events:
            raise ValueError("O JSONL raw não contém registros event")

        imported = 0
        for event_id, payload in events.items():
            start_timestamp = _as_int(payload.get("startTimestamp"))
            if start_timestamp is None:
                raise ValueError(f"Evento {event_id} não contém startTimestamp válido")
            participants = {
                "home": payload.get("homeTeam"),
                "away": payload.get("awayTeam"),
            }
            home_score = payload.get("homeScore") or {}
            away_score = payload.get("awayScore") or {}
            status = payload.get("status") or {}
            event = {
                "id": event_id,
                "tournament_id": ((payload.get("tournament") or {}).get("uniqueTournament") or {}).get("id"),
                "season_id": (payload.get("season") or {}).get("id"),
                "start_utc": datetime.fromtimestamp(start_timestamp, tz=timezone.utc).isoformat(),
                "status": {"class": "completed" if status.get("type") == "finished" else status.get("type")},
                "stage": {"name": ((payload.get("tournament") or {}).get("uniqueTournament") or {}).get("name")},
                "round": {"number": (payload.get("roundInfo") or {}).get("round")},
                "participants": participants,
                "score": {
                    "home": home_score.get("normaltime", home_score.get("current")),
                    "away": away_score.get("normaltime", away_score.get("current")),
                    "half_time": {"home": home_score.get("period1"), "away": away_score.get("period1")},
                },
            }
            import_event(session, event, slices.get(event_id, {}))
            imported += 1
        session.commit()
        return imported
    except Exception:
        session.rollback()
        raise
