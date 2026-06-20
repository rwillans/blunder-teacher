import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const forbiddenKeys = new Set([
  "white",
  "black",
  "event",
  "site",
  "date",
  "result",
  "source_file",
  "game_index",
]);

const scanTargets = [
  "public/puzzles.json",
  "public/weaknesses.json",
  "dist",
];

const pathPatterns = [
  /(^|[^A-Za-z])([A-Za-z]:(?!\/\/)[\\/][^\s"'<>]+)/,
  /(^|[\s"'(])\/(?:Users|home|mnt|tmp|var|Volumes|private|workspace|positron_projects)(?:\/[^\s"'<>]+)+/g,
];

const textNeedles = [
  "outputs/",
  "outputs\\",
  ".pgn",
];

const privateFieldReferencePatterns = [...forbiddenKeys].map((key) => ({
  key,
  pattern: new RegExp(`(?:^|[{,])\\s*["']${key}["']\\s*:`),
}));

privateFieldReferencePatterns.push(...["source_file", "game_index"].map((key) => ({
  key,
  pattern: new RegExp(`\\.${key}\\b`),
})));

function walkJson(value, location, problems) {
  if (Array.isArray(value)) {
    value.forEach((item, index) => walkJson(item, `${location}[${index}]`, problems));
    return;
  }
  if (!value || typeof value !== "object") {
    return;
  }
  for (const [key, nested] of Object.entries(value)) {
    if (forbiddenKeys.has(key)) {
      problems.push(`${location}.${key}: forbidden private field name`);
    }
    walkJson(nested, `${location}.${key}`, problems);
  }
}

function collectFiles(target) {
  if (!existsSync(target)) {
    return [];
  }
  const stats = statSync(target);
  if (stats.isFile()) {
    return [target];
  }
  if (!stats.isDirectory()) {
    return [];
  }
  return readdirSync(target).flatMap((name) => collectFiles(join(target, name)));
}

const problems = [];

for (const jsonPath of ["public/puzzles.json", "public/weaknesses.json"]) {
  if (!existsSync(jsonPath)) {
    continue;
  }
  try {
    walkJson(JSON.parse(readFileSync(jsonPath, "utf8")), jsonPath, problems);
  } catch (error) {
    problems.push(`${jsonPath}: could not parse JSON (${error.message})`);
  }
}

const files = scanTargets.flatMap(collectFiles);
for (const file of files) {
  const text = readFileSync(file, "utf8");
  const displayPath = relative(process.cwd(), file);
  for (const pattern of pathPatterns) {
    const match = text.match(pattern);
    if (match) {
      problems.push(`${displayPath}: absolute path-like value found (${(match[2] || match[0]).trim()})`);
    }
  }
  for (const needle of textNeedles) {
    if (text.includes(needle)) {
      problems.push(`${displayPath}: private/debug token found (${needle})`);
    }
  }
  for (const { key, pattern } of privateFieldReferencePatterns) {
    if (pattern.test(text)) {
      problems.push(`${displayPath}: private field reference found (${key})`);
    }
  }
}

if (problems.length) {
  console.error("Public artifact privacy check failed:");
  for (const problem of problems) {
    console.error(`- ${problem}`);
  }
  process.exit(1);
}

console.log(`Public artifact privacy check passed (${files.length} files scanned).`);
