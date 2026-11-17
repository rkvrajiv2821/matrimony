import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

type Tree = { [k: string]: string | Tree };

const load = (name: string): Tree =>
  JSON.parse(readFileSync(new URL(`../messages/${name}.json`, import.meta.url), "utf8"));

function flatten(tree: Tree, prefix = ""): Map<string, string> {
  const out = new Map<string, string>();
  for (const [k, v] of Object.entries(tree)) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (typeof v === "string") out.set(key, v);
    else for (const [ck, cv] of flatten(v, key)) out.set(ck, cv);
  }
  return out;
}

const placeholders = (s: string) => [...s.matchAll(/\{(\w+)\}|<(\w+)>/g)].map((m) => m[1] ?? m[2]).sort();

const en = flatten(load("en"));

for (const locale of ["ta", "ta-Latn"]) {
  const other = flatten(load(locale));

  test(`${locale} has exactly the same keys as en`, () => {
    assert.deepEqual([...other.keys()].sort(), [...en.keys()].sort());
  });

  test(`${locale} keeps every placeholder and rich-text tag`, () => {
    for (const [key, value] of en) {
      assert.deepEqual(placeholders(other.get(key) ?? ""), placeholders(value), key);
    }
  });

  test(`${locale} has no empty strings`, () => {
    for (const [key, value] of other) assert.ok(value.trim().length > 0, key);
  });
}

test("Tamil catalogue is actually written in Tamil script", () => {
  const ta = flatten(load("ta"));
  const tamil = [...ta.values()].filter((v) => /[஀-௿]/.test(v)).length;
  assert.ok(tamil / ta.size > 0.8, `only ${tamil}/${ta.size} strings contain Tamil script`);
});
