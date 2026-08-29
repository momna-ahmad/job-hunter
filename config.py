import os
from dotenv import load_dotenv

load_dotenv()

JSEARCH_API_KEY = os.environ["JSEARCH_API_KEY"]
JSEARCH_API_HOST = os.environ["JSEARCH_API_HOST"]

NEON_URL = os.environ["DATABASE_URL"]

RESUME_FILE_PATH = os.environ["RESUME_FILE_PATH"]