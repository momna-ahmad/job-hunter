import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

@contextmanager
def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()

def get_config():
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM config ORDER BY updated_at DESC LIMIT 1")
            row = cur.fetchone()
            return dict(row) if row else None

def get_active_resume():
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM resumes
                ORDER BY created_at DESC
                LIMIT 1
            """)
            row = cur.fetchone()
            return dict(row) if row else None

def job_exists_by_hash(job_key_hash: str) -> bool:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS(SELECT 1 FROM jobs WHERE job_key_hash = %s)",
                (job_key_hash,),
            )
            return cur.fetchone()[0]

def insert_job(job: dict):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO jobs (
                    source, external_id, title, company, location,
                    url, jd_text, job_key_hash
                ) VALUES (
                    %(source)s, %(external_id)s, %(title)s, %(company)s,
                    %(location)s, %(url)s, %(jd_text)s, %(job_key_hash)s
                )
            """, job)
            conn.commit()

def insert_match_profile(profile: dict):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO match_profiles (
                    job_id, resume_id, overall_score,
                    semantic_score, keyword_score,
                    skill_overlap, gap_analysis
                ) VALUES (
                    %(job_id)s, %(resume_id)s, %(overall_score)s,
                    %(semantic_score)s, %(keyword_score)s,
                    %(skill_overlap)s, %(gap_analysis)s
                )
            """, profile)
            conn.commit()

def insert_run_log(log: dict):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO run_logs (
                    started_at, ended_at, jobs_discovered,
                    jobs_deduped_skipped, matches_computed, errors
                ) VALUES (
                    %(started_at)s, %(ended_at)s, %(jobs_discovered)s,
                    %(jobs_deduped_skipped)s, %(matches_computed)s, %(errors)s
                )
            """, log)
            conn.commit()

def get_jobs_without_match_profiles(resume_id: str, limit: int = 50):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT j.*
                FROM jobs j
                LEFT JOIN match_profiles mp
                  ON j.id = mp.job_id AND mp.resume_id = %s
                WHERE mp.id IS NULL
                ORDER BY j.discovered_at DESC
                LIMIT %s
            """, (resume_id, limit))
            rows = cur.fetchall()
            return [dict(r) for r in rows]