import React from "react";

export const PIECE_FILE_BY_KEY = {
  wK: "/pieces/cburnett/wK.svg",
  wQ: "/pieces/cburnett/wQ.svg",
  wR: "/pieces/cburnett/wR.svg",
  wB: "/pieces/cburnett/wB.svg",
  wN: "/pieces/cburnett/wN.svg",
  wP: "/pieces/cburnett/wP.svg",
  bK: "/pieces/cburnett/bK.svg",
  bQ: "/pieces/cburnett/bQ.svg",
  bR: "/pieces/cburnett/bR.svg",
  bB: "/pieces/cburnett/bB.svg",
  bN: "/pieces/cburnett/bN.svg",
  bP: "/pieces/cburnett/bP.svg",
};

export const PIECE_LABEL_BY_KEY = {
  wK: "White king",
  wQ: "White queen",
  wR: "White rook",
  wB: "White bishop",
  wN: "White knight",
  wP: "White pawn",
  bK: "Black king",
  bQ: "Black queen",
  bR: "Black rook",
  bB: "Black bishop",
  bN: "Black knight",
  bP: "Black pawn",
};

export const PIECE_KEY_BY_FEN_CHAR = {
  K: "wK",
  Q: "wQ",
  R: "wR",
  B: "wB",
  N: "wN",
  P: "wP",
  k: "bK",
  q: "bQ",
  r: "bR",
  b: "bB",
  n: "bN",
  p: "bP",
};

function buildRenderer(pieceKey) {
  const src = PIECE_FILE_BY_KEY[pieceKey];
  const alt = PIECE_LABEL_BY_KEY[pieceKey];

  return function Renderer({ squareWidth, isDragging }) {
    const size = squareWidth || 60;
    return (
      <img
        src={src}
        alt={alt}
        draggable={false}
        style={{
          width: size,
          height: size,
          padding: size * 0.06,
          objectFit: "contain",
          opacity: isDragging ? 0.88 : 1,
          transform: isDragging ? "scale(1.03)" : "scale(1)",
          transition: "opacity 120ms ease, transform 120ms ease",
          filter: "drop-shadow(0 5px 6px rgba(38, 25, 14, 0.2))",
        }}
      />
    );
  };
}

export const bespokePieces = {
  wK: buildRenderer("wK"),
  wQ: buildRenderer("wQ"),
  wR: buildRenderer("wR"),
  wB: buildRenderer("wB"),
  wN: buildRenderer("wN"),
  wP: buildRenderer("wP"),
  bK: buildRenderer("bK"),
  bQ: buildRenderer("bQ"),
  bR: buildRenderer("bR"),
  bB: buildRenderer("bB"),
  bN: buildRenderer("bN"),
  bP: buildRenderer("bP"),
};
