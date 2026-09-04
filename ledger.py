"""
Root-level re-export for Aegis Canonical Ledger.
Delegates to aegis.backend.ledger to maintain single source of truth.
"""

import sys
import os
from pathlib import Path

# Add backend directory to sys.path
_repo_root = Path(__file__).resolve().parent
_backend_dir = _repo_root / "aegis" / "backend"

if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from aegis.backend.ledger import (
    get_db_path,
    get_connection,
    get_opening_balance,
    get_walked_balance,
)

__all__ = [
    "get_db_path",
    "get_connection",
    "get_opening_balance",
    "get_walked_balance",
]
