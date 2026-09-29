# MINERAÇÃO INFO ENGINE — V0.1 LOCAL

Motor local para executar a Skill **Big Nichos / Low Ticket** contra fontes reais via Apify.

## O que já faz
- carrega e identifica a Skill vigente por SHA-256;
- minera Meta Ads, TikTok e Google via Actors configuráveis;
- salva dados brutos em SQLite local;
- normaliza texto, anunciante, URL e datas quando disponíveis;
- calcula score heurístico de oportunidade;
- mede volume, longevidade, diversidade de anunciantes e diversidade de criativos;
- sinaliza claims de saúde que exigem validação;
- gera `REPORT.md`, `normalized.json` e `score.json` por execução;
- possui CLI e API local HTTP (`127.0.0.1:8791`).

## Arquitetura

`Skill -> Ativador -> Pipeline -> Apify -> SQLite -> Normalizacao -> Score -> REPORT.md`

Actors iniciais:
- Meta: `solidcode/meta-ads-library-scraper`
- TikTok: `clockworks/tiktok-scraper`
- Google: `apify/google-search-scraper`

Todos podem ser trocados em `config/providers.yaml` sem alterar o motor.

## Instalação Windows
Abra PowerShell dentro da pasta e execute:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup_windows.ps1
```

O instalador pedirá o token Apify sem exibi-lo e criará `.env` apenas na sua máquina.

## Uso

```powershell
.\mineracao.ps1 skill-status
.\mineracao.ps1 mine "emagrecimento" --depth quick
.\mineracao.ps1 mine "pancreas emagrecimento" --depth medium --sources meta,tiktok,google
.\mineracao.ps1 mine "MeuFluxo" --depth deep --sources meta
```

### Profundidades
- `quick`: até 25 resultados por fonte (Google adapta páginas)
- `medium`: até 100
- `deep`: até 300

Observe: limites reais dependem do Actor e da fonte. Cada execução da Apify pode gerar custo.

## API local

```powershell
.\start_server.ps1
```

Endpoints:
- `GET http://127.0.0.1:8791/health`
- `GET http://127.0.0.1:8791/skill/status`
- `POST http://127.0.0.1:8791/mine`
- `GET http://127.0.0.1:8791/jobs/{job_id}`

Exemplo de POST:

```json
{
  "seed": "emagrecimento",
  "depth": "quick",
  "sources": ["meta", "tiktok", "google"],
  "country": "BR"
}
```

## O que o score significa
O score serve para **priorizar investigação**. Ele não prova ROAS, lucro ou faturamento do anunciante.

O motor usa cinco sinais alinhados à Skill:
- volume de ads;
- longevidade;
- anunciantes independentes;
- criativos distintos;
- presença em múltiplas fontes.

## Ativador por Skill
`AGENTS.md` contém o protocolo para um agente local (Codex/Claude/etc.) reconhecer pedidos de mineração, ler a Skill e chamar o motor.

A Skill original fica em `skills/SKILL_ATUALIZADA_BIG_NICHOS_LOW_TICKET.md`.
O arquivo `config/skill_runtime.yaml` contém as regras estruturadas usadas pelo algoritmo.

## Para integrar ESTE chat automaticamente
O motor local funciona em `127.0.0.1`, mas um chat web em nuvem não consegue acessar diretamente o localhost do seu PC. Para chamada automática a partir deste ChatGPT, a etapa seguinte é expor uma ponte autenticada (plugin/MCP/HTTPS) para os endpoints locais ou hospedar apenas o executor. Não é necessário para usar a V0.1 local.

## Segurança
- token não fica no código;
- `.env` é criado localmente;
- não faça commit do `.env`;
- não exponha a API local para internet sem autenticação.
