from datetime import date, datetime, time, timedelta, timezone
from io import BytesIO
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, inspect, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

try:
    from app.backend.api_schemas import (
        HeadToHeadResponse,
        MatchAnalysisResponse,
        MatchListResponse,
        MatchResponse,
        TeamAveragesResponse,
        TeamStatisticsResponse,
    )
    from app.backend.database import SessionLocal
    from app.backend.models import CollectionRun, Competition, Match, Team, TeamMatchStatistics
except ModuleNotFoundError:
    from api_schemas import (
        HeadToHeadResponse,
        MatchAnalysisResponse,
        MatchListResponse,
        MatchResponse,
        TeamAveragesResponse,
        TeamStatisticsResponse,
    )
    from database import SessionLocal
    from models import CollectionRun, Competition, Match, Team, TeamMatchStatistics

router = APIRouter(prefix="/api")


def get_session():
    with SessionLocal() as session:
        yield session


SessionDependency = Annotated[Session, Depends(get_session)]


def _as_response(match: Match, analysis: MatchAnalysisResponse | None = None) -> MatchResponse:
    def invert(result: str | None) -> str | None:
        return {"Vitoria": "Derrota", "Derrota": "Vitoria", "Empate": "Empate"}.get(result)

    stats = [
        TeamStatisticsResponse(
            team_id=row.team_id,
            team_name=row.team.name,
            is_home=row.is_home,
            goals=match.home_goals if row.is_home else match.away_goals,
            half_time_goals=match.home_half_time_goals if row.is_home else match.away_half_time_goals,
            second_half_goals=match.home_second_half_goals if row.is_home else match.away_second_half_goals,
            result=match.home_result if row.is_home else invert(match.home_result),
            half_time_result=match.home_half_time_result if row.is_home else invert(match.home_half_time_result),
            second_half_result=match.home_second_half_result if row.is_home else invert(match.home_second_half_result),
            corners=row.corners,
            half_time_corners=row.half_time_corners,
            second_half_corners=row.second_half_corners,
            cards_total=row.cards_total,
            half_time_cards_total=row.half_time_cards_total,
            second_half_cards_total=row.second_half_cards_total,
            shots=row.shots,
            half_time_shots=row.half_time_shots,
            second_half_shots=row.second_half_shots,
            shots_on_target=row.shots_on_target,
            half_time_shots_on_target=row.half_time_shots_on_target,
            second_half_shots_on_target=row.second_half_shots_on_target,
        )
        for row in sorted(match.team_statistics, key=lambda item: (not item.is_home, item.team_id))
    ]
    return MatchResponse(
        id=match.id,
        source_id=match.source_id,
        match_date=match.match_date,
        status=match.status,
        round=match.round,
        season_source_id=match.season_source_id,
        competition=match.competition.name if match.competition else None,
        home_team=match.home_team.name,
        away_team=match.away_team.name,
        home_goals=match.home_goals,
        away_goals=match.away_goals,
        home_half_time_goals=match.home_half_time_goals,
        away_half_time_goals=match.away_half_time_goals,
        home_second_half_goals=match.home_second_half_goals,
        away_second_half_goals=match.away_second_half_goals,
        team_statistics=stats,
        analysis=analysis,
    )


def _base_match_query():
    return select(Match).options(
        joinedload(Match.home_team),
        joinedload(Match.away_team),
        joinedload(Match.competition),
        selectinload(Match.team_statistics).joinedload(TeamMatchStatistics.team),
    )


def _match_conditions(
    *, date_from: date | None, date_to: date | None, competition_id: int | None,
    competition: str | None, team: str | None, opponent: str | None,
    team_id: int | None, opponent_id: int | None, is_home: bool | None,
    round_number: int | None, status: str | None,
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="'from' deve ser anterior ou igual a 'to'.")
    conditions = []
    if date_from:
        conditions.append(Match.match_date >= datetime.combine(date_from, time.min, tzinfo=timezone.utc))
    if date_to:
        conditions.append(Match.match_date < datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc))
    if competition_id is not None:
        conditions.append(Match.competition_id == competition_id)
    if competition:
        conditions.append(Match.competition.has(Competition.name.ilike(f"%{competition.strip()}%")))
    if round_number is not None:
        conditions.append(Match.round == round_number)
    if status is not None:
        conditions.append(Match.status == status)
    if team:
        pattern = f"%{team.strip()}%"
        conditions.append(or_(Match.home_team.has(Team.name.ilike(pattern)), Match.away_team.has(Team.name.ilike(pattern))))
    if team_id is not None:
        conditions.append(or_(Match.home_team_id == team_id, Match.away_team_id == team_id))
    if (opponent or opponent_id is not None) and team_id is None and not team:
        raise HTTPException(status_code=422, detail="O filtro adversário exige também o parâmetro 'team'.")
    if opponent or opponent_id is not None:
        opponent_condition = Team.id == opponent_id if opponent_id is not None else Team.name.ilike(f"%{opponent.strip()}%")
        if team_id is not None:
            predicate = or_(
                (Match.home_team_id == team_id) & Match.away_team.has(opponent_condition),
                (Match.away_team_id == team_id) & Match.home_team.has(opponent_condition),
            )
        else:
            team_pattern = f"%{team.strip()}%"
            predicate = or_(
                (Match.home_team.has(Team.name.ilike(team_pattern)) & Match.away_team.has(opponent_condition)),
                (Match.away_team.has(Team.name.ilike(team_pattern)) & Match.home_team.has(opponent_condition)),
            )
        conditions.append(predicate)
    if is_home is not None:
        if not team and team_id is None:
            raise HTTPException(status_code=422, detail="O filtro casa/fora exige também o parâmetro 'team'.")
        if team_id is not None:
            conditions.append((Match.home_team_id if is_home else Match.away_team_id) == team_id)
        else:
            side = Match.home_team if is_home else Match.away_team
            conditions.append(side.has(Team.name.ilike(f"%{team.strip()}%")))
    return conditions


@router.get("/matches", response_model=MatchListResponse)
def list_matches(
    session: SessionDependency,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    competition_id: int | None = Query(default=None, gt=0),
    competition: str | None = Query(default=None, min_length=1, max_length=200),
    team: str | None = Query(default=None, min_length=1, max_length=200),
    opponent: str | None = Query(default=None, min_length=1, max_length=200),
    team_id: int | None = Query(default=None, gt=0),
    opponent_id: int | None = Query(default=None, gt=0),
    is_home: bool | None = None,
    round_number: int | None = Query(default=None, alias="round", gt=0),
    status: str | None = Query(default=None, min_length=1, max_length=50),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> MatchListResponse:
    conditions = _match_conditions(
        date_from=date_from, date_to=date_to, competition_id=competition_id, competition=competition,
        team=team, opponent=opponent, team_id=team_id, opponent_id=opponent_id, is_home=is_home,
        round_number=round_number, status=status,
    )
    count_query = select(func.count()).select_from(Match)
    for condition in conditions:
        count_query = count_query.where(condition)

    total = session.scalar(count_query) or 0
    matches = session.scalars(
        _base_match_query().where(*conditions)
        .order_by(Match.match_date.desc(), Match.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return MatchListResponse(items=[_as_response(match) for match in matches], total=total, limit=limit, offset=offset)


@router.get("/matches/export.xlsx")
def export_matches_excel(
    session: SessionDependency,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    competition_id: int | None = Query(default=None, gt=0),
    competition: str | None = Query(default=None, min_length=1, max_length=200),
    team_id: int | None = Query(default=None, gt=0),
    opponent_id: int | None = Query(default=None, gt=0),
    is_home: bool | None = None,
    round_number: int | None = Query(default=None, alias="round", gt=0),
    status: str | None = Query(default=None, min_length=1, max_length=50),
):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    conditions = _match_conditions(
        date_from=date_from, date_to=date_to, competition_id=competition_id, competition=competition,
        team=None, opponent=None, team_id=team_id, opponent_id=opponent_id, is_home=is_home,
        round_number=round_number, status=status,
    )
    matches = session.scalars(
        _base_match_query().where(*conditions).order_by(Match.match_date.asc(), Match.id.asc())
    ).all()
    ordinal_mark = chr(0x00ba)
    tilde_a = chr(0x00e3)
    headers = [
        "Data", "Campeonato", "Ord", "Time", "Adversario", "Local", "Rodada", "Placar", "Resultado", f"Placar 1{ordinal_mark}t",
        f"Resultado 1{ordinal_mark}t", f"Placar 2{ordinal_mark}t", f"Resultado 2{ordinal_mark}t", "Gol", f"Gol 1{ordinal_mark}t", f"Gol 2{ordinal_mark}t", "Escanteios",
        f"Cart{tilde_a}o", "Chutes", "Chutes Gol", f"Escanteios 1{ordinal_mark}t", f"Cart{tilde_a}o 1{ordinal_mark}t", f"Chutes 1{ordinal_mark}t",
        f"Chutes Gol 1{ordinal_mark}t", f"Escanteios 2{ordinal_mark}t", f"Cart{tilde_a}o 2{ordinal_mark}t", f"Chutes 2{ordinal_mark}t", f"Chutes Gol 2{ordinal_mark}t",
    ]
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Banco"
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.alignment = Alignment(horizontal="center", vertical="center")
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{max(1, len(matches) * 2 + 1)}"
    def invert_result(result: str | None) -> str | None:
        return {"Vitoria": "Derrota", "Derrota": "Vitoria", "Empate": "Empate"}.get(result)

    for ordinal, match in enumerate(matches, start=1):
        for stat in sorted(match.team_statistics, key=lambda row: (not row.is_home, row.team_id)):
            opponent_team = match.away_team if stat.is_home else match.home_team
            own_result = match.home_result if stat.is_home else invert_result(match.home_result)
            half_result = match.home_half_time_result if stat.is_home else invert_result(match.home_half_time_result)
            second_result = match.home_second_half_result if stat.is_home else invert_result(match.home_second_half_result)
            half_score = (match.home_half_time_goals, match.away_half_time_goals)
            second_score = (match.home_second_half_goals, match.away_second_half_goals)
            values = [
                match.match_date.replace(tzinfo=None), match.competition.name if match.competition else None,
                ordinal, stat.team.name, opponent_team.name, "Casa" if stat.is_home else "Fora", match.round,
                f"{match.home_goals} - {match.away_goals}" if match.home_goals is not None and match.away_goals is not None else None,
                own_result,
                f"HT {half_score[0]} - {half_score[1]}" if None not in half_score else None,
                half_result,
                f"{second_score[0]} - {second_score[1]}" if None not in second_score else None,
                second_result,
                match.home_goals if stat.is_home else match.away_goals,
                match.home_half_time_goals if stat.is_home else match.away_half_time_goals,
                match.home_second_half_goals if stat.is_home else match.away_second_half_goals,
                stat.corners, stat.cards_total, stat.shots, stat.shots_on_target, stat.half_time_corners,
                stat.half_time_cards_total, stat.half_time_shots, stat.half_time_shots_on_target,
                stat.second_half_corners, stat.second_half_cards_total, stat.second_half_shots,
                stat.second_half_shots_on_target,
            ]
            sheet.append(values)
    widths = [19, 24, 8, 24, 24, 10, 10, 14, 13, 15, 16, 15, 16, 8, 10, 10, 12, 10, 10, 12, 16, 12, 12, 16, 16, 13, 12, 16]
    for row in sheet.iter_rows(min_row=2, min_col=1, max_col=1):
        row[0].number_format = "dd/mm/yyyy hh:mm"
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="center")
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="sofadata-partidas.xlsx"'},
    )


@router.get("/teams")
def list_teams(
    session: SessionDependency,
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=500, ge=1, le=1000),
) -> dict:
    query = select(Team).order_by(Team.name.asc()).limit(limit)
    if q and q.strip():
        query = query.where(Team.name.ilike(f"%{q.strip()}%"))
    teams = session.scalars(query).all()
    return {"items": [{"id": team.id, "name": team.name} for team in teams]}


@router.get("/data/matches.json")
def export_matches_snapshot(session: SessionDependency) -> dict:
    """Return a static-friendly complete snapshot for publishing with GitHub Pages."""
    matches = session.scalars(
        _base_match_query().order_by(Match.match_date.desc(), Match.id.desc())
    ).all()
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(matches),
        "items": [_as_response(match).model_dump(mode="json") for match in matches],
    }


@router.get("/matches/{match_id}", response_model=MatchResponse)
def get_match(
    match_id: int,
    session: SessionDependency,
    window: str = Query(default="last_n", pattern="^(last_n|season)$"),
    n: int = Query(default=10, ge=1, le=50),
) -> MatchResponse:
    match = session.scalar(_base_match_query().where(Match.id == match_id))
    if match is None:
        raise HTTPException(status_code=404, detail="Partida não encontrada.")
    analysis = _match_analysis(session, match, window=window, n=n)
    return _as_response(match, analysis)


def _match_analysis(session: Session, match: Match, *, window: str, n: int) -> MatchAnalysisResponse:
    averages: list[TeamAveragesResponse] = []
    for team, is_home in ((match.home_team, True), (match.away_team, False)):
        conditions = [
            Match.status == "completed",
            Match.match_date < match.match_date,
            or_(Match.home_team_id == team.id, Match.away_team_id == team.id),
        ]
        if window == "season":
            if match.competition_id is None or match.season_source_id is None:
                past_matches: list[Match] = []
            else:
                conditions.extend([
                    Match.competition_id == match.competition_id,
                    Match.season_source_id == match.season_source_id,
                ])
                past_matches = session.scalars(
                    select(Match).where(*conditions).order_by(Match.match_date.desc()).options(
                        selectinload(Match.team_statistics)
                    )
                ).all()
        else:
            past_matches = session.scalars(
                select(Match).where(*conditions).order_by(Match.match_date.desc()).limit(n).options(
                    selectinload(Match.team_statistics)
                )
            ).all()

        rows = [
            (past, stat)
            for past in past_matches
            for stat in past.team_statistics
            if stat.team_id == team.id
        ]
        denominator = len(rows)

        def mean_of(field: str) -> float | None:
            values = [getattr(stat, field) for _, stat in rows]
            values = [value for value in values if value is not None]
            return round(sum(values) / len(values), 2) if values else None

        goals_values = [
            (past.home_goals if stat.is_home else past.away_goals)
            for past, stat in rows
        ]
        goals_values = [value for value in goals_values if value is not None]
        averages.append(TeamAveragesResponse(
            team_id=team.id,
            team_name=team.name,
            matches_used=denominator,
            window=window,
            goals=round(sum(goals_values) / len(goals_values), 2) if goals_values else None,
            corners=mean_of("corners"),
            cards_total=mean_of("cards_total"),
            shots=mean_of("shots"),
            shots_on_target=mean_of("shots_on_target"),
        ))

    h2h_conditions = [
        Match.id != match.id,
        Match.status == "completed",
        Match.match_date < match.match_date,
        or_(
            (Match.home_team_id == match.home_team_id) & (Match.away_team_id == match.away_team_id),
            (Match.home_team_id == match.away_team_id) & (Match.away_team_id == match.home_team_id),
        ),
    ]
    if match.competition_id is not None:
        h2h_conditions.append(Match.competition_id == match.competition_id)
    if match.season_source_id is not None:
        h2h_conditions.append(Match.season_source_id == match.season_source_id)
    h2h_matches = session.scalars(
        select(Match).where(*h2h_conditions).order_by(Match.match_date.desc()).options(
            joinedload(Match.home_team), joinedload(Match.away_team)
        )
    ).all()
    home_wins = draws = away_wins = 0
    meetings = []
    for previous in h2h_matches:
        home_goals, away_goals = previous.home_goals, previous.away_goals
        if home_goals is not None and away_goals is not None:
            if home_goals == away_goals:
                draws += 1
            else:
                current_home_won = (
                    home_goals > away_goals
                    if previous.home_team_id == match.home_team_id
                    else away_goals > home_goals
                )
                if current_home_won:
                    home_wins += 1
                else:
                    away_wins += 1
        meetings.append({
            "match_date": previous.match_date,
            "home_team": previous.home_team.name,
            "away_team": previous.away_team.name,
            "home_goals": home_goals,
            "away_goals": away_goals,
        })
    return MatchAnalysisResponse(
        window=window,
        limit=n if window == "last_n" else None,
        season_source_id=match.season_source_id if window == "season" else None,
        averages=averages,
        head_to_head=HeadToHeadResponse(
            matches_used=len(h2h_matches),
            home_wins=home_wins,
            draws=draws,
            away_wins=away_wins,
            meetings=meetings,
        ),
    )


@router.get("/collection/status")
def collection_status(session: SessionDependency) -> dict:
    enabled = os.getenv("COLLECTION_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    interval = int(os.getenv("COLLECTION_INTERVAL_MINUTES", "15"))
    tables = inspect(session.get_bind()).get_table_names()
    latest = (
        session.scalar(select(CollectionRun).order_by(CollectionRun.started_at.desc()).limit(1))
        if CollectionRun.__tablename__ in tables
        else None
    )
    return {
        "enabled": enabled,
        "interval_minutes": interval,
        "last_run": {
            "started_at": latest.started_at if latest else None,
            "finished_at": latest.finished_at if latest else None,
            "status": latest.status if latest else None,
            "imported_count": latest.imported_count if latest else None,
            "error": latest.error_message if latest else None,
        },
    }
