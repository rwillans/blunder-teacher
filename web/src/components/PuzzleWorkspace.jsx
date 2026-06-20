import React, { useEffect } from "react";

import { buildLinePositions } from "../chessPlayback";
import { classifySubmittedMove, masteryStatusForLevel } from "../srs";
import { BoardShell } from "./BoardShell";
import {
  buildLichessAnalysisUrl,
  buildLichessOpeningTrainingUrl,
  buildLichessOpeningUrl,
  buildLichessPracticeUrl,
  buildLichessThemeUrl,
} from "../lichessLinks";

function moveLookup(puzzle) {
  const options = Array.isArray(puzzle.legal_move_options) ? puzzle.legal_move_options : [];
  return Object.fromEntries(options.map((option) => [option.uci, option]));
}

function findBestOption(puzzle, lookup) {
  if (puzzle.best_move_uci && lookup[puzzle.best_move_uci]) {
    return lookup[puzzle.best_move_uci];
  }
  const options = Array.isArray(puzzle.legal_move_options) ? puzzle.legal_move_options : [];
  return options.find((option) => Number(option.eval_loss_cp || 0) === 0) || null;
}

function lineMoves(option) {
  if (!option) {
    return [];
  }
  const pv = Array.isArray(option.pv_uci) ? option.pv_uci.filter(Boolean) : [];
  return pv.length ? pv : [option.uci].filter(Boolean);
}

function buildOptionLinePositions(puzzle, option) {
  const moves = lineMoves(option);
  const positions = buildLinePositions(puzzle.fen, moves);
  if (positions.length > 1 || !option?.resulting_fen || !option?.uci) {
    return positions;
  }

  const continuationMoves = moves[0] === option.uci ? moves.slice(1) : moves;
  const continuationPositions = buildLinePositions(option.resulting_fen, continuationMoves);
  if (continuationPositions.length <= 1) {
    return positions;
  }

  return [
    { fen: puzzle.fen, moveUci: "", san: "Start", ply: 0 },
    { fen: option.resulting_fen, moveUci: option.uci, san: option.san || option.uci, ply: 1 },
    ...continuationPositions.slice(1).map((position, index) => ({
      ...position,
      ply: index + 2,
    })),
  ];
}

function formatDue(nextDue) {
  if (!nextDue) {
    return "Now";
  }
  const dueTime = new Date(nextDue).getTime();
  if (Number.isNaN(dueTime)) {
    return "Now";
  }
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const days = Math.ceil((dueTime - today.getTime()) / (24 * 60 * 60 * 1000));
  if (days <= 0) {
    return "Today";
  }
  if (days === 1) {
    return "Tomorrow";
  }
  return `${days} days`;
}

function LinePlaybackControls({
  label,
  positions,
  playbackPly,
  canShowBest,
  activeLineType,
  onSetPlaybackLine,
  onSetPlaybackPly,
}) {
  const maxPly = Math.max(0, positions.length - 1);
  if (!maxPly) {
    return null;
  }
  const safePly = Math.min(playbackPly, maxPly);
  const currentPosition = positions[safePly] || positions[0];

  return (
    <div className="line-playback">
      <div className="line-playback-header">
        <strong>{label}</strong>
        <span className="small-print">
          {safePly} / {maxPly} · {currentPosition.san}
        </span>
      </div>
      {canShowBest ? (
        <div className="segmented-control">
          <button
            type="button"
            className={activeLineType === "submitted" ? "segment-button active" : "segment-button"}
            onClick={() => onSetPlaybackLine("submitted")}
          >
            Your line
          </button>
          <button
            type="button"
            className={activeLineType === "best" ? "segment-button active" : "segment-button"}
            onClick={() => onSetPlaybackLine("best")}
          >
            Best line
          </button>
        </div>
      ) : null}
      <div className="playback-actions">
        <button type="button" className="ghost-button" onClick={() => onSetPlaybackPly(0)} disabled={safePly === 0}>
          Start
        </button>
        <button type="button" className="ghost-button" onClick={() => onSetPlaybackPly(safePly - 1)} disabled={safePly === 0}>
          Previous
        </button>
        <button type="button" onClick={() => onSetPlaybackPly(safePly + 1)} disabled={safePly >= maxPly}>
          Next
        </button>
      </div>
    </div>
  );
}

function LichessLinkStack({
  analysisUrl,
  opening,
  openingUrl,
  openingTrainingUrl,
  themeLinks,
  practiceLinks,
}) {
  const hasPrimaryLinks = Boolean(analysisUrl || openingUrl);
  const hasThematicLinks = Boolean(openingTrainingUrl || themeLinks.length || practiceLinks.length);
  if (!hasPrimaryLinks && !hasThematicLinks) {
    return null;
  }

  return (
    <div className="lichess-link-stack">
      {hasPrimaryLinks ? (
        <div className="lichess-link-group">
          {analysisUrl ? (
            <a href={analysisUrl} target="_blank" rel="noreferrer" className="analysis-link">
              Open position in Lichess
            </a>
          ) : null}
          {openingUrl ? (
            <a href={openingUrl} target="_blank" rel="noreferrer" className="analysis-link">
              Explore {opening} on Lichess
            </a>
          ) : null}
        </div>
      ) : null}
      {hasThematicLinks ? (
        <div className="lichess-link-group thematic-link-group">
          {openingTrainingUrl ? (
            <a href={openingTrainingUrl} target="_blank" rel="noreferrer" className="analysis-link">
              Open {opening} puzzles on Lichess
            </a>
          ) : null}
          {themeLinks.map((link) => (
            <a key={link.label} href={link.url} target="_blank" rel="noreferrer" className="analysis-link">
              Open {link.label.toLowerCase()} puzzles on Lichess
            </a>
          ))}
          {practiceLinks.map((link) => (
            <a key={`${link.label}-practice`} href={link.url} target="_blank" rel="noreferrer" className="analysis-link">
              Study {link.label.toLowerCase()} in Lichess Practice
            </a>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function PuzzleWorkspace({
  puzzle,
  puzzleState,
  canGoBack,
  canGoForward,
  onMoveSelect,
  onClearSelection,
  onSubmitMove,
  onReveal,
  onReset,
  onSetPlaybackLine,
  onSetPlaybackPly,
  onPrevious,
  onNext,
  onSolvedPlaybackComplete,
  trainerStats,
  trainerSummary = {},
}) {
  const lookup = moveLookup(puzzle);
  const selectedMove = puzzleState.selectedMoveUci ? lookup[puzzleState.selectedMoveUci] : null;
  const submittedMove = puzzleState.submittedMoveUci ? lookup[puzzleState.submittedMoveUci] : null;
  const bestOption = findBestOption(puzzle, lookup);
  const tags = Array.isArray(puzzle.tags) ? puzzle.tags : [];
  const playedMove = puzzle.played_move_san || puzzle.played_move_uci || "Unavailable";
  const bestMove = puzzle.best_move_san || puzzle.best_move_uci || "Unavailable";
  const activeLineType = puzzleState.playbackLineType || (submittedMove ? "submitted" : puzzleState.revealed ? "best" : "");
  const activeLineOption = activeLineType === "best" ? bestOption : submittedMove;
  const playbackPositions = activeLineOption ? buildOptionLinePositions(puzzle, activeLineOption) : [];
  const playbackMaxPly = Math.max(0, playbackPositions.length - 1);
  const playbackPly = Math.min(Number(puzzleState.playbackPly || 0), playbackMaxPly);
  const playbackPosition = playbackPositions[playbackPly] || null;
  const playbackFen = playbackPosition ? playbackPosition.fen : "";
  const playbackMoveUci = playbackPosition ? playbackPosition.moveUci : "";
  const canShowBestLine = Boolean(submittedMove && puzzleState.revealed && bestOption);
  const submittedAnalysisUrl = submittedMove ? buildLichessAnalysisUrl(submittedMove.resulting_fen || puzzle.fen, puzzle.side_to_move) : "";
  const revealedAnalysisUrl = bestOption ? buildLichessAnalysisUrl(bestOption.resulting_fen || puzzle.fen, puzzle.side_to_move) : buildLichessAnalysisUrl(puzzle.fen, puzzle.side_to_move);
  const lichessThemeLinks = tags
    .map((tag) => ({ label: tag, url: buildLichessThemeUrl(tag) }))
    .filter((link) => link.url);
  const lichessPracticeLinks = tags
    .map((tag) => ({ label: tag, url: buildLichessPracticeUrl(tag) }))
    .filter((link) => link.url);
  const lichessOpeningTrainingUrl = buildLichessOpeningTrainingUrl(puzzle.opening);
  const lichessOpeningUrl = buildLichessOpeningUrl(puzzle.opening);
  const studyAnalysisUrl = submittedMove ? submittedAnalysisUrl : revealedAnalysisUrl;
  const showCoachResult = Boolean(submittedMove || puzzleState.revealed);
  const engineLineLabel = activeLineType === "best" ? "Best engine line" : "Your move line";
  const submittedOutcome = submittedMove ? classifySubmittedMove(puzzle, submittedMove) : "";
  const submittedMoveSolved = submittedOutcome === "solved";
  const hasStudyLinks = Boolean(
    showCoachResult
      && (studyAnalysisUrl
        || lichessOpeningUrl
        || lichessOpeningTrainingUrl
        || lichessThemeLinks.length
        || lichessPracticeLinks.length),
  );

  useEffect(() => {
    if (!activeLineType || playbackMaxPly <= 1 || playbackPly >= playbackMaxPly) {
      return undefined;
    }
    if (!submittedMove && !puzzleState.revealed) {
      return undefined;
    }

    const timer = window.setTimeout(() => {
      onSetPlaybackPly(playbackPly + 1);
    }, playbackPly <= 1 ? 1000 : 1250);

    return () => window.clearTimeout(timer);
  }, [
    activeLineType,
    playbackMaxPly,
    playbackPly,
    puzzle.id,
    puzzleState.revealed,
    submittedMove,
    onSetPlaybackPly,
  ]);

  useEffect(() => {
    if (
      !canGoForward
      || !submittedMoveSolved
      || activeLineType !== "submitted"
      || playbackMaxPly < 1
      || playbackPly < playbackMaxPly
    ) {
      return undefined;
    }

    const timer = window.setTimeout(() => {
      onSolvedPlaybackComplete();
    }, 2500);

    return () => window.clearTimeout(timer);
  }, [
    activeLineType,
    canGoForward,
    onSolvedPlaybackComplete,
    playbackMaxPly,
    playbackPly,
    puzzle.id,
    submittedMoveSolved,
  ]);

  return (
    <section className="workspace-grid">
      <div className="workspace-main">
        <div className="hero-card">
          <div className="hero-copy">
            <span className="eyebrow">{puzzle.puzzle_prompt_type}</span>
            <h3>{puzzle.prompt}</h3>
            {puzzle.prompt_hint ? <p className="prompt-hint">{puzzle.prompt_hint}</p> : null}
            <p>{puzzle.opening || "Opening not recorded"}</p>
            <p className="hero-meta">
              {puzzle.white || "White"} vs {puzzle.black || "Black"} · {puzzle.event || "Unknown event"} ·{" "}
              {puzzle.date || "Unknown date"}
            </p>
          </div>

          <div className="toolbar">
            <button type="button" onClick={onPrevious} disabled={!canGoBack}>
              Previous
            </button>
            <button type="button" onClick={onNext} disabled={!canGoForward}>
              Next
            </button>
            <button type="button" className="ghost-button" onClick={onReset}>
              Reset
            </button>
          </div>
        </div>

        <BoardShell
          puzzle={puzzle}
          puzzleState={puzzleState}
          onMoveSelect={onMoveSelect}
          playbackFen={playbackFen}
          playbackMoveUci={playbackMoveUci}
        />
      </div>

      <aside className="workspace-sidebar">
        <section className="move-coach-card detail-card">
          <div className="coach-header">
            <span className="eyebrow">Move Coach</span>
          </div>

          {!showCoachResult ? (
            <>
              <strong className="coach-selection">
                {selectedMove ? `${selectedMove.san} (${selectedMove.uci})` : "Choose a piece, then choose a square"}
              </strong>
              <p className="small-print">Click a piece, then a destination square. Check your move or reveal the engine answer.</p>
              <div className="button-stack pending-actions">
                <button type="button" onClick={onSubmitMove} disabled={!selectedMove}>
                  Check move
                </button>
                <button type="button" className="ghost-button" onClick={onReveal}>
                  Show answer
                </button>
              </div>
              {selectedMove ? (
                <button type="button" className="link-button" onClick={onClearSelection}>
                  Clear selection
                </button>
              ) : null}
            </>
          ) : null}

          {submittedMove ? (
            <>
              <div className="result-strip">
                <div>
                  <span className="stat-label">Outcome</span>
                  <strong>{submittedOutcome || submittedMove.grade}</strong>
                </div>
                <div>
                  <span className="stat-label">Your move</span>
                  <strong>{submittedMove.san || submittedMove.uci}</strong>
                </div>
                <div>
                  <span className="stat-label">Eval loss</span>
                  <strong>{submittedMove.eval_loss_display}</strong>
                </div>
              </div>
              <LinePlaybackControls
                label={engineLineLabel}
                positions={playbackPositions}
                playbackPly={playbackPly}
                canShowBest={canShowBestLine}
                activeLineType={activeLineType}
                onSetPlaybackLine={onSetPlaybackLine}
                onSetPlaybackPly={onSetPlaybackPly}
              />
            </>
          ) : null}

          {puzzleState.revealed ? (
            <div className="answer-panel">
              <span className="eyebrow">Answer</span>
              <strong>{bestMove}</strong>
              <p>{puzzle.explanation || "No explanation available."}</p>
              {!submittedMove ? (
                <LinePlaybackControls
                  label={engineLineLabel}
                  positions={playbackPositions}
                  playbackPly={playbackPly}
                  canShowBest={canShowBestLine}
                  activeLineType={activeLineType}
                  onSetPlaybackLine={onSetPlaybackLine}
                  onSetPlaybackPly={onSetPlaybackPly}
                />
              ) : null}
            </div>
          ) : null}

          {showCoachResult ? (
            <>
              <details className="coach-details">
                <summary>Engine line</summary>
                {submittedMove ? (
                  <>
                    <p>
                      <strong>Resulting eval:</strong> {submittedMove.eval_display}
                    </p>
                    <p>
                      <strong>Your line:</strong> {submittedMove.pv_san || "Unavailable"}
                    </p>
                  </>
                ) : null}
                {puzzleState.revealed ? (
                  <p>
                    <strong>Best line:</strong> {puzzle.best_pv || "No principal variation recorded."}
                  </p>
                ) : null}
              </details>

              {hasStudyLinks ? (
                <details className="coach-details">
                  <summary>Study links</summary>
                  <LichessLinkStack
                    analysisUrl={studyAnalysisUrl}
                    opening={puzzle.opening}
                    openingUrl={lichessOpeningUrl}
                    openingTrainingUrl={lichessOpeningTrainingUrl}
                    themeLinks={lichessThemeLinks}
                    practiceLinks={lichessPracticeLinks}
                  />
                </details>
              ) : null}

              <div className="button-stack coach-actions">
                {!puzzleState.revealed ? (
                  <button type="button" className="ghost-button" onClick={onReveal}>
                    Show answer
                  </button>
                ) : null}
                <button type="button" className="ghost-button" onClick={onReset}>
                  Reset
                </button>
              </div>
            </>
          ) : null}
        </section>

        <section className="detail-card score-card compact-score-card">
          <span className="eyebrow">Score</span>
          <dl className="score-grid">
            <div>
              <dt>Total score</dt>
              <dd>{trainerSummary.totalScore || 0}</dd>
            </div>
            <div>
              <dt>Streak</dt>
              <dd>
                {trainerSummary.currentStreak || 0} / {trainerSummary.bestStreak || 0}
              </dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{masteryStatusForLevel(trainerStats.masteryLevel)}</dd>
            </div>
            <div>
              <dt>This puzzle</dt>
              <dd>
                {trainerStats.solved || 0} solved · {trainerStats.failed || 0} missed
              </dd>
            </div>
            <div>
              <dt>Next review</dt>
              <dd>{formatDue(trainerStats.nextDue)}</dd>
            </div>
          </dl>
        </section>

        <section className="detail-card position-details-card">
          <details>
            <summary>Position details</summary>
            <dl>
              <div>
                <dt>Opening</dt>
                <dd>{puzzle.opening || "Unknown opening"}</dd>
              </div>
              <div>
                <dt>Move number</dt>
                <dd>{puzzle.move_number}</dd>
              </div>
              <div>
                <dt>Side to move</dt>
                <dd>{puzzle.side_to_move}</dd>
              </div>
              <div>
                <dt>Source</dt>
                <dd>
                  {puzzle.source_file} (game {puzzle.game_index})
                </dd>
              </div>
              <div>
                <dt>Played in game</dt>
                <dd>{playedMove}</dd>
              </div>
              {tags.length ? (
                <div>
                  <dt>Themes</dt>
                  <dd className="detail-tags">
                    <div className="tag-list compact-tag-list">
                      {tags.map((tag) => (
                        <span key={tag} className="tag-pill">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </dd>
                </div>
              ) : null}
            </dl>
          </details>
        </section>

      </aside>
    </section>
  );
}
