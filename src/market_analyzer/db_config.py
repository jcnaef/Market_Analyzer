"""Database configuration for Market Analyzer."""

import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql:///market_analyzer?host=/var/run/postgresql")
