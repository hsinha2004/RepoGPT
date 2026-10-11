.PHONY: setup doctor dev up down logs ps models seed test test-backend test-frontend e2e lint fmt typecheck gen-api eval eval-report build prod-up backup restore ollama-pull clean

PYTHON ?= python
NPM ?= npm

setup:
	$(PYTHON) scripts/generate_secrets.py
	-pre-commit install

doctor:
	$(PYTHON) scripts/doctor.py

dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

models:
	$(PYTHON) -m app.scripts.download_models

seed:
	$(PYTHON) -m app.scripts.seed

test: test-backend test-frontend

test-backend:
	cd backend && $(PYTHON) -m pytest tests -v --cov=app --cov-report=term-missing

test-frontend:
	cd frontend && $(NPM) test

e2e:
	cd frontend && $(NPM) run test:e2e

lint:
	cd backend && $(PYTHON) -m ruff check app tests
	cd frontend && $(NPM) run lint

fmt:
	cd backend && $(PYTHON) -m ruff format app tests
	cd frontend && $(NPM) run format

typecheck:
	cd backend && $(PYTHON) -m mypy app
	cd frontend && $(NPM) run typecheck

gen-api:
	$(PYTHON) backend/app/scripts/export_openapi.py
	cd frontend && $(NPM) run gen:api

eval:
	$(PYTHON) -m app.services.eval.cli run --benchmark eval/benchmarks/sample_repo.yaml --strategies all --generate

eval-report:
	$(PYTHON) -m app.services.eval.cli report --out docs/report/results/

build:
	docker compose build

prod-up:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

backup:
	bash deploy/backup.sh

restore:
	bash deploy/restore.sh

ollama-pull:
	docker compose exec ollama ollama pull qwen2.5-coder:7b-instruct

clean:
	@echo "Cleaning caches and artifacts..."
	-rm -rf backend/.pytest_cache backend/.mypy_cache backend/.ruff_cache backend/htmlcov backend/.coverage
	-rm -rf frontend/dist frontend/node_modules/.vite
	@echo "Clean complete."
