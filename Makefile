.PHONY: help install dev test lint format migrate docker-up docker-down docker-build k8s-deploy clean

help:
	@echo "LLMOps Gateway AI - Make commands"
	@echo "  make install      Install Python dependencies"
	@echo "  make dev          Run the API locally with reload"
	@echo "  make test         Run the full test suite with coverage"
	@echo "  make lint         Run ruff + mypy"
	@echo "  make format       Auto-format code with black + ruff"
	@echo "  make migrate      Run Alembic database migrations"
	@echo "  make migrate-new  Create a new Alembic migration (use msg='...')"
	@echo "  make docker-up    Start full stack with docker-compose"
	@echo "  make docker-down  Stop all docker-compose services"
	@echo "  make docker-build Build the production Docker image"
	@echo "  make k8s-deploy   Apply Kubernetes manifests"
	@echo "  make clean        Remove caches and build artifacts"

install:
	pip install -r requirements.txt --break-system-packages
	pre-commit install

dev:
	uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v --cov=backend --cov-report=term-missing --cov-report=html

lint:
	ruff check backend/ tests/
	mypy backend/ --ignore-missing-imports --no-strict-optional

format:
	black backend/ tests/
	ruff check --fix backend/ tests/

migrate:
	alembic upgrade head

migrate-new:
	alembic revision --autogenerate -m "$(msg)"

migrate-down:
	alembic downgrade -1

docker-up:
	docker-compose up -d --build
	@echo "API:        http://localhost:8000/docs"
	@echo "Prometheus: http://localhost:9090"
	@echo "Grafana:    http://localhost:3000 (admin / llmops_grafana)"

docker-down:
	docker-compose down

docker-down-volumes:
	docker-compose down -v

docker-build:
	docker build -t llmops-gateway-ai:latest --target production .

docker-logs:
	docker-compose logs -f api

k8s-deploy:
	kubectl apply -f infrastructure/kubernetes/deployment.yaml

k8s-status:
	kubectl get all -n llmops

terraform-init:
	cd infrastructure/terraform && terraform init

terraform-plan:
	cd infrastructure/terraform && terraform plan

terraform-apply:
	cd infrastructure/terraform && terraform apply

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov .mypy_cache .ruff_cache
