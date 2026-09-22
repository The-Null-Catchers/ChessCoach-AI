from __future__ import annotations

import enum
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


def uuid4_str() -> str:
    return str(uuid.uuid4())


class JobStatus(str, enum.Enum):
    queued = 'queued'
    parsing = 'parsing'
    analyzing = 'analyzing'
    explaining = 'explaining'
    insights = 'insights'
    complete = 'complete'
    failed = 'failed'


class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    profile = relationship('Profile', back_populates='user', uselist=False, cascade='all, delete-orphan')


class Profile(Base):
    __tablename__ = 'profiles'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), unique=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user = relationship('User', back_populates='profile')


class ConnectedAccount(Base):
    __tablename__ = 'connected_accounts'
    __table_args__ = (UniqueConstraint('provider', 'provider_user_id', name='uq_provider_user'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    provider: Mapped[str] = mapped_column(String(32))
    provider_user_id: Mapped[str] = mapped_column(String(128))
    handle: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class Game(Base):
    __tablename__ = 'games'
    __table_args__ = (
        UniqueConstraint('user_id', 'fingerprint', name='uq_game_user_fingerprint'),
        Index('ix_games_user_played_at', 'user_id', 'played_at'),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    fingerprint: Mapped[str] = mapped_column(String(64))
    pgn: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(32), default='upload')
    event: Mapped[str | None] = mapped_column(String(255), nullable=True)
    site: Mapped[str | None] = mapped_column(String(255), nullable=True)
    white_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    black_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    result: Mapped[str | None] = mapped_column(String(16), nullable=True)
    eco: Mapped[str | None] = mapped_column(String(8), nullable=True)
    opening: Mapped[str | None] = mapped_column(String(255), nullable=True)
    played_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    analyzed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    moves = relationship('Move', back_populates='game', cascade='all, delete-orphan')


class Move(Base):
    __tablename__ = 'moves'
    __table_args__ = (UniqueConstraint('game_id', 'ply', name='uq_game_ply'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    game_id: Mapped[str] = mapped_column(ForeignKey('games.id', ondelete='CASCADE'), index=True)
    ply: Mapped[int] = mapped_column(Integer)
    san: Mapped[str] = mapped_column(String(32))
    uci: Mapped[str] = mapped_column(String(8))
    fen_before: Mapped[str] = mapped_column(String(120))
    fen_after: Mapped[str] = mapped_column(String(120))
    clock_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    game = relationship('Game', back_populates='moves')


class PositionAnalysis(Base):
    __tablename__ = 'position_analyses'
    __table_args__ = (UniqueConstraint('position_hash', 'engine_key', 'depth', name='uq_cached_position'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    position_hash: Mapped[str] = mapped_column(String(64), index=True)
    fen: Mapped[str] = mapped_column(String(120))
    engine_key: Mapped[str] = mapped_column(String(64), default='stockfish')
    depth: Mapped[int] = mapped_column(Integer)
    score_cp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mate_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    best_move_uci: Mapped[str | None] = mapped_column(String(8), nullable=True)
    pv_uci: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EngineAnalysis(Base):
    __tablename__ = 'engine_analyses'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    move_id: Mapped[str] = mapped_column(ForeignKey('moves.id', ondelete='CASCADE'), unique=True)
    eval_before_cp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eval_after_cp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mate_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mate_after: Mapped[int | None] = mapped_column(Integer, nullable=True)
    centipawn_loss: Mapped[int | None] = mapped_column(Integer, nullable=True)
    classification: Mapped[str] = mapped_column(String(24))
    best_move_uci: Mapped[str | None] = mapped_column(String(8), nullable=True)
    pv_uci: Mapped[str | None] = mapped_column(Text, nullable=True)
    depth: Mapped[int] = mapped_column(Integer)


class Mistake(Base):
    __tablename__ = 'mistakes'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    game_id: Mapped[str] = mapped_column(ForeignKey('games.id', ondelete='CASCADE'), index=True)
    move_id: Mapped[str] = mapped_column(ForeignKey('moves.id', ondelete='CASCADE'), unique=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    severity: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class PlayerWeakness(Base):
    __tablename__ = 'player_weaknesses'
    __table_args__ = (UniqueConstraint('user_id', 'category', name='uq_user_weakness'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    category: Mapped[str] = mapped_column(String(80))
    score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    sample_size: Mapped[int] = mapped_column(Integer)
    trend: Mapped[float] = mapped_column(Float, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Puzzle(Base):
    __tablename__ = 'puzzles'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    user_id: Mapped[str | None] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    source_game_id: Mapped[str | None] = mapped_column(ForeignKey('games.id', ondelete='SET NULL'), nullable=True)
    fen: Mapped[str] = mapped_column(String(120))
    solution_uci: Mapped[str] = mapped_column(Text)
    theme: Mapped[str] = mapped_column(String(80), index=True)
    difficulty: Mapped[int] = mapped_column(Integer, default=1200)
    source: Mapped[str] = mapped_column(String(32), default='user_game')


class PuzzleAttempt(Base):
    __tablename__ = 'puzzle_attempts'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    puzzle_id: Mapped[str] = mapped_column(ForeignKey('puzzles.id', ondelete='CASCADE'), index=True)
    correct: Mapped[bool] = mapped_column(Boolean)
    grade: Mapped[str] = mapped_column(String(16))
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AnalysisJob(Base):
    __tablename__ = 'analysis_jobs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    game_id: Mapped[str | None] = mapped_column(ForeignKey('games.id', ondelete='CASCADE'), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), default=JobStatus.queued.value, index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReviewState(Base):
    __tablename__ = 'review_states'
    __table_args__ = (UniqueConstraint('user_id', 'puzzle_id', name='uq_user_puzzle_review'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    puzzle_id: Mapped[str] = mapped_column(ForeignKey('puzzles.id', ondelete='CASCADE'), index=True)
    repetitions: Mapped[int] = mapped_column(Integer, default=0)
    interval_days: Mapped[int] = mapped_column(Integer, default=0)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)
    lapses: Mapped[int] = mapped_column(Integer, default=0)
    due_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TrainingPlan(Base):
    __tablename__ = 'training_plans'
    __table_args__ = (UniqueConstraint('user_id', 'week_start', name='uq_user_training_week'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    week_start: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(24), default='active')
    focus_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TrainingSession(Base):
    __tablename__ = 'training_sessions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    plan_id: Mapped[str] = mapped_column(ForeignKey('training_plans.id', ondelete='CASCADE'), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    session_type: Mapped[str] = mapped_column(String(40), index=True)
    focus_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    target_count: Mapped[int] = mapped_column(Integer, default=10)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    minutes_spent: Mapped[int] = mapped_column(Integer, default=0)


class AIExplanation(Base):
    __tablename__ = 'ai_explanations'
    __table_args__ = (UniqueConstraint('move_id', 'prompt_version', 'skill_band', name='uq_move_ai_explanation'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    move_id: Mapped[str] = mapped_column(ForeignKey('moves.id', ondelete='CASCADE'), index=True)
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(80))
    prompt_version: Mapped[str] = mapped_column(String(32))
    skill_band: Mapped[str] = mapped_column(String(24))
    explanation: Mapped[str] = mapped_column(Text)
    coaching_tip: Mapped[str] = mapped_column(Text)
    structured_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PlayerInsight(Base):
    __tablename__ = 'player_insights'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    insight_type: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    evidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
