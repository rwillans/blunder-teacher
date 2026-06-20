export const SRS_INTERVAL_DAYS = [0, 1, 3, 7, 21, 45, 90];
export const RELEARNING_SPACING_PRESENTATIONS = 10;

function asDate(now) {
  return now instanceof Date ? new Date(now) : new Date(now);
}

function todayStart(now) {
  const today = asDate(now);
  today.setHours(0, 0, 0, 0);
  return today;
}

function dueDateFromNow(days, now) {
  const dueDate = todayStart(now);
  dueDate.setDate(dueDate.getDate() + days);
  return dueDate.toISOString();
}

function legalMoveOptions(puzzle) {
  return Array.isArray(puzzle?.legal_move_options) ? puzzle.legal_move_options : [];
}

function findBestOption(puzzle) {
  const options = legalMoveOptions(puzzle);
  if (puzzle?.best_move_uci) {
    const bestByUci = options.find((option) => option.uci === puzzle.best_move_uci);
    if (bestByUci) {
      return bestByUci;
    }
  }
  return options.find((option) => Number(option.eval_loss_cp || 0) === 0) || options[0] || null;
}

function moverOutcomeBand(option) {
  const mate = Number(option?.mover_mate || 0);
  if (mate > 0) {
    return 1;
  }
  if (mate < 0) {
    return -1;
  }

  const evalCp = Number(option?.mover_eval_cp ?? option?.eval_cp ?? 0);
  if (evalCp >= 200) {
    return 1;
  }
  if (evalCp <= -200) {
    return -1;
  }
  return 0;
}

function lapseLevel(level) {
  if (level <= 2) {
    return 0;
  }
  if (level <= 4) {
    return Math.max(0, level - 2);
  }
  return Math.max(0, level - 3);
}

export function masteryStatusForLevel(level) {
  const normalizedLevel = Number(level || 0);
  if (normalizedLevel <= 2) {
    return "Learning";
  }
  if (normalizedLevel <= 4) {
    return "Familiar";
  }
  return "Established";
}

export function normalizeTrainerStat(stat = {}) {
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

export function normalizeTrainerStats(rawStats) {
  return Object.fromEntries(Object.entries(rawStats || {}).map(([puzzleId, stat]) => [puzzleId, normalizeTrainerStat(stat)]));
}

export function isDueStat(stat, now) {
  const normalized = normalizeTrainerStat(stat);
  if (!normalized.attempted && !normalized.revealed) {
    return true;
  }
  if (!normalized.nextDue) {
    return true;
  }
  const dueTime = new Date(normalized.nextDue).getTime();
  return Number.isNaN(dueTime) || dueTime <= asDate(now).getTime();
}

export function practiceGapForStats(stat) {
  const normalized = normalizeTrainerStat(stat);
  return normalized.failed + normalized.revealed - normalized.solved;
}

export function classifySubmittedMove(puzzle, move) {
  if (!move) {
    return "failed";
  }

  if (move.uci && move.uci === puzzle?.best_move_uci) {
    return "solved";
  }
  if (["Excellent", "Good"].includes(move.grade) || Number(move.eval_loss_cp || 0) <= 50) {
    return "solved";
  }

  const bestOption = findBestOption(puzzle);
  const bestBand = moverOutcomeBand(bestOption);
  const selectedBand = moverOutcomeBand(move);

  if (selectedBand < bestBand || selectedBand < 0) {
    return "failed";
  }

  return "acceptable";
}

export function nextTrainerStat(existingStat, outcome, selectedMoveUci = "", now, options = {}) {
  const existing = normalizeTrainerStat(existingStat);
  const currentTime = asDate(now);
  const nowIso = currentTime.toISOString();

  if (outcome === "solved") {
    const wasDue = isDueStat(existing, currentTime);
    const masteryLevel = options.relearning ? 1 : (wasDue ? Math.min(6, existing.masteryLevel + 1) : existing.masteryLevel);
    const currentStreak = existing.currentStreak + 1;
    const intervalDays = SRS_INTERVAL_DAYS[masteryLevel] || 90;
    const solved = existing.solved + 1;
    const attempted = existing.attempted + 1;
    return {
      ...existing,
      attempted,
      solved,
      firstSelectedMove: existing.firstSelectedMove || selectedMoveUci,
      lastPracticed: nowIso,
      lastResult: "solved",
      nextDue: wasDue || options.relearning ? dueDateFromNow(intervalDays, currentTime) : existing.nextDue,
      masteryLevel,
      currentStreak,
      bestStreak: Math.max(existing.bestStreak, currentStreak),
      score: solved * 10 + masteryLevel * 5 + currentStreak * 2 - existing.failed * 5 - existing.revealed * 3,
    };
  }

  if (outcome === "acceptable") {
    const intervalDays = Math.max(1, SRS_INTERVAL_DAYS[existing.masteryLevel] || 90);
    const attempted = existing.attempted + 1;
    return {
      ...existing,
      attempted,
      firstSelectedMove: existing.firstSelectedMove || selectedMoveUci,
      lastPracticed: nowIso,
      lastResult: "acceptable",
      nextDue: dueDateFromNow(intervalDays, currentTime),
      score: existing.score,
    };
  }

  if (outcome === "failed") {
    const failed = existing.failed + 1;
    const attempted = existing.attempted + 1;
    const masteryLevel = lapseLevel(existing.masteryLevel);
    return {
      ...existing,
      attempted,
      failed,
      firstSelectedMove: existing.firstSelectedMove || selectedMoveUci,
      lastPracticed: nowIso,
      lastResult: "again",
      nextDue: dueDateFromNow(0, currentTime),
      masteryLevel,
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
      nextDue: dueDateFromNow(0, currentTime),
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

export function puzzleMatchesReviewMode(puzzle, trainerStats, reviewMode, now) {
  const stats = normalizeTrainerStat(trainerStats[puzzle.id]);
  if (reviewMode === "due") {
    return isDueStat(stats, now);
  }
  if (reviewMode === "again") {
    return stats.lastResult === "again" || practiceGapForStats(stats) > 0;
  }
  if (reviewMode === "new") {
    return !stats.attempted && !stats.revealed;
  }
  if (reviewMode === "established" || reviewMode === "mastered") {
    return stats.masteryLevel >= 5;
  }
  return true;
}

export function queueRelearningCard(queue, puzzleId, currentPresentationCount, remainingPresentations) {
  if (!puzzleId) {
    return queue;
  }
  const spacing = Math.min(RELEARNING_SPACING_PRESENTATIONS, Math.max(0, Number(remainingPresentations || 0)));
  const entry = {
    puzzleId,
    readyAfter: Number(currentPresentationCount || 0) + spacing,
  };
  return [...queue.filter((item) => item.puzzleId !== puzzleId), entry];
}

export function removeRelearningCard(queue, puzzleId) {
  return queue.filter((item) => item.puzzleId !== puzzleId);
}

export function relearningEntryForPuzzle(queue, puzzleId) {
  return queue.find((item) => item.puzzleId === puzzleId) || null;
}

export function isRelearningCardReady(entry, presentationCount) {
  return Boolean(entry && Number(presentationCount || 0) >= Number(entry.readyAfter || 0));
}
