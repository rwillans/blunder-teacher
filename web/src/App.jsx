import React, { useEffect, useState } from "react";

import { PuzzleWorkspace } from "./components/PuzzleWorkspace";

const DEFAULT_PUZZLES_URL = import.meta.env.VITE_PUZZLES_URL || "/puzzles.json";

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

export default function App() {
  const [status, setStatus] = useState("loading");
  const [errorMessage, setErrorMessage] = useState("");
  const [puzzles, setPuzzles] = useState([]);
  const [puzzleStates, setPuzzleStates] = useState({});
  const [cursor, setCursor] = useState(0);
  const [filters, setFilters] = useState({
    promptType: "",
    opening: "",
    sideToMove: "",
  });

  useEffect(() => {
    let active = true;

    async function loadPuzzles() {
      try {
        const response = await fetch(DEFAULT_PUZZLES_URL);
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }

        const payload = await response.json();
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

  const filteredPuzzles = puzzles.filter((puzzle) => {
    if (filters.promptType && puzzle.puzzle_prompt_type !== filters.promptType) {
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
    updateCurrentPuzzleState((existing) => ({
      ...existing,
      submittedMoveUci: existing.selectedMoveUci,
    }));
  }

  function handleReveal() {
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
          <span className="eyebrow">Web Foundation</span>
          <h1>Blunder Teacher</h1>
          <p className="lede">
            A longer-term React viewer that loads backend puzzle data from <code>puzzles.json</code> and gives the board
            UI its own home.
          </p>
        </div>

        <section className="sidebar-card">
          <h2>Filters</h2>
          <label>
            <span>Prompt type</span>
            <select value={filters.promptType} onChange={(event) => handleFilterChange("promptType", event.target.value)}>
              <option value="">Any</option>
              {uniqueSorted(puzzles.map((puzzle) => puzzle.puzzle_prompt_type)).map((promptType) => (
                <option key={promptType} value={promptType}>
                  {promptType}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>Opening</span>
            <select value={filters.opening} onChange={(event) => handleFilterChange("opening", event.target.value)}>
              <option value="">Any</option>
              {uniqueSorted(puzzles.map((puzzle) => puzzle.opening)).map((opening) => (
                <option key={opening} value={opening}>
                  {opening}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>Side to move</span>
            <select value={filters.sideToMove} onChange={(event) => handleFilterChange("sideToMove", event.target.value)}>
              <option value="">Any</option>
              <option value="White">White</option>
              <option value="Black">Black</option>
            </select>
          </label>
        </section>

        <section className="sidebar-card">
          <h2>Source</h2>
          <p className="small-print">
            Loading from <code>{DEFAULT_PUZZLES_URL}</code>
          </p>
          <p className="small-print">
            This keeps the analysis pipeline and the board renderer decoupled, which is the important technical-debt win.
          </p>
        </section>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <span className="eyebrow">Puzzle Viewer</span>
            <h2>Component-driven board workspace</h2>
          </div>

          <div className="counter-pill">
            {filteredPuzzles.length ? `Puzzle ${safeCursor + 1} of ${filteredPuzzles.length}` : "No matching puzzles"}
          </div>
        </header>

        {status === "loading" ? (
          <section className="empty-state">
            <h3>Loading puzzles…</h3>
            <p>The frontend is waiting for the exported JSON payload.</p>
          </section>
        ) : null}

        {status === "error" ? (
          <section className="empty-state">
            <h3>Could not load puzzle data</h3>
            <p>{errorMessage}</p>
            <p>Make sure the Python pipeline has written a <code>puzzles.json</code> file and that the frontend can fetch it.</p>
          </section>
        ) : null}

        {status === "ready" && !currentPuzzle ? (
          <section className="empty-state">
            <h3>No puzzles match these filters</h3>
            <p>Try widening the opening, prompt, or side-to-move filters.</p>
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
