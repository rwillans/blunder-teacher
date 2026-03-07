from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import chess.pgn

from .openings import resolve_opening_fields


@dataclass
class GameRecord:
    source_file: str
    game_index: int
    event: str
    site: str
    date: str
    white: str
    black: str
    result: str
    eco: str
    opening: str


@dataclass
class ParsedGame:
    metadata: GameRecord
    game: chess.pgn.Game


def _header(headers: chess.pgn.Headers, key: str) -> str:
    return (headers.get(key) or "").strip()


def parse_pgn_files(pgn_files: Iterable[Path], player: str | None = None) -> List[ParsedGame]:
    records: List[ParsedGame] = []
    normalized_player = player.strip().lower() if player else None

    for pgn_file in pgn_files:
        logging.info("Parsing PGN file: %s", pgn_file)
        try:
            with pgn_file.open("r", encoding="utf-8", errors="replace") as handle:
                game_index = 0
                while True:
                    try:
                        game = chess.pgn.read_game(handle)
                    except Exception as exc:  # malformed section: continue to next file
                        logging.warning("Failed while parsing %s: %s", pgn_file, exc)
                        break

                    if game is None:
                        break

                    game_index += 1
                    headers = game.headers

                    white = _header(headers, "White")
                    black = _header(headers, "Black")
                    if normalized_player and normalized_player not in {
                        white.lower(),
                        black.lower(),
                    }:
                        continue

                    eco, opening = resolve_opening_fields(headers)

                    records.append(
                        ParsedGame(
                            metadata=GameRecord(
                                source_file=str(pgn_file),
                                game_index=game_index,
                                event=_header(headers, "Event"),
                                site=_header(headers, "Site"),
                                date=_header(headers, "Date"),
                                white=white,
                                black=black,
                                result=_header(headers, "Result"),
                                eco=eco,
                                opening=opening,
                            ),
                            game=game,
                        )
                    )
        except OSError as exc:
            logging.error("Could not read PGN file %s: %s", pgn_file, exc)

    return records
