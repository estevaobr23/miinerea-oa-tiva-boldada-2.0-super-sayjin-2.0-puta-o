import { BRANCH, OWNER, REPOSITORY, WORKFLOW } from "./constants.js";

const API = `https://api.github.com/repos/${OWNER}/${REPOSITORY}`;

export class GitHubError extends Error {
  constructor(status, code, publicMessage) {
    super(publicMessage);
    this.status = status;
    this.code = code;
    this.publicMessage = publicMessage;
  }
}

async function github(path, options = {}) {
  const token = process.env.GITHUB_WORKFLOW_TOKEN;
  if (!token) throw new GitHubError(503, "bridge_not_configured", "GITHUB_WORKFLOW_TOKEN não configurado.");
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${token}`,
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "mineracao-info-bridge",
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    if (response.status === 404) throw new GitHubError(404, "not_found", "Recurso ainda não disponível no repositório.");
    if (response.status === 401 || response.status === 403) {
      throw new GitHubError(502, "github_authorization_failed", "Token GitHub ausente, inválido ou sem permissão suficiente.");
    }
    throw new GitHubError(502, "github_api_error", `GitHub respondeu com status ${response.status}.`);
  }
  return response;
}

export async function dispatchMining(job) {
  await github(`/actions/workflows/${WORKFLOW}/dispatches`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ref: BRANCH, inputs: { job_json: JSON.stringify(job) } }),
  });
}

export async function latestWorkflowRun() {
  const params = new URLSearchParams({ branch: BRANCH, event: "workflow_dispatch", per_page: "1" });
  const response = await github(`/actions/workflows/${WORKFLOW}/runs?${params}`);
  const payload = await response.json();
  const run = payload.workflow_runs?.[0];
  if (!run) return null;
  return {
    id: run.id,
    status: run.status,
    conclusion: run.conclusion,
    html_url: run.html_url,
    created_at: run.created_at,
    run_started_at: run.run_started_at,
    updated_at: run.updated_at,
    head_sha: run.head_sha,
  };
}

export async function repositoryJson(path) {
  const response = await github(`/contents/${path}?ref=${BRANCH}`);
  const payload = await response.json();
  if (payload.type !== "file" || !payload.content) throw new GitHubError(502, "invalid_repository_file", "Arquivo inválido no repositório.");
  try {
    return JSON.parse(Buffer.from(payload.content, "base64").toString("utf8"));
  } catch {
    throw new GitHubError(502, "invalid_repository_json", "JSON inválido em results/latest.");
  }
}

export async function repositoryText(path) {
  const response = await github(`/contents/${path}?ref=${BRANCH}`);
  const payload = await response.json();
  if (payload.type !== "file" || !payload.content) throw new GitHubError(502, "invalid_repository_file", "Arquivo inválido no repositório.");
  return Buffer.from(payload.content, "base64").toString("utf8");
}
