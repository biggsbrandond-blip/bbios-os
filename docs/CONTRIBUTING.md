# Contributing to BBIOS OS

## 1. Purpose

This guide defines how human and AI-assisted contributors should work in BBIOS OS without destabilizing existing behavior. It applies to documentation, backend, cockpit, workflow, integration, monetization, frontend, and future infrastructure work.

## 2. Repository Orientation

- `bbi_os/` contains backend modules.
- `bbi_os/settings.py` contains centralized non-secret application settings.
- `bbi_os/cockpit/` contains the FastAPI cockpit prototype, cockpit Handler / Adapter, Application Service facade, dashboards, controls, analytics, and client management.
- `bbi_os/task_management/` contains the current internal request handler and task service/repository path.
- `bbi_os/workflows/` contains workflow definitions, execution, templates, actions, and repositories.
- `bbi_os/client_*` packages contain pipeline, onboarding, execution, and monetization capabilities.
- `bbi_os/integrations/` contains connector and webhook support.
- `cockpit-ui/` contains the React cockpit UI.
- `tests/` contains the root `unittest` suite.
- `docs/` contains governance, architecture, standards, testing, and readiness documents.

## 3. Contribution Principles

- Investigate before implementing.
- Keep changes bounded to the approved scope.
- Preserve public behavior unless explicitly approved.
- Make small, reversible changes.
- Prefer repository evidence over assumptions.
- Distinguish confirmed behavior, interpretation, planned work, and unresolved decisions.

## 4. Supported Development Workflow

Supported backend runtime: Python 3.12.13, within the project range `>=3.12,<3.13`. Python 3.9 is not supported for new development.

1. Investigate.
2. Document findings.
3. Obtain approval.
4. Implement bounded change.
5. Run focused tests.
6. Run full tests.
7. Review diff.
8. Commit.
9. Open pull request.
10. Merge after approval.

## 5. Before Starting Work

- Read the user request and any referenced documents.
- Check `git status --short`.
- Inspect relevant files with repository tools.
- Identify authorized files and stop conditions.
- Determine focused validation commands.
- Confirm whether the work is documentation-only, code-only, or mixed.

## 6. Branching Expectations

No branch protection or naming policy is confirmed in the repository. Recommended control: use short purpose-specific branches and keep each branch scoped to one approved objective.

## 7. Scope Control

- Do not modify unrelated files.
- Do not clean up formatting outside touched code.
- Do not refactor merely because code could be cleaner.
- Do not introduce new frameworks or dependencies without approval.
- Stop if the requested fix requires broader architecture changes.

## 8. Implementation Rules

- Routers and Handlers / Adapters translate transport concerns.
- Application Services orchestrate behavior.
- Domain Services and Workflow Controls own domain rules and workflow state.
- Repositories own persistence access.
- Do not add direct private Repository method access; the current cockpit `_read()` compatibility usage is recorded technical debt awaiting an approved Repository-contract correction.
- Use `bbi_os/settings.py` for supported application configuration instead of adding scattered environment reads.
- Preserve Compatibility Layers until deprecation is approved.

## 9. Testing Requirements

- Run focused tests first for the touched area.
- Then run `python3 -m unittest discover tests`.
- Do not modify tests merely to force passing results.
- Record exact commands and outcomes.
- If a test appears invalid, stop and request human approval before changing it.

## 10. Documentation Requirements

Update documentation when behavior, architecture, standards, commands, or risks change. Use relative repository paths such as `docs/ARCHITECTURE_DECISIONS.md`, not machine-specific paths.

## 11. Commit Standards

Commits should be intentional and scoped. A commit message should identify the affected area and outcome. Do not commit generated noise, local OS files, secrets, or unrelated changes.

## 12. Pull Request Standards

Pull requests should include:

- Purpose and scope.
- Files changed.
- Tests run.
- Compatibility notes.
- Risks and rollback plan.
- Linked ADRs or documentation where relevant.

Branch protection is recommended but not confirmed by repository evidence.

## 13. Review Standards

Reviewers should prioritize behavior, compatibility, security, tests, data integrity, and architectural boundaries. Style comments should not distract from correctness unless style affects maintainability or consistency.

## 14. Security and Sensitive Information

- Do not commit secrets.
- Do not print secret values in logs, docs, tests, or reviews.
- Environment variable names may be documented when needed, but values must remain outside the repository.
- Treat authentication, authorization, and audit behavior as request-boundary concerns.

## 15. AI-Assisted Development Rules

AI-assisted work must:

- Investigate before implementation.
- Use bounded file authorization.
- Avoid unrelated refactors.
- Avoid test modification merely to force passing results.
- Run exact validation commands.
- Report all changed files.
- Declare stop conditions.
- Obtain human approval before broad architecture changes.
- Avoid invented repository facts.
- Distinguish confirmed behavior from assumptions and recommendations.

## 16. Stop Conditions

Stop and request review when:

- Required changes exceed authorized files.
- A test appears invalid.
- Public behavior would change.
- Storage formats would change.
- New dependencies or infrastructure are required.
- Security or data exposure risk is unclear.
- The architecture decision is unresolved.

## 17. Definition of Ready

A task is ready when the objective, allowed files, prohibited changes, validation commands, evidence sources, and stop conditions are clear.

## 18. Definition of Done

A task is done when scoped changes are complete, focused tests pass, full tests pass, docs are updated if required, diff is reviewed, risks are reported, and no prohibited changes were made.

## 19. Example Contribution Sequence

1. Read the request and relevant docs.
2. Run `git status --short`.
3. Inspect target modules.
4. Write an investigation note or plan if required.
5. Implement only approved files.
6. Run the focused test for the touched module.
7. Run `python3 -m unittest discover tests`.
8. Run `git diff --check`.
9. Review the unified diff.
10. Report files changed, tests, risks, and next decision needed.
