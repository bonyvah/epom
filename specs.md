**Theme:** Project management / profiles dashboard — a service to create, update, share, and delete project information (details + attached documents).

**Stack:** Python 3.12+, FastAPI, PostgreSQL, SQLAlchemy, Docker, AWS S3 (file storage), AWS Lambda (image processing, file size calculations on S3 events), CI/CD via GitHub Actions.

### Scope — Phase 1

**Core functionality:**

- User registration & login (JWT, 1-hour expiry)
- Create / delete projects (owner-only delete)
- Update project details (name, description)
- Upload / update / delete documents (docx, pdf) per project
- Share project with other users (owner invites → participant access)

**Access model:** 2 roles — **owner** (full access, can delete) and **participant** (can modify, cannot delete).

**API endpoints:**

| Method | Endpoint | Description |
| --- | --- | --- |
| POST | /auth | Register user (login, password, repeat password) |
| POST | /login | Login → returns JWT |
| POST | /project | Create project (auto-assigns owner) |
| GET | /projects | List all accessible projects (full info) |
| GET | /project/<id\>/info | Get project details |
| PUT | /project/<id\>/info | Update project name/description |
| DELETE | /project/<id\> | Delete project + documents (owner only) |
| GET | /project/<id\>/documents | List project documents |
| POST | /project/<id\>/documents | Upload document(s) |
| GET | /document/<id\> | Download document |
| PUT | /document/<id\> | Update document |
| DELETE | /document/<id\> | Delete document |
| POST | /project/<id\>/invite | Grant access to a user (owner only) |
| POST | /project/<id\>/share?email=<email\> | send a join link with hashed token to an email. |

### Scope — Phase 2

- DB normalization / denormalization
- DB creation with and without ORM
- S3 + Lambda: image resize (optional), calculate total file size per project + apply limit
- Tests + CI/CD bindings
- Package setup: pyproject.toml, tox / poetry
- Pydantic validation on all inputs

### Implementation notes

1. All responses in JSON (except file downloads) + correct HTTP status codes.
2. All business logic endpoints must be authorized via JWT.