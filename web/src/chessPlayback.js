import { Chess } from "chess.js";

function uciToMove(uci) {
  if (!uci || uci.length < 4) {
    return null;
  }
  const move = {
    from: uci.slice(0, 2),
    to: uci.slice(2, 4),
  };
  if (uci.length > 4) {
    move.promotion = uci[4];
  }
  return move;
}

export function buildLinePositions(initialFen, pvUci) {
  if (!initialFen || !Array.isArray(pvUci) || !pvUci.length) {
    return [{ fen: initialFen, moveUci: "", san: "Start", ply: 0 }];
  }

  const positions = [{ fen: initialFen, moveUci: "", san: "Start", ply: 0 }];
  let game;
  try {
    game = new Chess(initialFen);
  } catch {
    return positions;
  }

  for (const uci of pvUci) {
    const moveRequest = uciToMove(uci);
    if (!moveRequest) {
      break;
    }

    try {
      const move = game.move(moveRequest);
      if (!move) {
        break;
      }
      positions.push({
        fen: game.fen(),
        moveUci: uci,
        san: move.san,
        ply: positions.length,
      });
    } catch {
      break;
    }
  }

  return positions;
}
