import psycopg2
import configparser
import os
from contextlib import contextmanager


def get_db_connection():
    """
    Reads credentials from database.ini and returns a psycopg2 connection.
    Do NOT keep a global connection open. Open and close per request.
    """
    config = configparser.ConfigParser()

    # Get absolute path to the database.ini file
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(base_dir, 'database.ini')

    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Missing config file: {config_file}")

    config.read(config_file)

    conn = psycopg2.connect(
        host=config.get('postgresql', 'host'),
        database=config.get('postgresql', 'database'),
        user=config.get('postgresql', 'user'),
        password=config.get('postgresql', 'password')
    )
    return conn


@contextmanager
def get_db():
    """
    Context manager for safe per-request database access.
    Automatically closes the connection when the 'with' block exits,
    even if an exception occurs — preventing connection leaks.

    Usage:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT ...")
    """
    conn = get_db_connection()
    try:
        yield conn
    except Exception:
        conn.rollback()   # Undo any partial changes on error
        raise             # Re-raise so the caller can handle it
    finally:
        conn.close()      # Always close — no leaked connections
