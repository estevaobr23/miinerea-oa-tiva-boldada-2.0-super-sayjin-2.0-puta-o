import { DEPTH_LIMITS, MAX_PAYLOAD_BYTES, SOURCES } from "./constants.js";

export class ValidationError extends Error {
  constructor(message, status = 400) {
    super(message);
    this.status = status;
    this.code = "invalid_job";
    this.publicMessage = message;
  }
}

function cleanText(value, name, { min = 1, max = 300 } = {}) {
  if (typeof value !== "string") throw new ValidationError(`${name} deve ser texto.`);
  const cleaned = value.trim().replace(/\s+/g, " ");
  if (cleaned.length < min || cleaned.length > max) {
    throw new ValidationError(`${name} deve conter entre ${min} e ${max} caracteres.`);
  }
  return cleaned;
}

export function parseAndValidateJob(body) {
  if (typeof body === "string") {
    try {
      body = JSON.parse(body);
    } catch {
      throw new ValidationError("JSON inválido.");
    }
  }
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    throw new ValidationError("O payload deve ser um objeto JSON.");
  }
  if (Buffer.byteLength(JSON.stringify(body), "utf8") > MAX_PAYLOAD_BYTES) {
    throw new ValidationError("Payload excede 16 KiB.", 413);
  }
  const allowed = new Set(["seed", "depth", "country", "sources", "keywords", "preflight"]);
  const unknown = Object.keys(body).filter((key) => !allowed.has(key));
  if (unknown.length) throw new ValidationError(`Campos não permitidos: ${unknown.join(", ")}.`);

  const seed = cleanText(body.seed, "seed", { min: 2 });
  const depth = body.depth ?? "quick";
  if (!Object.hasOwn(DEPTH_LIMITS, depth)) throw new ValidationError("depth deve ser quick, medium ou deep.");
  const country = cleanText(body.country ?? "BR", "country", { min: 2, max: 3 }).toUpperCase();
  if (!/^[A-Z]{2,3}$/.test(country)) throw new ValidationError("country deve usar código alfabético de 2 ou 3 letras.");

  if (!Array.isArray(body.sources) || body.sources.length < 1 || body.sources.length > 3) {
    throw new ValidationError("sources deve conter entre 1 e 3 fontes.");
  }
  const sources = [...new Set(body.sources)];
  if (sources.length !== body.sources.length || sources.some((source) => !SOURCES.has(source))) {
    throw new ValidationError("sources aceita apenas meta, tiktok e google, sem duplicatas.");
  }

  if (!Array.isArray(body.keywords) || body.keywords.length < 1) {
    throw new ValidationError("keywords deve conter pelo menos uma keyword.");
  }
  if (body.keywords.length > DEPTH_LIMITS[depth]) {
    throw new ValidationError(`depth ${depth} aceita no máximo ${DEPTH_LIMITS[depth]} keywords.`);
  }
  const keywords = body.keywords.map((value, index) => cleanText(value, `keywords[${index}]`));
  if (new Set(keywords).size !== keywords.length) throw new ValidationError("keywords não pode conter duplicatas.");
  if (body.preflight !== undefined && typeof body.preflight !== "boolean") {
    throw new ValidationError("preflight deve ser booleano.");
  }
  return { seed, depth, country, sources, keywords, preflight: body.preflight ?? false };
}
