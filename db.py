import os
import uuid
from dotenv import load_dotenv
from models import Config, Job, MatchProfile, Resume, RunLog
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

load_dotenv()

engine = create_engine(
    os.environ["DATABASE_URL"].replace(
        "postgres://", "postgresql://"
    )  # standard URL fix
)


# Generic Helper for inserts
def insert_record(model_cls, data: dict):
    with Session(engine) as session:
        session.add(model_cls(**data))
        session.commit()


# Specific Inserts (1-liners reusing the helper)
insert_job = lambda data: insert_record(Job, data)
insert_match_profile = lambda data: insert_record(MatchProfile, data)
insert_run_log = lambda data: insert_record(RunLog, data)


# Queries
def get_config():
    with Session(engine) as session:
        return session.scalars(
            select(Config).order_by(Config.updated_at.desc()).limit(1)
        ).first()


def get_active_resume():
    with Session(engine) as session:
        return session.scalars(
            select(Resume).order_by(Resume.created_at.desc()).limit(1)
        ).first()


def job_exists_by_hash(job_key_hash: str) -> bool:
    with Session(engine) as session:
        stmt = select(
            select(Job).where(Job.job_key_hash == job_key_hash).exists()
        )
        return bool(session.scalar(stmt))


def get_jobs_without_match_profiles(resume_id: str, limit: int = 50):
    with Session(engine) as session:
        stmt = (
            select(Job)
            .outerjoin(
                MatchProfile,
                (Job.id == MatchProfile.job_id)
                & (MatchProfile.resume_id == uuid.UUID(str(resume_id))),
            )
            .where(MatchProfile.id.is_(None))
            .order_by(Job.discovered_at.desc())
            .limit(limit)
        )
        return session.scalars(stmt).all()