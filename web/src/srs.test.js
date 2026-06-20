import { describe, expect, it } from "vitest";

import {
  isDueStat,
  nextTrainerStat,
  normalizeTrainerStat,
  puzzleMatchesReviewMode,
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

describe("SRS scheduling", () => {
  it("treats an unseen card as due", () => {
    expect(isDueStat(undefined, NOW)).toBe(true);
    expect(isDueStat({}, NOW)).toBe(true);
  });

  it("advances a new solved card correctly", () => {
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

  it("does not advance the level for a correct early review", () => {
    const existing = normalizeTrainerStat({
      attempted: 1,
      solved: 1,
      nextDue: "2026-06-23T00:00:00.000Z",
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

  it("advances the level for a correct due review", () => {
    const next = nextTrainerStat(
      {
        attempted: 1,
        solved: 1,
        nextDue: TODAY_START,
        masteryLevel: 1,
        currentStreak: 1,
        bestStreak: 1,
      },
      "solved",
      "e2e4",
      NOW,
    );

    expect(next.masteryLevel).toBe(2);
    expect(next.nextDue).toBe(localStartIso(3));
    expect(next.currentStreak).toBe(2);
    expect(next.bestStreak).toBe(2);
  });

  it("resets a failed review according to current behavior", () => {
    expect(
      nextTrainerStat(
        {
          attempted: 2,
          solved: 2,
          failed: 1,
          revealed: 1,
          firstSelectedMove: "d2d4",
          masteryLevel: 3,
          currentStreak: 2,
          bestStreak: 4,
        },
        "failed",
        "e2e4",
        NOW,
      ),
    ).toEqual({
      attempted: 3,
      solved: 2,
      failed: 2,
      revealed: 1,
      firstSelectedMove: "d2d4",
      lastPracticed: NOW.toISOString(),
      lastResult: "again",
      nextDue: NOW.toISOString(),
      masteryLevel: 0,
      currentStreak: 0,
      bestStreak: 4,
      score: 7,
    });
  });

  it("resets a reveal according to current behavior", () => {
    expect(
      nextTrainerStat(
        {
          attempted: 2,
          solved: 2,
          failed: 1,
          revealed: 1,
          masteryLevel: 3,
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
      nextDue: NOW.toISOString(),
      masteryLevel: 0,
      currentStreak: 0,
      bestStreak: 4,
      score: 9,
    });
  });

  it("handles invalid or missing due dates safely", () => {
    expect(isDueStat({ attempted: 1, nextDue: "" }, NOW)).toBe(true);
    expect(isDueStat({ attempted: 1, nextDue: "not-a-date" }, NOW)).toBe(true);
    expect(isDueStat({ attempted: 1, nextDue: TODAY_START }, NOW)).toBe(true);
    expect(isDueStat({ attempted: 1, nextDue: "2026-06-22T00:00:00.000Z" }, NOW)).toBe(false);
  });
});

describe("review modes", () => {
  it("retains current due, again, new, and mastered behavior", () => {
    const cards = {
      unseen: puzzle("unseen"),
      due: puzzle("due"),
      future: puzzle("future"),
      failed: puzzle("failed"),
      gap: puzzle("gap"),
      newRevealed: puzzle("newRevealed"),
      mastered: puzzle("mastered"),
    };
    const stats = {
      due: { attempted: 1, nextDue: TODAY_START },
      future: { attempted: 1, nextDue: "2026-06-22T00:00:00.000Z" },
      failed: { attempted: 1, failed: 1, lastResult: "again", nextDue: "2026-06-22T00:00:00.000Z" },
      gap: { attempted: 3, solved: 1, failed: 2, nextDue: "2026-06-22T00:00:00.000Z" },
      newRevealed: { revealed: 1 },
      mastered: { attempted: 3, solved: 3, masteryLevel: 3, nextDue: "2026-06-22T00:00:00.000Z" },
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

    expect(puzzleMatchesReviewMode(cards.mastered, stats, "mastered", NOW)).toBe(true);
    expect(puzzleMatchesReviewMode(cards.future, stats, "mastered", NOW)).toBe(false);
  });
});
