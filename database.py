"""
Database initialization and session management for Aegis.
Supports SQLite engine with foreign key enforcement.
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from models import Base

# DB_PATH = os.path.join(os.path.dirname(__file__), "aegis.db")
DB_PATH = os.path.join(os.path.dirname(__file__), "api", "data", "aegis.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

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
