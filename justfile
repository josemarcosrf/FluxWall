# Justfile - FluxWall Task Runner

# Set the working directory for Python/uv commands.
set working-directory := "backend"

default: help

# ─── Development ──────────────────────────────────────────────
dev:
	uv run python scripts/dev_server.py

api:
	uv run uvicorn fluxwall.main:app --reload --port 8000

ui:
	uv run streamlit run src/fluxwall/streamlit_app.py --server.port 8501

# ─── Code Quality ─────────────────────────────────────────────
format:
	uv run ruff format src tests

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src

check: format lint typecheck

# ─── Testing ──────────────────────────────────────────────────
test:
	uv run pytest tests -v

test-cov:
	uv run pytest tests --cov=fluxwall --cov-report=term-missing

# ─── Frontend (React) ─────────────────────────────────────────
frontend-install:
	cd ../frontend && npm install

frontend-dev:
	cd ../frontend && VITE_API_BASE=http://localhost:8000 npm run dev

frontend-build:
	cd ../frontend && npm run build

frontend-check:
	cd ../frontend && npx tsc -b

frontend-preview:
	cd ../frontend && npm run preview

# ─── Export / Build ───────────────────────────────────────────
export-presets:
	uv run python scripts/export_presets.py --all --output ./exports

export-preset name="gosper_gun":
	uv run python scripts/export_presets.py --preset {{name}} --output ./exports

# ─── Docker / Deploy ──────────────────────────────────────────
docker-build:
	docker compose build

docker-up:
	docker compose up

docker-run: docker-build
	docker compose up -d

docker-api:
	docker compose up api

docker-frontend:
	docker compose up frontend

deploy:
	railway up --detach

deploy-prod:
	railway up --environment production --detach

# ─── Utilities ────────────────────────────────────────────────
clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache dist build *.egg-info

install:
	uv sync --all-extras

update-deps:
	uv lock --upgrade

help:
	@just --list
