# LaunchPad monorepo tasks. Run `make help` for the list.
# Recipes must be indented with a TAB, not spaces.

AGENT  ?= orchestrator                 # agent for `make dev` / `make playground`, e.g. make dev AGENT=advisor
PORT   ?= 8501                         # playground port
AGENTS := $(notdir $(wildcard agents/*))

AGENT := $(strip $(AGENT))
PORT  := $(strip $(PORT))

.DEFAULT_GOAL := help
.PHONY: help install up down reset logs ps dev playground web lock test-rules

help:  ## Show this help
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-12s %s\n", $$1, $$2}'
	@echo "  Agents: $(AGENTS)"

install:  ## Install Python deps for the whole workspace (and web deps if apps/web exists)
	uv sync --all-packages
	@if [ -f apps/web/package.json ]; then cd apps/web && pnpm install; fi

up:  ## Start Postgres, Firestore and Pub/Sub emulators
	docker compose up -d --wait

down:  ## Stop the local services (keeps containers' data until removed)
	docker compose down

reset:  ## Stop the local services and delete their data
	docker compose down -v

logs:  ## Follow the local services' logs
	docker compose logs -f

ps:  ## Show the local services
	docker compose ps

playground:  ## Run the ADK playground for AGENT (default: orchestrator)
	cd agents/$(AGENT) && agents-cli playground --port $(PORT)

web:  ## Run the Next.js dev server
	@if [ ! -f apps/web/package.json ]; then echo "apps/web not created yet (Step 1.10)"; exit 1; fi
	cd apps/web && pnpm dev

dev: up  ## Start local services, the web app (if present) and the AGENT playground; Ctrl+C stops both
	@trap 'kill 0' INT TERM EXIT; \
	if [ -f apps/web/package.json ]; then (cd apps/web && pnpm dev) & \
	else echo "apps/web not created yet, skipping the web app"; fi; \
	(cd agents/$(AGENT) && agents-cli playground --port $(PORT)) & \
	wait

lock:  ## Refresh the root uv.lock and each agent's own uv.lock (used by its Dockerfile)
	uv lock
	@for a in $(AGENTS); do \
	  tmp=$$(mktemp -d) && \
	  cp agents/$$a/pyproject.toml agents/$$a/README.md $$tmp/ && \
	  cp agents/$$a/uv.lock $$tmp/ 2>/dev/null; \
	  (cd $$tmp && uv lock -q) && cp $$tmp/uv.lock agents/$$a/uv.lock && echo "locked $$a"; \
	  rm -r "$$tmp"; \
	done

test-rules: up  ## Test firestore/firestore.rules against the emulator (runs in a node:22 container)
	docker run --rm --network host -u $$(id -u):$$(id -g) -e HOME=/tmp \
	  -v "$(CURDIR)/firestore":/w -w /w/tests node:22 \
	  sh -c "npm ci --no-audit --no-fund --loglevel=error && npm test"
