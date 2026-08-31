# matcher.py
from typing import List, Dict, Any, Optional
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import re
import os

load_dotenv()

HF_TOKEN = os.getenv("HUGGING_FACE_TOKEN")

MODEL_NAME = "all-MiniLM-L6-v2"
_model = None

SENIORITY_KEYWORDS = {
    "intern": 1,
    "junior": 2,
    "associate": 2,
    "mid": 3,
    "senior": 4,
    "lead": 5,
    "staff": 5,
    "principal": 6,
    "manager": 5,
    "head": 6,
    "director": 6,
    "vp": 7,
    "chief": 8,
    "cto": 8,
    "ceo": 8,
}

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME, token=HF_TOKEN)
    return _model

def normalize_text(s: str) -> str:
    if not s:
        return ""
    return " ".join(s.lower().strip().split())

def extract_skills_from_text(text: str, candidate_skills: List[str]) -> List[str]:
    """
    Simple skill extractor: check which candidate_skills appear in text.
    In a more advanced version, you could use NER or a skill taxonomy.
    """
    text_lower = text.lower()
    matched = []
    for skill in candidate_skills:
        if skill.lower() in text_lower:
            matched.append(skill)
    return matched

def infer_seniority_level(text: str) -> int:
    """
    Very rough seniority inference from text.
    Returns 1-8 scale based on keywords.
    """
    text_lower = text.lower()
    levels = []
    for kw, level in SENIORITY_KEYWORDS.items():
        if kw in text_lower:
            levels.append(level)
    return max(levels) if levels else 3  # default to mid-level

def compute_match_scores(
    resume_text: str,
    jd_text: str,
    resume_skills: Optional[List[str]] = None,
    jd_required_skills: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Compute an extensive match profile between a resume and a job description.

    Returns a dict with:
      - overall_score (0-100)
      - semantic_score (0-1)
      - keyword_score (0-1)
      - seniority_score (0-1)
      - skill_overlap (list)
      - gap_analysis (dict)
      - reasoning (str)
    """
    model = get_model()

    # 1. Semantic similarity
    resume_emb = model.encode([resume_text])[0]
    jd_emb = model.encode([jd_text])[0]
    semantic_score = float(cosine_similarity([resume_emb], [jd_emb])[0][0])

    # 2. Keyword / skill overlap
    resume_skills = resume_skills or []
    jd_required_skills = jd_required_skills or []

    # Skills you have that appear in JD
    skill_overlap = extract_skills_from_text(jd_text, resume_skills)

    # If you have a curated list of "required skills" from JD, use that too
    if jd_required_skills:
        matched_required = extract_skills_from_text(resume_text, jd_required_skills)
    else:
        matched_required = skill_overlap

    keyword_score = (
        len(skill_overlap) / max(len(resume_skills), 1)
        if resume_skills else 0.0
    )

    # 3. Seniority alignment
    resume_seniority = infer_seniority_level(resume_text)
    jd_seniority = infer_seniority_level(jd_text)

    # Score higher if levels are close
    seniority_diff = abs(resume_seniority - jd_seniority)
    seniority_score = max(0.0, 1.0 - (seniority_diff * 0.2))  # penalize gaps

    # 4. Overall score (tunable weights)
    overall_score = (
        0.6 * semantic_score +
        0.25 * keyword_score +
        0.15 * seniority_score
    ) * 100

    # 5. Gap analysis
    missing_key_skills = [s for s in resume_skills if s not in skill_overlap]
    gap_analysis = {
        "missing_skills": missing_key_skills[:10],  # limit for brevity
        "resume_seniority_level": resume_seniority,
        "job_seniority_level": jd_seniority,
        "seniority_gap": seniority_diff,
    }

    # 6. Short reasoning
    reasoning_parts = []
    reasoning_parts.append(f"Semantic similarity: {semantic_score:.2f}.")
    reasoning_parts.append(
        f"Skill overlap: {len(skill_overlap)}/{len(resume_skills) if resume_skills else '?'} "
        f"({keyword_score:.2f})."
    )
    if seniority_diff > 1:
        reasoning_parts.append(
            f"Seniority gap: resume ~{resume_seniority}, job ~{jd_seniority}."
        )
    else:
        reasoning_parts.append("Seniority levels are well aligned.")

    reasoning = " ".join(reasoning_parts)

    return {
        "overall_score": round(overall_score, 2),
        "semantic_score": round(semantic_score, 2),
        "keyword_score": round(keyword_score, 2),
        "seniority_score": round(seniority_score, 2),
        "skill_overlap": skill_overlap,
        "gap_analysis": gap_analysis,
        "reasoning": reasoning,
    }