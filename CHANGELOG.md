# Changelog

All notable changes to BBIOS OS are recorded here.

## Unreleased

- Reserved for changes after the Version 0.1.0 baseline.

## Version 0.1.0 - 2026-07-18

### Added

- Engineering governance documentation, including the master plan, ADRs, development standards, testing strategy, contributing guide, readiness assessment, and cockpit stabilization plan.
- Backend dependency manifest in `pyproject.toml`.
- Python runtime policy using Python 3.12.13 as the validated development runtime and `>=3.12,<3.13` as the supported project range.
- Centralized non-secret application settings in `bbi_os/settings.py`.
- Focused settings tests covering defaults, overrides, parsing, invalid values, isolation, and absence of required secrets.
- Repository-level VS Code workspace configuration for the project `.venv` and `unittest` discovery.
- `CockpitApiHandler` compatibility adapter for internal cockpit handler-style routes.
- Richer `CockpitService` facade for cockpit dashboard and workflow-control use cases while preserving prototype service behavior.

### Changed

- FastAPI app metadata and cockpit router prefix now use centralized settings defaults.
- Project runtime standard moved from the local Python 3.9 interpreter to the validated Python 3.12.13 development runtime.
- Repository ignore patterns expanded for local virtual environments, Python caches, test caches, build artifacts, egg-info metadata, and `.DS_Store`.
- Engineering ADR statuses normalized for the accepted FastAPI boundary and private repository access standards.

### Fixed

- Resolved cockpit import failure for `CockpitApiHandler`.
- Resolved cockpit service/test architectural drift without deleting prototype routes or rewriting application architecture.
- Restored and preserved full `unittest` discovery baseline.

### Security

- Added `.env.example` with safe non-secret configuration placeholders.
- Centralized supported non-secret application configuration.
- No real secrets, authentication implementation, authorization redesign, or production security claims are included in this release.

### Technical Debt / Known Limitations

- Cockpit still has mixed prototype FastAPI routes and richer internal handler architecture.
- Current cockpit compatibility code temporarily calls private repository `_read()` as recorded technical debt.
- Persistence remains JSON-backed and in-memory depending on module path.
- Explicit transaction boundaries are not implemented.
- PostgreSQL is not implemented.
- Authentication is not production-ready and no new authentication work is included.
- Docker and CI/CD are not implemented.
- Full `/v1/*` API consolidation is not complete.
