// Replays tests/golden/parity_cases.json (written by the Python suite) against the Worker
// service and requires identical status codes and JSON bodies.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createService } from "../src/service.js";

const root = new URL("../../", import.meta.url);
const bundle = JSON.parse(readFileSync(new URL("data/build/evidence_bundle.json", root)));
const cases = JSON.parse(readFileSync(new URL("tests/golden/parity_cases.json", root)));
const service = createService(bundle);

test(`golden cases loaded (${cases.length})`, () => {
  assert.ok(cases.length >= 75);
});

for (const c of cases) {
  test(`${c.method} ${c.url}`, () => {
    const u = new URL(c.url, "https://example.test");
    const path = decodeURIComponent(u.pathname);
    const [status, body] = service.handle(c.method, path, [...u.searchParams]);
    assert.equal(status, c.status);
    assert.deepStrictEqual(JSON.parse(JSON.stringify(body)), c.body);
  });
}
