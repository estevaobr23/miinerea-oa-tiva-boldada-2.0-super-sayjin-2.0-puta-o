export function header(req, name) {
  const value = req.headers?.[name.toLowerCase()] ?? req.headers?.[name];
  return Array.isArray(value) ? value[0] : value;
}

export function json(res, status, payload) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(payload));
}

export function methodNotAllowed(res, allowed) {
  res.setHeader("Allow", allowed);
  return json(res, 405, { ok: false, error: "method_not_allowed" });
}

export function clientIp(req) {
  const forwarded = header(req, "x-forwarded-for");
  return String(forwarded || req.socket?.remoteAddress || "unknown").split(",")[0].trim();
}

export function safeError(res, error) {
  const status = Number.isInteger(error?.status) ? error.status : 502;
  const publicStatus = status >= 400 && status < 600 ? status : 502;
  return json(res, publicStatus, {
    ok: false,
    error: error?.code || "upstream_error",
    message: error?.publicMessage || "Falha ao comunicar com o GitHub.",
  });
}
