"""Usage: python3 tools/build_full_impl_doc.py .   (from the repo root)

Builds docs/firewatch-full-implementation.md.

From-scratch sections are written here; files that already exist in the repo are embedded verbatim
(so the document always matches the code); later steps are taken from the playbook.
"""

import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])
PLAYBOOK = (ROOT / "docs/firewatch-implementation-playbook.md").read_text()
OUT = ROOT / "docs/firewatch-full-implementation.md"

LANG = {".py": "python", ".tf": "hcl", ".yaml": "yaml", ".yml": "yaml", ".json": "json", ".js": "js",
        ".mjs": "js", ".ts": "ts", ".toml": "toml", ".sql": "sql", ".sh": "bash", ".rules": "",
        ".tfvars": "hcl", ".md": "markdown"}


def lang(path: str) -> str:
    name = Path(path).name
    if name == "Makefile":
        return "make"
    if name.startswith(".gitignore"):
        return "gitignore"
    return LANG.get(Path(path).suffix, "")


def embed(path: str, explain: str, *, transform=None, title: str | None = None) -> str:
    text = (ROOT / path).read_text().rstrip("\n")
    if transform:
        text = transform(text)
    fence = "````" if "```" in text else "```"
    head = f"**[Repo]** `{path}`" + (f" ({title})" if title else "")
    return f"{head}\n\n{fence}{lang(path)}\n{text}\n{fence}\n\n*What this does:* {explain}\n"


def section(start: str, end: str | None) -> str:
    i = PLAYBOOK.index(start)
    j = PLAYBOOK.index(end, i) if end else len(PLAYBOOK)
    return PLAYBOOK[i:j].rstrip() + "\n"


def drop_search_output(text: str) -> str:
    return re.sub(r'\noutput "search" \{.*?\n\}\n', "\n", text, flags=re.S)


def only_search_output(path: str) -> str:
    text = (ROOT / path).read_text()
    m = re.search(r'output "search" \{.*?\n\}\n', text, re.S)
    return m.group(0).rstrip("\n")


parts: list[str] = []
add = parts.append

# ---------------------------------------------------------------------------------------------
add("""# FireWatch: Full Implementation, From Zero to Go-Live

This document rebuilds the whole FireWatch platform from an empty GitHub repository and an empty Google
Cloud project, in order, with every command and every file. It follows the *Cymbal FireWatch
Implementation Guide v2*, adapted to a **single Google Cloud project** and to what was learned while
building it.

**How it is written**

- Steps that are already built in this repo embed the **actual files from the repo**, verbatim. The
  document was generated from the repo on 2026-09-28, so what you read is what is committed.
- Steps not built yet give the complete code to write. Where their code was run while writing (the
  Phase 3 graph and its tests, the ADK behaviours in section B), that is stated.
- Every step has **Why**, a **Diagram** where the flow is not obvious (with *How to read it*),
  numbered **Actions**, **Code** with *What this does*, a **Check**, and **If it fails**.
- Actions are tagged:
  - **[Local]** a command on your machine, no cloud side effects
  - **[Cloud]** creates or changes something in Google Cloud, Firebase or GitHub (may cost money)
  - **[Repo]** create or edit a file (commit it)

> Verified against `google-adk 2.10.0`, `google-agents-cli 1.7.0` and Terraform provider
> `hashicorp/google 7.46.1`. Anything that could not be checked without running it in the cloud is
> marked **(verify)** with the command to check it.

## Contents

- [A. Orientation](#a-orientation)
- [B. Corrections to the guide](#b-corrections-to-the-guide)
- [Phase 0: Prerequisites](#phase-0-prerequisites)
- [Phase 1: Foundation](#phase-1-foundation)
- [Phase 2: Knowledge](#phase-2-knowledge)
- [Phase 3: Campaign engine](#phase-3-campaign-engine)
- [Phase 4: Media Match and Product Advisor](#phase-4-media-match-and-product-advisor)
- [Phase 5: Hardening and go-live](#phase-5-hardening-and-go-live)
- [Appendix: command cheat sheet](#appendix-command-cheat-sheet)

---

## A. Orientation

""")

a1a2 = section("### A.1 Fixed names used everywhere", "### A.3 Where things are today")
a1a2 = a1a2.replace(
    "| Orchestrator engine | `projects/270490372651/locations/us-east1/reasoningEngines/6482216981041774592` |",
    "| Orchestrator engine | created in Step 1.5; this repo's is `projects/270490372651/locations/us-east1/reasoningEngines/6482216981041774592` |")
add(a1a2)
add("""
If you build in a different project, replace the project ID and number everywhere (the Terraform
`terraform.tfvars`, `backend.tf`, `cicd.tf`, and the commands below). `grep -rn 3e77a7b7 .` finds them.

### A.3 Build order

| Phase | Steps, in the order to do them |
| --- | --- |
| 0 Prerequisites | 0.1 tooling · 0.2 project and billing · 0.3 credentials · 0.4 repository · 0.5 ADRs |
| 1 Foundation | 1.1 agents-cli · 1.2 monorepo · 1.3 scaffold agents · 1.4 local stack · 1.5 agents-cli infra · 1.6 Terraform module · 1.7 networking · 1.8 Firestore rules · 1.12 CI/CD · 1.9 identity · 1.10 web shell · 1.10b web deploy · 1.13 hello agent · 1.11 BFF client · Gate 1 |
| 2 Knowledge | 2.1 shared models · 2.2 seed data · 2.3 datastores · 2.4 signed uploads · 2.7a Model Armor templates · 2.5 ingest worker · 2.6 knowledge Q&A and image search · 2.7b guardrails · 2.8 brief extractor · Gate 2 |
| 3 Campaign engine | 3.0 identity · 3.1 skills · 3.2 researcher and judge · 3.3 gates and routing · 3.4 copy agents and audit · 3.5 graph · 3.6 mirror and wiring · 3.7 BFF resume · 3.8 dispatch · 3.9 workspace UI · 3.10 evals · Gate 3 |
| 4 Media and Advisor | 4.1 AlloyDB · 4.2 journalist import · 4.3 VectorStore · 4.4 backfill · 4.5 media_matcher · 4.6 pitches · 4.7 advisor · Gate 4 |
| 5 Hardening | 5.1 observability · 5.2 alerts · 5.3 resilience · 5.4 load/security · 5.5 governance · 5.6 backup · 5.7 cost · 5.8 retention · 5.9 runbook · 5.10 go-live · Gate 5 |

CI/CD (1.12) comes before identity (1.9) because every later step is merged through pull requests.

""")
add(section("### A.4 Rules that apply to every step", "## B. Corrections to the guide"))
add("\n---\n\n")
add(section("## B. Corrections to the guide", "## 0. Before you start").rstrip().rstrip("-").rstrip() + "\n")

# ---------------------------------------------------------------------------------------------
add("""
---

## Phase 0: Prerequisites

### Step 0.1 Tooling

**Why:** every later step uses these tools; exact versions avoid the surprises hit while building
(an old `agents-cli` without `infra show`, Node 12 too old for pnpm).

**Actions**

1. **[Local]** Install the command-line tools:

   ```bash
   # Google Cloud CLI: https://cloud.google.com/sdk/docs/install  (then: gcloud components update)
   # Docker Engine + compose plugin: https://docs.docker.com/engine/install/
   # Terraform >= 1.8: https://developer.hashicorp.com/terraform/install
   curl -LsSf https://astral.sh/uv/install.sh | sh                  # uv (Python + packages)
   uv python install 3.12
   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
   exec $SHELL
   nvm install 22 && nvm alias default 22                           # Node 22
   corepack enable                                                  # pnpm, pinned per repo
   # GitHub CLI: https://cli.github.com/  (then: gh auth login)
   ```

2. **[Local]** Install `agents-cli` at the version this document uses:

   ```bash
   uv tool install --upgrade 'google-agents-cli==1.7.*'
   agents-cli --version          # agents-cli, version 1.7.x
   agents-cli setup              # installs its coding-agent skills
   ```

   *What this does:* `uv tool` installs the CLI in its own environment. The guide's `uvx google-agents-cli setup`
   can reuse an older cached copy; pinning avoids that (commands like `agents-cli infra show` only exist in 1.7).

**Check:** `gcloud version`, `docker compose version`, `terraform -version` (≥ 1.8), `uv --version`,
`node -v` (v22), `pnpm -v`, `gh --version`, `agents-cli --version` (1.7.x) all succeed.

### Step 0.2 Google Cloud project and billing

**Why:** one project holds everything (ADR 0001). Billing must be linked before any API can be enabled.

**Actions**

1. **[Cloud]** Create or pick the project and link billing:

   ```bash
   export P=project-3e77a7b7-cc39-467f-8a8          # or your own project ID
   gcloud projects create $P                        # skip if it already exists
   gcloud billing accounts list
   gcloud billing projects link $P --billing-account=<ACCOUNT_ID>
   gcloud config set project $P
   gcloud config set compute/region us-east1
   gcloud services enable serviceusage.googleapis.com cloudresourcemanager.googleapis.com iam.googleapis.com
   ```

   *What this does:* the three APIs let Terraform enable everything else (Step 1.6).

2. **[Cloud]** Budget alerts (Billing → Budgets & alerts): one budget for the project with alerts at
   50%, 90% and 100%. Step 5.2 moves it into Terraform. Also turn on billing export to BigQuery
   (Billing → Billing export → BigQuery, dataset `billing_export`, created in Step 1.6; come back after it).

3. **[Cloud]** Check organisation policies that commonly block this stack (skip if the project has no
   organisation): `gcloud resource-manager org-policies list --project $P`. Look for
   `iam.allowedPolicyMemberDomains` (blocks `allUsers` on the web service), `run.allowedIngress`,
   `gcp.resourceLocations` (must allow `us-east1` and `global`).

4. **[Cloud]** Request Gemini quota if you expect load (Console → IAM & Admin → Quotas, filter
   "Gemini", region `us-east1`). Defaults are enough for development.

**Check:** `gcloud projects describe $P` works and `gcloud billing projects describe $P` shows
`billingEnabled: true`.

### Step 0.3 Credentials and quota project

**Why:** SDKs, Terraform and agents-cli use Application Default Credentials (ADC). Discovery Engine,
Model Armor and Identity Platform reject user credentials that have no quota project (this caused a
failed `terraform apply` while building Step 2.3).

**Actions**

1. **[Local]**

   ```bash
   gcloud auth login
   gcloud auth application-default login
   gcloud auth application-default set-quota-project $P
   agents-cli login
   deactivate 2>/dev/null; unset VIRTUAL_ENV     # in every terminal used for this repo
   ```

   *What this does:* your user signs in for `gcloud` and for ADC; the quota project makes every API
   call bill quota to your project. An activated virtualenv from another folder makes uv print
   `VIRTUAL_ENV … does not match` on every command, so deactivate it.

### Step 0.4 Repository

**Actions**

1. **[Cloud]** Create the repository and clone it:

   ```bash
   gh repo create vanthuan/firewatch-gcp --private --clone
   cd firewatch-gcp
   ```

   Protect `main` (Settings → Branches): require a pull request and passing checks.

2. **[Repo]** `.gitignore` at the root:

   ```gitignore
   .venv/
   node_modules/
   .env
   .env.*
   !.env.example
   *.tfplan
   plan.txt
   __pycache__/
   .next/
   # vendored into agents by `make vendor` (Step 2.6a)
   agents/*/app/shared/
   agents/*/app/skills/
   ```

   *What this does:* keeps local environments, secrets, build output and generated copies out of git.

3. **[Local]** Make sure you own the working tree. If the folder was created by another user (for
   example with `sudo`), git refuses with "dubious ownership": `sudo chown -R $USER:$USER .`

### Step 0.5 Architecture decision records

""")
adr = section("### 0.4 Architecture decision records", "## Phase 1 leftovers")
adr = adr.replace("### 0.4 Architecture decision records\n", "").rstrip().rstrip("-").rstrip() + "\n"
add(adr)

# ---------------------------------------------------------------------------------------------
add("""
---

## Phase 1: Foundation

### Step 1.1 agents-cli

Done in Step 0.1. `agents-cli --version` must print 1.7.x before you scaffold: the flags below and the
generated files depend on it.

### Step 1.2 Monorepo layout

**Why:** agents, web app, workers, shared packages and infrastructure live in one repository, share
one Python lockfile and one pnpm lockfile, and deploy through path-filtered pipelines (Step 1.12).

**Diagram**

```text
firewatch-gcp/
├── apps/web/                  Next.js app: UI + BFF route handlers                (1.10)
├── agents/                    one agents-cli project per agent                    (1.3)
│   ├── orchestrator/  advisor/            Agent Runtime
│   └── researcher/  judge/  media-matcher/ Cloud Run (A2A)
├── skills/                    promo-writer, social-post, press-release, research  (3.1)
├── packages/
│   ├── shared-py/firewatch_shared/        Pydantic models, kb search, guardrails  (2.1)
│   └── shared-ts/                         generated zod schemas                   (2.1)
├── workers/                   ingest, dispatch, backfill, pitch (Cloud Run)       (2.5, 3.8, 4.x)
├── infra/terraform/           modules/{firewatch,cicd}, envs/dev                  (1.6, 1.12)
├── cloudbuild/                pipeline files                                      (1.12)
├── firestore/                 rules, indexes, rules tests                         (1.8)
├── tools/                     seed, admin and eval scripts                        (2.2)
├── data/seed/                 generated demo data                                 (2.2)
└── docs/adr/                  decisions                                           (0.5)
```

**Actions**

1. **[Local]**

   ```bash
   mkdir -p apps agents skills packages/shared-py packages/shared-ts workers \\
            infra/terraform/modules/firewatch infra/terraform/modules/cicd infra/terraform/envs/dev \\
            cloudbuild firestore/tests tools/sql data/seed docs/adr
   ```

""")
add(embed("pyproject.toml",
          "makes the repo a uv workspace. Every member shares one `uv.lock` at the root, so `uv sync --all-packages` "
          "installs everything into one `.venv` for local work. Each deployable member also keeps its own "
          "`uv.lock` for its Docker build (Step 1.3)."))

add("""
### Step 1.3 Scaffold the agents

**Why:** agents-cli generates each agent's app skeleton, tests, Dockerfile, Terraform and pipelines. The
deployment target and CI runner must be passed explicitly: without them `create` makes a prototype with
no Terraform.

**Actions**

1. **[Local]**

   ```bash
   cd agents
   agents-cli scaffold create orchestrator  -d agent_runtime --cicd-runner google_cloud_build --region us-east1 --bq-analytics -y
   agents-cli scaffold create advisor       -d agent_runtime --cicd-runner google_cloud_build --region us-east1 --bq-analytics -y
   agents-cli scaffold create researcher    -d cloud_run     --cicd-runner google_cloud_build --region us-east1 -y
   agents-cli scaffold create judge         -d cloud_run     --cicd-runner google_cloud_build --region us-east1 -y
   agents-cli scaffold create media-matcher -d cloud_run     --cicd-runner google_cloud_build --region us-east1 -y
   cd ..
   ```

   *What this does:* creates five projects. Each has `app/agent.py` (a sample agent you replace later),
   `app/fast_api_app.py` (serves the agent and its A2A card under `/a2a/app`), `tests/`, a `Dockerfile`,
   `deployment/terraform/{single-project,cicd}` and `agents-cli-manifest.yaml`. The folder name
   `media-matcher` (hyphen) is also the Cloud Run service name used everywhere below.

2. **[Repo]** Pin ADK 2.10 with the extras each agent needs. In each agent's `pyproject.toml`, replace the
   `google-adk…` dependency line:

   | Agent | Line |
   | --- | --- |
   | orchestrator, advisor | `"google-adk[a2a,bigquery-analytics,gcp,otel-gcp]==2.10.*",` |
   | researcher, judge, media-matcher | `"google-adk[a2a,gcp,otel-gcp]==2.10.*",` |

   *What this does:* `gcp` brings Model Armor (`google-cloud-modelarmor`), `bigquery-analytics` the
   analytics plugin (Step 5.1), `a2a` the `RemoteA2aAgent` client (Step 3.2). Scaffolds pin older ADK
   versions, and `agents-cli scaffold upgrade` can lower the pin again (B12): re-check these lines after
   any scaffold command.

3. **[Local]** Lock. Two kinds of lockfile exist, and both must be current:

   ```bash
   uv lock                      # the workspace lock (local development)
   make lock                    # also each agent's own uv.lock (after Step 1.4 adds the Makefile)
   uv sync --all-packages
   ```

   *What this does:* inside the workspace, `uv lock` only updates the root `uv.lock`. But each agent's
   `Dockerfile` copies only its own folder and runs `uv sync --frozen` on **its own** `uv.lock`; a stale one
   silently ships old versions. `make lock` re-locks every agent outside the workspace and copies the
   result back.

**Check:** `grep -A1 '^name = "google-adk"' agents/*/uv.lock` shows `version = "2.10.0"` for all five, and
`cd agents/orchestrator && agents-cli run "hello"` answers (it starts a temporary local server).

### Step 1.4 Local development stack

**Why:** develop against local Postgres (with pgvector), Firestore and Pub/Sub; only the AI services
are called in the cloud.

""")
add(embed("docker-compose.yml",
          "starts three containers. Postgres with pgvector stands in for AlloyDB; it is published on host port "
          "**5433** because 5432 is often taken by a system PostgreSQL. The Firestore emulator listens on 8080. "
          "The Pub/Sub emulator only exists in gcloud's **beta** commands (`gcloud emulators pubsub` fails with "
          "`Invalid choice`) and takes the project ID it emulates."))
add("""
**[Repo]** Each agent's `.env` (not committed; copy to `.env.example` with empty values):

```bash
GOOGLE_CLOUD_PROJECT=project-3e77a7b7-cc39-467f-8a8
GOOGLE_CLOUD_LOCATION=us-east1
GOOGLE_GENAI_USE_VERTEXAI=TRUE
VECTOR_BACKEND=alloydb
FIRESTORE_EMULATOR_HOST=localhost:8080     # only for code that should use the emulator
PUBSUB_EMULATOR_HOST=localhost:8085
DATABASE_URL=postgresql://postgres:dev@localhost:5433/firewatch
```

""")
add(embed("Makefile",
          "one entry point for local work (`make help` lists everything):\n"
          "- `up` / `down` / `reset` / `logs` / `ps` manage the containers (`--wait` blocks until healthy).\n"
          "- `dev` starts the containers, the web app (when it exists) and one agent's playground; Ctrl+C stops all.\n"
          "- `lock` updates the workspace lock and every agent's own lock (Step 1.3).\n"
          "- `test-rules`, `schemas`, `seed`, `seed-assets` are used from Steps 1.8, 2.1 and 2.2.\n\n"
          "Recipe lines must start with a Tab. Later steps add `vendor` (2.6a) and extend `lock` to workers (2.5)."))
add("""
**Check:** `make up` then `docker compose ps` shows three healthy services;
`docker compose exec -T postgres psql -U postgres -d firewatch -c "CREATE EXTENSION IF NOT EXISTS vector"` succeeds;
`curl localhost:8080` and `curl localhost:8085` print `Ok`.

**If it fails:** `address already in use` on a port: another service uses it; change the host side of the
mapping (`"5434:5432"`) and every URL that points to it.

### Step 1.5 Provision the orchestrator with `agents-cli infra single-project`

**Why:** agents-cli creates the pieces its own deploys need: the agent's service account, a logs bucket,
the telemetry dataset and a placeholder Agent Runtime engine.

**Actions**

1. **[Cloud]**

   ```bash
   cd agents/orchestrator
   agents-cli infra single-project --project $P            # plan only
   agents-cli infra single-project --project $P --apply    # apply
   agents-cli infra show                                   # outputs
   cd ../..
   ```

   *What this does:* applies `deployment/terraform/single-project` with local state (the
   `terraform.tfstate` file in that folder; keep it). `infra show` prints the engine ID, the
   `orchestrator-app` service account and the `…-orchestrator-logs` bucket.

2. **Cost note.** The generated engine has `min_instances = 1` and 4 CPU / 8 GiB (billed while idle).
   Step 1.13 reduces it.

**To undo** (agents-cli has no destroy command):

```bash
cd agents/orchestrator/deployment/terraform/single-project
terraform plan -destroy -var-file=vars/env.tfvars
terraform destroy -var-file=vars/env.tfvars      # the logs bucket must be empty first
```

### Step 1.6 FireWatch Terraform module

**Why:** everything agents-cli does not create (APIs, service accounts, buckets, Pub/Sub, Firestore,
secrets, BigQuery, network, AlloyDB, IAM) comes from code, so the project can be rebuilt and drift is
visible.

**Diagram**

```text
 infra/terraform/envs/dev  (root: backend, providers, variables)
   ├── module "firewatch"  → modules/firewatch  (resources, one file per area)
   └── module "cicd"       → modules/cicd       (Step 1.12)
 state: gs://<project>-tfstate/firewatch/dev  (created by hand, versioned)
```

**Actions**

1. **[Cloud]** The state bucket (once, by hand, because Terraform needs it before it can run):

   ```bash
   gcloud storage buckets create gs://$P-tfstate --location=us-east1 --uniform-bucket-level-access --public-access-prevention
   gcloud storage buckets update gs://$P-tfstate --versioning
   ```

2. **[Repo]** The environment root:

""")
for path, explain in [
    ("infra/terraform/envs/dev/backend.tf", "stores state in the bucket above, under `firewatch/dev`. Versioning lets you recover an older state."),
    ("infra/terraform/envs/dev/providers.tf",
     "pins provider versions and sets `user_project_override` + `billing_project`, so API quota is billed to "
     "your project for any credential. Without it, Discovery Engine calls from a user login fail with "
     "`SERVICE_DISABLED` against Google's shared project (Step 2.3)."),
    ("infra/terraform/envs/dev/variables.tf", "the inputs of this environment. `enable_alloydb` stays false until Phase 4 (cost)."),
    ("infra/terraform/envs/dev/terraform.tfvars", "the values for this project."),
    ("infra/terraform/envs/dev/main.tf",
     "calls the module with the list of services that get their own service account. Later steps add inputs "
     "(`web_origins`, `push_endpoints`, `alert_email`, `a2a_services`, …)."),
    ("infra/terraform/envs/dev/outputs.tf", "re-exports the module outputs (`terraform output firewatch`). Step 1.12 adds `cicd`."),
]:
    if path.endswith("outputs.tf"):
        add(embed(path, explain, transform=lambda t: re.sub(r'\noutput "cicd" \{.*?\n\}', "", t, flags=re.S)))
    else:
        add(embed(path, explain))
add(embed("infra/terraform/.gitignore", "keeps local Terraform files, state copies and plans out of git."))

add("\n3. **[Repo]** The module, one file per area:\n\n")
module = [
    ("versions.tf", "provider requirements for the module, and the project data source used for its number."),
    ("variables.tf",
     "the module's inputs. `vector_backend` is validated; `services` drives service-account creation; "
     "`search_location` is used from Step 2.3."),
    ("apis.tf",
     "enables every API the stack uses. `disable_on_destroy = false` because the agents-cli Terraform "
     "relies on some of the same APIs; destroying this module must not switch them off."),
    ("service_accounts.tf",
     "one service account per service, named `sa-<service>` so they never collide with agents-cli's "
     "`<agent>-app` accounts."),
    ("storage.tf", "five buckets: uniform access, public access prevented, versioning on briefs. CORS (2.4) and "
                   "lifecycle rules (5.8) are added later."),
    ("pubsub.tf",
     "two work topics, each with a dead-letter topic after 5 failed deliveries and a subscription that keeps "
     "dead-lettered messages for 7 days. The Pub/Sub service agent needs publish on the DLQ and subscribe on "
     "the source for dead-lettering to work. Step 2.5 switches the subscriptions to push."),
    ("firestore.tf",
     "the Native-mode `(default)` database in `us-east1` with point-in-time recovery and delete protection. "
     "The location cannot be changed after creation."),
    ("secrets.tf", "empty secret containers; values are added by `alloydb.tf` and by hand (Step 5.10)."),
    ("bigquery.tf", "the three datasets in `us-east1`."),
    ("network.tf",
     "the VPC, a subnet with Private Google Access, the Private Services Access range AlloyDB uses, Cloud NAT "
     "for outbound traffic, and two firewall rules: egress from the subnet to the AlloyDB range is allowed on "
     "**5432 and 5433** only (5433 is the port the AlloyDB connectors and Auth Proxy use), everything else to "
     "that range is denied."),
    ("alloydb.tf",
     "the AlloyDB cluster and primary, created only when `enable_alloydb = true`. The admin password is random "
     "and stored in Secret Manager; backups run daily and are kept 14 days; IAM login is enabled."),
    ("iam.tf",
     "least-privilege roles per service, generated from small tables so a service missing from `services` "
     "simply gets no bindings. Every deployed agent also gets log, trace and quota-consumer roles, and write "
     "access to the artifacts bucket (ADK's artifact service, `LOGS_BUCKET_NAME`)."),
    ("outputs.tf", "service-account emails, bucket, topic and subscription names, network names. The `search` "
                   "output is added in Step 2.3."),
]
for name, explain in module:
    path = f"infra/terraform/modules/firewatch/{name}"
    add(embed(path, explain, transform=drop_search_output if name == "outputs.tf" else None))

add("""
4. **[Cloud]** Apply:

   ```bash
   cd infra/terraform/envs/dev
   terraform init
   terraform plan -out=dev.tfplan
   terraform apply dev.tfplan
   terraform plan          # "No changes." : the guide's done-when for this step
   cd ../../../..
   ```

**Check:** the second `plan` prints `No changes`. Edit a label on a bucket in the console and plan again:
Terraform shows the drift.

**If it fails**

- `Saved plan is stale`: something changed state after the plan (often a failed earlier apply that
  created part of the resources). Run `terraform plan -out=dev.tfplan` again and apply the new plan.
- `SERVICE_DISABLED` naming a project number that is not yours: the `providers.tf` override is missing,
  or ADC has no quota project (Step 0.3).

### Step 1.7 Networking to AlloyDB

**Why:** only services that need AlloyDB can reach it, and only over private IP.

**Diagram**

```text
 Cloud Run service/job with Direct VPC egress ──▶ firewatch-vpc / subnet 10.10.0.0/24
                                                    │ firewall: egress to PSA range only on 5432, 5433
                                                    ▼
                                    Private Services Access peering ──▶ AlloyDB primary (private IP)
 Agent Runtime agents ──✗ (no VPC)   they reach journalist data only through the media-matcher A2A service
```

*How to read it:* the network pieces already exist from `network.tf`. A Cloud Run service joins the VPC
at deploy time (`--network firewatch-vpc --subnet firewatch-us-east1 --vpc-egress private-ranges-only`)
and connects with the AlloyDB Python connector using IAM login. Agent Runtime stays outside the VPC by
design.

**Check:** the guide's test (a job with VPC egress runs `SELECT 1`, the same job without it fails) needs
AlloyDB running, which starts billing, so it is done at the start of Phase 4 (Step 4.1, action 3).

### Step 1.8 Firestore rules and indexes

**Why:** the browser reads some Firestore data directly (the live campaign timeline). Rules decide what a
signed-in user may read; all writes go through the BFF's Admin SDK, which bypasses rules.

""")
add(embed("firebase.json", "tells the Firebase CLI where the rules and indexes are, and the emulator port."))
add(embed("firestore/firestore.rules",
          "users read only their own org's campaigns, using the `org_id` claim in their sign-in token (set in Step 1.9). "
          "Documents under a campaign (runs, steps, drafts) are checked against the parent campaign's `org_id`, "
          "because child documents do not carry it. Browsers can never write. A member can read their own membership. "
          "Anything not matched is denied. Differences from the guide: the org comes from the token, not a "
          "`users/{uid}` document that nothing creates, and subcollections check the parent."))
add(embed("firestore/firestore.indexes.json",
          "composite indexes for the queries the app runs. The guide's `steps(started_at)` is left out: single-field "
          "indexes are automatic, and this file only accepts multi-field ones."))
add(embed("firestore/tests/package.json", "the rules test project (Node 22 in a container, so the host Node version does not matter)."))
add(embed("firestore/tests/rules.test.js",
          "14 tests against the emulator: own-org reads succeed; another org, signed-out users and unfiltered list "
          "queries fail; browsers cannot write campaigns, steps or their own role; closed collections stay closed. "
          "The `PERMISSION_DENIED` lines printed during the run are the expected denials."))
add(embed("firestore/.gitignore", "ignores the tests' `node_modules`."))
add("""
**[Local]** `make test-rules` (starts the emulator if needed, then runs the tests in a `node:22` container).
Commit the generated `firestore/tests/package-lock.json`.

**Check:** `Tests  14 passed (14)`. Deploying the rules needs Firebase added to the project, which
happens in Step 1.9.

### Step 1.12 CI/CD (single project)

**Why:** every change is checked on a pull request, only for the parts it touches, and merged changes
deploy themselves. The guide's `agents-cli infra cicd` needs separate staging and prod projects (with one
project its two environments create identical resource names and fail), so this repo defines its own
Cloud Build triggers.

**Diagram**

```text
 PR to main ──▶ Cloud Build trigger (path filter)          push to main ──▶ deploy trigger (path filter)
   agents/judge/**         ─▶ pr-judge      (agent-pr.yaml)   agents/<a>/**   ─▶ deploy-<a> (agent-deploy.yaml, --update-only)
   apps/web/**             ─▶ pr-web        (web-pr.yaml)     apps/web/**     ─▶ deploy-web (Step 1.10b)
   infra/**, cloudbuild/** ─▶ pr-infra      (infra-pr.yaml)   workers/<w>/**  ─▶ deploy-<w> (Step 2.5)
   firestore/**            ─▶ pr-firestore  (firestore-pr.yaml)
 all builds run as sa-cloudbuild; logs go to Cloud Logging
```

*How to read it:* one trigger per component, each with an `included_files` filter, so a PR touching only
`agents/judge` runs only `pr-judge` (the guide's done-when). Shared pipeline files take the component as a
substitution (`_SERVICE`) instead of one copy per agent, and each step runs inside `agents/<name>` because
Cloud Build starts at the repo root.

**Actions**

1. **[Cloud]** Connect GitHub to Cloud Build (browser, once): Console → Cloud Build → **Repositories**
   → **2nd gen** → *Create host connection*: GitHub, region **us-east1**, name `github-firewatch`;
   authorise and install the Cloud Build GitHub App on `vanthuan/firewatch-gcp` only; then *Link repository*
   (`vanthuan-firewatch-gcp`). Check:

   ```bash
   gcloud builds repositories list --connection=github-firewatch --region=us-east1
   ```

2. **[Repo]** Pipeline files:

""")
for path, explain in [
    ("cloudbuild/agent-pr.yaml",
     "PR checks for one agent: install with the workspace lock, check the agent's **own** `uv.lock` is current "
     "(the Docker build uses it), lint with agents-cli, unit and integration tests. Step 2.6a adds a vendor step, "
     "Step 3.10 an eval step."),
    ("cloudbuild/agent-deploy.yaml",
     "deploys one agent with `agents-cli deploy --update-only`: CI can only update an existing engine or "
     "service, never create a duplicate (the first deploy of each agent is manual). The runtime identity and "
     "logs bucket come from trigger substitutions."),
    ("cloudbuild/web-pr.yaml", "PR checks for the web app. Step 1.10 replaces it with a version that installs at the workspace root."),
    ("cloudbuild/infra-pr.yaml",
     "`terraform fmt -check`, `validate` and a read-only `plan` (`-lock=false`, so a PR never blocks a real apply)."),
    ("cloudbuild/firestore-pr.yaml",
     "starts the Firestore emulator as a detached container on Cloud Build's `cloudbuild` network, then runs the rules tests against it."),
]:
    add(embed(path, explain))
add("\n3. **[Repo]** The CI/CD module and its use:\n\n")
for path, explain in [
    ("infra/terraform/modules/cicd/variables.tf", "inputs: the linked repository, branch, and one entry per agent (runtime identity, logs bucket, deploy on/off)."),
    ("infra/terraform/modules/cicd/main.tf",
     "the build service account `sa-cloudbuild` with the roles the agents-cli CI uses plus read-only roles for "
     "`terraform plan`; act-as permission on each agent's runtime identity only; a PR trigger and a deploy "
     "trigger per agent; PR triggers for web, infra and Firestore. PRs from outside contributors need a "
     "`/gcbrun` comment from a maintainer before they run."),
    ("infra/terraform/modules/cicd/outputs.tf", "the build account and the trigger names (disabled ones marked)."),
    ("infra/terraform/envs/dev/cicd.tf",
     "wires the module. Only `deploy-orchestrator` starts enabled (its engine exists from Step 1.5); the others "
     "are switched on after each agent's first manual deploy. The orchestrator keeps the identity agents-cli "
     "gave it until Step 3.0."),
]:
    add(embed(path, explain))
add("""
   Add to `infra/terraform/envs/dev/outputs.tf`:

   ```hcl
   output "cicd" {
     description = "Cloud Build service account and triggers"
     value       = module.cicd
   }
   ```

4. **[Cloud]** Apply (`terraform init` again because a module was added), then push:

   ```bash
   cd infra/terraform/envs/dev && terraform init && terraform plan -out=dev.tfplan && terraform apply dev.tfplan && cd -
   git add -A && git commit -m "Foundation: monorepo, Terraform, CI" && git push -u origin main
   ```

**Check:** open a PR that changes one line in `agents/judge`: Cloud Build → History (region us-east1)
shows only `pr-judge` (merge the CI files first, or this first PR also runs `pr-infra`).

""")

# ---------------------------------------------------------------------------------------------
phase1 = section("### Step 1.9 Identity and roles", "## Phase 2: Knowledge")
phase1 = phase1.replace("redo Step 0.2.", "redo Step 0.3.")
phase1 = phase1.replace(
    "**Why:** every later UI step adds pages to this frame. It also fixes the `pr-web` pipeline, which fails\ntoday because dependencies are missing.",
    "**Why:** every later UI step adds pages to this frame, and `pr-web` needs a buildable app.")
create_app = """**Create the app first**

1. **[Local]** From the repo root:

   ```bash
   cd apps && pnpm create next-app@latest web --ts --tailwind --app --eslint && cd web
   pnpm dlx shadcn@latest init
   pnpm dlx shadcn@latest add button
   cd ../..
   ```

   *What this does:* creates the Next.js app (App Router, TypeScript, Tailwind) and shadcn/ui, whose
   `Button` the pages below use. create-next-app writes its own `pnpm-workspace.yaml` and lockfile inside
   `apps/web`; action 1 below moves both to the root.

   > Run every `pnpm add` for the web app with `--filter web` from the root (or inside `apps/web`).
   > Running it at the repo root without a filter adds the libraries to the root `package.json` instead
   > (and picks zod 4, which the generated schemas do not use).

"""
phase1 = phase1.replace("**Diagram**\n\n```text\n repo root (pnpm workspace)", create_app + "**Diagram**\n\n```text\n repo root (pnpm workspace)", 1)
phase1 = phase1.replace(
    "   Also commit an `apps/web/.env.example` with the same keys and empty values.",
    "   Also commit an `apps/web/.env.example` with the same keys and empty values. (If you follow the\n"
    "   build order, the web app is created in Step 1.10; create `apps/web/` now for this file, or come back to\n"
    "   actions 5 to 11 after 1.10's first action.)")
add("## Phase 1 (continued): identity, web app, first deploy\n\n")
add(phase1)

# ---------------------------------------------------------------------------------------------
add("""
---

## Phase 2: Knowledge

Order: **2.1 → 2.2 → 2.3 → 2.4 → 2.7a → 2.5 → 2.6 → 2.7b → 2.8**. The Model Armor templates (2.7a) come
before the ingest worker because the worker screens every file with them.

### Step 2.1 Shared models (Python first, TypeScript generated)

**Why:** agents, workers and the web app must agree on the shape of a fact sheet, a verdict, a claim
check. The Pydantic models are the source; the zod schemas the web app uses are generated from them.

**Diagram**

```text
 packages/shared-py/firewatch_shared/models.py  ──export_schema.py──▶  packages/shared-ts/schema.json
                                                                        │ generate.mjs (per model)
                                                                        ▼
                                                  packages/shared-ts/src/schemas.ts  (zod + TS types)
```

""")
for path, explain in [
    ("packages/shared-py/pyproject.toml", "makes the folder a workspace package (`firewatch-shared`) that agents and workers can use."),
    ("packages/shared-py/firewatch_shared/__init__.py", "marks the package (empty)."),
    ("packages/shared-py/firewatch_shared/models.py",
     "the guide's models. `EXPORTED_MODELS` lists what is exported to TypeScript. Step 2.8 adds a `field` to "
     "`Citation` and the `ApprovalDecision` model."),
    ("packages/shared-py/firewatch_shared/export_schema.py",
     "prints one JSON Schema with every exported model under `$defs`."),
    ("packages/shared-ts/package.json", "the TypeScript package `@firewatch/shared-ts`; its entry is the generated `src/schemas.ts`."),
    ("packages/shared-ts/generate.mjs",
     "converts each `$def` separately, with references inlined, into one zod schema and one inferred type per "
     "model. The guide's single `json-schema-to-zod` call only converts the root, which here is empty, so it "
     "produced `z.any()` (B8)."),
    ("packages/shared-ts/.gitignore", "ignores `node_modules`."),
]:
    add(embed(path, explain))
add("""
**[Local]** From the **repo root** (the paths in the commands are relative to it):

```bash
make schemas
```

which runs `uv run --package firewatch-shared python -m firewatch_shared.export_schema > packages/shared-ts/schema.json`
and then `generate.mjs` in a `node:22` container. `--package` is needed because the root is not itself a
Python package. Commit `schema.json` and `src/schemas.ts`.

**Check:** `src/schemas.ts` exports `CitationSchema`, `ProductFactSheetSchema`, … and their types;
`npx -p typescript tsc --noEmit --strict --skipLibCheck packages/shared-ts/src/schemas.ts` passes.

**If it fails:** `bash: packages/shared-ts/schema.json: No such file or directory`: you ran it from
another folder; `cd` to the repo root.

### Step 2.2 Seed data

**Why:** `make seed` on a fresh project gives a usable demo in one command: briefs to upload, a catalog,
journalists and swatch images, all synthetic (fake names, `example.com` emails).

**Diagram**

```text
 tools/make_seed_assets.py ──▶ data/seed/{catalog.csv, journalists.csv, articles.csv, swatches/*.png, briefs/*.pdf}
                                  (deterministic: re-running gives identical files; commit them)
 tools/seed.py (make seed)
   gcs    ─▶ gs://…-briefs/demo-org/seed-NN/*.pdf, gs://…-assets/swatches/*.png
   db     ─▶ products, journalists, articles in DATABASE_URL (local pgvector; AlloyDB from a VPC job, Step 4.1)
   search ─▶ gs://…-artifacts/catalog/products.jsonl → Vertex AI Search catalog (Step 2.3)
```

""")
for path, explain in [
    ("tools/make_seed_assets.py",
     "generates all seed files. The five briefs are real PDFs with a feature list, a spec table and a swatch "
     "image (so the layout parser has text, tables and images to work on), and their prices and coverage "
     "match `catalog.csv` exactly: they are the answer key for the extraction eval (Step 2.8). Every 8th "
     "journalist has opted out. `invariant=True` makes the PDFs byte-identical across runs."),
    ("tools/sql/schema.sql",
     "the Step 4.1 tables for local development, until Alembic migrations take over in Step 4.1 (which also "
     "switches to 1536 dimensions, ADR 0004)."),
    ("tools/seed.py",
     "loads everything, idempotently: uploads overwrite, products upsert on SKU, journalists upsert on email "
     "(and never clear an opt-out), articles are replaced per seeded journalist. The `search` part stages the "
     "catalog JSONL and starts imports when the datastores exist (Step 2.3); until then it prints `skipped`. "
     "Step 2.5 removes the brief import from here, because uploads then trigger ingestion."),
]:
    add(embed(path, explain))
add("""
**[Local]**

```bash
make seed-assets     # writes data/seed (commit it)
make seed            # starts local services, then loads everything
```

**Check:** the output lists 5 briefs, 12 swatches, `12 products, 40 journalists, 80 articles`; a second
`make seed` gives the same counts.

### Step 2.3 Vertex AI Search datastores

**Why:** the advisor and the extractor search the product catalog; knowledge Q&A searches uploaded
documents with layout-aware parsing (tables, images, page spans).

**Diagram**

```text
 catalog (structured, NO_CONTENT)   ◀─ products.jsonl import (FULL)      ─▶ app "catalog-search" (standard tier)
 kb (unstructured, CONTENT_REQUIRED) ◀─ PDFs, layout parser + chunking    ─▶ app "kb-search" (enterprise tier)
          Discovery Engine service agent reads the artifacts, briefs and kb buckets for imports
```

*How to read it:* datastores hold documents; apps (search engines) are what you query and what the
console's **Preview** tab uses. Vertex AI Search only offers `global`, `us` and `eu`; this project uses
`global`.

""")
add(embed("infra/terraform/modules/firewatch/search.tf",
          "the two datastores and two apps. `kb` parses documents with the layout parser, lets Gemini annotate "
          "tables and images, and splits them into 500-token chunks that keep their headings. The enterprise tier "
          "on `kb-search` returns the passages behind results, which citations need. Imports from GCS run as the "
          "Discovery Engine service agent, so it gets read access to the three source buckets."))
add("**[Repo]** Add to `infra/terraform/modules/firewatch/outputs.tf`:\n\n```hcl\n" + only_search_output("infra/terraform/modules/firewatch/outputs.tf") + "\n```\n\n")
add("""*What this does:* exposes the datastore names (for `VertexAiSearchTool(data_store_id=…)` and the chunk
search helper) and the app IDs (for the console and queries).

**[Cloud]**

```bash
cd infra/terraform/envs/dev && terraform plan -out=dev.tfplan && terraform apply dev.tfplan && cd -
uv run tools/seed.py --only search      # imports the catalog (and, until Step 2.5, the briefs)
```

Imports run in the background: the catalog takes a minute or two, briefs longer (each page goes
through the layout parser).

**Check**

```bash
curl -s -X POST -H "Authorization: Bearer $(gcloud auth print-access-token)" -H "x-goog-user-project: $P" \\
  -H "Content-Type: application/json" \\
  "https://discoveryengine.googleapis.com/v1/projects/$P/locations/global/collections/default_collection/engines/catalog-search/servingConfigs/default_search:search" \\
  -d '{"query":"sage matte paint","pageSize":3}' | python3 -m json.tool | head -30
```

returns `ECO-MAT-SAGE` ($54.99, 12 m²/L). The same query to `kb-search` with "what is the promotion for
EcoGreen" returns `01-ecogreen-interior-matte.pdf`. In the console: AI Applications → Apps → each app →
**Preview**.

**If it fails**

- `Error 403 … requires a quota project … SERVICE_DISABLED` during `apply`: see Step 1.6's providers and
  Step 0.3. A failed apply leaves part of the resources created; re-plan before applying again.
- Empty results right after seeding: the import is still running; poll the operation name the seed
  printed (`GET https://discoveryengine.googleapis.com/v1/<operation>`).

""")

rest = section("### Step 2.4 Signed uploads", None)
rest = rest.replace("(Step 0.3)", "(Step 0.4)")
add(rest)

text = "".join(parts)
fences = len(re.findall(r"^\s*```", text, re.M))
OUT.write_text(text)
print(f"wrote {OUT} ({text.count(chr(10))} lines, {fences} fence lines, {'balanced' if fences % 2 == 0 else 'UNBALANCED'})")
