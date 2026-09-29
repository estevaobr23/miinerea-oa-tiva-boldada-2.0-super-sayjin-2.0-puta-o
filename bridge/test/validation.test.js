import test from "node:test";
import assert from "node:assert/strict";

import { parseAndValidateJob, ValidationError } from "../lib/validation.js";

const minimal = {
  seed: "MeuFluxo",
  depth: "quick",
  country: "br",
  sources: ["meta"],
  keywords: ["MeuFluxo"],
  preflight: false,
};

test("normaliza e valida o job mínimo", () => {
  assert.deepEqual(parseAndValidateJob(minimal), { ...minimal, country: "BR" });
});

test("rejeita source, depth e campos desconhecidos", () => {
  assert.throws(() => parseAndValidateJob({ ...minimal, sources: ["youtube"] }), ValidationError);
  assert.throws(() => parseAndValidateJob({ ...minimal, depth: "huge" }), ValidationError);
  assert.throws(() => parseAndValidateJob({ ...minimal, token: "não permitido" }), /Campos não permitidos/);
});

test("aplica teto de keywords por profundidade", () => {
  const keywords = Array.from({ length: 6 }, (_, index) => `keyword ${index}`);
  assert.throws(() => parseAndValidateJob({ ...minimal, keywords }), /no máximo 5/);
});

test("rejeita payload acima de 16 KiB", () => {
  assert.throws(() => parseAndValidateJob({ ...minimal, seed: "a".repeat(17_000) }), /16 KiB/);
});
