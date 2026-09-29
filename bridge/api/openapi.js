import { header, json, methodNotAllowed } from "../lib/http.js";

export default function handler(req, res) {
  if (req.method !== "GET") return methodNotAllowed(res, "GET");
  const host = header(req, "x-forwarded-host") || header(req, "host") || "localhost";
  const protocol = header(req, "x-forwarded-proto") || "https";
  return json(res, 200, {
    openapi: "3.1.0",
    info: { title: "Mineração Info Bridge", version: "1.0.0" },
    servers: [{ url: `${protocol}://${host}` }],
    components: {
      securitySchemes: {
        bearerAuth: { type: "http", scheme: "bearer" },
      },
      schemas: {
        MiningJob: {
          type: "object",
          additionalProperties: false,
          required: ["seed", "depth", "country", "sources", "keywords"],
          properties: {
            seed: { type: "string", minLength: 2, maxLength: 300 },
            depth: { type: "string", enum: ["quick", "medium", "deep"] },
            country: { type: "string", minLength: 2, maxLength: 3 },
            sources: { type: "array", minItems: 1, maxItems: 3, uniqueItems: true, items: { type: "string", enum: ["meta", "tiktok", "google"] } },
            keywords: { type: "array", minItems: 1, maxItems: 30, uniqueItems: true, items: { type: "string", minLength: 1, maxLength: 300 } },
            preflight: { type: "boolean", default: false },
          },
        },
      },
    },
    security: [{ bearerAuth: [] }],
    paths: {
      "/api/mine": {
        post: {
          operationId: "startMining",
          summary: "Dispara um job de mineração no GitHub Actions",
          requestBody: { required: true, content: { "application/json": { schema: { $ref: "#/components/schemas/MiningJob" } } } },
          responses: { "202": { description: "Workflow disparado" }, "400": { description: "Job inválido" }, "401": { description: "Não autorizado" } },
        },
      },
      "/api/status": {
        get: { operationId: "getMiningStatus", summary: "Consulta a execução mais recente", responses: { "200": { description: "Status mais recente" }, "401": { description: "Não autorizado" } } },
      },
      "/api/latest": {
        get: {
          operationId: "getLatestMiningResults",
          summary: "Lê o último Intelligence Packet compacto",
          parameters: [{ name: "include_report", in: "query", required: false, schema: { type: "boolean" } }],
          responses: { "200": { description: "Summary, score e REPORT opcional" }, "401": { description: "Não autorizado" }, "404": { description: "Nenhum resultado disponível" } },
        },
      },
    },
  });
}
