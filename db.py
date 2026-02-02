"""
PostgreSQL database connection using psycopg2.
"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Extract PostgreSQL configuration from environment variables
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")

# Database connection
connection = None

try:
    connection = psycopg2.connect(
        host=POSTGRES_HOST,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DB
    )
    print("Database connected successfully")
except psycopg2.Error as e:
    print(f"Error connecting to database: {e}")
    sys.exit(1)
