// Answers requests with the jshttp content-disposition releases, for tests/test_oracles_node.py.
// The packages come from the npm tarballs listed in tests/upstream/MANIFEST.json, unpacked by
// the test. Usage: node jshttp_oracle.mjs <1.0.1 package folder> <3.0.0 package folder>
// Each stdin line is a JSON array [operation, ...arguments]; each stdout line is
// {"ok": result} or {"error": message}.
import { createRequire } from "node:module";
import { createInterface } from "node:readline";
import path from "node:path";
import { pathToFileURL } from "node:url";

const [, , oldFolder, newFolder] = process.argv;
const v1 = createRequire(import.meta.url)(path.resolve(oldFolder, "index.js"));
const v3 = await import(pathToFileURL(path.resolve(newFolder, "dist", "index.js")).href);

const plain = (result) => ({ type: result.type, parameters: { ...result.parameters } });
const operations = {
  parse1: (header) => plain(v1.parse(header)),
  parse3: (header) => plain(v3.parse(header)),
  parse3multipart: (header) => plain(v3.parse(header, { multipart: true })),
  format3multipart: (type, parameters) => v3.format({ type, parameters }, { multipart: true }),
};

const lines = createInterface({ input: process.stdin, crlfDelay: Infinity });
for await (const line of lines) {
  if (!line) continue;
  const [operation, ...args] = JSON.parse(line);
  let answer;
  try {
    answer = { ok: operations[operation](...args) };
  } catch (error) {
    answer = { error: String(error.message) };
  }
  process.stdout.write(JSON.stringify(answer) + "\n");
}
