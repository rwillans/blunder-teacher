export const LICHESS_THEME_SLUGS = {
  "Advanced pawn": "advancedPawn",
  "Advantage": "advantage",
  "Attacking f2 or f7": "attackingF2F7",
  "Bishop endgame": "bishopEndgame",
  "Castling": "castling",
  "Checkmate": "mate",
  "Crushing": "crushing",
  "Defensive move": "defensiveMove",
  "Discovered attack": "discoveredAttack",
  "Discovered check": "discoveredCheck",
  "Double check": "doubleCheck",
  "Endgame": "endgame",
  "En passant rights": "enPassant",
  "Equality": "equality",
  "Exposed king": "exposedKing",
  "Fork": "fork",
  "Hanging piece": "hangingPiece",
  "Kingside attack": "kingsideAttack",
  "Knight endgame": "knightEndgame",
  "Mate in 1": "mateIn1",
  "Mate in 2": "mateIn2",
  "Mate in 3": "mateIn3",
  "Mate in 4": "mateIn4",
  "Mate in 5 or more": "mateIn5",
  "Middlegame": "middlegame",
  "Opening": "opening",
  "Pawn endgame": "pawnEndgame",
  "Pin": "pin",
  "Promotion": "promotion",
  "Queen and Rook": "queenRookEndgame",
  "Queen endgame": "queenEndgame",
  "Queenside attack": "queensideAttack",
  "Quiet move": "quietMove",
  "Rook endgame": "rookEndgame",
  "Sacrifice": "sacrifice",
  "Skewer": "skewer",
  "Underpromotion": "underPromotion",
};

const PRACTICE_THEMES = new Set([
  "Bishop endgame",
  "Defensive move",
  "Discovered attack",
  "Discovered check",
  "Double check",
  "Endgame",
  "Fork",
  "Knight endgame",
  "Pawn endgame",
  "Pin",
  "Queen endgame",
  "Rook endgame",
  "Skewer",
  "Underpromotion",
]);

export function buildLichessAnalysisUrl(fen, orientation) {
  if (!fen) {
    return "";
  }
  const color = orientation === "Black" ? "black" : "white";
  const encodedFen = encodeURIComponent(fen).replace(/%2F/g, "/");
  return `https://lichess.org/analysis/${encodedFen}?color=${color}`;
}

export function buildLichessThemeUrl(theme) {
  const slug = LICHESS_THEME_SLUGS[theme];
  return slug ? `https://lichess.org/training/${slug}` : "";
}

export function buildLichessPracticeUrl(theme) {
  return PRACTICE_THEMES.has(theme) ? "https://lichess.org/practice" : "";
}

export function buildLichessOpeningSlug(opening) {
  if (!opening || opening === "Unknown Opening" || opening === "Unknown opening") {
    return "";
  }
  return opening
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\bDefence\b/g, "Defense")
    .replace(/['’]/g, "")
    .replace(/[^A-Za-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

export function buildLichessOpeningTrainingUrl(opening) {
  const slug = buildLichessOpeningSlug(opening);
  return slug ? `https://lichess.org/training/${slug}` : "";
}

export function buildLichessOpeningUrl(opening) {
  const slug = buildLichessOpeningSlug(opening);
  return slug ? `https://lichess.org/opening/${slug}` : "";
}
