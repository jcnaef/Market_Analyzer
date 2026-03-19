"""Database configuration for Market Analyzer."""

import os
from contextlib import contextmanager

import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials as fb_credentials

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql:///market_analyzer?host=/var/run/postgresql")


def init_firebase():
    """Initialize Firebase Admin SDK from environment variables."""
    if firebase_admin._apps:
        return  # Already initialized

    project_id = os.getenv("FIREBASE_PROJECT_ID")
    client_email = os.getenv("FIREBASE_CLIENT_EMAIL")
    private_key = os.getenv("FIREBASE_PRIVATE_KEY", "")

    if not all([project_id, client_email, private_key]):
        return  # Firebase not configured — skip init

    # Environment variables store \n as literal characters; convert to newlines
    private_key = private_key.replace("\\n", "\n")

    cred = fb_credentials.Certificate({
        "type": "service_account",
        "project_id": project_id,
        "client_email": client_email,
        "private_key": private_key,
        "token_uri": "https://oauth2.googleapis.com/token",
    })
    firebase_admin.initialize_app(cred)

_pool: ThreadedConnectionPool | None = None


def init_pool(db_url: str = None, minconn: int = 2, maxconn: int = 10):
    """Initialize the connection pool. Call once at server startup."""
    global _pool
    _pool = ThreadedConnectionPool(minconn, maxconn, dsn=db_url or DATABASE_URL)


def close_pool():
    """Close all connections in the pool. Call at server shutdown."""
    global _pool
    if _pool:
        _pool.closeall()
        _pool = None


@contextmanager
def get_db(db_url: str = None):
    """Get a database connection as a context manager.

    If db_url is provided (e.g. in tests), opens a direct connection that
    is closed when the block exits. Otherwise, borrows from the pool and
    returns it when the block exits.
    """
    if db_url:
        conn = psycopg2.connect(db_url)
        try:
            yield conn
        finally:
            conn.close()
    else:
        if _pool is None:
            raise RuntimeError("Connection pool not initialized. Call init_pool() first.")
        conn = _pool.getconn()
        try:
            yield conn
        finally:
            _pool.putconn(conn)
