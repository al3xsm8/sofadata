from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

try:
    from app.backend.database import Base
except ModuleNotFoundError:
    from database import Base


class Competition(Base):
    __tablename__ = "competitions"
    __table_args__ = (UniqueConstraint("source_id", name="uq_competitions_source_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)

    matches: Mapped[list["Match"]] = relationship(back_populates="competition")


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("source_id", name="uq_teams_source_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    home_matches: Mapped[list["Match"]] = relationship(
        back_populates="home_team", foreign_keys="Match.home_team_id"
    )
    away_matches: Mapped[list["Match"]] = relationship(
        back_populates="away_team", foreign_keys="Match.away_team_id"
    )
    statistics: Mapped[list["TeamMatchStatistics"]] = relationship(back_populates="team")


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("source_id", name="uq_matches_source_id"),
        CheckConstraint("home_team_id <> away_team_id", name="ck_matches_distinct_teams"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    competition_id: Mapped[int | None] = mapped_column(ForeignKey("competitions.id"), nullable=True)
    season_source_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    match_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    round: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_half_time_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_half_time_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_second_half_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_second_half_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_result: Mapped[str | None] = mapped_column(String(20), nullable=True)
    home_half_time_result: Mapped[str | None] = mapped_column(String(20), nullable=True)
    home_second_half_result: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    competition: Mapped[Competition | None] = relationship(back_populates="matches")
    home_team: Mapped[Team] = relationship(back_populates="home_matches", foreign_keys=[home_team_id])
    away_team: Mapped[Team] = relationship(back_populates="away_matches", foreign_keys=[away_team_id])
    team_statistics: Mapped[list["TeamMatchStatistics"]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )


class TeamMatchStatistics(Base):
    __tablename__ = "team_match_statistics"
    __table_args__ = (
        UniqueConstraint("match_id", "team_id", name="uq_team_match_statistics_match_team"),
        CheckConstraint("shots >= 0 OR shots IS NULL", name="ck_team_stats_shots_nonnegative"),
        CheckConstraint("shots_on_target >= 0 OR shots_on_target IS NULL", name="ck_team_stats_sot_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    is_home: Mapped[bool] = mapped_column(Boolean, nullable=False)
    corners: Mapped[int | None] = mapped_column(Integer, nullable=True)
    half_time_corners: Mapped[int | None] = mapped_column(Integer, nullable=True)
    second_half_corners: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cards_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    half_time_cards_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    second_half_cards_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    half_time_shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    second_half_shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shots_on_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    half_time_shots_on_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    second_half_shots_on_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    match: Mapped[Match] = relationship(back_populates="team_statistics")
    team: Mapped[Team] = relationship(back_populates="statistics")


class CollectionRun(Base):
    __tablename__ = "collection_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    imported_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
