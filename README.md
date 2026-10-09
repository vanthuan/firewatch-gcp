# FireWatch: Autonomous Wildfire Intelligence and Response

FireWatch turns raw environmental sensor events into **investigated, evidence-backed, human-approved**
wildfire incident decisions within minutes, and remembers each outcome so the next investigation is
smarter.

Wildfire detection today relies on fragmented signals: ground sensors, weather feeds, satellite
hotspots and historical reports live in separate systems. Operators correlate them by hand, and false
positives (industrial smoke, agricultural burns) cause alert fatigue. FireWatch brings those signals
together, has an agent investigate every anomaly, computes risk with an auditable formula, and leaves
every consequential decision to a person.

> FireWatch is a decision-support prototype. It does not dispatch emergency services, does not replace
> official alerting systems, and runs on synthetic and public data.

## How it works

1. **Sense.** Sensors (a simulator with `normal`, `wildfire` and `industrial` modes) publish readings to
   Pub/Sub. A Dataflow pipeline validates them and computes rolling features per sensor.
2. **Detect.** When the anomaly score or the model's wildfire probability crosses a threshold, an
   incident is created (deduplicated per sensor and time window) and appears on the live map.
3. **Investigate.** A deterministic ADK workflow runs: screen untrusted input → analyse the sensor →
   ML prediction → weather, regional history, cited knowledge (RAG) and similar past incidents in
   parallel → risk fusion → recommendation. Every step is streamed to the operator's trace panel.
4. **Explain.** Risk is computed by a weighted formula, never by the LLM. Gemini only writes the
   recommendation and answers the operator's questions in chat, grounded in tool outputs and cited
   documents.
5. **Decide.** The agent can only *request* approval. Approve and reject are authenticated actions by a
   human operator, recorded with the risk snapshot.
6. **Learn.** The real outcome (confirmed fire, industrial smoke, false alarm) is written into an
   incident-memory corpus, so a matching signature later is recognised.

### Risk function

```text
weights  = {p_wildfire: 0.40, sensor_anomaly: 0.25, weather_risk: 0.15, historical_risk: 0.10, visual_probability: 0.10}
risk     = Σ(wᵢ·sᵢ for signals present) / Σ(wᵢ for signals present)     # renormalised when a signal is missing
coverage = Σ(wᵢ for signals present)                                    # shown in the UI
level    = LOW < 0.40 ≤ MEDIUM < 0.70 ≤ HIGH                            # "needs evidence" hint when coverage < 0.65
```

Weights and their version live in config and are stored on every incident.

## Architecture

```text
 Browser (Next.js) ── REST + chat SSE ──▶ firewatch-api (Cloud Run: FastAPI + ADK)
   │ Firestore listeners (read-only)          │  investigation workflow · chat agent · Model Armor
   ▼                                          ├──▶ Gemini (Agent Platform)
 Firestore: incidents, agent_events,          ├──▶ classifier endpoint (XGBoost)
            approvals                         ├──▶ RAG Engine: knowledge + incident memory
                                              └──▶ weather API (Open-Meteo)
 Simulator ─▶ Pub/Sub sensor-raw ─▶ Dataflow (features) ─▶ BigQuery + Pub/Sub sensor-features ─push─▶ firewatch-api

 Offline: GCS raw ─▶ Dataprep by Alteryx ─▶ BigQuery curated ─▶ Serverless Spark ─▶ training tables
          ─▶ XGBoost training ─▶ Model Registry ─▶ endpoint
```

| Service | Runs on | Role |
| --- | --- | --- |
| `firewatch-web` | Cloud Run (Node 22) | Dashboard, map, incident view, chat, Firebase Auth |
| `firewatch-api` | Cloud Run (Python 3.12) | Pub/Sub push handler, REST, chat streaming, investigation workflow, tools |
| `firewatch-stream` | Dataflow (streaming) | Validation, rolling features, BigQuery sink |
| `firewatch-batch` | Serverless for Apache Spark | Regional and historical aggregates, training tables |
| `firewatch-classifier` | Agent Platform endpoint | Wildfire probability and anomaly score |
| `firewatch-knowledge`, `firewatch-memory` | RAG Engine corpora | Procedures and reports; resolved incidents with outcomes |

## Screens

| Screen | Purpose |
| --- | --- |
| Operations dashboard (`/`) | Live map and incident list, system status |
| Incident investigation (`/incidents/[id]`) | Signals, risk breakdown, live agent trace, evidence with citations, approve / reject / record outcome |
| Chat | Bound to an incident: "why is this high risk?", "get more evidence" |
| Data platform (`/data-platform`) | Real status of Dataflow, Spark, Dataprep, the endpoint and RAG corpora |
| Evaluation (`/evaluation`) | ML, RAG and agent metrics from the eval harness |

## Technology

ADK 2.x on Gemini Enterprise Agent Platform (`gemini-3.8-flash`, `gemini-3.5-flash-lite`), RAG Engine,
XGBoost on an Agent Platform endpoint, Pub/Sub, Dataflow (Apache Beam), Serverless for Apache Spark,
Cloud Dataprep by Alteryx, BigQuery, Firestore, Cloud Run, Model Armor, Firebase Auth, Next.js 16 with
Tailwind and shadcn/ui, Terraform and Cloud Build.

## Targets

| Metric | Target |
| --- | --- |
| Sensor event → incident on the dashboard | < 10 s (direct), < 30 s (via Dataflow) |
| Full investigation | < 60 s |
| Classifier ROC-AUC (held-out synthetic set) | ≥ 0.90 |
| False-positive rate at HIGH | ≤ 10% |
| Citation correctness | ≥ 90% |
| Scripted prompt-injection attempts blocked | 100% |
| Consequential actions without human approval | 0 |

## Repository status

This repository is being repurposed for FireWatch. It currently contains the **platform foundation**
built for an earlier agent product, which FireWatch reuses:

- a uv/pnpm monorepo with agents-cli agent projects under `agents/` (to be replaced by the FireWatch
  investigation workflow and chat agent);
- Terraform for a single Google Cloud project (`infra/terraform`: service accounts, Pub/Sub with
  dead-letter topics, Firestore, BigQuery, Secret Manager, networking, Vertex AI Search) and Cloud Build
  CI with path-filtered pull-request checks and deploy triggers;
- a local stack (`docker-compose.yml`: Postgres with pgvector, Firestore and Pub/Sub emulators) and
  `make` targets;
- Firestore security rules with tests.

The FireWatch-specific services (sensor simulator, `firewatch-api`, Dataflow and Spark pipelines,
classifier, RAG corpora, operator UI) are built following the blueprint below.

## Getting started

```bash
uv tool install --upgrade 'google-agents-cli==1.7.*'
gcloud auth login && gcloud auth application-default login
gcloud auth application-default set-quota-project <PROJECT_ID>

make install     # Python workspace and web dependencies
make up          # local Postgres + pgvector (5433), Firestore (8080) and Pub/Sub (8085) emulators
make help        # every target
```

Provision with Terraform from `infra/terraform/envs/dev` (`terraform init`, `plan`, `apply`). Gemini 3.x
chat models are served on the `global` endpoint; set `GOOGLE_CLOUD_LOCATION=global` for agents and keep
data services in their region.

## Documentation

- [FireWatch Implementation Blueprint](docs/FireWatch_Implementation_Blueprint.md): PRD, technical design,
  UI, app flow, schemas, plan and step-by-step build guide
- [`docs/firewatch-full-implementation.md`](docs/firewatch-full-implementation.md) and
  [`docs/firewatch-implementation-playbook.md`](docs/firewatch-implementation-playbook.md): how the
  reused foundation (Terraform, CI, local stack, Firestore rules) was built, step by step. Their
  application-specific steps describe the earlier product, not FireWatch.
