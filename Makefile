.PHONY: up down install migrate revision api capture check lint type test clean

up:
	docker compose up -d

down:
	docker compose down

install:
	poetry install
	poetry run playwright install chromium

migrate:
	poetry run alembic upgrade head

revision:
	poetry run alembic revision --autogenerate -m "$(msg)"

api:
	poetry run uvicorn adspy.api.app:app --reload --port 8000

worker:
	poetry run python -m adspy.queue.worker

# Interactive Playwright session capture for non-Graph-API sources (X / TikTok / etc.).
capture:
	poetry run python -m adspy.scrapers.capture_replay capture --platform $(platform)

check: lint type test

lint:
	poetry run ruff check adspy tests
	poetry run ruff format --check adspy tests

type:
	poetry run mypy adspy

test:
	poetry run pytest

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache
