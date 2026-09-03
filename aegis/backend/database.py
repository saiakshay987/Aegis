"""
database.py — Database session management for the Financial Guardian backend.

Points to the ML-populated database at ML_model/data/aegis.db.
Lives alongside main.py so every router resolves
    from database import engine, get_db, Base
without touching the root-level database.py.
"""

import os
import sys
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

# ── Paths ────────────────────────────────────────────────────────
_BACKEND_DIR  = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_BACKEND_DIR))  # d:\Aegis\Aegis

# ── Database location: the single ML-populated aegis.db ─────────
DB_PATH      = os.path.join(_BACKEND_DIR, "ML_model", "data", "aegis.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# ── Make models.py (at project root) importable without polluting
#    sys.path in a way that would expose the root database.py to
#    other import statements.  We append (not insert) so BACKEND_DIR
#    still wins for any 'database' import resolution. ────────────
if _PROJECT_ROOT not in sys.path:
    sys.path.append(_PROJECT_ROOT)

from models import Base  # noqa: E402  (models.py lives at project root)

# ── Engine ───────────────────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforce FK constraints on every new SQLite connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    FastAPI dependency — yields a scoped Session, closes on exit.

        @router.get("/...")
        def my_route(db: Session = Depends(get_db)): ...
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
