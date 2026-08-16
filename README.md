# EPOM — Effective PrOject Management

A REST API for creating, managing, and sharing projects with document attachments.
Built with FastAPI and PostgreSQL, fully containerized with Docker.

## Tech Stack

- **Python 3.12** / FastAPI
- **PostgreSQL 16**
- **SQLAlchemy 2** + Alembic
- **Docker** / Docker Compose

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/)
- [Make](https://www.gnu.org/software/make/)

## Getting Started

**1. Set up environment variables**
```bash
cp .env.example .env
```
Open `.env` and fill in your values.

**2. Build and start**
```bash
make build
```

Migrations run automatically on startup. Once ready:

- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs

## Running Tests

The integration tests depend on a test database running on port `5433` (managed by Docker Compose). To start the database container and run the tests, execute:

```bash
make test
```

Alternatively, you can run `tox` directly to run testing/linting in isolated virtual environments.

## Make Commands

| Command | Description |
|---|---|
| `make build` | Build images and start all services |
| `make up` | Start services without rebuilding |
| `make down` | Stop and remove containers |
| `make logs` | Tail live logs |
| `make shell` | Open a shell inside the API container |
| `make test` | Run the pytest test suite (spins up `db_test` container automatically) |

## Limitations & Stub Features

- **Virus Scanner Simulation**: The virus scanner (implemented in `lambda/handler.py`) is a demonstration stub. It randomly clean-marks or quarantines uploaded documents to simulate scanning behavior, and does not perform actual contents scanning. For a real production environment, a service like ClamAV running as a container or an S3 quarantine bucket workflow should be integrated.