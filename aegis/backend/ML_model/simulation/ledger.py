"""
Simulation-level re-export for Aegis Canonical Ledger.
Delegates to aegis.backend.ledger to maintain single source of truth.
"""

import sys
import os
from pathlib import Path

_backend_dir = Path(__file__).resolve().parents[2]
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

import ledger as _canonical_ledger

get_db_path = _canonical_ledger.get_db_path
get_connection = _canonical_ledger.get_connection
get_opening_balance = _canonical_ledger.get_opening_balance
get_walked_balance = _canonical_ledger.get_walked_balance

__all__ = [
    "get_db_path",
    "get_connection",
    "get_opening_balance",
    "get_walked_balance",
]
