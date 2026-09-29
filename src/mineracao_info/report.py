from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import ClaimMatch, JobSpec, NormalizedResult


def _json_write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _safe(value: Any) -> str:
    return str(value if value not in (None, "") else "—").replace("|", "\\|").replace("\n", " ")


def _provider_rows(provider_stats: dict[str, Any]) -> list[str]:
    rows = []
    for key, stat in sorted(provider_stats.items()):
        rows.append(
            f"| {_safe(stat.get('source'))} | {_safe(stat.get('keyword'))} | {_safe(stat.get('actor_id'))} | "
            f"{_safe(stat.get('status'))} | {int(stat.get('items', 0))} | {int(stat.get('normalized', 0))} | {_safe(stat.get('error'))} |"
        )
    return rows


def build_intelligence_packet(
    *,
    job_id: str,
    status: str,
    spec: JobSpec,
    records: list[NormalizedResult],
    claims: list[ClaimMatch],
    score: dict[str, Any],
    metrics: dict[str, Any],
    provider_stats: dict[str, Any],
    skill: Any,
    outputs_dir: Path,
) -> tuple[Path, dict[str, Any]]:
    run_dir = outputs_dir / job_id
    run_dir.mkdir(parents=True, exist_ok=True)
    normalized_payload = [record.model_dump(mode="json") for record in records]
    claims_payload = [claim.model_dump(mode="json") for claim in claims]
    summary = {
        "job_id": job_id,
        "status": status,
        "seed": spec.seed,
        "depth": spec.depth,
        "country": spec.country,
        "keywords_executed": spec.keywords,
        "sources": spec.sources,
        "skill": {"version": skill.version, "sha256": skill.sha256},
        "counts": {
            "provider_items": sum(int(item.get("items", 0)) for item in provider_stats.values()),
            "raw_count": metrics["raw_count"],
            "deduplicated_count": metrics["deduplicated_count"],
            "claims": len(claims),
        },
        "provider_status": provider_stats,
        "metrics": metrics,
        "claims": claims_payload,
        "evidence_score": score,
        "strategic_assessment": None,
        "warning": "Evidencias de persistencia e recorrencia nao provam lucro. A avaliacao estrategica pertence ao ChatGPT/humano.",
    }
    _json_write(run_dir / "normalized.json", normalized_payload)
    _json_write(run_dir / "score.json", score)
    _json_write(run_dir / "summary.json", summary)

    lines: list[str] = [
        "# MINERAÇÃO INFO — INTELLIGENCE PACKET",
        "",
        f"**JOB:** `{job_id}`  ",
        f"**STATUS:** `{status}`  ",
        f"**SEED:** `{spec.seed}`  ",
        f"**DEPTH:** `{spec.depth}`  ",
        f"**PAÍS:** `{spec.country}`  ",
        f"**SKILL:** `{skill.version}` (`{skill.sha256}`)",
        "",
        "> Longevidade, volume, recorrência e diversidade são sinais de investigação. Não provam lucro, ROAS ou demanda garantida.",
        "",
        "## KEYWORDS EXECUTADAS",
    ]
    lines.extend(f"- `{keyword}`" for keyword in spec.keywords)
    lines.extend(["", "## FONTES", ", ".join(spec.sources), "", "## STATUS DOS PROVIDERS", "| Fonte | Keyword | Actor | Status | Itens | Normalizados | Erro |", "|---|---|---|---|---:|---:|---|"])
    lines.extend(_provider_rows(provider_stats))
    lines.extend([
        "",
        "## VOLUME",
        f"- Provider items: **{summary['counts']['provider_items']}**",
        f"- RAW COUNT (registros normalizados antes da deduplicação): **{metrics['raw_count']}**",
        f"- DEDUPLICATED COUNT: **{metrics['deduplicated_count']}**",
        "",
        "## EVIDENCE SCORE",
        f"**{score['score']}/100**",
        "",
        "Esse score prioriza evidências coletadas. O campo `strategic_assessment` permanece vazio para análise posterior do ChatGPT.",
        "",
        "| Componente | Pontos | Peso |",
        "|---|---:|---:|",
    ])
    for name, points in score.get("components", {}).items():
        lines.append(f"| {name} | {points} | {score.get('weights', {}).get(name, 0)} |")

    lines.extend(["", "## TOP ADVERTISERS"])
    for item in metrics.get("top_advertisers", []):
        lines.append(f"- **{item['name']}** — {item['count']} anúncio(s) deduplicado(s)")
    lines.append(f"- Anunciantes independentes: **{metrics.get('independent_advertisers', 0)}**")

    longevity = metrics.get("longevity", {})
    lines.extend([
        "",
        "## LONGEVIDADE",
        f"- Máximo: **{longevity.get('max_days', 0)} dias**",
        f"- Mediana: **{longevity.get('median_days', 0)} dias**",
    ])
    for label, count in longevity.get("buckets", {}).items():
        lines.append(f"- {label}: **{count}**")

    lines.extend(["", "## ANÚNCIOS MAIS LONGEVOS", "| Anunciante | Dias | Início | Fim | Ativo | URL |", "|---|---:|---|---|---|---|"])
    for item in metrics.get("longest_ads", []):
        lines.append(f"| {_safe(item['advertiser'])} | {item['days_running']} | {_safe(item['started_at'])} | {_safe(item['ended_at'])} | {_safe(item['is_active'])} | {_safe(item['landing_url'])} |")

    lines.extend([
        "",
        "## DIVERSIDADE",
        f"- Copies distintas: **{metrics.get('distinct_copies', 0)}**",
        f"- Criativos distintos: **{metrics.get('distinct_creatives', 0)}**",
        "",
        "## DATAS DE LANÇAMENTO",
    ])
    lines.extend(f"- `{value}`" for value in metrics.get("launch_dates", []))
    lines.extend(["", "## POSSÍVEIS RELAUNCHES"])
    if metrics.get("possible_relaunches"):
        for item in metrics["possible_relaunches"]:
            lines.append(f"- **{item['advertiser']}** — datas: {', '.join(item['distinct_start_dates'])}; chave: `{item['offer_key']}`")
    else:
        lines.append("- Nenhum possível relaunch detectado com os dados disponíveis.")

    lines.extend(["", "## DOMÍNIOS"])
    lines.extend(f"- `{item['domain']}` — {item['count']}" for item in metrics.get("domains", []))
    lines.extend(["", "## RELATED QUERIES"])
    lines.extend(f"- {value}" for value in metrics.get("related_queries", []))
    lines.extend(["", "## PEOPLE ALSO ASK"])
    lines.extend(f"- {value}" for value in metrics.get("people_also_ask", []))
    lines.extend(["", "## TERMOS RECORRENTES"])
    lines.extend(f"- `{item['term']}` — {item['count']}" for item in metrics.get("top_terms", []))
    lines.extend(["", "## MECANISMOS CANDIDATOS", "Heurísticas linguísticas para investigação; não são conclusões estratégicas."])
    lines.extend(f"- `{item['term']}` — {item['occurrences']} ocorrência(s)" for item in metrics.get("candidate_mechanisms", []))

    lines.extend(["", "## CLAIMS ENCONTRADOS"])
    if claims:
        lines.extend(["| Tipo | Termo | Severidade | Status | Contexto |", "|---|---|---|---|---|"])
        for claim in claims:
            lines.append(f"| {_safe(claim.claim_type)} | {_safe(claim.matched_term)} | {claim.severity} | {claim.status} | {_safe(claim.context)} |")
    else:
        lines.append("- Nenhum claim configurado foi detectado.")

    lines.extend(["", "## AMOSTRAS REPRESENTATIVAS", "| Fonte | Tipo | Keyword(s) | Anunciante/Título | Texto | URL |", "|---|---|---|---|---|---|"])
    for record in records[:20]:
        label = record.advertiser_name or record.title
        text = (record.text or record.description or "")[:260]
        lines.append(f"| {record.source} | {record.result_type} | {_safe(', '.join(record.matched_queries))} | {_safe(label)} | {_safe(text)} | {_safe(record.landing_url)} |")

    lines.extend([
        "",
        "## PRÓXIMA ANÁLISE PELO CHATGPT",
        "1. Separar escala da dor de compra da promessa.",
        "2. Identificar microdor, mecanismo, avatar e entrega.",
        "3. Comparar anunciantes independentes, criativos e datas escalonadas.",
        "4. Validar tecnicamente claims antes de reutilizá-los.",
        "5. Decidir se uma nova rodada de keywords é necessária.",
    ])
    report_path = run_dir / "REPORT.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path, summary


def build_report(*args: Any, **kwargs: Any) -> Path:
    """Compatibilidade nominal; use build_intelligence_packet no pipeline V1."""
    report_path, _ = build_intelligence_packet(*args, **kwargs)
    return report_path
