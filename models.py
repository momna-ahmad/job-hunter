# models.py
from datetime import datetime
from sqlalchemy import DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
  pass


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