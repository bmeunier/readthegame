.PHONY: setup-dev test fmt lint up down seed api run e2e

setup-dev:
	python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

fmt:
	black src tests
	ruff check src tests --fix

lint:
	ruff check src tests
	black --check src tests

test:
	pytest -q

up:
	docker compose up -d

down:
	docker compose down -v

api:
	uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload

run:
	python src/main.py run --from rss --to output --episode "$(EP)" || true

e2e:
	pytest -q -k "e2e"