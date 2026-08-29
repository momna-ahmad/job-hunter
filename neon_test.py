import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

try:
    conn = psycopg2.connect(DATABASE_URL)
    print("✅ Connection successful!")

    with conn.cursor() as cur:
        # Check PostgreSQL version
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print("PostgreSQL version:", version)

        # Query the keyword column from the config table
        cur.execute("SELECT keywords FROM config;")
        rows = cur.fetchall()

        # Extract values into a clean Python list
        keywords = [row[0] for row in rows]
        print("Fetched keywords:", keywords)

    conn.close()

except Exception as e:
    print("❌ Connection failed:")
    print(e)