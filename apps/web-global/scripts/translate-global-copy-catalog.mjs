import fs from "node:fs";
import path from "node:path";
import ts from "typescript";

const projectRoot = path.resolve(import.meta.dirname, "..");
const workspaceRoot = path.resolve(projectRoot, "../..");
const sourceRoot = path.join(projectRoot, "src");
const catalogPath = path.join(projectRoot, "scripts/global-copy-catalog.json");

const parseEnv = (filePath) => Object.fromEntries(
  fs.readFileSync(filePath, "utf8").split(/\r?\n/).flatMap((line) => {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) return [];
    const index = trimmed.indexOf("=");
    return [[trimmed.slice(0, index), trimmed.slice(index + 1).replace(/^['"]|['"]$/g, "")]];
  }),
);

const env = { ...parseEnv(path.join(workspaceRoot, ".env")), ...process.env };
const apiKey = env.OFFERSTEADY_CHAT_QWEN_API_KEY;
const baseUrl = env.OFFERSTEADY_CHAT_QWEN_BASE_URL?.replace(/\/$/, "");
const model = env.OFFERSTEADY_CHAT_QWEN_MODEL;
if (!apiKey || !baseUrl || !model) throw new Error("Translation API configuration is incomplete.");

const normalize = (value) => value.trim().replace(/\s+/g, " ");
const sourceFiles = fs.readdirSync(sourceRoot)
  .filter((name) => /\.(ts|tsx)$/.test(name))
  .filter((name) => name !== "global-copy.generated.ts" && !name.includes(".test."));
const occurrences = new Map();
for (const name of sourceFiles) {
  const filePath = path.join(sourceRoot, name);
  const content = fs.readFileSync(filePath, "utf8");
  const sourceFile = ts.createSourceFile(filePath, content, ts.ScriptTarget.Latest, true, name.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  const visit = (node) => {
    if ((ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node) || ts.isJsxText(node)) && /[\u3400-\u9fff]/.test(node.text)) {
      const source = normalize(node.text);
      if (source) {
        const location = sourceFile.getLineAndCharacterOfPosition(node.getStart(sourceFile));
        const list = occurrences.get(source) ?? [];
        list.push(`${name}:${location.line + 1}`);
        occurrences.set(source, list);
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(sourceFile);
}

if (!fs.existsSync(catalogPath)) throw new Error("Global copy catalogue does not exist.");
const catalog = JSON.parse(fs.readFileSync(catalogPath, "utf8"));

const pending = [...occurrences.keys()].filter((source) => !catalog[source]);
const batches = Array.from({ length: Math.ceil(pending.length / 30) }, (_, index) => pending.slice(index * 30, index * 30 + 30));

for (let index = 0; index < batches.length; index += 1) {
  const items = batches[index].map((source) => ({ source, context: occurrences.get(source)?.slice(0, 4) }));
  const response = await fetch(`${baseUrl}/chat/completions`, {
    method: "POST",
    headers: { authorization: `Bearer ${apiKey}`, "content-type": "application/json" },
    body: JSON.stringify({
      model,
      temperature: 0,
      response_format: { type: "json_object" },
      messages: [
        {
          role: "system",
          content: "You localize a commercial AI interview product for US/UK/AU/CA users. Translate every Chinese source into concise, natural English appropriate for its UI/code context. Never use a generic fallback sentence. Preserve numbers, punctuation, format tokens, HTML fragments, identifiers, and technical meanings. Error messages must explain the actual error. Return only a JSON object whose key is the exact source and value is its English translation.",
        },
        { role: "user", content: JSON.stringify(items) },
      ],
    }),
  });
  if (!response.ok) throw new Error(`Translation request failed with HTTP ${response.status}.`);
  const payload = await response.json();
  const content = payload.choices?.[0]?.message?.content;
  if (typeof content !== "string") throw new Error("Translation response did not contain text.");
  const translated = JSON.parse(content.replace(/^```json\s*|\s*```$/g, ""));
  for (const source of batches[index]) {
    const value = translated[source];
    if (typeof value !== "string" || !value.trim() || /[\u3400-\u9fff]/.test(value)) {
      throw new Error(`Invalid translation returned for ${JSON.stringify(source)}.`);
    }
    catalog[source] = value.trim();
  }
  fs.writeFileSync(catalogPath, `${JSON.stringify(Object.fromEntries(Object.entries(catalog).sort(([a], [b]) => a.localeCompare(b, "zh-CN"))), null, 2)}\n`);
  console.log(`Translated batch ${index + 1}/${batches.length}.`);
}

console.log(`Global copy catalogue contains ${Object.keys(catalog).length} explicit entries.`);
