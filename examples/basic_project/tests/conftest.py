"""
conftest.py

Make the example project's src directory importable during pytest collection.
"""

from __future__ import annotations

import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"

source_root_text = str(SOURCE_ROOT)

if source_root_text not in sys.path:
    sys.path.insert(0, source_root_text)
