# Copilot Instructions for RFCC Automation v2

## Purpose

This file instructs Copilot-style assistants (and human contributors) how this repository is organized, the architectural patterns to follow, and the coding conventions and expectations for changes.

## Core principles

- Be explicit: prefer typed function signatures and return types (PEP 484).
- Prefer small, pure functions with dependency injection for side-effecting components.
- Keep async/IO boundaries explicit: use async functions and `asyncio.run` at top-level entrypoints.
- Tests and documentation must accompany non-trivial behavior changes.

## Repository layout

- `main.py`: CLI entrypoint and orchestrator. It dispatches high-level flows via `asyncio.run`.
- `app/`: application code organized by responsibility:
  - `application/`: orchestrations, pipelines and higher-level flows.
  - `domain/`: domain models and enums.
  - `infrastructure/`: external integrations (Playwright, Excel, web clients, etc.).
  - `services/`, `transactions/`: reusable service-level code.
- `config/`: runtime configuration and secrets (do not commit secrets).
- `data/`, `logs/`, `processed/`: runtime data and artifacts (gitignored).

## Entry points and flows

- Use `main.py` as the single canonical launcher for programmatic runs (CLI) and for the new GUI launcher.
- High-level flows live under `app/application/orchestrations/` and should expose a single async function (e.g. `async def run_full_pims_flow(...)`).
- Pipeline flows include:
  - **RFCC:** CSV import → sign certificates via PIMS (dossier, check items, signatures)
  - **RFWCC:** Excel import (one column) → sign certificates via PIMS (identical to RFCC workflow)

## Database schema

- **Subsystems table** (columns: id, external_id, rfcc_status, rfwcc_status):
  - `rfcc_status`: tracks RFCC certificate signing state (NOT_UPLOADED, NOT_SIGNED, SIGNED)
  - `rfwcc_status`: tracks RFWCC certificate signing state (same enum values)
  - Status is per-certificate to allow independent workflows
- **Documents and Subsystem-Document links:** unchanged; provide discipline mappings for both certificates

- Python 3.11+ typing features are allowed (e.g. `tuple[Path, Optional[str]]`).
- Use `black` for formatting, `isort` for imports, and `ruff`/`flake8` for linting.
- Docstrings: module-level and function-level docstrings using Google or NumPy style; include `Args`, `Returns`, and `Raises` for public functions.
- Use `pathlib.Path` for filesystem paths.
- Avoid hard-coded absolute paths; accept `Path` or config objects instead.
- Prefer `async def` for IO-bound functions and explicitly close resources (context managers / `async with`).

## Testing and validation

- Add unit tests for pure logic under a `tests/` directory.
- For integration tests that require Playwright, provide fixtures and mark them separately.
- Tests should be runnable with `pytest`.

## How Copilot should make changes

When asked to modify code, follow these rules:

1. Preserve existing public APIs unless the change is explicitly a breaking change.
2. Add type hints to any new functions; prefer explicit return types.
3. When modifying an async flow, ensure `asyncio.run(...)` is used only at top-level entrypoints.
4. For long-running browser automation (Playwright), use `async with` context managers and ensure proper `close()` calls in `__aexit__`.
5. If adding CLI flags, use `argparse` consistent with `main.py` style and add help strings.
6. When adding user-facing features (like a GUI launcher), keep it optional and non-blocking for headless CI runs.
7. Do not commit secrets; reference `config/secrets.py` for runtime-only injection.

## Specific guidance for the GUI launcher task

- Implement a single launcher in `main.py` that starts an interactive GUI when invoked without CLI args (e.g. `python main.py --gui` or simply `python main.py`).
- The launcher should:
  - Discover runnable scripts and orchestrations by scanning `app/` and the repository for modules exposing `async def run_*` or `if __name__ == '__main__'` markers.
  - Present a simple GUI (Tkinter or a light wrapper) listing discovered commands with buttons.
  - Provide a folder picker dialog for arguments that are filesystem paths; when a button is pressed, pass selected folders as CLI args to the target script or call the underlying run function directly.
  - Run targets in subprocesses (via `subprocess.Popen`) or in background threads so the GUI remains responsive. Capture and stream stdout/stderr to a log pane.
  - Support running multiple flows sequentially; clearly indicate running state and disable buttons while a process runs.

## Deliverables expected from Copilot edits

- Add or update `main.py` with the GUI launcher (non-invasive: preserve existing CLI behaviour).
- Create a single small GUI helper module if needed (e.g. `app/tools/launcher.py`) and add tests if logic is non-trivial.
- Update this `copilot-instructions.md` if you change conventions.

## Developer workflow

- Branch naming: `feature/<short-description>` or `fix/<short-desc>`.
- Commit messages: short title, blank line, longer description (imperative mood).
- Open a PR with a clear summary, list of files changed, and testing instructions.

## Security and secrets

- Never store credentials in the repo. Use `config/secrets.py` with instructions to populate from environment variables.

## Maintenance

- If new long-running integrations are added (e.g., new Playwright flows), add documentation under `app/application/orchestrations/README.md` describing entrypoints and required config.

## RFWCC (New Certificate) Support

Since v2 dual-certificate update:

- Both RFCC and RFWCC use identical signing workflows (dossier, check items, signatures).
- Each subsystem can have independent RFCC and RFWCC statuses.
- **Import difference:** RFCC imports from CSV with full document data; RFWCC imports from Excel (one column of subsystem IDs).
- **PIMSClient methods:**
  - `sign_rfcc_for_subsystem(subsystem_external_id, disciplines)` → returns "SIGNED" | "NOT_FOUND" | "FAILED"
  - `sign_rfwcc_for_subsystem(subsystem_external_id, disciplines)` → identical interface for RFWCC
- **Pipeline naming:** `import_rfwcc_pipeline.py`, `rfwcc_signing_pipeline.py` parallel RFCC pipelines.
- If UI/PIMS changes the certificate names or tab locations, update both RFCC and RFWCC methods in `PIMSClient` consistently.

## Questions

- If a behavior is ambiguous, ask for preferred UI framework (Tkinter vs PySimpleGUI) and whether subprocess execution or in-process calls are preferred.

Thank you — follow these rules to keep the codebase consistent and maintainable.
