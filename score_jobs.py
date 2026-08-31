# score_jobs.py
import os
from datetime import datetime
from dotenv import load_dotenv
from db import (
    get_active_resume,
    get_jobs_without_match_profiles,
    insert_match_profile,
    insert_run_log,
)
from matcher import compute_match_scores

load_dotenv()

RESUME_FILE_PATH = os.getenv("RESUME_FILE_PATH", "./resumes/my_resume.txt")


def load_resume_text_from_file() -> str:
    with open(RESUME_FILE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def score_jobs(limit: int = 100):
    """
    Score jobs for the active resume:
      - Fetch up to `limit` jobs without match profiles.
      - Compute match scores using the extensive matcher.
      - Insert match profiles into the DB.
      - Log the run.
    """
    started_at = datetime.utcnow().isoformat()

    resume = get_active_resume()
    if not resume:
        raise RuntimeError(
            "No resume found in DB. Please insert at least one row into the resumes table."
        )

    # Prefer parsed_text from DB; fallback to file if needed
    resume_text = resume.parsed_text or load_resume_text_from_file()
    resume_skills = resume.skills or []

    # Fetch jobs that don't have a match profile for this resume
    jobs = get_jobs_without_match_profiles(resume.id, limit=limit)

    if not jobs:
        print("✅ No jobs to score at the moment.")
        return

    computed = 0
    errors = []

    for job in jobs:
        try:
            jd_text = job.jd_text
            if not jd_text:
                jd_text = f"{job.title} at {job.company} in {job.location}"

            scores = compute_match_scores(
                resume_text=resume_text,
                jd_text=jd_text,
                resume_skills=resume_skills,
                jd_required_skills=None,  # can be enhanced later
            )

            profile = {
                "job_id": job.id,
                "resume_id": resume.id,
                "overall_score": scores["overall_score"],
                "semantic_score": scores["semantic_score"],
                "keyword_score": scores["keyword_score"],
                "skill_overlap": scores["skill_overlap"],
                "gap_analysis": scores["gap_analysis"],
            }
            insert_match_profile(profile)
            computed += 1

        except Exception as e:
            errors.append({
                "job_id": job.id,
                "error": str(e),
            })

    ended_at = datetime.utcnow().isoformat()

    log = {
        "started_at": started_at,
        "ended_at": ended_at,
        "jobs_discovered": 0,  # not relevant in this script
        "jobs_deduped_skipped": 0,
        "matches_computed": computed,
        "errors": errors if errors else None,
    }
    insert_run_log(log)

    print(f"✅ Computed {computed} match profiles for resume {resume.id}.")
    if errors:
        print(f"⚠️  Errors: {len(errors)}")
        for err in errors[:5]:  # show first few
            print("  -", err)


if __name__ == "__main__":
    # You can tune `limit` as needed
    score_jobs(limit=100)