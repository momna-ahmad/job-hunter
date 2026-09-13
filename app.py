from fetch_jobs import SessionLocal
from models import Resume
from resume_parser import ingest_resume
import streamlit as st

st.set_page_config(page_title="Resume Ingestion", layout="wide")
st.title("📄 Resume Ingestion & Parser")

uploaded_files = st.file_uploader(
    "Upload Resume PDFs", type=["pdf"], accept_multiple_files=True
)

if uploaded_files:
  if st.button("Process & Ingest Resumes"):
    for uploaded_file in uploaded_files:
      with st.spinner(f"Ingesting {uploaded_file.name}..."):
        try:
          file_bytes = uploaded_file.read()
          saved_record = ingest_resume(file_bytes, uploaded_file.name)
          st.success(f"Saved: {saved_record.file_path}")
          st.write(f"**Detected Skills:** {', '.join(saved_record.skills)}")
        except Exception as e:
          st.error(f"Error processing {uploaded_file.name}: {e}")

st.divider()
st.subheader("Existing Resumes in Neon DB")

with SessionLocal() as session:
  resumes = (
      session.query(Resume).order_by(Resume.created_at.desc()).limit(10).all()
  )
  for r in resumes:
    with st.expander(
        f"{r.file_path} {'(ACTIVE)' if r.is_active else ''} - {r.created_at.strftime('%Y-%m-%d %H:%M')}"
    ):
      st.markdown(f"**Storage Path:** `{r.file_path}`")
      st.markdown(f"**Extracted Skills:** {', '.join(r.skills)}")
      st.text_area(
          "Parsed Raw Text", r.parsed_text, height=150, key=f"txt_{r.id}"
      )