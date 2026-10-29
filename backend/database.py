"""SQLite access layer. This is the ONLY file that contains SQL."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

_db_path = None


class DatabaseError(Exception):
    """Raised when something goes wrong while using SQLite."""


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS saved_content (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    title             TEXT NOT NULL,
    content_type      TEXT NOT NULL,
    user_input        TEXT NOT NULL,
    generated_content TEXT NOT NULL,
    tone              TEXT NOT NULL,
    output_length     TEXT NOT NULL,
    created_at        TEXT NOT NULL
)
"""


@contextmanager
def get_connection():
    """Open a connection, commit on success, roll back on error, always close it."""
    if _db_path is None:
        raise DatabaseError("The database has not been initialised.")
    try:
        conn = sqlite3.connect(_db_path, timeout=10)
    except sqlite3.Error as exc:
        raise DatabaseError(f"Could not open the database: {exc}") from exc
    conn.row_factory = sqlite3.Row  # rows behave like dictionaries
    try:
        yield conn
        conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        raise DatabaseError(str(exc)) from exc
    finally:
        conn.close()


def init_db(db_path):
    """Create the database folder, file and table if they do not exist yet."""
    global _db_path
    _db_path = str(db_path)
    Path(_db_path).parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.execute(CREATE_TABLE_SQL)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_saved_created ON saved_content (created_at DESC)")


def create_item(title, content_type, user_input, generated_content, tone, output_length):
    """Insert one saved item and return it as a dict. Values are passed as ? parameters."""
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO saved_content "
            "(title, content_type, user_input, generated_content, tone, output_length, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, content_type, user_input, generated_content, tone, output_length, created_at),
        )
        new_id = cursor.lastrowid
    return get_item(new_id)


def get_item(item_id):
    """Return one item as a dict, or None if it does not exist."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM saved_content WHERE id = ?", (item_id,)).fetchone()
    return dict(row) if row else None


def list_items(limit=100):
    """Return the newest items first, with a short preview instead of the full text."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, title, content_type, tone, output_length, created_at, "
            "       substr(generated_content, 1, 160) AS preview, "
            "       length(generated_content) AS content_length "
            "FROM saved_content ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def delete_item(item_id):
    """Delete an item. Returns True if a row was deleted, False if the id did not exist."""
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM saved_content WHERE id = ?", (item_id,))
        return cursor.rowcount > 0


def count_items():
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM saved_content").fetchone()[0]