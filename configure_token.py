from pathlib import Path
from getpass import getpass

root=Path(__file__).resolve().parent
env=root/".env"
print("Configuracao local do token Apify.")
token=getpass("Cole seu APIFY_API_TOKEN (nao sera exibido): ").strip()
if not token:
    raise SystemExit("Token vazio. Nada alterado.")
content = (
    f"APIFY_API_TOKEN={token}\n"
    "MINERACAO_DB_PATH=data/mineracao_info.db\n"
    "MINERACAO_SKILL_PATH=skills/SKILL_ATUALIZADA_BIG_NICHOS_LOW_TICKET.md\n"
    "MINERACAO_RUNTIME_PATH=config/skill_runtime.yaml\n"
    "MINERACAO_ENGINE_PATH=config/engine.yaml\n"
    "MINERACAO_OUTPUTS_DIR=outputs\n"
)
env.write_text(content, encoding="utf-8")
print(f"OK: token salvo localmente em {env}")
