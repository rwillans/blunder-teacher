import React from "react";

import { buildLinePositions } from "../chessPlayback";
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
  trainerStats,
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
  const playbackPositions = activeLineOption ? buildLinePositions(puzzle.fen, lineMoves(activeLineOption)) : [];
  const playbackMaxPly = Math.max(0, playbackPositions.length - 1);
  const playbackPly = Math.min(Number(puzzleState.playbackPly || 0), playbackMaxPly);
  const playbackPosition = playbackPositions[playbackPly] || null;
  const playbackFen = playbackPosition ? playbackPosition.fen : "";
  const playbackMoveUci = playbackPosition ? playbackPosition.moveUci : "";
  const canShowBestLine = Boolean(submittedMove && puzzleState.revealed && bestOption);
  const currentBoardLichessUrl = submittedMove ? buildLichessAnalysisUrl(submittedMove.resulting_fen, puzzle.side_to_move) : "";
  const lichessThemeLinks = tags
    .map((tag) => ({ label: tag, url: buildLichessThemeUrl(tag) }))
    .filter((link) => link.url);
  const lichessPracticeLinks = tags
    .map((tag) => ({ label: tag, url: buildLichessPracticeUrl(tag) }))
    .filter((link) => link.url);
  const lichessOpeningTrainingUrl = buildLichessOpeningTrainingUrl(puzzle.opening);
  const lichessOpeningUrl = buildLichessOpeningUrl(puzzle.opening);

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
        <section className="detail-card">
          <span className="eyebrow">At A Glance</span>
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
        </section>

        <section className="detail-card score-card">
          <span className="eyebrow">Score</span>
          <dl>
            <div>
              <dt>Total score</dt>
              <dd>{trainerStats.score || 0}</dd>
            </div>
            <div>
              <dt>Attempts</dt>
              <dd>
                {trainerStats.solved || 0} solved · {trainerStats.failed || 0} missed
              </dd>
            </div>
            <div>
              <dt>Streak</dt>
              <dd>
                {trainerStats.currentStreak || 0} current · {trainerStats.bestStreak || 0} best
              </dd>
            </div>
            <div>
              <dt>Next review</dt>
              <dd>{formatDue(trainerStats.nextDue)}</dd>
            </div>
          </dl>
        </section>

        <section className="selection-card detail-card">
          <span className="eyebrow">Pending Move</span>
          <strong>{selectedMove ? `${selectedMove.san} (${selectedMove.uci})` : "Choose a piece, then choose a square"}</strong>
          <p className="small-print">This trainer uses click-to-move: source square first, target square second.</p>
          <div className="button-stack pending-actions">
            <button type="button" onClick={onSubmitMove} disabled={!selectedMove || Boolean(submittedMove)}>
              Check move
            </button>
            <button type="button" className="ghost-button" onClick={onReveal}>
              Show answer
            </button>
          </div>
          {selectedMove ? (
            <button type="button" className="link-button" onClick={submittedMove ? onReset : onClearSelection}>
              {submittedMove ? "Reset" : "Clear selection"}
            </button>
          ) : null}
        </section>

        {submittedMove ? (
          <section className="detail-card feedback-card">
            <span className="eyebrow">Move Result</span>
            <h4>{submittedMove.grade}</h4>
            <dl>
              <div>
                <dt>Your move</dt>
                <dd>{submittedMove.san || submittedMove.uci}</dd>
              </div>
              <div>
                <dt>Resulting eval</dt>
                <dd>{submittedMove.eval_display}</dd>
              </div>
              <div>
                <dt>Eval loss</dt>
                <dd>{submittedMove.eval_loss_display}</dd>
              </div>
              <div>
                <dt>Engine line</dt>
                <dd>{submittedMove.pv_san || "Unavailable"}</dd>
              </div>
            </dl>
            <LinePlaybackControls
              label={activeLineType === "best" ? "Best engine line" : "Your move line"}
              positions={playbackPositions}
              playbackPly={playbackPly}
              canShowBest={canShowBestLine}
              activeLineType={activeLineType}
              onSetPlaybackLine={onSetPlaybackLine}
              onSetPlaybackPly={onSetPlaybackPly}
            />
            {currentBoardLichessUrl ? (
              <div className="lichess-link-stack">
                <div className="lichess-link-group">
                  <a
                    href={currentBoardLichessUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="analysis-link"
                  >
                    Open position in Lichess
                  </a>
                  {lichessOpeningUrl ? (
                    <a href={lichessOpeningUrl} target="_blank" rel="noreferrer" className="analysis-link">
                      Explore {puzzle.opening} on Lichess
                    </a>
                  ) : null}
                </div>
                {lichessOpeningTrainingUrl || lichessThemeLinks.length || lichessPracticeLinks.length ? (
                  <div className="lichess-link-group thematic-link-group">
                    {lichessOpeningTrainingUrl ? (
                      <a href={lichessOpeningTrainingUrl} target="_blank" rel="noreferrer" className="analysis-link">
                        Open {puzzle.opening} puzzles on Lichess
                      </a>
                    ) : null}
                    {lichessThemeLinks.map((link) => (
                      <a key={link.label} href={link.url} target="_blank" rel="noreferrer" className="analysis-link">
                        Open {link.label.toLowerCase()} puzzles on Lichess
                      </a>
                    ))}
                    {lichessPracticeLinks.map((link) => (
                      <a key={`${link.label}-practice`} href={link.url} target="_blank" rel="noreferrer" className="analysis-link">
                        Study {link.label.toLowerCase()} in Lichess Practice
                      </a>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}
          </section>
        ) : null}

        {puzzleState.revealed ? (
          <section className="detail-card reveal-card">
            <span className="eyebrow">Answer</span>
            <h4>{bestMove}</h4>
            <dl>
              <div>
                <dt>Best move</dt>
                <dd>{bestMove}</dd>
              </div>
              <div>
                <dt>Played in game</dt>
                <dd>{playedMove}</dd>
              </div>
              <div>
                <dt>Engine line</dt>
                <dd>{puzzle.best_pv || "No principal variation recorded."}</dd>
              </div>
            </dl>
            <LinePlaybackControls
              label={activeLineType === "submitted" ? "Your move line" : "Best engine line"}
              positions={playbackPositions}
              playbackPly={playbackPly}
              canShowBest={canShowBestLine}
              activeLineType={activeLineType}
              onSetPlaybackLine={onSetPlaybackLine}
              onSetPlaybackPly={onSetPlaybackPly}
            />
            <p>{puzzle.explanation || "No explanation available."}</p>
          </section>
        ) : null}
      </aside>
    </section>
  );
}
