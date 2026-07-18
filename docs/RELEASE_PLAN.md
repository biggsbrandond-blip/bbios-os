# BBIOS OS Release Plan

## 1. Purpose

This plan defines how BBIOS OS releases are prepared, validated, approved, and reviewed. It protects the current pre-production baseline while preserving clear boundaries for future persistence, API, security, and operations work.

## 2. Versioning Policy

BBIOS OS follows Semantic Versioning guidance. `0.x` versions represent active pre-production development. Version `1.0.0` is reserved until production-readiness gates are approved and met. Patch releases are for backward-compatible fixes, minor releases are for backward-compatible capabilities, and major releases after `1.0.0` are for approved breaking changes.

## 3. Release Types

- Baseline releases capture a stable engineering checkpoint before a new phase begins.
- Patch releases correct defects without changing public contracts.
- Minor releases add approved capabilities without breaking existing behavior.
- Major releases require explicit approval for breaking changes after `1.0.0`.

## 4. Release Readiness Gates

A release is ready only when scope is documented, intended files are identified, generated artifacts are excluded, tests pass, diff checks pass, and known limitations are recorded without overstating production readiness.

## 5. Validation Requirements

Required validation for the current backend release process:

1. `git status --short`
2. `git diff --stat`
3. `git diff --check`
4. `.venv/bin/python -m unittest discover tests`
5. `.venv/bin/python -m compileall bbi_os`

Additional validation must be added when future phases introduce persistence, authentication, API consolidation, deployment, or frontend release scope.

## 6. Change Control

Release preparation must not expand implementation scope. Repository contract cleanup, PostgreSQL, SQLAlchemy, Alembic, authentication, Docker, CI/CD, and API consolidation require separate approval.

## 7. Changelog Requirements

Each release must update `CHANGELOG.md` with a dated version entry and clear categories for added, changed, fixed, security, and known limitations. The changelog must distinguish current behavior from planned work.

## 8. Release Notes Requirements

Release notes must summarize scope, validation, compatibility, known limitations, setup expectations, and the next planned phase. They must not claim branch protections, automation, deployment pipelines, or production readiness unless confirmed by repository evidence.

## 9. Tagging Policy

Release tags should use the form `vMAJOR.MINOR.PATCH`, such as `v0.1.0`. Tags should be created only after human review confirms the intended release contents.

## 10. Rollback Expectations

Every release should identify a rollback path. For documentation and configuration releases, rollback is a revert of the release commit. Future database or deployment releases require explicit migration and operational rollback plans.

## 11. Migration Notes

Version 0.1.0 has no database migration. Future persistence work must document data migration, schema migration, rollback, and repository parity validation before release.

## 12. Security Review Requirements

Release review must confirm that no secrets are committed, secret values are not logged or documented, authentication claims match current behavior, and security-related limitations are visible.

## 13. Release Approval

Human approval is required before committing, tagging, pushing, or opening a release pull request. Approval should confirm intended files, validation results, known limitations, and next-phase boundaries.

## 14. Post-Release Validation

After a release commit or tag is created, rerun the baseline tests and diff hygiene checks from a clean working state where practical. Confirm that no generated artifacts or local-only files were included.

## 15. Emergency Release Process

Emergency releases must remain narrowly scoped to the defect or security issue. They still require validation, changelog notes, release notes, and explicit review of any skipped gates.

## 16. AI-Assisted Release Rules

AI-assisted release work must inspect git state first, avoid deleting local artifacts without explicit authorization, avoid broad refactoring, report exact commands and outcomes, and stop for human review before commit, push, tag, or pull request creation.
