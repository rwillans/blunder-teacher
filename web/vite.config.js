import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const configDir = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(configDir, "..");
const defaultPuzzlePath = path.join(projectRoot, "outputs", "puzzles.json");
const defaultWeaknessPath = path.join(projectRoot, "outputs", "weaknesses.json");

function serveJsonFile(res, filePath, missingPayload, readErrorMessage) {
  if (!fs.existsSync(filePath)) {
    res.statusCode = 404;
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.end(JSON.stringify(missingPayload));
    return;
  }

  try {
    const content = fs.readFileSync(filePath, "utf8");
    res.statusCode = 200;
    res.setHeader("Cache-Control", "no-store");
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.end(content);
  } catch (error) {
    res.statusCode = 500;
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.end(
      JSON.stringify({
        error: error instanceof Error ? error.message : readErrorMessage,
      }),
    );
  }
}

function serveLocalPuzzleData() {
  return {
    name: "serve-local-puzzle-data",
    configureServer(server) {
      server.middlewares.use("/api/puzzles", (req, res, next) => {
        serveJsonFile(
          res,
          defaultPuzzlePath,
          { error: "outputs/puzzles.json was not found" },
          "Unable to read outputs/puzzles.json",
        );
      });
      server.middlewares.use("/api/weaknesses", (req, res, next) => {
        serveJsonFile(
          res,
          defaultWeaknessPath,
          [],
          "Unable to read outputs/weaknesses.json",
        );
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), serveLocalPuzzleData()],
});
