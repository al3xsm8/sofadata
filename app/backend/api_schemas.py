from datetime import datetime

from pydantic import BaseModel


class TeamStatisticsResponse(BaseModel):
    team_id: int
    team_name: str
    is_home: bool
    goals: int | None
    half_time_goals: int | None
    second_half_goals: int | None
    result: str | None
    half_time_result: str | None
    second_half_result: str | None
    corners: int | None
    half_time_corners: int | None
    second_half_corners: int | None
    cards_total: int | None
    half_time_cards_total: int | None
    second_half_cards_total: int | None
    shots: int | None
    half_time_shots: int | None
    second_half_shots: int | None
    shots_on_target: int | None
    half_time_shots_on_target: int | None
    second_half_shots_on_target: int | None


class MatchResponse(BaseModel):
    id: int
    source_id: int
    match_date: datetime
    status: str | None
    round: int | None
    season_source_id: int | None
    competition: str | None
    home_team: str
    away_team: str
    home_goals: int | None
    away_goals: int | None
    home_half_time_goals: int | None
    away_half_time_goals: int | None
    home_second_half_goals: int | None
    away_second_half_goals: int | None
    team_statistics: list[TeamStatisticsResponse]
    analysis: "MatchAnalysisResponse | None" = None


class TeamAveragesResponse(BaseModel):
    team_id: int
    team_name: str
    matches_used: int
    window: str
    goals: float | None
    corners: float | None
    cards_total: float | None
    shots: float | None
    shots_on_target: float | None


class HeadToHeadResponse(BaseModel):
    matches_used: int
    home_wins: int
    draws: int
    away_wins: int
    meetings: list[dict]


class MatchAnalysisResponse(BaseModel):
    window: str
    limit: int | None
    season_source_id: int | None
    averages: list[TeamAveragesResponse]
    head_to_head: HeadToHeadResponse


class MatchListResponse(BaseModel):
    items: list[MatchResponse]
    total: int
    limit: int
    offset: int
