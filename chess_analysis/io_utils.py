from __future__ import annotations

from pathlib import Path
from typing import List


class InputPathError(ValueError):
    """Raised when an input path is invalid."""


def discover_pgn_files(input_path: str) -> List[Path]:
    """Return a sorted list of PGN files from a file or directory input."""
    path = Path(input_path)

    if not path.exists():
        raise InputPathError(f"Input path does not exist: {path}")

    if path.is_file():
        if path.suffix.lower() != ".pgn":
            raise InputPathError(f"Input file is not a .pgn file: {path}")
        return [path]

    pgn_files = sorted(p for p in path.glob("*.pgn") if p.is_file())
    if not pgn_files:
        raise InputPathError(f"No .pgn files found in directory: {path}")
    return pgn_files


def ensure_output_dir(output_path: str) -> Path:
    out = Path(output_path)
    out.mkdir(parents=True, exist_ok=True)
    return out
