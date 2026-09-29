from __future__ import annotations

import json
import typer
from rich.console import Console
from rich.table import Table

from .pipeline import mine
from .config import get_settings
from .skill import load_skill

app = typer.Typer(add_completion=False, help="MINERACAO INFO ENGINE - motor local orientado pela Skill.")
console = Console()

@app.command("skill-status")
def skill_status():
    s = get_settings(require_token=False)
    skill = load_skill(s.skill_path, s.runtime_path)
    console.print(f"[bold green]Skill ativa:[/] {skill.version}")
    console.print(f"Arquivo: {s.skill_path}")
    console.print(f"SHA-256: {skill.sha256}")

@app.command("mine")
def mine_cmd(
    seed: str = typer.Argument(..., help="Nicho, dor, keyword ou anunciante a minerar."),
    depth: str = typer.Option("quick", "--depth", "-d", help="quick | medium | deep"),
    sources: str = typer.Option("meta,tiktok,google", "--sources", "-s"),
    country: str = typer.Option("BR", "--country", "-c"),
):
    srcs=[x.strip() for x in sources.split(",") if x.strip()]
    console.print(f"[bold]Minerando:[/] {seed} | depth={depth} | sources={srcs}")
    result=mine(seed, depth=depth, sources=srcs, country=country)
    table=Table(title="MINERACAO INFO")
    table.add_column("Campo")
    table.add_column("Valor")
    table.add_row("Run", result["run_id"])
    table.add_row("Score", str(result["score"]["score"]))
    table.add_row("Report", result["report_path"])
    console.print(table)
    for src,st in result["providers"].items():
        if st.get("status") != "ok":
            console.print(f"[yellow]{src}: {st.get('status')} — {st.get('error','')}[/]")

@app.command("json")
def mine_json(seed: str, depth: str = "quick", sources: str = "meta,tiktok,google", country: str = "BR"):
    srcs=[x.strip() for x in sources.split(",") if x.strip()]
    typer.echo(json.dumps(mine(seed, depth, srcs, country), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    app()
