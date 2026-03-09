.PHONY: up down build logs test lint migrate seed clean

# Start all services
up:
	docker compose up -d --build

# Stop all services
down:
	docker compose down

# Rebuild images
build:
	docker compose build

# View logs (follow mode)
logs:
	docker compose logs -f

# View specific service logs
logs-%:
	docker compose logs -f $*

# Run database migrations
migrate:
	docker compose run --rm migrate

# Run backend tests
test:
	cd backend && pip install -e ".[dev]" && pytest --cov=app --cov=workers --cov-report=term -v

# Run linting
lint:
	cd backend && pip install -e ".[dev]" && black --check . && isort --check-only . && flake8 .

# Format code
format:
	cd backend && black . && isort .

# Seed development data
seed:
	docker compose exec api python scripts/seed_data.py

# Remove all volumes and containers
clean:
	docker compose down -v --remove-orphans

# Shell into the API container
shell:
	docker compose exec api bash

# Check health of all services
health:
	@echo "API:" && curl -s http://localhost:8000/api/v1/health | python3 -m json.tool || echo "API: DOWN"
	@echo "\nReadiness:" && curl -s http://localhost:8000/api/v1/health/ready | python3 -m json.tool || echo "Readiness: DOWN"

# Open Flower dashboard
flower:
	open http://localhost:5555

# Open API docs
docs:
	open http://localhost:8000/docs
