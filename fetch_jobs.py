import os
import requests
from dotenv import load_dotenv
import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert
from typing import Any, Dict, List
from models import Job
import hashlib

load_dotenv()

RAPIDAPI_KEY = os.getenv("JSEARCH_API_KEY")
RAPIDAPI_HOST = "jsearch.p.rapidapi.com"

# SQLAlchemy requires 'postgresql://' instead of 'postgres://'
DATABASE_URL = os.environ["DATABASE_URL"].replace("postgres://", "postgresql://")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#function to fetch jobs from the JSearch API
def fetch_jobs(query: str, page: int = 1, num_pages: int = 1, remote_only: bool = False):
    """
    Fetches job listings from the JSearch API.
    """
    url = "https://jsearch.p.rapidapi.com/search-v2"

    headers = {
        "content-type": "application/json",
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }

    params = {
        "query": query,
        "page": str(page),
        "num_pages": str(num_pages),
        "date_posted": "all",  # Options: all, today, 3days, week, month
        "remote_jobs_only": str(remote_only).lower()
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        raw_data = data.get("data", [])
        jobs = raw_data.get("jobs", []) 
        print(f"Fetched {len(jobs)} jobs for query '{query}' on page {page}.")
        print(jobs)
        return jobs

    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return []

# function to save jobs to database
def save_jobs_to_neon(jobs_data: List[Dict[str, Any]]) -> int:
    """Bulk inserts job records into the Neon PostgreSQL database."""
    records = [
        map_jsearch_to_dict(job)
        for job in jobs_data
        if (job.get("job_apply_link") or job.get("job_google_link"))
        and job.get("job_title")
        and job.get("employer_name")
    ]

    if not records:
        return 0

    stmt = (
        insert(Job)
        .values(records)
        .on_conflict_do_nothing(index_elements=["job_key_hash"])
    )

    with SessionLocal() as session:
        result = session.execute(stmt)
        session.commit()
        inserted_count = result.rowcount

    total_valid = len(records)
    skipped_count = max(0, total_valid - inserted_count)

    return inserted_count, skipped_count

def generate_job_key_hash(company: str, title: str, location: str) -> str:
    """Generates a consistent SHA256 hash based on company, title, and location."""
    raw_key = f"{company.strip().lower()}|{title.strip().lower()}|{(location or '').strip().lower()}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def map_jsearch_to_dict(job: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts and formats fields from a JSearch record to match the DB schema."""
    external_id = job.get("job_id")
    title = job.get("job_title", "").strip()
    company = job.get("employer_name", "").strip()

    # Determine location fallback
    city = job.get("job_city")
    country = job.get("job_country")
    if job.get("job_is_remote"):
        location = "Remote"
    elif job.get("job_location"):
        location = job.get("job_location")
    elif city or country:
        location = f"{city or ''}, {country or ''}".strip(", ")
    else:
        location = None

    url = job.get("job_apply_link") or job.get("job_google_link")
    jd_text = job.get("job_description")
    job_key_hash = generate_job_key_hash(company, title, location or "")

    return {
        "source": "jsearch",
        "external_id": external_id,
        "title": title,
        "company": company,
        "location": location,
        "url": url,
        "jd_text": jd_text,
        "job_key_hash": job_key_hash,
    }