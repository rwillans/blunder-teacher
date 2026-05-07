import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const configDir = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(configDir, "..");
const defaultPuzzlePath = path.join(projectRoot, "outputs", "puzzles.json");

function serveLocalPuzzleData() {
  return {
    name: "serve-local-puzzle-data",
    configureServer(server) {
      server.middlewares.use("/api/puzzles", (req, res, next) => {
        if (!fs.existsSync(defaultPuzzlePath)) {
          res.statusCode = 404;
          res.setHeader("Content-Type", "application/json; charset=utf-8");
          res.end(JSON.stringify({ error: "outputs/puzzles.json was not found" }));
          return;
        }

        try {
          const content = fs.readFileSync(defaultPuzzlePath, "utf8");
          res.statusCode = 200;
          res.setHeader("Cache-Control", "no-store");
          res.setHeader("Content-Type", "application/json; charset=utf-8");
          res.end(content);
        } catch (error) {
          res.statusCode = 500;
          res.setHeader("Content-Type", "application/json; charset=utf-8");
          res.end(
            JSON.stringify({
              error: error instanceof Error ? error.message : "Unable to read outputs/puzzles.json",
            }),
          );
        }
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), serveLocalPuzzleData()],
});
