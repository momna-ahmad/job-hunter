# models.py
from datetime import datetime , timezone
from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict
import uuid
from sqlalchemy import DateTime, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
)


class Base(DeclarativeBase):
  pass

class AgentState(TypedDict):
  active_resume: Optional[Dict[str, Any]]
  config: Optional[Dict[str, Any]]
  discovered_job_count: int
  scored_jobs: List[Dict[str, Any]]  # [{job, match_score, ...}]
  selected_jobs: List[Dict[str, Any]]  # Top N eligible for application
  applied_jobs: List[str]  # IDs of jobs processed
  requires_approval: bool
  run_errors: List[str]

class Job(Base):
  __tablename__ = "jobs"

  id: Mapped[str] = mapped_column(
      UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
  )
  source: Mapped[str] = mapped_column(Text, default="jsearch")
  external_id: Mapped[str | None] = mapped_column(Text, nullable=True)
  title: Mapped[str] = mapped_column(Text, nullable=False)
  company: Mapped[str] = mapped_column(Text, nullable=False)
  location: Mapped[str | None] = mapped_column(Text, nullable=True)
  url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
  jd_text: Mapped[str | None] = mapped_column(Text, nullable=True)
  job_key_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
  discovered_at: Mapped[datetime] = mapped_column(
      DateTime(timezone=True), server_default=func.now()
  )

class Config(Base):
    __tablename__ = "config"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    plan: Mapped[str] = mapped_column(Text, default="free")
    max_requests_per_day: Mapped[int] = mapped_column(Integer, default=6)
    max_requests_per_month: Mapped[int] = mapped_column(Integer, default=200)
    keywords: Mapped[list] = mapped_column(JSONB, default=list)
    locations: Mapped[list] = mapped_column(JSONB, default=list)
    min_score_threshold: Mapped[float] = mapped_column(Numeric, default=70.0)
    require_human_confirmation: Mapped[bool] = mapped_column(default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Resume(Base):
    __tablename__ = "resumes"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    file_path: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True)
    parsed_text: Mapped[str] = mapped_column(Text)
    skills: Mapped[list | None] = mapped_column(JSONB, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

class MatchProfile(Base):
    __tablename__ = "match_profiles"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE")
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE")
    )
    overall_score: Mapped[float] = mapped_column(Numeric)
    semantic_score: Mapped[float | None] = mapped_column(Numeric, default=None)
    keyword_score: Mapped[float | None] = mapped_column(Numeric, default=None)
    skill_overlap: Mapped[dict | list | None] = mapped_column(
        JSONB, default=None
    )
    gap_analysis: Mapped[dict | list | None] = mapped_column(
        JSONB, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class RunLog(Base):
    __tablename__ = "run_logs"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    jobs_discovered: Mapped[int] = mapped_column(Integer, default=0)
    jobs_deduped_skipped: Mapped[int] = mapped_column(Integer, default=0)
    matches_computed: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[dict | list | None] = mapped_column(JSONB, default=None)