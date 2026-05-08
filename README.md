# blunder-teacher (web-first training viewer)

A local chess analysis pipeline for PGN files that extracts critical moments and exports a puzzle set for the React training app.

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
- Exports puzzle-ready records from critical positions with instructional prompt categories and Lichess-style theme tags.
- Configurable analysis settings:
  - `--engine-depth` (default: 14)
  - `--eval-threshold` in centipawns (default: 150)
- Default output:
  - `puzzles.json`
  - `weaknesses.json`

`puzzles.json` carries the full frontend-friendly puzzle payload, including Lichess links, best and played move details, explanation text, a primary theme, theme tags, and precomputed legal-move grading data for the trainer. `weaknesses.json` summarizes recurring themes, openings, phases, sides, and severity buckets so the frontend can surface personal drill priorities.

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

Generate app data:
```bash
python main.py --input /path/to/file_or_folder --output /path/to/output
```

Start the React trainer:
```bash
python main.py --input /path/to/file_or_folder --output /path/to/output
cd web
npm install
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173).

Tighter critical detection:
```bash
python main.py --input /path/to/file_or_folder --output /path/to/output --engine-depth 16 --eval-threshold 200
```

Optional engine path override:
```bash
export STOCKFISH_PATH=/custom/path/to/stockfish
python main.py --output /path/to/output
```

## React App

The repo includes a React/Vite frontend in [web/README.md](/D:/positron_projects/blunder-teacher/web/README.md). Each pipeline run writes `puzzles.json` to your chosen output folder and also syncs a copy into `web/public/puzzles.json` for static builds. During local Vite development, the app reads directly from `outputs/puzzles.json` through `/api/puzzles`, so you are not depending on a stale copied file.

## Notes
- Directory scan is top-level `*.pgn` only (non-recursive).
- Missing `ECO`/`Opening` tags are treated as blank values.
- Invalid or malformed PGN sections are handled best-effort.
- Critical positions capture the board state immediately before the played move.
- Puzzle prompt types are instructional labels, while `tags` are the Lichess-style study themes used by the trainer filter.
- The React trainer also reads `weaknesses.json` when present and tracks local solve/fail/reveal history in browser storage.
- `--player-mistakes-only` has effect only when `--player` is provided.
- Precomputing every legal move for each critical position increases analysis cost roughly in proportion to the number of legal moves in those positions, but it keeps the viewer deterministic and offline-friendly.
