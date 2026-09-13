from datetime import datetime, timezone
from typing import Any, Dict, Literal
from fetch_jobs import fetch_jobs, save_jobs_to_neon , SessionLocal
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from matcher import compute_match_scores
from models import Config, Job, JobApplication, Resume
from orchestrator_state import AgentState
from sqlalchemy import select

# --- Nodes ---


def load_context_node(state: AgentState) -> Dict[str, Any]:
  """Loads configuration and active resume from DB."""
  with SessionLocal() as session:
    cfg = session.scalar(select(Config).limit(1))
    resume = session.scalar(
        select(Resume).where(Resume.is_active == True).limit(1)
    )

    if not resume:
      raise RuntimeError("No active resume configured.")

    cfg_dict = {
        "daily_apply_limit": cfg.daily_apply_limit if cfg else 5,
        "min_score_threshold": cfg.min_score_threshold if cfg else 0.70,
        "require_human_confirmation": (
            cfg.require_human_confirmation if cfg else False
        ),
        "keywords": (
            cfg.keywords if cfg else ["Full Stack", "Backend Developer"]
        ),
        "locations": cfg.locations if cfg else ["Remote"],
    }

    resume_dict = {
        "id": str(resume.id),
        "parsed_text": resume.parsed_text,
        "skills": resume.skills or [],
    }

  return {
      "config": cfg_dict,
      "active_resume": resume_dict,
      "requires_approval": cfg_dict["require_human_confirmation"],
      "run_errors": [],
  }


def discover_jobs_node(state: AgentState) -> Dict[str, Any]:
  """Fetches from API, deduplicates, and commits to Neon DB."""
  cfg = state["config"]
  total_inserted = 0

  for kw in cfg["keywords"]:
    for loc in cfg["locations"]:
      query = f"{kw} in {loc}".strip()
      raw_jobs = fetch_jobs(query=query, page=1, num_pages=1)
      inserted, _ = save_jobs_to_neon(raw_jobs)
      total_inserted += inserted

  return {"discovered_job_count": total_inserted}


def score_and_filter_node(state: AgentState) -> Dict[str, Any]:
  """Filters out already-applied jobs, scores match, and picks top N."""
  cfg = state["config"]
  resume = state["active_resume"]

  with SessionLocal() as session:
    # 1. Fetch IDs of already applied jobs
    applied_ids = set(session.scalars(select(JobApplication.job_id)).all())

    # 2. Get unapplied jobs
    jobs = session.scalars(select(Job)).all()
    eligible_jobs = [j for j in jobs if j.id not in applied_ids]

    scored = []
    for job in eligible_jobs:
      jd = job.jd_text or f"{job.title} at {job.company}"
      scores = compute_match_scores(resume["parsed_text"], jd, resume["skills"])

      if scores["overall_score"] >= cfg["min_score_threshold"]:
        scored.append({
            "job_id": str(job.id),
            "title": job.title,
            "company": job.company,
            "url": job.url,
            "score": scores["overall_score"],
        })

    # Sort descending by score and pick top N
    scored.sort(key=lambda x: x["score"], reverse=True)
    top_candidates = scored[: cfg["daily_apply_limit"]]

  return {"scored_jobs": scored, "selected_jobs": top_candidates}


def apply_job_executor(job: Dict[str, Any]) -> bool:
  """Executes submission via browser agent or API payload."""
  print(f"[APPLYING] -> {job['title']} at {job['company']} ({job['url']})")
  # Implement form-filler or email dispatch here
  return True


def apply_jobs_node(state: AgentState) -> Dict[str, Any]:
  """Executes applications and records state to DB."""
  selected = state.get("selected_jobs", [])
  resume_id = state["active_resume"]["id"]
  applied_ids = []

  with SessionLocal() as session:
    for job in selected:
      success = apply_job_executor(job)
      if success:
        app_record = JobApplication(
            job_id=job["job_id"], resume_id=resume_id, status="applied"
        )
        session.add(app_record)
        applied_ids.append(job["job_id"])
    session.commit()

  return {"applied_jobs": applied_ids}


# --- Routing & Construction ---


def route_confirmation(state: AgentState) -> Literal["human_gate", "apply_jobs"]:
  if state.get("requires_approval") and state.get("selected_jobs"):
    return "human_gate"
  return "apply_jobs"


def human_gate_node(state: AgentState) -> Dict[str, Any]:
  """Approval step: used alongside LangGraph interrupts for human review."""
  print(
      f"Review Required: {len(state['selected_jobs'])} jobs waiting for approval."
  )
  return state


def build_orchestrator():
  builder = StateGraph(AgentState)

  builder.add_node("load_context", load_context_node)
  builder.add_node("discover_jobs", discover_jobs_node)
  builder.add_node("score_and_filter", score_and_filter_node)
  builder.add_node("human_gate", human_gate_node)
  builder.add_node("apply_jobs", apply_jobs_node)

  builder.add_edge(START, "load_context")
  builder.add_edge("load_context", "discover_jobs")
  builder.add_edge("discover_jobs", "score_and_filter")

  builder.add_conditional_edges(
      "score_and_filter",
      route_confirmation,
      {"human_gate": "human_gate", "apply_jobs": "apply_jobs"},
  )

  builder.add_edge("human_gate", "apply_jobs")
  builder.add_edge("apply_jobs", END)

  # Checkpointer enables breakpoints/interrupts for human confirmation
  memory = MemorySaver()
  return builder.compile(
      checkpointer=memory, interrupt_before=["human_gate"]
  )