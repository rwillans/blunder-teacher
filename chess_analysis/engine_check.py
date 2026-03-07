from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import chess
import chess.engine


DEFAULT_STOCKFISH_PATH = "/usr/games/stockfish"


@dataclass
class EngineCheckResult:
    success: bool
    engine_path: str
    detail: str


def run_stockfish_smoke_test() -> EngineCheckResult:
    engine_path = os.environ.get("STOCKFISH_PATH", DEFAULT_STOCKFISH_PATH)
    logging.info("Running Stockfish smoke test with engine: %s", engine_path)

    try:
        with chess.engine.SimpleEngine.popen_uci(engine_path) as engine:
            board = chess.Board()
            info = engine.analyse(board, chess.engine.Limit(depth=8))
            score = info.get("score")
            if score is None:
                return EngineCheckResult(False, engine_path, "Engine responded without score")
            return EngineCheckResult(True, engine_path, f"Engine responded with score: {score}")
    except FileNotFoundError:
        return EngineCheckResult(False, engine_path, "Engine binary not found")
    except Exception as exc:
        return EngineCheckResult(False, engine_path, f"Engine analysis failed: {exc}")
