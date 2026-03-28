# blunder-teacher (v5 training viewer)

A minimal local chess analysis pipeline for PGN files, with critical-moment extraction, puzzle export, and a local single-position HTML training viewer.

## Features in v5
- Accepts one PGN file or a folder of PGN files.
- Supports default input directory: if `--input` is omitted, uses `./inputs`.
- Combines all discovered PGN files in one analysis run.
- Parses games with `python-chess`.
- Extracts metadata per game:
  - Event, Site, Date, White, Black, Result, ECO, Opening.
- Optional player filter via `--player` (case-insensitive exact name match on White/Black).
- Optional `--player-mistakes-only` mode to keep only the selected player's critical moments/puzzles.
- Runs a real Stockfish smoke test (`analyse()` from initial position).
- Performs move-by-move engine analysis and flags critical moments using eval swing thresholding.
- Exports puzzle-ready records from critical positions with simple rule-based prompt assignment.
- Produces a standalone HTML training viewer with one puzzle at a time, sidebar filters, next/previous navigation, a local board, a local eval bar, and delayed answer reveal.
- Configurable analysis settings:
  - `--engine-depth` (default: 14)
  - `--eval-threshold` in centipawns (default: 150)
- Writes:
  - `games_summary.csv`
  - `critical_positions.csv`
  - `puzzles.csv`
  - `puzzles.html`
  - `summary_report.md`

`critical_positions.csv` includes a `mate_related` column so mate-transition moments can be separated from centipawn-only stats.

`puzzles.csv` now carries richer training metadata, including Lichess links, best/played move details, precomputed eval data, explanation text, and serialized legal-move grading data for the local viewer.

## Requirements
- Python 3.10+
- Stockfish installed locally.
  - Uses `STOCKFISH_PATH` env var if set.
  - Falls back to `/usr/games/stockfish`.

## Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage
Default input directory (`./inputs`):
```bash
python main.py --output /path/to/output
```

Explicit input path:
```bash
python main.py --input /path/to/file_or_folder --output /path/to/output
```

Optional player-focused run:
```bash
python main.py --output /path/to/output --player "Rob Willans"
python main.py --input /path/to/file_or_folder --output /path/to/output --player "Rob Willans"
python main.py --input /path/to/file_or_folder --output /path/to/output --player "Rob Willans" --player-mistakes-only
```

Open the generated local viewer:
```bash
python main.py --input /path/to/file_or_folder --output /path/to/output
# then open /path/to/output/puzzles.html in your browser
```

Tighter critical detection:
```bash
python main.py --input /path/to/file_or_folder --output /path/to/output --engine-depth 16 --eval-threshold 200
```

Optional engine path override:
```bash
export STOCKFISH_PATH=/custom/path/to/stockfish
python main.py --output /path/to/output
```

## Notes
- Directory scan is top-level `*.pgn` only (non-recursive).
- Missing `ECO`/`Opening` tags are treated as blank values.
- Invalid or malformed PGN sections are handled best-effort.
- Critical positions capture the board state immediately before the played move.
- Summary centipawn swing statistics are reported for non-mate critical moments, with mate-related moments counted separately.
- Puzzle prompt types are intentionally simple in v5: `Find the best move`, `Spot the danger`, and `Defend accurately`.
- `--player-mistakes-only` has effect only when `--player` is provided.
- The HTML viewer grades moves locally from precomputed legal-move evals rather than calling a browser engine.
- Precomputing every legal move for each critical position increases analysis cost roughly in proportion to the number of legal moves in those positions, but it keeps the viewer deterministic and offline-friendly.
