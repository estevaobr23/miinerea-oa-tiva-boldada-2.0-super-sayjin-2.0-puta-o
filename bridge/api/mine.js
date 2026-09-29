import { BRANCH, MAX_PAYLOAD_BYTES, OWNER, REPOSITORY, WORKFLOW } from "../lib/constants.js";
import { dispatchMining } from "../lib/github.js";
import { header, json, methodNotAllowed, safeError } from "../lib/http.js";
import { authenticate, rateLimit } from "../lib/security.js";
import { parseAndValidateJob } from "../lib/validation.js";

export default async function handler(req, res) {
  if (req.method !== "POST") return methodNotAllowed(res, "POST");
  if (!authenticate(req, res) || !rateLimit(req, res, { limit: 5, scope: "mine" })) return;
  const contentLength = Number(header(req, "content-length") || 0);
  if (contentLength > MAX_PAYLOAD_BYTES) return json(res, 413, { ok: false, error: "payload_too_large" });
  try {
    const job = parseAndValidateJob(req.body);
    await dispatchMining(job);
    return json(res, 202, {
      ok: true,
      status: "dispatched",
      repository: `${OWNER}/${REPOSITORY}`,
      workflow: WORKFLOW,
      ref: BRANCH,
      requested_at: new Date().toISOString(),
    });
  } catch (error) {
    return safeError(res, error);
  }
}
