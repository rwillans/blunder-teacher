export const SRS_INTERVAL_DAYS = [0, 1, 3, 7, 14, 30, 60];

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

export function nextTrainerStat(existingStat, outcome, selectedMoveUci = "", now) {
  const existing = normalizeTrainerStat(existingStat);
  const currentTime = asDate(now);
  const nowIso = currentTime.toISOString();

  if (outcome === "solved") {
    const wasDue = isDueStat(existing, currentTime);
    const masteryLevel = wasDue ? Math.min(6, existing.masteryLevel + 1) : existing.masteryLevel;
    const currentStreak = existing.currentStreak + 1;
    const intervalDays = SRS_INTERVAL_DAYS[masteryLevel] || 60;
    const solved = existing.solved + 1;
    const attempted = existing.attempted + 1;
    return {
      ...existing,
      attempted,
      solved,
      firstSelectedMove: existing.firstSelectedMove || selectedMoveUci,
      lastPracticed: nowIso,
      lastResult: "solved",
      nextDue: wasDue ? dueDateFromNow(intervalDays, currentTime) : existing.nextDue,
      masteryLevel,
      currentStreak,
      bestStreak: Math.max(existing.bestStreak, currentStreak),
      score: solved * 10 + masteryLevel * 5 + currentStreak * 2 - existing.failed * 5 - existing.revealed * 3,
    };
  }

  if (outcome === "failed") {
    const failed = existing.failed + 1;
    const attempted = existing.attempted + 1;
    return {
      ...existing,
      attempted,
      failed,
      firstSelectedMove: existing.firstSelectedMove || selectedMoveUci,
      lastPracticed: nowIso,
      lastResult: "again",
      nextDue: nowIso,
      masteryLevel: 0,
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
      nextDue: nowIso,
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
  if (reviewMode === "mastered") {
    return stats.masteryLevel >= 3;
  }
  return true;
}
