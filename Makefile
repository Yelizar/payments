include .env

build: # Build docker images
	docker compose --project-directory . build

up: # Start docker containers
	docker compose --project-directory . up -d

down: # Stop docker containers
	docker compose --project-directory . down

restart: down up # Down and up docker containers
rebuild: down build up # Rebuild docker images and restart containers

format: # Format Python code and sort imports
	uv run black src
	uv run isort src

format-check: # Check formatting and import order without modifying files
	uv run black --check src
	uv run isort --check-only src

typecheck: # Run static type checking
	uv run mypy

check: format-check typecheck # Run all code quality checks

