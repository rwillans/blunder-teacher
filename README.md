# blunder-teacher (v1 pipeline)

A minimal local chess analysis pipeline for PGN files.

## Features in v1
- Accepts one PGN file or a folder of PGN files.
- Parses games with `python-chess`.
- Extracts metadata per game:
  - Event, Site, Date, White, Black, Result, ECO, Opening.
- Optional player filter via `--player` (case-insensitive exact name match on White/Black).
- Runs a real Stockfish smoke test (`analyse()` from initial position).
- Writes:
  - `games_summary.csv`
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

Optional engine path override:
```bash
export STOCKFISH_PATH=/custom/path/to/stockfish
python main.py --input /path/to/file_or_folder --output /path/to/output
```

## Notes
- Missing `ECO`/`Opening` tags are treated as blank values.
- Invalid or malformed PGN sections are handled best-effort; parsing continues where possible.
