.PHONY: up down install migrate revision api worker check lint type test clean

up:
	docker compose up -d

down:
	docker compose down

install:
	poetry install

migrate:
	poetry run alembic upgrade head

revision:
	poetry run alembic revision --autogenerate -m "$(msg)"

api:
	poetry run uvicorn adspy.api.app:app --reload --port 8000

worker:
	poetry run celery -A adspy.workers.app worker --loglevel=info

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
