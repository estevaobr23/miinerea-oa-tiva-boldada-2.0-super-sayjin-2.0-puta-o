import { createHash, timingSafeEqual } from "node:crypto";
import { clientIp, header, json } from "./http.js";

const windows = new Map();

function digest(value) {
  return createHash("sha256").update(value).digest();
}

export function authenticate(req, res) {
  const expected = process.env.MINERACAO_TRIGGER_KEY;
  if (!expected) {
    json(res, 503, { ok: false, error: "bridge_not_configured" });
    return false;
  }
  const authorization = String(header(req, "authorization") || "");
  const provided = authorization.startsWith("Bearer ") ? authorization.slice(7).trim() : "";
  const valid = provided.length > 0 && timingSafeEqual(digest(provided), digest(expected));
  if (!valid) {
    json(res, 401, { ok: false, error: "unauthorized" });
    return false;
  }
  return true;
}

export function rateLimit(req, res, { limit = 10, windowMs = 60_000, scope = "default" } = {}) {
  const now = Date.now();
  const key = `${scope}:${digest(clientIp(req)).toString("hex")}`;
  const current = windows.get(key);
  if (!current || current.resetAt <= now) {
    windows.set(key, { count: 1, resetAt: now + windowMs });
    return true;
  }
  current.count += 1;
  if (current.count > limit) {
    res.setHeader("Retry-After", String(Math.max(1, Math.ceil((current.resetAt - now) / 1000))));
    json(res, 429, { ok: false, error: "rate_limited" });
    return false;
  }
  return true;
}
