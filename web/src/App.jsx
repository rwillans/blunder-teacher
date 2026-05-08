import React, { useEffect, useState } from "react";

import { PuzzleWorkspace } from "./components/PuzzleWorkspace";
import {
  buildLichessOpeningTrainingUrl,
  buildLichessOpeningUrl,
  buildLichessPracticeUrl,
  buildLichessThemeUrl,
} from "./lichessLinks";

const DEFAULT_PUZZLES_URL = import.meta.env.VITE_PUZZLES_URL || (import.meta.env.DEV ? "/api/puzzles" : "/puzzles.json");
const DEFAULT_WEAKNESSES_URL = import.meta.env.VITE_WEAKNESSES_URL || (import.meta.env.DEV ? "/api/weaknesses" : "/weaknesses.json");
const TRAINER_STATS_KEY = "blunder-teacher:trainer-stats:v1";

function buildPuzzleState(puzzle) {
  return {
    selectedMoveUci: "",
    submittedMoveUci: "",
    revealed: false,
    sourceSquare: "",
    puzzleId: puzzle.id,
  };
}

function buildStateMap(puzzles) {
  const nextState = {};
  for (const puzzle of puzzles) {
    nextState[puzzle.id] = buildPuzzleState(puzzle);
  }
  return nextState;
}

function uniqueSorted(values) {
  return [...new Set(values.filter(Boolean))].sort((left, right) => left.localeCompare(right));
}

function countThemes(puzzles) {
  const counts = {};
  for (const puzzle of puzzles) {
    const tags = Array.isArray(puzzle.tags) ? uniqueSorted(puzzle.tags) : [];
    for (const tag of tags) {
      counts[tag] = (counts[tag] || 0) + 1;
    }
  }
  return counts;
}

function countValues(values) {
  const counts = {};
  for (const value of values) {
    if (value) {
      counts[value] = (counts[value] || 0) + 1;
    }
  }
  return counts;
}

function loadTrainerStats() {
  if (typeof window === "undefined") {
    return {};
  }
  try {
    const rawStats = window.localStorage.getItem(TRAINER_STATS_KEY);
    return rawStats ? JSON.parse(rawStats) : {};
  } catch {
    return {};
  }
}

function moveLookup(puzzle) {
  const options = Array.isArray(puzzle.legal_move_options) ? puzzle.legal_move_options : [];
  return Object.fromEntries(options.map((option) => [option.uci, option]));
}

function isSolvedMove(move) {
  if (!move) {
    return false;
  }
  return ["Excellent", "Good"].includes(move.grade) || Number(move.eval_loss_cp || 0) <= 50;
}

function practiceGapForWeakness(weakness, trainerStats) {
  const puzzleIds = Array.isArray(weakness.puzzle_ids)
    ? weakness.puzzle_ids
    : (Array.isArray(weakness.examples) ? weakness.examples.map((example) => example.id) : []);
  return puzzleIds.reduce((score, puzzleId) => {
    const stats = trainerStats[puzzleId] || {};
    return score + Number(stats.failed || 0) + Number(stats.revealed || 0) - Number(stats.solved || 0);
  }, 0);
}

function weaknessDrillLinks(weakness) {
  const links = [];
  const label = weakness.label || "";
  if (weakness.group_type === "opening") {
    const trainingUrl = buildLichessOpeningTrainingUrl(label);
    const openingUrl = buildLichessOpeningUrl(label);
    if (trainingUrl) {
      links.push({ label: "Puzzles", url: trainingUrl });
    }
    if (openingUrl) {
      links.push({ label: "Explore", url: openingUrl });
    }
  }
  if (["theme", "primary_theme", "phase"].includes(weakness.group_type)) {
    const themeUrl = buildLichessThemeUrl(label);
    const practiceUrl = buildLichessPracticeUrl(label);
    if (themeUrl) {
      links.push({ label: "Puzzles", url: themeUrl });
    }
    if (practiceUrl) {
      links.push({ label: "Practice", url: practiceUrl });
    }
  }
  return links;
}

function WeaknessPanel({ weaknesses, trainerStats }) {
  const topWeaknesses = [...weaknesses]
    .sort((left, right) => {
      const leftGap = practiceGapForWeakness(left, trainerStats);
      const rightGap = practiceGapForWeakness(right, trainerStats);
      return rightGap - leftGap || Number(right.weakness_score || 0) - Number(left.weakness_score || 0);
    })
    .slice(0, 5);

  if (!topWeaknesses.length) {
    return null;
  }

  return (
    <section className="sidebar-card weakness-card">
      <div className="sidebar-section-header">
        <h2>Weaknesses</h2>
        <span className="counter-pill">{weaknesses.length} groups</span>
      </div>
      <div className="weakness-list">
        {topWeaknesses.map((weakness) => {
          const drillLinks = weaknessDrillLinks(weakness);
          const practiceGapScore = practiceGapForWeakness(weakness, trainerStats);
          return (
            <article key={`${weakness.group_type}:${weakness.label}`} className="weakness-item">
              <div>
                <span className="eyebrow">{String(weakness.group_type).replaceAll("_", " ")}</span>
                <h3>{weakness.label}</h3>
              </div>
              <p className="small-print">
                {weakness.count} positions · avg {weakness.average_eval_loss_display} · gap {practiceGapScore}
              </p>
              {drillLinks.length ? (
                <div className="weakness-links">
                  {drillLinks.map((link) => (
                    <a key={link.label} href={link.url} target="_blank" rel="noreferrer" className="analysis-link">
                      {link.label}
                    </a>
                  ))}
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}

export default function App() {
  const [status, setStatus] = useState("loading");
  const [errorMessage, setErrorMessage] = useState("");
  const [puzzles, setPuzzles] = useState([]);
  const [weaknesses, setWeaknesses] = useState([]);
  const [puzzleStates, setPuzzleStates] = useState({});
  const [trainerStats, setTrainerStats] = useState(loadTrainerStats);
  const [cursor, setCursor] = useState(0);
  const [filters, setFilters] = useState({
    theme: "",
    opening: "",
    sideToMove: "",
  });

  useEffect(() => {
    let active = true;

    async function loadPuzzles() {
      try {
        const response = await fetch(DEFAULT_PUZZLES_URL);
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload?.error || `Request failed with status ${response.status}`);
        }
        if (!Array.isArray(payload)) {
          throw new Error("Expected puzzles.json to contain a top-level array.");
        }
        if (!active) {
          return;
        }

        setPuzzles(payload);
        setPuzzleStates(buildStateMap(payload));
        setStatus("ready");
      } catch (error) {
        if (!active) {
          return;
        }
        setStatus("error");
        setErrorMessage(error instanceof Error ? error.message : "Unknown error");
      }
    }

    loadPuzzles();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;

    async function loadWeaknesses() {
      try {
        const response = await fetch(DEFAULT_WEAKNESSES_URL);
        if (response.status === 404) {
          return;
        }
        const payload = await response.json();
        if (!active) {
          return;
        }
        setWeaknesses(Array.isArray(payload) ? payload : []);
      } catch {
        if (active) {
          setWeaknesses([]);
        }
      }
    }

    loadWeaknesses();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    window.localStorage.setItem(TRAINER_STATS_KEY, JSON.stringify(trainerStats));
  }, [trainerStats]);

  const filteredPuzzles = puzzles.filter((puzzle) => {
    const tags = Array.isArray(puzzle.tags) ? puzzle.tags : [];
    if (filters.theme && !tags.includes(filters.theme)) {
      return false;
    }
    if (filters.opening && puzzle.opening !== filters.opening) {
      return false;
    }
    if (filters.sideToMove && puzzle.side_to_move !== filters.sideToMove) {
      return false;
    }
    return true;
  });

  const safeCursor = filteredPuzzles.length === 0 ? 0 : Math.min(cursor, filteredPuzzles.length - 1);
  const currentPuzzle = filteredPuzzles[safeCursor] || null;
  const currentPuzzleState = currentPuzzle ? puzzleStates[currentPuzzle.id] : null;
  const themes = uniqueSorted(puzzles.flatMap((puzzle) => (Array.isArray(puzzle.tags) ? puzzle.tags : [])));
  const themeCounts = countThemes(puzzles);
  const openings = uniqueSorted(puzzles.map((puzzle) => puzzle.opening));
  const openingCounts = countValues(puzzles.map((puzzle) => puzzle.opening));
  const sideToMoveCounts = countValues(puzzles.map((puzzle) => puzzle.side_to_move));
  const activeFilterCount = Object.values(filters).filter(Boolean).length;

  function updateCurrentPuzzleState(mutator) {
    if (!currentPuzzle) {
      return;
    }

    setPuzzleStates((currentState) => {
      const existing = currentState[currentPuzzle.id] || buildPuzzleState(currentPuzzle);
      return {
        ...currentState,
        [currentPuzzle.id]: mutator(existing),
      };
    });
  }

  function handleFilterChange(key, value) {
    setFilters((currentFilters) => ({
      ...currentFilters,
      [key]: value,
    }));
    setCursor(0);
  }

  function clearFilters() {
    setFilters({
      theme: "",
      opening: "",
      sideToMove: "",
    });
    setCursor(0);
  }

  function recordTrainerResult(puzzleId, mutator) {
    if (!puzzleId) {
      return;
    }
    setTrainerStats((currentStats) => {
      const existing = currentStats[puzzleId] || {
        attempted: 0,
        solved: 0,
        failed: 0,
        revealed: 0,
        firstSelectedMove: "",
        lastPracticed: "",
      };
      return {
        ...currentStats,
        [puzzleId]: mutator(existing),
      };
    });
  }

  function handleMoveSelect(selection) {
    updateCurrentPuzzleState((existing) => ({
      ...existing,
      selectedMoveUci: selection.moveUci,
      sourceSquare: selection.sourceSquare,
    }));
  }

  function handleClearSelection() {
    updateCurrentPuzzleState((existing) => ({
      ...existing,
      selectedMoveUci: "",
      sourceSquare: "",
    }));
  }

  function handleSubmitMove() {
    const selectedMove = currentPuzzle && currentPuzzleState ? moveLookup(currentPuzzle)[currentPuzzleState.selectedMoveUci] : null;
    if (currentPuzzle && selectedMove && !currentPuzzleState.submittedMoveUci) {
      const solved = isSolvedMove(selectedMove);
      recordTrainerResult(currentPuzzle.id, (existing) => ({
        ...existing,
        attempted: Number(existing.attempted || 0) + 1,
        solved: Number(existing.solved || 0) + (solved ? 1 : 0),
        failed: Number(existing.failed || 0) + (solved ? 0 : 1),
        firstSelectedMove: existing.firstSelectedMove || selectedMove.uci,
        lastPracticed: new Date().toISOString(),
      }));
    }
    updateCurrentPuzzleState((existing) => ({
      ...existing,
      submittedMoveUci: existing.selectedMoveUci,
    }));
  }

  function handleReveal() {
    if (currentPuzzle && currentPuzzleState && !currentPuzzleState.revealed) {
      recordTrainerResult(currentPuzzle.id, (existing) => ({
        ...existing,
        revealed: Number(existing.revealed || 0) + 1,
        lastPracticed: new Date().toISOString(),
      }));
    }
    updateCurrentPuzzleState((existing) => ({
      ...existing,
      revealed: true,
    }));
  }

  function handleReset() {
    updateCurrentPuzzleState(() => buildPuzzleState(currentPuzzle));
  }

  return (
    <div className="page-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <span className="eyebrow">Training App</span>
          <h1>Blunder Teacher</h1>
          <p className="lede">
            Review critical positions from your PGNs, try your move on the board, and reveal the engine answer only when
            you are ready.
          </p>
        </div>

        <section className="sidebar-card">
          <div className="sidebar-section-header">
            <h2>Session</h2>
            <span className="counter-pill">{puzzles.length} loaded</span>
          </div>
          <div className="stat-grid">
            <div className="stat-card">
              <span className="stat-label">Visible now</span>
              <strong>{filteredPuzzles.length}</strong>
            </div>
            <div className="stat-card">
              <span className="stat-label">Openings</span>
              <strong>{openings.length}</strong>
            </div>
            <div className="stat-card">
              <span className="stat-label">Themes</span>
              <strong>{themes.length}</strong>
            </div>
          </div>
        </section>

        <section className="sidebar-card">
          <div className="sidebar-section-header">
            <h2>Filters</h2>
            <button type="button" className="link-button muted-action" onClick={clearFilters} disabled={!activeFilterCount}>
              Clear all
            </button>
          </div>
          <p className="small-print">Narrow the training set by theme, opening, or side to move.</p>
          <label>
            <span>Theme</span>
            <select value={filters.theme} onChange={(event) => handleFilterChange("theme", event.target.value)}>
              <option value="">Any</option>
              {themes.map((theme) => (
                <option key={theme} value={theme}>
                  {theme} [{themeCounts[theme] || 0}]
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>Opening</span>
            <select value={filters.opening} onChange={(event) => handleFilterChange("opening", event.target.value)}>
              <option value="">Any</option>
              {openings.map((opening) => (
                <option key={opening} value={opening}>
                  {opening} [{openingCounts[opening] || 0}]
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>Side to move</span>
            <select value={filters.sideToMove} onChange={(event) => handleFilterChange("sideToMove", event.target.value)}>
              <option value="">Any</option>
              <option value="White">White [{sideToMoveCounts.White || 0}]</option>
              <option value="Black">Black [{sideToMoveCounts.Black || 0}]</option>
            </select>
          </label>
        </section>

        <section className="sidebar-card">
          <h2>How To Use It</h2>
          <p className="small-print">
            Pick a piece, then click a destination square. Use <strong>Check move</strong> to grade your choice, or
            reveal the answer if you want the engine line and explanation.
          </p>
        </section>

        <WeaknessPanel weaknesses={weaknesses} trainerStats={trainerStats} />
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <span className="eyebrow">Study Board</span>
            <h2>{currentPuzzle ? currentPuzzle.prompt : "Ready to train"}</h2>
          </div>

          <div className="counter-pill">
            {filteredPuzzles.length ? `Puzzle ${safeCursor + 1} of ${filteredPuzzles.length}` : "No matching puzzles"}
          </div>
        </header>

        {status === "loading" ? (
          <section className="empty-state">
            <h3>Loading puzzles…</h3>
            <p>The board will appear as soon as the latest puzzle set has loaded.</p>
          </section>
        ) : null}

        {status === "error" ? (
          <section className="empty-state">
            <h3>Could not load puzzle data</h3>
            <p>{errorMessage}</p>
            <p>Run the Python pipeline again and make sure the app can still read <code>{DEFAULT_PUZZLES_URL}</code>.</p>
          </section>
        ) : null}

        {status === "ready" && !currentPuzzle ? (
          <section className="empty-state">
            <h3>{puzzles.length === 0 ? "No puzzles loaded yet" : "No puzzles match the current filters"}</h3>
            <p>
              {puzzles.length === 0
                ? "Run the Python pipeline to generate fresh puzzle data, then refresh this page."
                : "Clear one or more filters to bring positions back into the training set."}
            </p>
          </section>
        ) : null}

        {status === "ready" && currentPuzzle && currentPuzzleState ? (
          <PuzzleWorkspace
            puzzle={currentPuzzle}
            puzzleState={currentPuzzleState}
            canGoBack={safeCursor > 0}
            canGoForward={safeCursor < filteredPuzzles.length - 1}
            onMoveSelect={handleMoveSelect}
            onClearSelection={handleClearSelection}
            onSubmitMove={handleSubmitMove}
            onReveal={handleReveal}
            onReset={handleReset}
            onPrevious={() => setCursor((value) => Math.max(0, value - 1))}
            onNext={() => setCursor((value) => Math.min(filteredPuzzles.length - 1, value + 1))}
          />
        ) : null}
      </main>
    </div>
  );
}
