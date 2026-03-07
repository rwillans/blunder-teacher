# blunder-teacher (v2 pipeline)

A minimal local chess analysis pipeline for PGN files, with critical-moment extraction.

## Features in v2
- Accepts one PGN file or a folder of PGN files.
- Parses games with `python-chess`.
- Extracts metadata per game:
  - Event, Site, Date, White, Black, Result, ECO, Opening.
- Optional player filter via `--player` (case-insensitive exact name match on White/Black).
- Runs a real Stockfish smoke test (`analyse()` from initial position).
- Performs move-by-move engine analysis and flags critical moments using eval swing thresholding.
- Configurable analysis settings:
  - `--engine-depth` (default: 14)
  - `--eval-threshold` in centipawns (default: 150)
- Writes:
  - `games_summary.csv`
  - `critical_positions.csv`
  - `summary_report.md`

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
Analyze all games:
```bash
python main.py --input /path/to/file_or_folder --output /path/to/output
```

Analyze games for one player only:
```bash
python main.py --input /path/to/file_or_folder --output /path/to/output --player "Rob Willans"
```

Tighter critical detection:
```bash
python main.py --input /path/to/file_or_folder --output /path/to/output --engine-depth 16 --eval-threshold 200
```

Optional engine path override:
```bash
export STOCKFISH_PATH=/custom/path/to/stockfish
python main.py --input /path/to/file_or_folder --output /path/to/output
```

## Notes
- Missing `ECO`/`Opening` tags are treated as blank values.
- Invalid or malformed PGN sections are handled best-effort.
- Critical positions capture the board state immediately before the played move.
