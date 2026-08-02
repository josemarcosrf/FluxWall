# Justfile - FluxWall Task Runner

default: help

# ─── Development ──────────────────────────────────────────────
dev:
	uv run python scripts/dev_server.py

api:
	uv run uvicorn fluxwall.main:app --reload --port 8000

ui:
	uv run streamlit run src/fluxwall/streamlit_app.py --server.port 8501

# ─── Code Quality ─────────────────────────────────────────────
fmt:
	uv run ruff format src tests

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src

check: fmt lint typecheck

# ─── Testing ──────────────────────────────────────────────────
test:
	uv run pytest tests -v

test-cov:
	uv run pytest tests --cov=fluxwall --cov-report=term-missing

# ─── Webapp (React) ──────────────────────────────────────────
webapp-install:
	cd webapp && npm install

webapp-dev:
	cd webapp && VITE_API_BASE=http://localhost:8000 npm run dev

webapp-build:
	cd webapp && npm run build

webapp-check:
	cd webapp && npx tsc -b

webapp-preview:
	cd webapp && npm run preview

# ─── Export / Build ───────────────────────────────────────────
export-presets:
	uv run python scripts/export_presets.py --all --output ./exports

export-preset name="gosper_gun":
	uv run python scripts/export_presets.py --preset {{name}} --output ./exports

# ─── Docker / Deploy ──────────────────────────────────────────
docker-build:
	docker build -t fluxwall:latest .

docker-run:
	docker run -p 8000:8000 -p 8501:8501 fluxwall:latest

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