import test from "node:test";
import assert from "node:assert/strict";

import mine from "../api/mine.js";
import status from "../api/status.js";
import latest from "../api/latest.js";
import openapi from "../api/openapi.js";

class MockResponse {
  headers = {};
  statusCode = 200;
  body = "";
  setHeader(name, value) { this.headers[name] = value; }
  end(value = "") { this.body = value; }
  payload() { return JSON.parse(this.body); }
}

function request(method, body, { authorized = true, query = {}, ip = "127.0.0.1" } = {}) {
  return {
    method,
    body,
    query,
    headers: authorized ? { authorization: "Bearer trigger-test" } : {},
    socket: { remoteAddress: ip },
  };
}

const job = {
  seed: "MeuFluxo",
  depth: "quick",
  country: "BR",
  sources: ["meta"],
  keywords: ["MeuFluxo"],
  preflight: false,
};

test.beforeEach(() => {
  process.env.MINERACAO_TRIGGER_KEY = "trigger-test";
  process.env.GITHUB_WORKFLOW_TOKEN = "github-test";
});

test.afterEach(() => {
  delete process.env.MINERACAO_TRIGGER_KEY;
  delete process.env.GITHUB_WORKFLOW_TOKEN;
  delete globalThis.fetch;
});

test("POST /api/mine exige bearer token", async () => {
  const res = new MockResponse();
  await mine(request("POST", job, { authorized: false, ip: "10.0.0.1" }), res);
  assert.equal(res.statusCode, 401);
  assert.equal(res.payload().error, "unauthorized");
});

test("POST /api/mine despacha workflow_dispatch com job_json", async () => {
  let captured;
  globalThis.fetch = async (url, options) => {
    captured = { url, options };
    return new Response(null, { status: 204 });
  };
  const res = new MockResponse();
  await mine(request("POST", job, { ip: "10.0.0.2" }), res);
  assert.equal(res.statusCode, 202);
  assert.equal(res.payload().status, "dispatched");
  assert.match(captured.url, /actions\/workflows\/mine\.yml\/dispatches$/);
  const dispatch = JSON.parse(captured.options.body);
  assert.equal(dispatch.ref, "main");
  assert.deepEqual(JSON.parse(dispatch.inputs.job_json), job);
  assert.equal(captured.options.headers.Authorization, "Bearer github-test");
});

test("GET /api/status retorna a execução mais recente", async () => {
  globalThis.fetch = async () => new Response(JSON.stringify({ workflow_runs: [{
    id: 42, status: "completed", conclusion: "success", html_url: "https://github.test/run/42",
    created_at: "2026-01-01", run_started_at: "2026-01-01", updated_at: "2026-01-01", head_sha: "abc",
  }] }), { status: 200, headers: { "Content-Type": "application/json" } });
  const res = new MockResponse();
  await status(request("GET", undefined, { ip: "10.0.0.3" }), res);
  assert.equal(res.statusCode, 200);
  assert.equal(res.payload().run.id, 42);
  assert.equal(res.payload().run.conclusion, "success");
});

test("GET /api/latest agrega summary, score e REPORT opcional", async () => {
  globalThis.fetch = async (url) => {
    const value = url.includes("summary.json") ? { job_id: "abc" }
      : url.includes("score.json") ? { score: 72 }
        : "# REPORT";
    const content = Buffer.from(typeof value === "string" ? value : JSON.stringify(value)).toString("base64");
    return new Response(JSON.stringify({ type: "file", content }), { status: 200, headers: { "Content-Type": "application/json" } });
  };
  const res = new MockResponse();
  await latest(request("GET", undefined, { query: { include_report: "true" }, ip: "10.0.0.4" }), res);
  assert.equal(res.statusCode, 200);
  assert.equal(res.payload().summary.job_id, "abc");
  assert.equal(res.payload().score.score, 72);
  assert.equal(res.payload().report, "# REPORT");
});

test("GET /api/openapi publica contrato sem segredos", () => {
  const req = request("GET", undefined, { authorized: false, ip: "10.0.0.5" });
  req.headers.host = "bridge.example";
  const res = new MockResponse();
  openapi(req, res);
  assert.equal(res.statusCode, 200);
  assert.equal(res.payload().servers[0].url, "https://bridge.example");
  assert.ok(res.payload().paths["/api/mine"]);
  assert.doesNotMatch(res.body, /github-test|trigger-test/);
});
