# CodeAtlas

CodeAtlas is an AI-powered codebase intelligence platform designed to help developers understand repositories, explore code relationships, and make better engineering decisions.

## Current Status

Sprint 0 — Foundation

Implemented:
- FastAPI application
- Root endpoint
- Health endpoint
- Interactive API documentation
- Automated endpoint tests

## Technology Stack

- Python
- FastAPI
- Uvicorn
- pytest
- HTTPX

## Prerequisites

- Python 3.12 recommended
- Git (recommended)
- Visual Studio Code (recommended)

## Local Setup — Windows PowerShell

Run these commands from the project root.

### 1. Create a virtual environment

```powershell
python -m venv .venv
```

### 2. Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script activation, use an approved execution-policy approach for your environment rather than disabling security controls globally.

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Start the development server

```powershell
python -m uvicorn app.main:app --app-dir backend --reload
```

The API will be available at:

http://127.0.0.1:8000

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Returns application information |
| GET | `/health` | Returns a basic application health response |

## Interactive API Documentation

Open:

http://127.0.0.1:8000/docs

## Running Tests

Run the automated test suite from the project root:

```powershell
python -m pytest backend/tests -v
```

The current baseline contains three endpoint tests.

## Current Limitations

- The health endpoint does not yet check external dependencies.
- No database or repository ingestion pipeline is implemented yet.
- Authentication and authorization are not implemented yet.
- AI features are not implemented yet.

## Development Principles

- Build incrementally, one Scrum story at a time.
- Keep the architecture simple and modular.
- Add automated tests alongside new behavior.
- Never execute untrusted repository code as part of code analysis.
- Document architectural decisions when they become relevant.

## License

License and distribution terms have not yet been selected.