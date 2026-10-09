# firewatch-gcp: Cymbal FireWatch agent platform

FireWatch is a multi-agent platform on Google Cloud that takes a product launch from brief to sent
campaign. A marketer uploads a launch brief; agents extract the product facts, research the market,
draft copy for every channel in the brand voice, check it against brand and legal rules, and wait for a
person to approve before anything is sent. The same platform matches the announcement to relevant
journalists and runs a public product advisor for shoppers.

It is built with the [Agent Development Kit (ADK)](https://adk.dev) 2.10, deployed with
[agents-cli](https://pypi.org/project/google-agents-cli/) 1.7, and runs on Gemini models through the
Gemini Enterprise Agent Platform.

## What it does

| Area | What happens | Main pieces |
| --- | --- | --- |
| **Knowledge** | Briefs and documents are screened, parsed (text, tables, images) and made searchable; users ask questions and get answers with `[document, page]` citations, or search pages by image | Vertex AI Search (`kb`, `catalog`), ingest worker, knowledge agent |
| **Campaign engine** | A workflow graph: extract facts → person confirms → research and judge (loop) → five copy agents in parallel → claim audit → compliance check → person approves → dispatch | Orchestrator on Agent Runtime, researcher and judge as A2A services, skills with a compliance script |
| **Media Match** | Finds the 20 best-fit journalists for an announcement (vector search, opt-outs excluded), writes personalised pitches for a PR manager to approve | media-matcher service, AlloyDB + pgvector, pitch worker |
| **Product Advisor** | Public chat that recommends paint and calculates how much to buy | Advisor agent, catalog search |
| **Guardrails** | Every model input and output is screened; banned claims are blocked; every block is logged | Model Armor, keyword guardrail, `guardrail_events` |

## Architecture

```text
 Browser ──▶ Next.js app (UI + BFF route handlers, Cloud Run) ──▶ Agent Runtime: orchestrator, advisor, knowledge
    │  signed upload                     │ Firebase Auth, roles            │ A2A (IAM)
    ▼                                    ▼                                 ▼
 Cloud Storage ──▶ Pub/Sub ──▶ ingest worker            Firestore     Cloud Run: researcher, judge, media-matcher ──▶ AlloyDB (VPC)
                                   └─▶ Vertex AI Search (kb)         (live timeline)          dispatch worker ◀── Pub/Sub
```

The browser only talks to the BFF, which holds the credentials for the agents. Uploads go straight to
Cloud Storage with signed URLs. Only services inside the VPC can reach AlloyDB. Everything is provisioned
with Terraform in a single Google Cloud project.

## Repository layout

| Path | Contents |
| --- | --- |
| `agents/` | One [agents-cli](https://pypi.org/project/google-agents-cli/) project per agent: `orchestrator`, `advisor` (Agent Runtime); `researcher`, `judge`, `media-matcher` (Cloud Run, A2A) |
| `apps/web/` | Next.js 16 app: UI and BFF route handlers |
| `packages/shared-py/` | `firewatch_shared`: Pydantic models shared by agents and workers |
| `packages/shared-ts/` | zod schemas generated from the Python models |
| `workers/` | Cloud Run workers and jobs: `ingest`, `dispatch`, `backfill` |
| `skills/` | Agent skills (brand voice, rules, compliance script) |
| `infra/terraform/` | `modules/firewatch` (all platform resources), `modules/cicd` (Cloud Build triggers), `envs/dev` |
| `cloudbuild/` | Pipeline files used by the triggers |
| `firestore/` | Security rules, indexes and their tests |
| `tools/` | Seed data generator and loader, document builder |
| `data/seed/` | Synthetic demo data (briefs, catalog, journalists, swatches) |
| `docs/` | Implementation guide, playbook, ADRs |

## Getting started

### Prerequisites

Google Cloud CLI, Docker with Compose, Terraform ≥ 1.8, [uv](https://docs.astral.sh/uv/), Node 22 with
`corepack enable`, and `agents-cli` 1.7:

```bash
uv tool install --upgrade 'google-agents-cli==1.7.*'
gcloud auth login
gcloud auth application-default login
gcloud auth application-default set-quota-project <PROJECT_ID>
```

The quota project matters: Discovery Engine and Model Armor reject user credentials without one.

### Run locally

```bash
make install          # Python workspace (uv) and web dependencies
make up               # Postgres + pgvector (port 5433), Firestore emulator (8080), Pub/Sub emulator (8085)
make seed             # demo data into the local database and the dev project's buckets and search
make dev AGENT=orchestrator   # web app + one agent's playground; Ctrl+C stops both
```

Each agent reads its own `agents/<name>/.env` (copy `.env.example`). `make help` lists every target.

### Provision and deploy

```bash
cd infra/terraform/envs/dev
terraform init && terraform plan -out=dev.tfplan && terraform apply dev.tfplan
```

After that, merging to `main` deploys: each agent, worker and the web app has a path-filtered pull
request check and a deploy trigger in Cloud Build. The first deploy of each agent is done by hand
(`agents-cli deploy …`); CI only updates existing deployments.

## Working conventions

- **Dependencies:** after editing any `pyproject.toml`, run `make lock`. It updates the workspace lock
  and each service's own `uv.lock`, which its Dockerfile installs from.
- **Shared models:** after editing `packages/shared-py/firewatch_shared/models.py`, run `make schemas`
  and commit the regenerated `packages/shared-ts` files.
- **Model location:** Gemini 3.x chat models are served on the `global` endpoint, so agents pin
  `GOOGLE_CLOUD_LOCATION=global`; embeddings (`gemini-embedding-001`) use `us-east1`.
- **Infrastructure:** change resources in Terraform only, always `plan` before `apply`.
- **Tests:** `make test-rules` for Firestore rules; `uv run --package <agent> pytest agents/<agent>/tests/unit` for an agent.

## Status

Foundation is in place: monorepo, agent scaffolds, local stack, Terraform for the platform, Firestore
rules, single-project CI/CD, shared models, seed data and the Vertex AI Search datastores. Identity, the
web shell, the ingest worker and the campaign graph are next. The step-by-step plan and progress are in
the documents below.

## Documentation

- [Full implementation guide](docs/firewatch-full-implementation.md): every step from an empty project to go-live, with commands and code
- [Implementation playbook](docs/firewatch-implementation-playbook.md): the remaining steps in detail
- [`docs/adr/`](docs/adr/): architecture decisions
