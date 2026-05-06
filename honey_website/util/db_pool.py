from contextlib import contextmanager
import os

from psycopg2.pool import SimpleConnectionPool

POOL: SimpleConnectionPool | None = None


def init_pool(minconn: int = 1, maxconn: int = 5):
    """Initialize the global connection pool. Call this once at startup."""
    global POOL
    if POOL is None:
        # Heroku stores the database URL in the environment variable $DATABASE_URL
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            raise RuntimeError("DATABASE_URL not set")
        POOL = SimpleConnectionPool(
            minconn=minconn,
            maxconn=maxconn,
            dsn=db_url,
            sslmode="require",
        )


def get_conn():
    """Get a connection from the pool."""
    if POOL is None:
        init_pool()
    return POOL.getconn()


def put_conn(conn) -> None:
    """Return a connection to the pool."""
    if POOL is not None and conn is not None:
        POOL.putconn(conn)


def close_pool() -> None:
    """Close all connections (usually only on graceful shutdown)."""
    global POOL
    if POOL is not None:
        POOL.closeall()
        POOL = None


@contextmanager
def db_connection():
    """
    Get a connection from the pool and guarantee it is returned.

    Usage:
        from util.db_pool import db_connection

        with db_connection() as conn:
            cur = conn.cursor()
            ...
    """
    conn = get_conn()
    try:
        yield conn
    finally:
        put_conn(conn)


@contextmanager
def db_transaction():
    """
    Connection + automatic commit/rollback.

    Usage:
        from util.db_pool import db_transaction

        with db_transaction() as conn:
            cur = conn.cursor()
            cur.execute(...)
            # commit on success, rollback on exception
    """
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        put_conn(conn)
