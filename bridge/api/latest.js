import { repositoryJson, repositoryText } from "../lib/github.js";
import { json, methodNotAllowed, safeError } from "../lib/http.js";
import { authenticate, rateLimit } from "../lib/security.js";

export default async function handler(req, res) {
  if (req.method !== "GET") return methodNotAllowed(res, "GET");
  if (!authenticate(req, res) || !rateLimit(req, res, { limit: 30, scope: "read" })) return;
  const includeReport = ["1", "true", "yes"].includes(String(req.query?.include_report || "").toLowerCase());
  try {
    const [summary, score, report] = await Promise.all([
      repositoryJson("results/latest/summary.json"),
      repositoryJson("results/latest/score.json"),
      includeReport ? repositoryText("results/latest/REPORT.md") : Promise.resolve(undefined),
    ]);
    return json(res, 200, { ok: true, summary, score, ...(includeReport ? { report } : {}) });
  } catch (error) {
    return safeError(res, error);
  }
}
