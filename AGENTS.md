# Repository Instructions

## Scope discipline

- Work only inside the explicitly authorized release and phase.
- Do not silently broaden product, architecture, dependency, or release scope.
- Do not begin the next phase until the current phase exit gate is approved.
- Treat out-of-scope work as a separate proposal, not an incidental change.
- Keep unrelated refactors and cleanup out of scoped changes.

## Canonical artifacts

Release work is governed by these artifacts:

```text
docs/specs/vX.Y.Z-*.md
plans/vX.Y.Z.md
plans/HANDOFF.md
```

- The SPEC is the canonical product and release contract.
- The PLAN sequences approved SPEC work into reviewable phases.
- HANDOFF records only the current operational state and next gate.
- A PLAN cannot override or redefine its SPEC.
- HANDOFF cannot override the SPEC or PLAN.
- Avoid duplicating product requirements across these artifacts.
- Derive implementation Issues from an approved SPEC.

## Git

- Treat `main` as protected and never push changes directly to it.
- Use `release/vX.Y.Z-english-slug` for release branches.
- Use English Conventional Commit subjects.
- Do not force-push or rewrite shared history.
- Do not merge, tag, publish, or create a Release without explicit authorization.
- Keep commits focused, reviewable, and limited to confirmed paths.
- Preserve unrelated local and tracked changes.

## Validation

- Run deterministic repository validation for every change.
- Run tests that protect behavior, invariants, boundaries, and regressions.
- Do not add low-value tests merely to increase a count.
- Unity validation is required for Unity behavior, code, asset, or metadata changes.
- Record commands and observed results accurately.
- Never claim validation that was not actually run.
- A green CI result supports review but does not replace independent review.

## Public content

- Keep repository content in English.
- Do not commit secrets, credentials, personal paths, or private instructions.
- Use repository-relative paths in public documentation.
- Do not track generated artifacts unless repository policy explicitly requires them.
- Keep public status claims aligned with verified behavior and distribution state.

## Implementation

- Prefer small, focused files and changes.
- Preserve package and assembly boundaries.
- Use public, supported Unity and integration APIs.
- Keep product logic separate from Editor presentation concerns.
- Avoid mutable global state unless an approved design requires it.
- Read-only phases must not mutate scenes, assets, or project state.
- Do not add dependencies or compatibility claims outside an approved SPEC and phase.
- Do not implement future roadmap capabilities early.

## Review gates

- Each meaningful phase requires independent review before the next phase begins.
- Resolve blocking findings within the authorized phase only.
- Update HANDOFF when operational state or the next gate changes.
- Stop at the approved gate when further work requires new authorization.
