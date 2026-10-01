// Package only code and synthetic fixtures for a no-write, separate-process check.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
const candidate = resolve("artifacts/global-practice-20260929/candidate");
const names = ["app.core.config", "app.schemas.mock_interview", "app.services.mock_interview_rounds",
  "app.services.mock_interview_repository", "app.services.mock_interview_tts",
  "app.services.mock_interview_generation", "app.services.mock_interview_audio"];
const modules = Object.fromEntries(names.map(name => [name, readFileSync(resolve(candidate, "apps/backend", name.replaceAll(".", "/") + ".py"), "utf8")]));
const paths = ["ai/prompts/mock-interview/en/question.md", "ai/prompts/mock-interview/en/report.md",
  "ai/prompts/mock-interview/en/answer-structure.md", "ai/prompts/mock-interview/en/tts.txt", "ai/evals/global-mock-interview-v1.jsonl"];
const assets = Object.fromEntries(paths.map(path => [path, readFileSync(resolve(candidate, path), "utf8")]));
const runner = readFileSync("apps/backend/scripts/verify_mock_interview_providers.py", "utf8");
const payload = JSON.stringify({ modules, assets, runner });
process.stdout.write("import json\nBUNDLE = json.loads(" + JSON.stringify(payload) + ")\n");
process.stdout.write(readFileSync("apps/backend/scripts/verify_global_practice_in_memory.py", "utf8"));
