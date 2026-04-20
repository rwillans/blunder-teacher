# Blunder Teacher Web

This is the longer-term frontend foundation for moving the trainer away from a giant generated HTML file and toward a real component-driven web app.

## What It Expects

The Python pipeline now writes `puzzles.json` into the selected output directory and also syncs a copy to `web/public/puzzles.json`. This frontend loads that payload and renders it with React plus `react-chessboard`.

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

## Why This Exists

- The board UI now has a dedicated component boundary.
- Piece and board aesthetics can evolve independently from the analysis pipeline.
- A future FastAPI or similar backend can serve `puzzles.json` without rewriting the viewer again.

## Piece Set

The frontend now uses the classic Cburnett SVG piece set from `web/public/pieces/cburnett/`, rendered through `react-chessboard`'s custom piece API. The exported HTML viewer also copies the same assets into its output folder so both viewers stay visually aligned.
