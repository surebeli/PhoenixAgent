from __future__ import annotations

import sys
from pathlib import Path


src_dir = Path(__file__).resolve().parent / "src"
if src_dir.exists():
    src_str = str(src_dir)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)
