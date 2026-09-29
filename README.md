# MINERAÇÃO INFO ENGINE

Executor de pesquisa de mercado orientado pela Skill **Big Nichos / Low Ticket**. O ChatGPT define seeds, keywords G6 e novas rodadas; o engine coleta evidências no Meta Ads, TikTok e Google, normaliza, deduplica, calcula métricas, persiste em SQLite e entrega um Intelligence Packet legível.

> Longevidade de anúncio é sinal de investigação, não prova automática de lucro. O Evidence Score prioriza evidências; a avaliação estratégica pertence ao ChatGPT.

## Arquitetura

```text
Job (seed + keywords)
        |
        +--> Meta Ads --+
        +--> TikTok ----+--> raw data --> normalização --> deduplicação
        +--> Google ----+                                  |
                                                            v
                              SQLite <-- métricas/claims/score
                                                            |
                                                            v
                       REPORT.md + summary.json + score.json + normalized.json
```

Os providers possuem uma interface comum e seus Actor IDs ficam somente em `config/providers.yaml`. Os limites e pesos ficam em `config/engine.yaml`.

## Instalação no Windows

Requer Python 3.11 ou superior.

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup_windows.ps1
```

O instalador cria `.venv`, instala as dependências e pede o token sem exibi-lo. O token é gravado apenas no `.env` local, que não é versionado.

Para configurar ou trocar o token manualmente:

```powershell
.\.venv\Scripts\python.exe .\configure_token.py
```

O engine lê somente a variável `APIFY_API_TOKEN`. Nunca coloque o token em JSON, YAML, código, relatório ou commit.

## Skill oficial

A metodologia integral está em `skills/SKILL_ATUALIZADA_BIG_NICHOS_LOW_TICKET.md`. O `AGENTS.md` obriga sua leitura antes de tarefas de mineração, Big Pain, G6, validação de oferta, raio-X de anunciante, mecanismos, Meta Ads, TikTok, Google e pesquisa de keywords.

Confira a versão ativa:

```powershell
.\mineracao.ps1 skill-status
```

## Modelo de job

Cada keyword é executada separadamente em cada fonte. O relacionamento resultado ↔ todas as queries encontradas é mantido mesmo depois da deduplicação.

```json
{
  "seed": "emagrecimento",
  "depth": "quick",
  "country": "BR",
  "sources": ["meta", "tiktok", "google"],
  "keywords": [
    "emagrecer depois dos 40",
    "resistência à insulina",
    "fígado gorduroso"
  ]
}
```

Um exemplo versionado está em `examples/job.example.json`.

## CLI

```powershell
.\mineracao.ps1 mine "MeuFluxo" --sources meta --depth quick
.\mineracao.ps1 mine "emagrecimento" --sources meta,tiktok,google --depth quick
.\mineracao.ps1 mine "emagrecimento" --keyword "barriga hormonal" --keyword "fome noturna" --depth quick
.\mineracao.ps1 run-job .\examples\job.example.json
```

Profundidades e tetos rígidos:

| Modo | Queries | Resultados/query | Total/job | Detalhes Meta |
|---|---:|---:|---:|---|
| quick | 5 | 10 | 150 | não |
| medium | 15 | 50 | 500 | sim |
| deep | 30 | 100 | 1000 | sim |

Além dos limites por modo, os tetos globais `MAX_QUERIES_PER_JOB`, `MAX_RESULTS_PER_QUERY` e `MAX_TOTAL_RESULTS_PER_JOB` são aplicados pelo pipeline. Uma configuração acima deles é rejeitada antes de chamar a Apify.

Use `--preflight` para solicitar a pré-contagem barata do provider Meta antes da coleta. A disponibilidade e a cobrança dessa operação continuam sujeitas ao Actor configurado.

## Providers

- **Meta Ads:** preserva ID do anúncio, página/anunciante, copy, headline, CTA, destino, criativo/snapshot, datas, status e plataformas. Nos modos `medium` e `deep`, solicita detalhes adicionais.
- **TikTok:** preserva ID, caption, autor, URL, data, métricas, hashtags, música e seguidores quando fornecidos.
- **Google:** transforma cada item de `organicResults`, `peopleAlsoAsk` e `relatedQueries` em registro separado, mantendo tipo, query, posição, URL e domínio.

Campos ausentes permanecem `null`; o engine não inventa valores. Os schemas dos Actors podem mudar, portanto fixtures e normalizadores devem ser revistos quando o provider for substituído.

## Deduplicação e proveniência

A chave usa `source + external_id` quando há ID. Sem ID, usa fingerprint SHA-256 determinístico de campos estáveis; URLs são canonizadas e parâmetros de rastreamento são removidos. Um resultado visto por três keywords conta uma vez, mas `matched_queries` e a tabela `result_queries` preservam as três origens.

O relatório distingue `raw_count` de `deduplicated_count`.

## SQLite e estados

O banco padrão é `data/mineracao_info.db`. A pasta é local e ignorada pelo Git. Migrações simples criam e versionam:

- `jobs`, `queries`, `provider_runs`;
- `raw_results`, `normalized_results`, `result_queries`;
- `advertisers`, `claims`, `reports`, `scores`.

Estados persistidos: `queued`, `running`, `partial`, `completed` e `failed`. Se ao menos um provider falhar e outro funcionar, o job termina como `partial`; se todos falharem, termina como `failed`.

## Evidence Score

O score de 0 a 100 é explicável e não contém conclusão comercial automática:

| Componente | Peso máximo |
|---|---:|
| volume deduplicado | 20 |
| longevidade | 20 |
| anunciantes independentes | 15 |
| diversidade criativa | 15 |
| datas escalonadas / possíveis relaunches | 10 |
| presença em múltiplas fontes | 10 |
| repetição de termos/mecanismos | 10 |

`score.json` contém pesos, valores observados e pontos por componente. `strategic_assessment` permanece vazio para ser preenchido pelo cérebro analítico.

## Longevidade e claims

Para anúncio ativo: `agora - started_at`. Para anúncio encerrado: `ended_at - started_at`; a duração não continua crescendo. Faixas: teste (1–7), watchlist (8–20), investigar (21–45), forte sinal (46–90) e muito forte (90+).

Claims de saúde são registros com `result_id`, tipo, termo, contexto, severidade e status. O engine marca `CLAIM_ENCONTRADO` e `VALIDAR_TECNICAMENTE`; não decide se a alegação é verdadeira ou falsa.

## Intelligence Packet

Cada execução gera:

```text
outputs/<job_id>/
  REPORT.md
  summary.json
  score.json
  normalized.json
```

O relatório traz seed, keywords, status dos providers, contagens, anunciantes, longevidade, copies/criativos, datas, possíveis relaunches, domínios, related queries, People Also Ask, termos, mecanismos candidatos, claims, Evidence Score e amostras. A pasta `outputs/` não é versionada.

## API local

```powershell
.\start_server.ps1
```

Escuta apenas em `127.0.0.1:8791`:

- `GET /health`
- `GET /skill/status`
- `POST /mine`
- `GET /jobs/{id}`
- `GET /jobs/{id}/report`

`POST /mine` aceita o modelo de job acima, retorna `202` e persiste o estado antes de iniciar a execução em segundo plano. A consulta não depende de memória do processo.

## GitHub Actions e results/latest

O workflow manual `.github/workflows/mine.yml` recebe um único input `job_json`, instala dependências, usa exclusivamente `secrets.APIFY_API_TOKEN`, executa o engine e publica o pacote completo como artifact por 14 dias.

Somente a versão compacta é commitada:

```text
results/latest/REPORT.md
results/latest/summary.json
results/latest/score.json
results/<job_id>/...
```

Banco, raw data, token e `normalized.json` não entram no commit. O workflow só responde a `workflow_dispatch`, usa teto de 30 minutos e inclui `[skip ci]`, evitando disparos em loop.

Para executar: GitHub → **Actions** → **Mine intelligence packet** → **Run workflow** → cole o Job JSON.

## Ponte HTTP na Vercel

A pasta `bridge/` contém uma função serverless mínima. Ela não executa o engine: apenas autentica a chamada, dispara `mine.yml` pela API do GitHub e lê o último resultado compacto.

Rotas:

- `POST /api/mine` — valida o Job JSON e dispara `workflow_dispatch` em `main`;
- `GET /api/status` — retorna a execução manual mais recente do workflow;
- `GET /api/latest` — retorna `summary.json` e `score.json`;
- `GET /api/latest?include_report=true` — inclui também `REPORT.md`;
- `GET /api/openapi` — contrato OpenAPI para conectar um cliente/Action do ChatGPT.

As três rotas operacionais exigem:

```http
Authorization: Bearer <MINERACAO_TRIGGER_KEY>
```

Variáveis exclusivas da Vercel:

- `MINERACAO_TRIGGER_KEY`: chave longa e aleatória compartilhada apenas com o cliente autorizado;
- `GITHUB_WORKFLOW_TOKEN`: fine-grained Personal Access Token restrito ao repositório oficial, com **Actions: Read and write** e **Contents: Read-only**.

O token GitHub não precisa de permissões administrativas, Issues, Pull Requests, deployments ou acesso a outros repositórios. `APIFY_API_TOKEN` permanece somente em GitHub Actions Secrets e nunca vai para a Vercel.

A ponte rejeita payloads acima de 16 KiB, fontes desconhecidas, profundidades inválidas, keywords duplicadas e jobs acima do teto de cada profundidade. Há rate limiting em memória como proteção de primeira linha; por ser serverless, limites distribuídos mais rígidos exigiriam um armazenamento externo, deliberadamente não adicionado nesta versão.

Teste local da ponte:

```powershell
Set-Location .\bridge
npm test
```

Deploy manual, quando necessário:

```powershell
Set-Location .\bridge
npx vercel --prod
```

## Testes

```powershell
.\test.ps1
```

As fixtures representam os formatos atuais usados pelos normalizadores Meta, TikTok e Google. A suíte cobre Skill, parsing do job, configuração/tetos, normalização, deduplicação, proveniência, longevidade, claims, score, storage, status parcial e Intelligence Packet.

Testes reais consomem créditos Apify e devem usar `quick`, uma fonte por vez e o menor conjunto de keywords.

## Segurança, custos e limitações

- `.env`, `.venv`, `data`, `outputs`, caches e bytecode são ignorados.
- O token não é enviado ao frontend (não existe frontend), relatório ou logs.
- Cada combinação keyword × fonte cria uma execução de Actor e pode gerar cobrança; comece em `quick`.
- Resultados dependem da cobertura e do schema atual de Actors terceiros.
- Detecção de relaunch e mecanismos é heurística e exige interpretação humana.
- Longevidade, volume e score são sinais, nunca comprovação de faturamento, lucro, eficácia ou segurança médica.
- A API é local e não deve ser exposta diretamente à internet sem autenticação.

## Estrutura principal

```text
config/                 limites, pesos, providers e runtime da Skill
bridge/                 ponte HTTP mínima para Vercel
skills/                 Skill oficial integral
src/mineracao_info/     pipeline, providers, normalizadores, banco e relatórios
tests/                  testes e fixtures
examples/               Job JSON de exemplo
.github/workflows/      execução remota manual
results/                relatórios compactos versionáveis
```
