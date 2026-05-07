# Blunder Teacher Web

This is the main trainer UI. It loads exported puzzle data from `puzzles.json` and presents it as a browser-based study board.

## What It Expects

The Python pipeline writes `puzzles.json` into the selected output directory and also syncs a copy to `web/public/puzzles.json`. This frontend loads that payload and renders it as the default viewer.

By default the app fetches `/puzzles.json`.

You can also point it at another URL by setting `VITE_PUZZLES_URL`.

## Local Dev

1. Generate puzzle data from the Python pipeline.
2. Install dependencies.
3. Start Vite.

Example:

```bash
python main.py --input ./inputs --output ./outputs
cd web
npm install
npm run dev
```

If you want to point the frontend at a different JSON file or backend route, set `VITE_PUZZLES_URL`.

## What The App Does

- lets you filter the current puzzle set
- shows one position at a time
- grades a selected move from precomputed engine analysis
- reveals the engine line and explanation on demand

## Piece Set

The app uses the classic Cburnett SVG piece set from `web/public/pieces/cburnett/`.
