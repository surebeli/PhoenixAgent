from __future__ import annotations

from pathlib import Path


__path__ = [str(Path(__file__).resolve().parent / "src" / "phoenix")]


def main(argv: list[str] | None = None) -> int:
    from phoenix.cli import main as cli_main

    return cli_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
