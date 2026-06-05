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
const TRAINER_SUMMARY_KEY = "blunder-teacher:trainer-summary:v1";
const SRS_INTERVAL_DAYS = [0, 1, 3, 7, 14, 30, 60];
const REVIEW_MODES = [
  { id: "all", label: "All" },
  { id: "due", label: "Due" },
  { id: "again", label: "Again" },
  { id: "new", label: "New" },
  { id: "mastered", label: "Mastered" },
];

function buildPuzzleState(puzzle) {
  return {
    selectedMoveUci: "",
    submittedMoveUci: "",
    revealed: false,
    sourceSquare: "",
    playbackLineType: "",
    playbackPly: 0,
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

function todayStart() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return today;
}

function dueDateFromNow(days) {
  const dueDate = todayStart();
  dueDate.setDate(dueDate.getDate() + days);
  return dueDate.toISOString();
}

function normalizeTrainerStat(stat = {}) {
  const attempted = Number(stat.attempted || 0);
  const solved = Number(stat.solved || 0);
  const failed = Number(stat.failed || 0);
  const revealed = Number(stat.revealed || 0);
  const masteryLevel = Number(stat.masteryLevel || 0);
  const currentStreak = Number(stat.currentStreak || 0);
  const bestStreak = Number(stat.bestStreak || 0);
  return {
    attempted,
    solved,
    failed,
    revealed,
    firstSelectedMove: stat.firstSelectedMove || "",
    lastPracticed: stat.lastPracticed || "",
    lastResult: stat.lastResult || "",
    nextDue: stat.nextDue || "",
    masteryLevel,
    currentStreak,
    bestStreak,
    score: Number(stat.score || solved * 10 + masteryLevel * 5 + currentStreak * 2 - failed * 5 - revealed * 3),
  };
}

function normalizeTrainerStats(rawStats) {
  return Object.fromEntries(Object.entries(rawStats || {}).map(([puzzleId, stat]) => [puzzleId, normalizeTrainerStat(stat)]));
}

function buildTrainerSummaryFromStats(stats = {}) {
  const summary = {
    attempted: 0,
    solved: 0,
    failed: 0,
    revealed: 0,
    currentStreak: 0,
    bestStreak: 0,
    totalScore: 0,
    lastPracticed: "",
    lastResult: "",
  };

  for (const stat of Object.values(normalizeTrainerStats(stats))) {
    summary.attempted += stat.attempted;
    summary.solved += stat.solved;
    summary.failed += stat.failed;
    summary.revealed += stat.revealed;
    summary.bestStreak = Math.max(summary.bestStreak, stat.bestStreak);
    summary.totalScore += stat.score;
    if (stat.lastPracticed && (!summary.lastPracticed || stat.lastPracticed > summary.lastPracticed)) {
      summary.lastPracticed = stat.lastPracticed;
      summary.lastResult = stat.lastResult;
    }
  }

  return summary;
}

function normalizeTrainerSummary(summary = {}) {
  return {
    attempted: Number(summary.attempted || 0),
    solved: Number(summary.solved || 0),
    failed: Number(summary.failed || 0),
    revealed: Number(summary.revealed || 0),
    currentStreak: Number(summary.currentStreak || 0),
    bestStreak: Number(summary.bestStreak || 0),
    totalScore: Number(summary.totalScore ?? summary.score ?? 0),
    lastPracticed: summary.lastPracticed || "",
    lastResult: summary.lastResult || "",
  };
}

function loadTrainerStats() {
  if (typeof window === "undefined") {
    return {};
  }
  try {
    const rawStats = window.localStorage.getItem(TRAINER_STATS_KEY);
    return rawStats ? normalizeTrainerStats(JSON.parse(rawStats)) : {};
  } catch {
    return {};
  }
}

function loadTrainerSummary() {
  if (typeof window === "undefined") {
    return normalizeTrainerSummary();
  }
  try {
    const rawSummary = window.localStorage.getItem(TRAINER_SUMMARY_KEY);
    if (rawSummary) {
      return normalizeTrainerSummary(JSON.parse(rawSummary));
    }
    const rawStats = window.localStorage.getItem(TRAINER_STATS_KEY);
    return rawStats ? buildTrainerSummaryFromStats(JSON.parse(rawStats)) : normalizeTrainerSummary();
  } catch {
    return normalizeTrainerSummary();
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

function isDueStat(stat, now = new Date()) {
  const normalized = normalizeTrainerStat(stat);
  if (!normalized.attempted && !normalized.revealed) {
    return true;
  }
  if (!normalized.nextDue) {
    return true;
  }
  const dueTime = new Date(normalized.nextDue).getTime();
  return Number.isNaN(dueTime) || dueTime <= now.getTime();
}

function practiceGapForStats(stat) {
  const normalized = normalizeTrainerStat(stat);
  return normalized.failed + normalized.revealed - normalized.solved;
}

function nextTrainerStat(existingStat, outcome, selectedMoveUci = "") {
  const existing = normalizeTrainerStat(existingStat);
  const nowIso = new Date().toISOString();

  if (outcome === "solved") {
    const wasDue = isDueStat(existing);
    const masteryLevel = wasDue ? Math.min(6, existing.masteryLevel + 1) : existing.masteryLevel;
    const currentStreak = existing.currentStreak + 1;
    const intervalDays = SRS_INTERVAL_DAYS[masteryLevel] || 60;
    const solved = existing.solved + 1;
    const attempted = existing.attempted + 1;
    return {
      ...existing,
      attempted,
      solved,
      firstSelectedMove: existing.firstSelectedMove || selectedMoveUci,
      lastPracticed: nowIso,
      lastResult: "solved",
      nextDue: wasDue ? dueDateFromNow(intervalDays) : existing.nextDue,
      masteryLevel,
      currentStreak,
      bestStreak: Math.max(existing.bestStreak, currentStreak),
      score: solved * 10 + masteryLevel * 5 + currentStreak * 2 - existing.failed * 5 - existing.revealed * 3,
    };
  }

  if (outcome === "failed") {
    const failed = existing.failed + 1;
    const attempted = existing.attempted + 1;
    return {
      ...existing,
      attempted,
      failed,
      firstSelectedMove: existing.firstSelectedMove || selectedMoveUci,
      lastPracticed: nowIso,
      lastResult: "again",
      nextDue: new Date().toISOString(),
      masteryLevel: 0,
      currentStreak: 0,
      score: existing.solved * 10 - failed * 5 - existing.revealed * 3,
    };
  }

  if (outcome === "revealed") {
    const revealed = existing.revealed + 1;
    return {
      ...existing,
      revealed,
      lastPracticed: nowIso,
      lastResult: "again",
      nextDue: new Date().toISOString(),
      masteryLevel: 0,
      currentStreak: 0,
      score: existing.solved * 10 - existing.failed * 5 - revealed * 3,
    };
  }

  return {
    ...existing,
    lastPracticed: nowIso,
  };
}

function nextTrainerSummary(existingSummary, outcome) {
  const existing = normalizeTrainerSummary(existingSummary);
  const nowIso = new Date().toISOString();

  if (outcome === "solved") {
    const currentStreak = existing.currentStreak + 1;
    const scoreGain = 10 + Math.min(10, currentStreak * 2);
    return {
      ...existing,
      attempted: existing.attempted + 1,
      solved: existing.solved + 1,
      currentStreak,
      bestStreak: Math.max(existing.bestStreak, currentStreak),
      totalScore: existing.totalScore + scoreGain,
      lastPracticed: nowIso,
      lastResult: "solved",
    };
  }

  if (outcome === "failed") {
    return {
      ...existing,
      attempted: existing.attempted + 1,
      failed: existing.failed + 1,
      currentStreak: 0,
      totalScore: existing.totalScore - 5,
      lastPracticed: nowIso,
      lastResult: "again",
    };
  }

  if (outcome === "revealed") {
    return {
      ...existing,
      revealed: existing.revealed + 1,
      currentStreak: 0,
      totalScore: existing.totalScore - 3,
      lastPracticed: nowIso,
      lastResult: "again",
    };
  }

  return {
    ...existing,
    lastPracticed: nowIso,
  };
}

function puzzleMatchesReviewMode(puzzle, trainerStats, reviewMode) {
  const stats = normalizeTrainerStat(trainerStats[puzzle.id]);
  if (reviewMode === "due") {
    return isDueStat(stats);
  }
  if (reviewMode === "again") {
    return stats.lastResult === "again" || practiceGapForStats(stats) > 0;
  }
  if (reviewMode === "new") {
    return !stats.attempted && !stats.revealed;
  }
  if (reviewMode === "mastered") {
    return stats.masteryLevel >= 3;
  }
  return true;
}

function reviewCounts(puzzles, trainerStats) {
  return Object.fromEntries(
    REVIEW_MODES.map((mode) => [
      mode.id,
      puzzles.filter((puzzle) => puzzleMatchesReviewMode(puzzle, trainerStats, mode.id)).length,
    ]),
  );
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

function practiceStatsForWeakness(weakness, trainerStats) {
  const puzzleIds = Array.isArray(weakness.puzzle_ids)
    ? weakness.puzzle_ids
    : (Array.isArray(weakness.examples) ? weakness.examples.map((example) => example.id) : []);
  return puzzleIds.reduce(
    (totals, puzzleId) => {
      const stats = normalizeTrainerStat(trainerStats[puzzleId] || {});
      return {
        solved: totals.solved + stats.solved,
        failed: totals.failed + stats.failed,
        revealed: totals.revealed + stats.revealed,
      };
    },
    { solved: 0, failed: 0, revealed: 0 },
  );
}

function priorityStatus(practiceStats) {
  const hardAttempts = practiceStats.failed + practiceStats.revealed;
  if (!practiceStats.solved && !hardAttempts) {
    return "Not practiced yet";
  }
  if (hardAttempts > practiceStats.solved) {
    return `Needs review: ${hardAttempts} misses or reveals vs ${practiceStats.solved} solves`;
  }
  if (hardAttempts > 0) {
    return `Improving: ${practiceStats.solved} solves vs ${hardAttempts} misses or reveals`;
  }
  return `Stable: ${practiceStats.solved} solves`;
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
    .filter((weakness) => weakness.group_type !== "prompt_type")
    .sort((left, right) => {
      const leftGap = practiceGapForWeakness(left, trainerStats);
      const rightGap = practiceGapForWeakness(right, trainerStats);
      return rightGap - leftGap || Number(right.weakness_score || 0) - Number(left.weakness_score || 0);
    })
    .slice(0, 4);

  if (!topWeaknesses.length) {
    return null;
  }

  return (
    <section className="sidebar-card weakness-card">
      <div className="sidebar-section-header">
        <h2>Training Priorities</h2>
        <span className="counter-pill">{topWeaknesses.length} shown</span>
      </div>
      <p className="small-print weakness-intro">
        Recurring patterns mined from your games, ranked by repeated eval loss and your practice results.
      </p>
      <div className="weakness-list">
        {topWeaknesses.map((weakness) => {
          const drillLinks = weaknessDrillLinks(weakness);
          const practiceStats = practiceStatsForWeakness(weakness, trainerStats);
          return (
            <article key={`${weakness.group_type}:${weakness.label}`} className="weakness-item">
              <div>
                <span className="eyebrow">{String(weakness.group_type).replaceAll("_", " ")}</span>
                <h3>{weakness.label}</h3>
              </div>
              <p className="small-print">
                {weakness.count} positions · avg loss {weakness.average_eval_loss_display}
              </p>
              <p className="priority-status">{priorityStatus(practiceStats)}</p>
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

function ReviewPanel({ puzzles, trainerStats, trainerSummary, reviewMode, onReviewModeChange }) {
  const counts = reviewCounts(puzzles, trainerStats);
  const summary = normalizeTrainerSummary(trainerSummary);

  return (
    <section className="sidebar-card review-card">
      <div className="sidebar-section-header">
        <h2>Review</h2>
        <span className="counter-pill">{counts.due || 0} due</span>
      </div>
      <div className="stat-grid review-stat-grid">
        <div className="stat-card">
          <span className="stat-label">Again</span>
          <strong>{counts.again || 0}</strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">New</span>
          <strong>{counts.new || 0}</strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">Score</span>
          <strong>{summary.totalScore}</strong>
        </div>
      </div>
      <div className="review-mode-grid">
        {REVIEW_MODES.map((mode) => (
          <button
            key={mode.id}
            type="button"
            className={reviewMode === mode.id ? "review-mode-button active" : "review-mode-button"}
            onClick={() => onReviewModeChange(mode.id)}
          >
            {mode.label} [{counts[mode.id] || 0}]
          </button>
        ))}
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
  const [trainerSummary, setTrainerSummary] = useState(loadTrainerSummary);
  const [cursor, setCursor] = useState(0);
  const [reviewMode, setReviewMode] = useState("all");
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

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    window.localStorage.setItem(TRAINER_SUMMARY_KEY, JSON.stringify(trainerSummary));
  }, [trainerSummary]);

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
    const puzzleState = puzzleStates[puzzle.id];
    if (reviewMode !== "all" && (puzzleState?.submittedMoveUci || puzzleState?.revealed)) {
      return true;
    }
    if (!puzzleMatchesReviewMode(puzzle, trainerStats, reviewMode)) {
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
  const activeFilterCount = Object.values(filters).filter(Boolean).length + (reviewMode === "all" ? 0 : 1);
  const hasWeaknesses = weaknesses.length > 0;

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
    setReviewMode("all");
    setCursor(0);
  }

  function handleReviewModeChange(value) {
    setReviewMode(value);
    setCursor(0);
  }

  function recordTrainerResult(puzzleId, mutator) {
    if (!puzzleId) {
      return;
    }
    setTrainerStats((currentStats) => {
      const existing = normalizeTrainerStat(currentStats[puzzleId]);
      return {
        ...currentStats,
        [puzzleId]: mutator(existing),
      };
    });
  }

  function recordTrainerSummaryResult(outcome) {
    setTrainerSummary((currentSummary) => nextTrainerSummary(currentSummary, outcome));
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
      recordTrainerResult(currentPuzzle.id, (existing) => nextTrainerStat(existing, solved ? "solved" : "failed", selectedMove.uci));
      recordTrainerSummaryResult(solved ? "solved" : "failed");
    }
    updateCurrentPuzzleState((existing) => ({
      ...existing,
      submittedMoveUci: existing.selectedMoveUci,
      playbackLineType: "submitted",
      playbackPly: 1,
    }));
  }

  function handleReveal() {
    if (currentPuzzle && currentPuzzleState && !currentPuzzleState.revealed) {
      const outcome = currentPuzzleState.submittedMoveUci ? "viewed" : "revealed";
      recordTrainerResult(currentPuzzle.id, (existing) => nextTrainerStat(existing, outcome));
      recordTrainerSummaryResult(outcome);
    }
    updateCurrentPuzzleState((existing) => ({
      ...existing,
      revealed: true,
      playbackLineType: existing.submittedMoveUci ? existing.playbackLineType || "submitted" : "best",
      playbackPly: existing.playbackPly || 1,
    }));
  }

  function handleReset() {
    updateCurrentPuzzleState(() => buildPuzzleState(currentPuzzle));
  }

  function handleSetPlaybackLine(lineType) {
    updateCurrentPuzzleState((existing) => ({
      ...existing,
      playbackLineType: lineType,
      playbackPly: 1,
    }));
  }

  function handleSetPlaybackPly(ply) {
    updateCurrentPuzzleState((existing) => ({
      ...existing,
      playbackPly: Math.max(0, ply),
    }));
  }

  return (
    <div className="page-shell">
      <aside className={hasWeaknesses ? "sidebar with-priorities" : "sidebar"}>
        {hasWeaknesses ? (
          <div className="sidebar-priority-column">
            <WeaknessPanel weaknesses={weaknesses} trainerStats={trainerStats} />
          </div>
        ) : null}

        <div className="sidebar-control-column">
          <div className="brand-block">
            <span className="eyebrow">Training App</span>
            <h1>Blunder Teacher</h1>
            <p className="lede">
              Review critical positions from your PGNs, try your move on the board, and reveal the engine answer only when
              you are ready.
            </p>
          </div>

          <ReviewPanel
            puzzles={puzzles}
            trainerStats={trainerStats}
            trainerSummary={trainerSummary}
            reviewMode={reviewMode}
            onReviewModeChange={handleReviewModeChange}
          />

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
        </div>
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
            onSetPlaybackLine={handleSetPlaybackLine}
            onSetPlaybackPly={handleSetPlaybackPly}
            trainerStats={normalizeTrainerStat(trainerStats[currentPuzzle.id])}
            trainerSummary={normalizeTrainerSummary(trainerSummary)}
            onPrevious={() => setCursor((value) => Math.max(0, value - 1))}
            onNext={() => setCursor((value) => Math.min(filteredPuzzles.length - 1, value + 1))}
          />
        ) : null}
      </main>
    </div>
  );
}
