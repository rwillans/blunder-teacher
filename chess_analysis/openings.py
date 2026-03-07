from __future__ import annotations

from typing import Mapping


def resolve_opening_fields(headers: Mapping[str, str]) -> tuple[str, str]:
    """Best-effort opening resolution.

    v1 behavior: read ECO and Opening only from PGN headers if present.
    Future versions can extend this module to infer openings from moves.
    """
    eco = (headers.get("ECO") or "").strip()
    opening = (headers.get("Opening") or "").strip()
    return eco, opening
