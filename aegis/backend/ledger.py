"""
Project Aegis — Canonical Ledger & Balance Service
==================================================
Handles OS-agnostic database location discovery, ledger walk,
and bounce-aware balance calculation.
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional


def get_db_path() -> str:
    """
    Resolve the canonical path to aegis.db in an OS-agnostic way.
    Checks AEGIS_DB_PATH env var first, then checks repo-relative locations.
    Fails loudly if the database does not exist or is empty (0 bytes).
    """
    env_path = os.environ.get("AEGIS_DB_PATH")
    if env_path:
        p = Path(env_path).resolve()
        if p.is_file() and p.stat().st_size > 0:
            return str(p)
        raise FileNotFoundError(
            f"AEGIS_DB_PATH was set to '{env_path}', but the file does not exist or is empty."
        )

    base_dir = Path(__file__).resolve().parent  # aegis/backend
    candidates = [
        base_dir / "ML_model" / "data" / "aegis.db",
        base_dir.parent / "backend" / "ML_model" / "data" / "aegis.db",
        base_dir.parent.parent / "aegis" / "backend" / "ML_model" / "data" / "aegis.db",
        base_dir.parent.parent / "aegis.db",
        base_dir / "aegis.db",
    ]

    for cand in candidates:
        if cand.is_file() and cand.stat().st_size > 0:
            return str(cand.resolve())

    searched = "\n  - ".join(str(c) for c in candidates)
    raise FileNotFoundError(
        f"Aegis database (aegis.db) not found or is 0 bytes.\n"
        f"Searched locations:\n  - {searched}\n"
        f"Please set the AEGIS_DB_PATH environment variable or generate data via data_generation.py."
    )


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Return an active SQLite connection to the resolved database."""
    target_path = db_path or get_db_path()
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_opening_balance(user_id: str, conn: Optional[sqlite3.Connection] = None) -> float:
    """
    Derive the user's opening balance from their initial transaction.
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        cur = conn.cursor()
        # Query first transaction
        cur.execute(
            """
            SELECT type, amount, balance_after
            FROM transactions
            WHERE user_id = ? OR customer_id = ?
            ORDER BY date ASC, txn_id ASC
            LIMIT 1
            """,
            (user_id, user_id),
        )
        row = cur.fetchone()
        if not row:
            return 0.0

        tx_type = str(row["type"]).lower()
        amt = float(row["amount"])
        bal_after = float(row["balance_after"])

        if tx_type == "debit":
            return round(bal_after + amt, 2)
        else:
            return round(bal_after - amt, 2)
    finally:
        if close_conn:
            conn.close()


def get_walked_balance(
    user_id: str,
    as_of_date: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> float:
    """
    Walk each user's transaction ledger forward from their opening balance.
    Implements bounce-aware calculation:
    - Credits increase balance.
    - Debits exceeding available balance bounce: debit amount is NOT deducted,
      and a ₹500 standard NACH bounce fee is charged.
    - Debits with available funds are deducted normally.
    Never trusts a stale snapshot column.
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        opening_bal = get_opening_balance(user_id, conn=conn)

        query = """
            SELECT type, amount, category, status, date, balance_after
            FROM transactions
            WHERE user_id = ? OR customer_id = ?
        """
        params = [user_id, user_id]

        if as_of_date:
            query += " AND date <= ?"
            params.append(as_of_date)

        query += " ORDER BY date ASC, txn_id ASC"

        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()

        bal = float(opening_bal)
        for r in rows:
            tx_type = str(r["type"]).lower()
            amt = float(r["amount"])
            status = str(r["status"]).lower() if "status" in r.keys() and r["status"] else "success"

            if tx_type == "credit":
                bal += amt
            elif tx_type == "debit":
                if status == "bounced" or bal < amt:
                    bal -= 500.0  # Standard bounce fee
                    bal = max(bal, 0.0)
                else:
                    bal -= amt

        return round(bal, 2)
    finally:
        if close_conn:
            conn.close()
