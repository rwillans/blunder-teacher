import { describe, expect, it } from "vitest";

import {
  classifySubmittedMove,
  isDueStat,
  isRelearningCardReady,
  masteryStatusForLevel,
  nextTrainerStat,
  normalizeTrainerStat,
  puzzleMatchesReviewMode,
  queueRelearningCard,
  removeRelearningCard,
  relearningEntryForPuzzle,
} from "./srs";

const NOW = new Date("2026-06-20T15:30:00.000Z");
const TODAY_START = localStartIso(0);
const TOMORROW_START = localStartIso(1);

function localStartIso(daysFromNow) {
  const date = new Date(NOW);
  date.setHours(0, 0, 0, 0);
  date.setDate(date.getDate() + daysFromNow);
  return date.toISOString();
}

function puzzle(id = "puzzle-1") {
  return { id };
}

function option({
  uci,
  grade = "Mistake",
  evalLoss = 120,
  moverEval = 0,
  moverMate = null,
}) {
  return {
    uci,
    grade,
    eval_loss_cp: evalLoss,
    mover_eval_cp: moverEval,
    mover_mate: moverMate,
  };
}

function puzzleWithOptions(options, bestMoveUci = "best") {
  return {
    id: "puzzle-1",
    best_move_uci: bestMoveUci,
    legal_move_options: options,
  };
}

describe("SRS scheduling", () => {
  it("treats an unseen card as due", () => {
    expect(isDueStat(undefined, NOW)).toBe(true);
    expect(isDueStat({}, NOW)).toBe(true);
  });

  it("advances a new solved card to level 1 for tomorrow", () => {
    expect(nextTrainerStat({}, "solved", "e2e4", NOW)).toEqual({
      attempted: 1,
      solved: 1,
      failed: 0,
      revealed: 0,
      firstSelectedMove: "e2e4",
      lastPracticed: NOW.toISOString(),
      lastResult: "solved",
      nextDue: TOMORROW_START,
      masteryLevel: 1,
      currentStreak: 1,
      bestStreak: 1,
      score: 17,
    });
  });

  it("does not advance the level or due date for a correct early review", () => {
    const existing = normalizeTrainerStat({
      attempted: 1,
      solved: 1,
      nextDue: localStartIso(3),
      masteryLevel: 2,
      currentStreak: 1,
      bestStreak: 1,
      score: 22,
    });

    const next = nextTrainerStat(existing, "solved", "e2e4", NOW);

    expect(next.masteryLevel).toBe(2);
    expect(next.nextDue).toBe(existing.nextDue);
    expect(next.currentStreak).toBe(2);
    expect(next.bestStreak).toBe(2);
    expect(next.solved).toBe(2);
    expect(next.attempted).toBe(2);
  });

  it("advances only a correct due review and uses the revised intervals", () => {
    const next = nextTrainerStat(
      {
        attempted: 1,
        solved: 1,
        nextDue: TODAY_START,
        masteryLevel: 3,
        currentStreak: 1,
        bestStreak: 1,
      },
      "solved",
      "e2e4",
      NOW,
    );

    expect(next.masteryLevel).toBe(4);
    expect(next.nextDue).toBe(localStartIso(21));
    expect(next.currentStreak).toBe(2);
    expect(next.bestStreak).toBe(2);
  });

  it("uses the level 5 and 6 revised intervals", () => {
    expect(
      nextTrainerStat({ attempted: 1, solved: 1, nextDue: TODAY_START, masteryLevel: 4 }, "solved", "e2e4", NOW).nextDue,
    ).toBe(localStartIso(45));
    expect(
      nextTrainerStat({ attempted: 1, solved: 1, nextDue: TODAY_START, masteryLevel: 5 }, "solved", "e2e4", NOW).nextDue,
    ).toBe(localStartIso(90));
  });

  it("applies failure lapse rules at boundary levels 2, 3, 4, 5, and 6", () => {
    const cases = [
      [2, 0],
      [3, 1],
      [4, 2],
      [5, 2],
      [6, 3],
    ];

    for (const [level, expectedLevel] of cases) {
      const next = nextTrainerStat(
        {
          attempted: 2,
          solved: 2,
          failed: 1,
          revealed: 1,
          masteryLevel: level,
          currentStreak: 2,
          bestStreak: 4,
        },
        "failed",
        "e2e4",
        NOW,
      );

      expect(next.masteryLevel).toBe(expectedLevel);
      expect(next.currentStreak).toBe(0);
      expect(next.nextDue).toBe(TODAY_START);
      expect(next.lastResult).toBe("again");
    }
  });

  it("resets a reveal to level 0 and resets the current streak", () => {
    expect(
      nextTrainerStat(
        {
          attempted: 2,
          solved: 2,
          failed: 1,
          revealed: 1,
          masteryLevel: 6,
          currentStreak: 2,
          bestStreak: 4,
        },
        "revealed",
        "",
        NOW,
      ),
    ).toEqual({
      attempted: 2,
      solved: 2,
      failed: 1,
      revealed: 2,
      firstSelectedMove: "",
      lastPracticed: NOW.toISOString(),
      lastResult: "again",
      nextDue: TODAY_START,
      masteryLevel: 0,
      currentStreak: 0,
      bestStreak: 4,
      score: 9,
    });
  });

  it("schedules a successful relearning attempt for tomorrow at level 1", () => {
    const next = nextTrainerStat(
      {
        attempted: 2,
        solved: 1,
        failed: 1,
        nextDue: TODAY_START,
        masteryLevel: 3,
        currentStreak: 0,
      },
      "solved",
      "e2e4",
      NOW,
      { relearning: true },
    );

    expect(next.masteryLevel).toBe(1);
    expect(next.nextDue).toBe(TOMORROW_START);
    expect(next.currentStreak).toBe(1);
    expect(next.lastResult).toBe("solved");
  });

  it("schedules an acceptable move with the current level interval and does not advance", () => {
    const next = nextTrainerStat(
      {
        attempted: 1,
        solved: 1,
        nextDue: TODAY_START,
        masteryLevel: 4,
        currentStreak: 2,
        bestStreak: 2,
      },
      "acceptable",
      "e2e4",
      NOW,
    );

    expect(next.attempted).toBe(2);
    expect(next.solved).toBe(1);
    expect(next.failed).toBe(0);
    expect(next.masteryLevel).toBe(4);
    expect(next.currentStreak).toBe(2);
    expect(next.nextDue).toBe(localStartIso(21));
    expect(next.lastResult).toBe("acceptable");
  });

  it("handles invalid or missing due dates safely", () => {
    expect(isDueStat({ attempted: 1, nextDue: "" }, NOW)).toBe(true);
    expect(isDueStat({ attempted: 1, nextDue: "not-a-date" }, NOW)).toBe(true);
    expect(isDueStat({ attempted: 1, nextDue: TODAY_START }, NOW)).toBe(true);
    expect(isDueStat({ attempted: 1, nextDue: localStartIso(2) }, NOW)).toBe(false);
  });
});

describe("move outcome classification", () => {
  it("solves an alternative Excellent move", () => {
    const best = option({ uci: "a1a8", grade: "Excellent", evalLoss: 0, moverEval: 600 });
    const alternative = option({ uci: "b1b8", grade: "Excellent", evalLoss: 0, moverEval: 580 });

    expect(classifySubmittedMove(puzzleWithOptions([best, alternative], best.uci), alternative)).toBe("solved");
  });

  it("solves an alternative Good move", () => {
    const best = option({ uci: "a1a8", grade: "Excellent", evalLoss: 0, moverEval: 600 });
    const alternative = option({ uci: "b1b8", grade: "Good", evalLoss: 45, moverEval: 555 });

    expect(classifySubmittedMove(puzzleWithOptions([best, alternative], best.uci), alternative)).toBe("solved");
  });

  it("accepts an acceptable but non-promoting move", () => {
    const best = option({ uci: "a7a8q", grade: "Excellent", evalLoss: 0, moverEval: 900 });
    const nonPromotion = option({ uci: "h2h4", grade: "Inaccuracy", evalLoss: 110, moverEval: 650 });

    expect(classifySubmittedMove(puzzleWithOptions([best, nonPromotion], best.uci), nonPromotion)).toBe("acceptable");
  });

  it("accepts an inferior move that remains winning", () => {
    const best = option({ uci: "e1e7", grade: "Excellent", evalLoss: 0, moverEval: 790 });
    const inferiorWinning = option({ uci: "d6d3", grade: "Blunder", evalLoss: 300, moverEval: 350 });

    expect(classifySubmittedMove(puzzleWithOptions([best, inferiorWinning], best.uci), inferiorWinning)).toBe("acceptable");
  });

  it("fails a move that changes winning to equal", () => {
    const best = option({ uci: "e1e7", grade: "Excellent", evalLoss: 0, moverEval: 500 });
    const equalizer = option({ uci: "e1e2", grade: "Mistake", evalLoss: 260, moverEval: 0 });

    expect(classifySubmittedMove(puzzleWithOptions([best, equalizer], best.uci), equalizer)).toBe("failed");
  });

  it("fails a move that changes equal to losing", () => {
    const best = option({ uci: "g1f3", grade: "Excellent", evalLoss: 0, moverEval: 20 });
    const losing = option({ uci: "g1h3", grade: "Mistake", evalLoss: 230, moverEval: -350 });

    expect(classifySubmittedMove(puzzleWithOptions([best, losing], best.uci), losing)).toBe("failed");
  });

  it("fails a miss in a genuine only-move position", () => {
    const onlyMove = option({ uci: "g6g7", grade: "Excellent", evalLoss: 0, moverMate: 1, moverEval: 100000 });
    const mateMiss = option({ uci: "g6h6", grade: "Blunder", evalLoss: 100000, moverMate: -2, moverEval: -100000 });

    expect(classifySubmittedMove(puzzleWithOptions([onlyMove, mateMiss], onlyMove.uci), mateMiss)).toBe("failed");
  });
});

describe("review modes and status labels", () => {
  it("labels levels 0-2 as Learning, 3-4 as Familiar, and 5-6 as Established", () => {
    expect([0, 1, 2].map(masteryStatusForLevel)).toEqual(["Learning", "Learning", "Learning"]);
    expect([3, 4].map(masteryStatusForLevel)).toEqual(["Familiar", "Familiar"]);
    expect([5, 6].map(masteryStatusForLevel)).toEqual(["Established", "Established"]);
  });

  it("retains due, again, new, learning, familiar, and established review behavior", () => {
    const cards = {
      unseen: puzzle("unseen"),
      due: puzzle("due"),
      future: puzzle("future"),
      failed: puzzle("failed"),
      gap: puzzle("gap"),
      newRevealed: puzzle("newRevealed"),
      learning: puzzle("learning"),
      familiar: puzzle("familiar"),
      established: puzzle("established"),
    };
    const stats = {
      due: { attempted: 1, nextDue: TODAY_START },
      future: { attempted: 1, nextDue: localStartIso(2) },
      failed: { attempted: 1, failed: 1, lastResult: "again", nextDue: localStartIso(2) },
      gap: { attempted: 3, solved: 1, failed: 2, nextDue: localStartIso(2) },
      newRevealed: { revealed: 1 },
      learning: { attempted: 2, solved: 2, masteryLevel: 2, nextDue: localStartIso(2) },
      familiar: { attempted: 3, solved: 3, masteryLevel: 4, nextDue: localStartIso(2) },
      established: { attempted: 5, solved: 5, masteryLevel: 5, nextDue: localStartIso(2) },
    };

    expect(puzzleMatchesReviewMode(cards.unseen, stats, "due", NOW)).toBe(true);
    expect(puzzleMatchesReviewMode(cards.due, stats, "due", NOW)).toBe(true);
    expect(puzzleMatchesReviewMode(cards.future, stats, "due", NOW)).toBe(false);

    expect(puzzleMatchesReviewMode(cards.failed, stats, "again", NOW)).toBe(true);
    expect(puzzleMatchesReviewMode(cards.gap, stats, "again", NOW)).toBe(true);
    expect(puzzleMatchesReviewMode(cards.future, stats, "again", NOW)).toBe(false);

    expect(puzzleMatchesReviewMode(cards.unseen, stats, "new", NOW)).toBe(true);
    expect(puzzleMatchesReviewMode(cards.newRevealed, stats, "new", NOW)).toBe(false);
    expect(puzzleMatchesReviewMode(cards.due, stats, "new", NOW)).toBe(false);

    expect(puzzleMatchesReviewMode(cards.learning, stats, "learning", NOW)).toBe(true);
    expect(puzzleMatchesReviewMode(cards.familiar, stats, "learning", NOW)).toBe(false);
    expect(puzzleMatchesReviewMode(cards.familiar, stats, "familiar", NOW)).toBe(true);
    expect(puzzleMatchesReviewMode(cards.established, stats, "familiar", NOW)).toBe(false);

    expect(puzzleMatchesReviewMode(cards.familiar, stats, "established", NOW)).toBe(false);
    expect(puzzleMatchesReviewMode(cards.established, stats, "established", NOW)).toBe(true);
  });
});

describe("session relearning queue", () => {
  it("requeues a lapsed card after 10 other presentations when possible", () => {
    const queue = queueRelearningCard([], "puzzle-1", 4, 20);
    const entry = relearningEntryForPuzzle(queue, "puzzle-1");

    expect(entry).toEqual({ puzzleId: "puzzle-1", readyAfter: 14 });
    expect(isRelearningCardReady(entry, 13)).toBe(false);
    expect(isRelearningCardReady(entry, 14)).toBe(true);
  });

  it("places a lapsed card at the session end when fewer than 10 cards remain", () => {
    const queue = queueRelearningCard([], "puzzle-1", 4, 3);
    const entry = relearningEntryForPuzzle(queue, "puzzle-1");

    expect(entry).toEqual({ puzzleId: "puzzle-1", readyAfter: 7 });
  });

  it("removes a relearned card from the session queue", () => {
    const queue = queueRelearningCard([], "puzzle-1", 4, 20);

    expect(removeRelearningCard(queue, "puzzle-1")).toEqual([]);
  });
});
