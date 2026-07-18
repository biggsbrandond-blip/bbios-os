# BBIOS OS Release Notes v0.1.0

## 1. Release Summary

Version 0.1.0 establishes a clean pre-production baseline for BBIOS OS after cockpit stabilization and Phase 1 engineering foundation work.

## 2. Release Scope

This release captures documentation governance, cockpit compatibility restoration, centralized settings, dependency metadata, Python runtime standardization, settings tests, and repository-level VS Code configuration.

## 3. Highlights

- Full `unittest` baseline restored and validated at 95 passing tests.
- Cockpit import and service/test drift resolved.
- Python 3.12.13 established as the validated development runtime.
- `pyproject.toml` established as the backend dependency manifest.
- Centralized non-secret settings added for application metadata, local runtime values, API prefix, and data directory defaults.

## 4. Engineering Improvements

- ADRs, development standards, testing strategy, contributing guidance, readiness assessment, and release governance now provide controlled engineering direction.
- FastAPI is recorded as the accepted future HTTP boundary while existing `/cockpit/*` prototype routes remain compatibility paths.
- Private repository access is prohibited as an accepted standard, with current cockpit `_read()` usage recorded as temporary technical debt.

## 5. Runtime and Tooling

- Validated development runtime: Python 3.12.13.
- Supported project range: `requires-python = ">=3.12,<3.13"`.
- Current development setup uses `.venv`.
- VS Code workspace settings point to `${workspaceFolder}/.venv/bin/python` and enable `unittest` discovery under `tests`.

## 6. Test Results

- Command: `.venv/bin/python -m unittest discover tests`
- Result: 95 tests passing, 0 failures, 0 errors.

## 7. Compatibility

Default FastAPI metadata and router prefix behavior remain compatible with the existing cockpit prototype. Public route paths are not changed by this release.

## 8. Known Limitations

- Mixed prototype and versioned cockpit architecture remains.
- Current cockpit compatibility code temporarily calls private repository `_read()`.
- Persistence remains JSON-backed and in-memory depending on module path.
- Explicit transaction boundaries are not implemented.
- PostgreSQL is not implemented.
- Authentication is not production-ready.
- Docker and CI/CD are not implemented.
- Full `/v1/*` API consolidation is not complete.

## 9. Deferred Work

- Repository contract cleanup.
- PostgreSQL persistence planning and implementation.
- SQLAlchemy and Alembic adoption after approval.
- Authentication and authorization hardening.
- API consolidation.
- Docker, CI/CD, and production deployment readiness.

## 10. Upgrade / Setup Notes

Use Python 3.12.13 and a project-local `.venv`. Install the project from `pyproject.toml` before running tests or FastAPI tooling.

## 11. Validation Commands

```bash
.venv/bin/python -m unittest discover tests
.venv/bin/python -m compileall bbi_os
git diff --check
```

## 12. Next Planned Phase

The next planned phase is repository contract cleanup before PostgreSQL persistence begins.
