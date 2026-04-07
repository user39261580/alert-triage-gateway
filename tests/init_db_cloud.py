import os
import psycopg2
import sys
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

# Cloud Database Configuration from environment variables
DB_HOST = os.getenv("CLOUD_DB_HOST", "")
DB_PORT = os.getenv("CLOUD_DB_PORT", "5432")
DB_NAME = os.getenv("CLOUD_DB_NAME", "infra_ops")
DB_USER = os.getenv("CLOUD_DB_USER", "")
DB_PASS = os.getenv("CLOUD_DB_PASS", "")

def init_db():
    print(f"Connecting to {DB_HOST}:{DB_PORT}/{DB_NAME} as {DB_USER}...")
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            connect_timeout=10
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Running schema.sql content...")
        with open("schema.sql", "r") as f:
            sql = f.read()
            cur.execute(sql)
            
        print("Database initialization successful!")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False

if __name__ == "__main__":
    if init_db():
        sys.exit(0)
    else:
        sys.exit(1)
