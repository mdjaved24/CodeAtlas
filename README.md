# CodeAtlas

**AI-powered codebase intelligence for understanding unfamiliar repositories.**

CodeAtlas is being built to help developers understand large or unfamiliar codebases faster. The long-term goal is to combine source-code structure, repository context, and AI-assisted analysis to make onboarding, code discovery, and change-impact investigation easier.

> **Development status:** Early development — Sprint 1 completed through CA-008. Source-code parsing with Tree-sitter is the next planned story.

## Table of Contents

- [Problem Statement](#problem-statement)
- [Current Progress](#current-progress)
- [Planned Capabilities](#planned-capabilities)
- [Technology Stack](#technology-stack)
- [Architecture](#architecture)
- [Security Principles](#security-principles)
- [Getting Started](#getting-started)
- [Running Tests](#running-tests)
- [API Usage](#api-usage)
- [Development Workflow](#development-workflow)
- [Roadmap](#roadmap)

## Problem Statement

Understanding an unfamiliar codebase can require significant time and effort. Documentation may be outdated, dependencies may be difficult to trace, and important implementation details can be scattered across many files.

CodeAtlas aims to help developers:

- Discover where important functionality is implemented.
- Understand relationships between source-code components.
- Ask questions about a repository and receive evidence-backed answers.
- Identify potentially affected components when code changes.
- Generate structured repository documentation and onboarding guidance.

These are product goals; capabilities are introduced incrementally as development progresses.

## Current Progress

### Implemented

- FastAPI application foundation and health endpoint.
- Versioned API route for ZIP repository uploads.
- ZIP upload size and expanded-content limits.
- ZIP path-traversal and unsafe-entry validation.
- Safe temporary extraction with cleanup on failure.
- File-selection policy for Python, JavaScript, TypeScript, Java, and C#.
- Inclusion and exclusion rules for source files, tests, documentation, configuration, generated files, binary files, and sensitive-file patterns.
- Selection manifests containing file paths, decisions, categories, reasons, and language metadata.
- Automated unit and integration tests for the implemented functionality.

**Latest reported test status:** 47 tests passed after CA-008. Run the test suite locally to verify the current checkout.

### In progress / next

- CA-009: Tree-sitter-based source-code parsing and symbol extraction.

## Planned Capabilities

The following capabilities are planned and should not be considered implemented until their respective stories are completed and tested.

- **Code intelligence:** Extract functions, classes, methods, and symbols.
- **Repository graph:** Explore relationships and dependencies between code components.
- **Code Q&A:** Answer repository questions with source-code citations.
- **Change impact analysis:** Identify potentially affected components.
- **Documentation intelligence:** Detect documentation drift and generate repository understanding documents.
- **Security analysis:** Identify potential security concerns without executing repository code.
- **Onboarding assistance:** Generate structured learning paths for unfamiliar codebases.

## Technology Stack

| Area | Technology | Status |
|---|---|---|
| Backend API | Python, FastAPI | Implemented |
| Validation and configuration | Pydantic / Pydantic Settings | Foundation |
| Automated testing | pytest, HTTPX | Implemented |
| Repository ingestion | ZIP validation and safe extraction | Implemented |
| File analysis | Custom file-selection policy | Implemented |
| Source parsing | Tree-sitter | Planned for CA-009 |
| Frontend | React, TypeScript, Vite, plain CSS | Planned / evolving |
| Metadata database | PostgreSQL | Planned |
| Code graph | Neo4j | Planned |
| Vector search | Qdrant | Planned |
| Background processing | Celery and Redis | Planned |
| AI models | Provider abstraction with free-tier options where available | Planned |

The architecture will evolve as individual components are implemented and validated.

## Architecture

The initial backend is a modular FastAPI application.

```text
Repository ZIP
     |
     v
Upload API
     |
     v
ZIP Validation
     |
     v
Safe Temporary Extraction
     |
     v
File Selection Policy
     |
     v
Selection Manifest
     |
     v
Tree-sitter Parsing (planned)
     |
     v
Code Intelligence and AI Features (planned)
```

The current ingestion flow validates and extracts the uploaded archive, applies the file-selection policy, returns a selection manifest, and cleans up temporary workspaces.

Future architecture components will be added only when required by a validated product capability.

## Security Principles

CodeAtlas treats uploaded repositories as untrusted input.

- **No code execution:** Uploaded repository code is not executed.
- **Upload limit:** Maximum compressed upload size of 100 MiB.
- **Expanded-content limit:** Maximum total expanded size of 500 MiB.
- **File-count limit:** Maximum of 20,000 archive entries.
- **Per-file limit:** Maximum expanded size of 10 MiB per file.
- **Compression-ratio limit:** Reject entries exceeding the configured ratio of 100.
- **Path validation:** Reject unsafe paths, path traversal, duplicate or conflicting paths, and unsafe special entries.
- **Temporary storage:** Use isolated temporary workspaces and clean them up after processing or failure.
- **Sensitive-file exclusions:** Mandatory filename-based exclusions cannot be overridden by user include patterns.
- **Explicit file-selection decisions:** Each file receives a selection decision and reason.

**Important:** Filename-based exclusions are not a complete secret-detection system. Content-based secret detection and redaction must be implemented and verified before source code is sent to hosted AI providers.

## Getting Started

### Prerequisites

- Python installed and available in PowerShell.
- Git.
- VS Code or another code editor.

### 1. Clone the repository

Replace the placeholder with your actual GitHub repository URL.

```powershell
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd CodeAtlas
```

If you already have the repository locally, open its existing directory instead.

### 2. Create and activate a virtual environment

Run these commands from the project root:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks script activation, use the Python executable inside the virtual environment directly instead of changing system-wide execution policies.

### 3. Install backend dependencies

```powershell
cd backend
python -m pip install -r requirements.txt
```

### 4. Start the backend

```powershell
python -m uvicorn app.main:app --reload
```

The API should be available at:

- Application root: `http://127.0.0.1:8000/`
- Health endpoint: `http://127.0.0.1:8000/health`
- Interactive API documentation: `http://127.0.0.1:8000/docs`

Keep the terminal running while using the API.

## Running Tests

From the `backend` directory, with the project virtual environment active:

```powershell
python -m pytest tests -v
```

To run the suite with a concise summary:

```powershell
python -m pytest tests -q
```

Run the tests before committing changes and investigate any failures.

## API Usage

### Upload a repository ZIP

**Endpoint:** `POST /api/v1/repositories/upload-zip`

**Content type:** `multipart/form-data`

**Form field:** `file`

The endpoint currently validates the uploaded ZIP, extracts it into temporary storage, applies the file-selection policy, and returns processing metadata and a selection manifest.

Open `http://127.0.0.1:8000/docs`, select the upload endpoint, and upload a ZIP file to test it interactively.

The response includes information such as:

- Upload status and filename.
- Compressed upload size.
- Number of extracted files and expanded bytes.
- Number of selected and excluded files.
- Selection policy version.
- Per-file selection decisions and reasons.

The current workflow is temporary ingestion, not persistent repository storage or full AI analysis.

## Development Workflow

CodeAtlas is developed incrementally, using a Scrum-style workflow.

For each story:

1. Understand the requirement and acceptance criteria.
2. Design the smallest suitable solution.
3. Implement the feature.
4. Add unit tests.
5. Add integration tests where needed.
6. Test realistic inputs and failure cases.
7. Review security, reliability, and maintainability.
8. Update documentation.
9. Close the story before moving forward.

## Roadmap

- [x] CA-001 — Project skeleton
- [x] CA-002 — FastAPI application foundation
- [x] CA-003 — Automated testing foundation
- [x] CA-004 — Local development documentation
- [x] CA-005 — Foundation review
- [x] CA-006 — ZIP upload API contract
- [x] CA-007 — Secure ZIP ingestion
- [x] CA-008 — Repository file selection
- [ ] CA-009 — Tree-sitter source parsing and symbol extraction
- [ ] Subsequent stories — Code graph, repository Q&A, change impact, and documentation intelligence

## Engineering Principles

- Build a reliable modular monolith before considering distributed services.
- Avoid unnecessary infrastructure and abstractions.
- Do not introduce Kafka or Kubernetes without a demonstrated requirement.
- Prefer explicit interfaces, focused modules, and testable behavior.
- Treat security, correctness, and maintainability as core requirements.
- Mark planned capabilities honestly and verify functionality with tests.

---

**CodeAtlas is under active development.** Features and architecture may change as requirements are validated and new stories are completed.