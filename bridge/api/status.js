import { latestWorkflowRun } from "../lib/github.js";
import { json, methodNotAllowed, safeError } from "../lib/http.js";
import { authenticate, rateLimit } from "../lib/security.js";

export default async function handler(req, res) {
  if (req.method !== "GET") return methodNotAllowed(res, "GET");
  if (!authenticate(req, res) || !rateLimit(req, res, { limit: 30, scope: "read" })) return;
  try {
    const run = await latestWorkflowRun();
    return json(res, 200, { ok: true, run });
  } catch (error) {
    return safeError(res, error);
  }
}
