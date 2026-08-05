.PHONY: dev down down-test test migrate migration build-lambda

build:
	docker compose up --build -d
	@echo "→ API ready at http://localhost:8000/docs"

up:
	docker compose up -d
	@echo "→ API ready at http://localhost:8000/docs"

down:
	docker compose down

logs:
	docker compose logs -f

shell:
	docker compose exec api sh