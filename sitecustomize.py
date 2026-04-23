from __future__ import annotations

import sys
import types
from pathlib import Path


src_dir = Path(__file__).resolve().parent / "src"
if src_dir.exists():
    src_str = str(src_dir)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)


if sys.platform == "win32":
    try:
        import resource  # type: ignore  # noqa: F401
    except ModuleNotFoundError:
        shim = types.ModuleType("resource")
        shim.RLIMIT_NOFILE = 7
        shim.RLIM_INFINITY = -1

        def _setrlimit(_limit: int, _values: tuple[int, int]) -> None:
            return None

        def _getrlimit(_limit: int) -> tuple[int, int]:
            return (shim.RLIM_INFINITY, shim.RLIM_INFINITY)

        shim.setrlimit = _setrlimit  # type: ignore[attr-defined]
        shim.getrlimit = _getrlimit  # type: ignore[attr-defined]
        sys.modules["resource"] = shim
