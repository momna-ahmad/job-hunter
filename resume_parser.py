import io
import os
import re
from typing import List, Set
from pypdf import PdfReader
import uuid
from fetch_jobs import SessionLocal
from dotenv import load_dotenv
from models import Resume
from supabase import Client, create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_ANON_KEY"]  # Service role bypasses RLS
BUCKET_NAME = "resumes"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Master taxonomy for deterministic matching
CORE_SKILLS = {
    # Languages
    "python",
    "javascript",
    "typescript",
    "java",
    "c++",
    "c#",
    "go",
    "rust",
    "sql",
    "html",
    "css",
    # Frameworks / Libraries
    "react",
    "next.js",
    "node.js",
    "express",
    "fastapi",
    "flask",
    "django",
    "tailwind",
    "langchain",
    "pytorch",
    "tensorflow",
    # Databases / Tools
    "postgresql",
    "mysql",
    "mongodb",
    "redis",
    "supabase",
    "docker",
    "kubernetes",
    "aws",
    "azure",
    "git",
    "linux",
    "graphql",
    "rest api",
}


def extract_text_from_pdf(file_bytes: bytes) -> str:
  """Extracts raw text from a PDF byte stream using pypdf."""
  reader = PdfReader(io.BytesIO(file_bytes))
  pages_text = [
      page.extract_text() or "" for page in reader.pages if page.extract_text()
  ]
  return "\n".join(pages_text).strip()


def extract_skills_deterministic(text: str) -> List[str]:
  """Matches known skills against raw resume text using word boundaries."""
  lowered_text = text.lower()
  found_skills: Set[str] = set()

  for skill in CORE_SKILLS:
    # Escape characters like +, ., # for regex safety
    pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"
    if re.search(pattern, lowered_text):
      found_skills.add(skill)

  return sorted(list(found_skills))

def upload_pdf_to_storage(file_bytes: bytes, original_filename: str) -> str:
  """Uploads file to Supabase bucket and returns the object path."""
  unique_name = f"{uuid.uuid4()}_{original_filename}"
  storage_path = f"raw/{unique_name}"

  res = supabase.storage.from_(BUCKET_NAME).upload(
      path=storage_path,
      file=file_bytes,
      file_options={"content-type": "application/pdf"},
  )
  return storage_path


def ingest_resume(
    file_bytes: bytes, file_name: str, set_as_active: bool = True
) -> Resume:
  """End-to-end pipeline: Parse -> Extract Skills -> Upload S3 -> Save Neon."""
  # 1. Parse text
  raw_text = extract_text_from_pdf(file_bytes)
  if not raw_text:
    raise ValueError("Failed to extract text from PDF or PDF is empty.")

  # 2. Extract skills
  skills = extract_skills_deterministic(raw_text)

  # 3. Upload to Supabase Storage
  storage_path = upload_pdf_to_storage(file_bytes, file_name)

  # 4. Save metadata to Neon DB
  with SessionLocal() as session:
    if set_as_active:
      # Deactivate previous active resumes
      session.query(Resume).filter(Resume.is_active == True).update(
          {"is_active": False}
      )

    new_resume = Resume(
        file_name=file_name,
        storage_path=storage_path,
        raw_text=raw_text,
        skills=skills,
        is_active=set_as_active,
    )
    session.add(new_resume)
    session.commit()
    session.refresh(new_resume)
    return new_resume