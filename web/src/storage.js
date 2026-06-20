import { normalizeTrainerStats } from "./srs";

export const TRAINER_STATS_KEY = "blunder-teacher:trainer-stats:v1";
export const TRAINER_SUMMARY_KEY = "blunder-teacher:trainer-summary:v1";

export function buildTrainerSummaryFromStats(stats = {}) {
  const summary = {
    attempted: 0,
    solved: 0,
    failed: 0,
    revealed: 0,
    currentStreak: 0,
    bestStreak: 0,
    totalScore: 0,
    lastPracticed: "",
    lastResult: "",
  };

  for (const stat of Object.values(normalizeTrainerStats(stats))) {
    summary.attempted += stat.attempted;
    summary.solved += stat.solved;
    summary.failed += stat.failed;
    summary.revealed += stat.revealed;
    summary.bestStreak = Math.max(summary.bestStreak, stat.bestStreak);
    summary.totalScore += stat.score;
    if (stat.lastPracticed && (!summary.lastPracticed || stat.lastPracticed > summary.lastPracticed)) {
      summary.lastPracticed = stat.lastPracticed;
      summary.lastResult = stat.lastResult;
    }
  }

  return summary;
}

export function normalizeTrainerSummary(summary = {}) {
  return {
    attempted: Number(summary.attempted || 0),
    solved: Number(summary.solved || 0),
    failed: Number(summary.failed || 0),
    revealed: Number(summary.revealed || 0),
    currentStreak: Number(summary.currentStreak || 0),
    bestStreak: Number(summary.bestStreak || 0),
    totalScore: Number(summary.totalScore ?? summary.score ?? 0),
    lastPracticed: summary.lastPracticed || "",
    lastResult: summary.lastResult || "",
  };
}

export function loadTrainerStats() {
  if (typeof window === "undefined") {
    return {};
  }
  try {
    const rawStats = window.localStorage.getItem(TRAINER_STATS_KEY);
    return rawStats ? normalizeTrainerStats(JSON.parse(rawStats)) : {};
  } catch {
    return {};
  }
}

export function loadTrainerSummary() {
  if (typeof window === "undefined") {
    return normalizeTrainerSummary();
  }
  try {
    const rawSummary = window.localStorage.getItem(TRAINER_SUMMARY_KEY);
    if (rawSummary) {
      return normalizeTrainerSummary(JSON.parse(rawSummary));
    }
    const rawStats = window.localStorage.getItem(TRAINER_STATS_KEY);
    return rawStats ? buildTrainerSummaryFromStats(JSON.parse(rawStats)) : normalizeTrainerSummary();
  } catch {
    return normalizeTrainerSummary();
  }
}

export function saveTrainerStats(trainerStats) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(TRAINER_STATS_KEY, JSON.stringify(trainerStats));
}

export function saveTrainerSummary(trainerSummary) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(TRAINER_SUMMARY_KEY, JSON.stringify(trainerSummary));
}
