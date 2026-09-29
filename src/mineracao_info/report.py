from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .scoring import top_terms, classify_longevity


def health_flags(records: list[dict[str, Any]], flags: list[str]) -> list[tuple[str,int]]:
    joined = "\n".join((r.get("text") or "").lower() for r in records)
    found=[]
    for flag in flags:
        n=joined.count(flag.lower())
        if n:
            found.append((flag,n))
    return sorted(found, key=lambda x: x[1], reverse=True)


def build_report(run_id: str, seed: str, country: str, sources: list[str], records: list[dict[str, Any]], score: dict[str, Any], skill, provider_stats: dict[str, Any], outputs_dir: Path) -> Path:
    outputs_dir.mkdir(parents=True, exist_ok=True)
    run_dir = outputs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # JSON completo normalizado
    (run_dir / "normalized.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "score.json").write_text(json.dumps(score, ensure_ascii=False, indent=2), encoding="utf-8")

    adv = Counter((r.get("advertiser") or "[sem anunciante]") for r in records if r["source"] == "meta")
    longevity = Counter(classify_longevity(r.get("days_running")) for r in records if r["source"] == "meta")
    flags = health_flags(records, skill.rules.get("health_claim_flags", []))
    terms = top_terms(records, 25)

    lines=[]
    lines.append(f"# MINERAÇÃO INFO — RELATÓRIO DE EXECUÇÃO\n")
    lines.append(f"**Run:** `{run_id}`  ")
    lines.append(f"**Seed:** `{seed}`  ")
    lines.append(f"**País:** `{country}`  ")
    lines.append(f"**Fontes solicitadas:** {', '.join(sources)}  ")
    lines.append(f"**Skill runtime:** `{skill.version}`  ")
    lines.append(f"**Skill SHA-256:** `{skill.sha256}`\n")
    lines.append("> Regra: longevidade, volume e repetição são sinais de investigação. Não provam lucro.\n")

    lines.append("## Opportunity Score")
    lines.append(f"**{score['score']}/100**\n")
    lines.append("| Componente | Pontos |")
    lines.append("|---|---:|")
    for k,v in score["components"].items(): lines.append(f"| {k} | {v} |")
    lines.append("")
    lines.append(f"- Meta ads coletados: **{score['meta_ads']}**")
    lines.append(f"- Anunciantes independentes detectados: **{score['unique_advertisers']}**")
    lines.append(f"- Criativos/textos distintos: **{score['unique_creatives']}**")
    lines.append(f"- Maior longevidade detectada: **{score['max_days']} dias**")
    lines.append(f"- Mediana de longevidade: **{score['median_days']} dias**")
    lines.append(f"- Fontes com dados: **{score['source_presence']}**\n")

    lines.append("## Coleta por fonte")
    lines.append("| Fonte | Actor | Itens | Status |")
    lines.append("|---|---|---:|---|")
    for src, st in provider_stats.items():
        lines.append(f"| {src} | `{st.get('actor_id','')}` | {st.get('count',0)} | {st.get('status','')} |")
    lines.append("")

    lines.append("## Longevidade dos anúncios Meta")
    for label in ["teste","watchlist","investigar","forte","muito_forte","sem_data"]:
        if longevity[label]: lines.append(f"- **{label}:** {longevity[label]}")
    lines.append("")

    lines.append("## Top anunciantes encontrados")
    for name,count in adv.most_common(20): lines.append(f"- **{name}** — {count} registros")
    lines.append("")

    lines.append("## Termos recorrentes — candidatos a microdor/mecanismo")
    for term,count in terms: lines.append(f"- `{term}` — {count}")
    lines.append("")

    if flags:
        lines.append("## ⚠️ Claims de saúde que exigem validação")
        lines.append("Detectados automaticamente. Não reutilizar como fato apenas porque aparecem em anúncios.")
        for flag,count in flags: lines.append(f"- `{flag}` — {count} ocorrências")
        lines.append("")

    lines.append("## Próxima leitura segundo a Skill")
    lines.append("1. Separar **dor populacional** de **oferta comercial**.")
    lines.append("2. Identificar microdor, avatar, promessa, nova causa, mecanismo e entrega.")
    lines.append("3. Verificar se existem **anunciantes independentes**, não apenas duplicações do mesmo anunciante.")
    lines.append("4. Investigar anúncios com 21–45 dias; tratar 46–90 como sinal forte; 90+ como sinal muito forte.")
    lines.append("5. Modelar a **engenharia do mecanismo**, não copiar claims, criativos ou alegações sem validação.")

    path = run_dir / "REPORT.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
