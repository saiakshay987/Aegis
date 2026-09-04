"""
Database initialization and session management for Aegis.
Points to the populated ML database (aegis/backend/ML_model/data/aegis.db).
"""

import os
import sys
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

# Ensure backend and models are on path
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.join(_THIS_DIR, "aegis", "backend")
for _p in [_THIS_DIR, _BACKEND_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ledger import get_db_path

DB_PATH = get_db_path()
DATABASE_URL = f"sqlite:///{DB_PATH}"

from models import Base

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

# Enforce foreign key constraints for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(use_schema_sql: bool = True):
    """Initializes tables using schema.sql or SQLAlchemy metadata."""
    if use_schema_sql:
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            with engine.connect() as conn:
                for statement in schema_sql.split(";"):
                    stmt = statement.strip()
                    if stmt:
                        conn.exec_driver_sql(stmt)
                conn.commit()
            return
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency / generator for database session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
