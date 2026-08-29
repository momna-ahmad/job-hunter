from datetime import datetime
from config import RESUME_FILE_PATH
from db import (
    get_config,
    get_active_resume,
    insert_match_profile,
    insert_run_log,
    get_jobs_without_match_profiles,
)
from discovery import discover_jobs_for_query
from matcher import compute_match_scores

def load_resume_text():
    with open(RESUME_FILE_PATH, "r", encoding="utf-8") as f:
        return f.read()

def run_discovery():
    started_at = datetime.utcnow().isoformat()
    config = get_config()
    resume = get_active_resume()

    if not resume:
        raise RuntimeError("No resume found in DB. Please insert one.")

    keywords = config["keywords"]
    locations = config["locations"]
    max_per_query = 5  # tune to stay under 200 requests/month
    print(keywords,locations)

    total_inserted = 0
    total_skipped = 0

    # Discover jobs
    for kw in keywords:
        for loc in locations:
            inserted, skipped = discover_jobs_for_query(
                query=kw,
                location=loc,
                max_jobs_per_run=max_per_query,
            )
            total_inserted += inserted
            total_skipped += skipped

    # Compute match profiles for jobs that don't have one yet
    resume_text = load_resume_text()
    resume_skills = resume.get("skills") or []

    jobs_to_score = get_jobs_without_match_profiles(resume["id"], limit=50)

    matches_computed = 0
    for job in jobs_to_score:
        jd_text = job["jd_text"] or f"{job['title']} at {job['company']} in {job['location']}"
        scores = compute_match_scores(resume_text, jd_text, resume_skills)

        profile = {
            "job_id": job["id"],
            "resume_id": resume["id"],
            "overall_score": scores["overall_score"],
            "semantic_score": scores["semantic_score"],
            "keyword_score": scores["keyword_score"],
            "skill_overlap": scores["skill_overlap"],
            "gap_analysis": scores["gap_analysis"],
        }
        insert_match_profile(profile)
        matches_computed += 1

    ended_at = datetime.utcnow().isoformat()

    log = {
        "started_at": started_at,
        "ended_at": ended_at,
        "jobs_discovered": total_inserted,
        "jobs_deduped_skipped": total_skipped,
        "matches_computed": matches_computed,
        "errors": None,
    }
    insert_run_log(log)

if __name__ == "__main__":
    run_discovery()