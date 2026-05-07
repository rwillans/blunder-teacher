import React from "react";

import { PIECE_FILE_BY_KEY, PIECE_KEY_BY_FEN_CHAR, PIECE_LABEL_BY_KEY } from "./pieceSet";

const FILES = ["a", "b", "c", "d", "e", "f", "g", "h"];

function parseFenBoard(fen) {
  const boardMap = {};
  const rows = fen.split(" ")[0].split("/");

  rows.forEach((row, rowIndex) => {
    const rank = 8 - rowIndex;
    let fileIndex = 0;
    for (const token of row) {
      if (/\d/.test(token)) {
        fileIndex += Number(token);
      } else {
        boardMap[`${FILES[fileIndex]}${rank}`] = token;
        fileIndex += 1;
      }
    }
  });

  return boardMap;
}

function squareOrder(sideToMove) {
  const files = sideToMove === "Black" ? [...FILES].reverse() : FILES;
  const ranks = sideToMove === "Black" ? [1, 2, 3, 4, 5, 6, 7, 8] : [8, 7, 6, 5, 4, 3, 2, 1];
  const order = [];

  for (const rank of ranks) {
    for (const file of files) {
      order.push(`${file}${rank}`);
    }
  }

  return order;
}

function movesBySource(puzzle) {
  const grouped = {};
  const options = Array.isArray(puzzle.legal_move_options) ? puzzle.legal_move_options : [];
  for (const option of options) {
    const source = option.uci.slice(0, 2);
    grouped[source] = grouped[source] || [];
    grouped[source].push(option);
  }
  return grouped;
}

function findMoveBySquares(puzzle, sourceSquare, targetSquare) {
  const options = Array.isArray(puzzle.legal_move_options) ? puzzle.legal_move_options : [];
  const candidates = options.filter(
    (option) => option.uci.slice(0, 2) === sourceSquare && option.uci.slice(2, 4) === targetSquare,
  );

  if (!candidates.length) {
    return null;
  }

  return candidates.find((option) => option.uci.endsWith("q")) || candidates[0];
}

function buildPieceImage(piece) {
  const pieceKey = PIECE_KEY_BY_FEN_CHAR[piece];
  if (!pieceKey) {
    return null;
  }

  return (
    <img
      src={PIECE_FILE_BY_KEY[pieceKey]}
      alt={PIECE_LABEL_BY_KEY[pieceKey]}
      className="board-piece"
      draggable={false}
    />
  );
}

export function BoardShell({ puzzle, puzzleState, onMoveSelect }) {
  const options = Array.isArray(puzzle.legal_move_options) ? puzzle.legal_move_options : [];
  const lookup = Object.fromEntries(options.map((option) => [option.uci, option]));
  const submittedMove = puzzleState.submittedMoveUci ? lookup[puzzleState.submittedMoveUci] : null;
  const displayedFen = submittedMove ? submittedMove.resulting_fen : puzzle.fen;
  const boardMap = parseFenBoard(displayedFen);
  const groupedMoves = movesBySource(puzzle);
  const selectedSource = submittedMove ? "" : puzzleState.sourceSquare;
  const targetSquares = selectedSource ? (groupedMoves[selectedSource] || []).map((option) => option.uci.slice(2, 4)) : [];

  function handleSquareClick(square) {
    if (submittedMove) {
      return;
    }

    if (selectedSource) {
      const chosenMove = findMoveBySquares(puzzle, selectedSource, square);
      if (chosenMove) {
        onMoveSelect({
          moveUci: chosenMove.uci,
          sourceSquare: selectedSource,
        });
        return;
      }
    }

    const sourceMoves = groupedMoves[square] || [];
    if (!sourceMoves.length) {
      onMoveSelect({
        moveUci: "",
        sourceSquare: "",
      });
      return;
    }

    const preservedMove =
      puzzleState.selectedMoveUci && puzzleState.selectedMoveUci.startsWith(square) ? puzzleState.selectedMoveUci : "";

    onMoveSelect({
      moveUci: preservedMove,
      sourceSquare: square,
    });
  }

  return (
    <section className="board-card">
      <div className="board-frame">
        <div className="board-grid" role="grid" aria-label={`Chessboard for puzzle ${puzzle.id}`}>
          {squareOrder(puzzle.side_to_move).map((square) => {
            const fileIndex = FILES.indexOf(square[0]);
            const rank = Number(square[1]);
            const dark = (fileIndex + rank) % 2 === 0;
            const isSubmitted =
              submittedMove && (submittedMove.uci.startsWith(square) || submittedMove.uci.slice(2, 4) === square);

            const className = [
              "board-square",
              dark ? "dark-square" : "light-square",
              selectedSource === square ? "selected" : "",
              targetSquares.includes(square) ? "target" : "",
              isSubmitted ? "submitted" : "",
            ]
              .filter(Boolean)
              .join(" ");

            return (
              <button
                key={square}
                type="button"
                className={className}
                onClick={() => handleSquareClick(square)}
                aria-label={square}
              >
                {buildPieceImage(boardMap[square])}
              </button>
            );
          })}
        </div>
      </div>
      <p className="board-note">
        Select a piece, then select its destination square. The board flips automatically based on the side to move.
      </p>
    </section>
  );
}
