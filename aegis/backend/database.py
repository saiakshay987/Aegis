"""
database.py — Database session management for the Financial Guardian backend.

Points to the populated ML database at ML_model/data/aegis.db.
This file lives alongside main.py so that all routers can resolve
`from database import get_db / engine / Base` without relying on
sys.path gymnastics to find the root-level database.py.

The ML pipeline (api/pipeline.py) already uses the same physical
aegis.db file via its own raw sqlite3 connection — we connect to it
here via SQLAlchemy for the ORM-based service layer.
"""

import os
import sys
import importlib.util
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

# ── All paths are resolved relative to this file's location ─────
_BACKEND_DIR  = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_BACKEND_DIR))  # d:\Aegis\Aegis

# ── Single source of truth: the ML-populated SQLite database ────
DB_PATH      = os.path.join(_BACKEND_DIR, "ML_model", "data", "aegis.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# ── Import models.Base by absolute file path so we never need to
#    put PROJECT_ROOT on sys.path (which would cause Python to
#    shadow this file with the root-level database.py). ──────────
_models_path = os.path.join(_PROJECT_ROOT, "models.py")
_spec = importlib.util.spec_from_file_location("_aegis_models", _models_path)
_models_mod  = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_models_mod)
Base = _models_mod.Base

# ── SQLAlchemy engine ────────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforce foreign-key constraints on every new SQLite connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    FastAPI dependency — yields a SQLAlchemy Session and closes it
    automatically when the request finishes.

    Usage in a router:
        from database import get_db
        @router.get("/...")
        def my_route(db: Session = Depends(get_db)): ...
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
