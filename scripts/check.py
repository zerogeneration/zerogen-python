"""Runs every check before a commit or a release: Ruff's linter and formatter, pyright, and the
tests. Run it with `uv run scripts/check.py`."""

from __future__ import annotations

import subprocess
import sys

STEPS = [
    ["ruff", "check", "."],
    ["ruff", "format", "--check", "."],
    ["pyright"],
    ["pytest"],
]


def main() -> None:
    for step in STEPS:
        print(f"$ {' '.join(step)}", flush=True)
        if subprocess.run([sys.executable, "-m", *step]).returncode != 0:
            sys.exit(f"{step[0]} failed")


if __name__ == "__main__":
    main()
