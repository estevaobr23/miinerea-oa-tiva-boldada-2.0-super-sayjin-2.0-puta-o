from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .config import get_settings
from .models import JobSpec
from .pipeline import run_job, run_job_file
from .skill import load_skill

app = typer.Typer(add_completion=False, help="MINERACAO INFO ENGINE - executor local orientado pela Skill.")
console = Console()


@app.command("skill-status")
def skill_status() -> None:
    settings = get_settings(require_token=False)
    skill = load_skill(settings.skill_path, settings.runtime_path)
    console.print(f"[bold green]Skill ativa:[/] {skill.version}")
    console.print(f"Arquivo: {settings.skill_path}")
    console.print(f"SHA-256: {skill.sha256}")


def _show_result(result: dict) -> None:
    table = Table(title="MINERACAO INFO")
    table.add_column("Campo")
    table.add_column("Valor")
    table.add_row("Job", result["job_id"])
    table.add_row("Status", result["status"])
    table.add_row("Raw", str(result["raw_count"]))
    table.add_row("Deduplicados", str(result["deduplicated_count"]))
    table.add_row("Evidence Score", str(result["score"]["score"]))
    table.add_row("Report", result["report_path"])
    console.print(table)


@app.command("mine")
def mine_cmd(
    seed: str = typer.Argument(..., help="Seed/nome do job. Quando não há --keyword, também é a query."),
    depth: str = typer.Option("quick", "--depth", "-d", help="quick | medium | deep"),
    sources: str = typer.Option("meta,tiktok,google", "--sources", "-s"),
    country: str = typer.Option("BR", "--country", "-c"),
    keyword: list[str] | None = typer.Option(None, "--keyword", "-k", help="Pode ser repetido para executar múltiplas keywords."),
    preflight: bool = typer.Option(False, "--preflight", help="Executa pré-contagem Meta antes da coleta."),
) -> None:
    source_list = [value.strip() for value in sources.split(",") if value.strip()]
    spec = JobSpec(seed=seed, depth=depth, sources=source_list, country=country, keywords=keyword or [], preflight=preflight)
    console.print(f"[bold]Executando job:[/] {spec.seed} | depth={spec.depth} | queries={len(spec.keywords)} | sources={spec.sources}")
    _show_result(run_job(spec))


@app.command("run-job")
def run_job_cmd(
    job_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    result_file: Path | None = typer.Option(None, "--result-file", help="Grava metadados finais em JSON (útil no GitHub Actions)."),
) -> None:
    result = run_job_file(job_path)
    if result_file:
        result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    _show_result(result)


@app.command("json")
def mine_json(seed: str, depth: str = "quick", sources: str = "meta,tiktok,google", country: str = "BR") -> None:
    source_list = [value.strip() for value in sources.split(",") if value.strip()]
    result = run_job(JobSpec(seed=seed, depth=depth, sources=source_list, country=country))
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    app()
