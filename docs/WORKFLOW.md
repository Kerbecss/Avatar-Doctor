# Controlled Release Workflow

Avatar Doctor is developed through small, authorized, and verifiable releases. This document defines the repository workflow; it does not authorize work beyond the current release.

## Release goals

- One release is one development goal.
- Every release has a precise scope, measurable acceptance criteria, and a Definition of Done.
- Work on later releases must not begin early, even when it appears simple or closely related.
- Scope expansion requires explicit authorization from the project owner.
- A release normally contains one to four focused commits.

## Branches

The stable branch is `main`. Development branches use this format:

```text
release/vX.Y.Z-english-slug
```

Example:

```text
release/v0.0.1-repository-foundation
```

Rules:

- Never push project changes directly to `main`.
- Never force-push.
- Keep `main` compilable.
- Do not mix unrelated releases in one branch.
- Do not merge a Pull Request without explicit approval.

## Issues and Milestones

Each release has one GitHub Milestone with the same version and release name. The release should normally use between one and four Issues that describe the real work and include verifiable acceptance criteria.

Only the current Milestone and, when useful, at most the next two Milestones may be created. The full roadmap must not be pre-created as GitHub work items.

Labels should use the smallest relevant set from these groups:

- `type: feature`, `type: bug`, `type: tests`, `type: documentation`, or `type: maintenance`;
- an appropriate `area: ...` label; and
- `risk: low`, `risk: medium`, or `risk: high`.

## Commits

Commit messages use Conventional Commits in English:

```text
feat:
fix:
test:
docs:
refactor:
chore:
ci:
build:
```

Every commit must:

- have one clear responsibility;
- leave the tree in a reasonable state;
- exclude unrelated files, generated clutter, secrets, and personal data;
- use an English subject and body; and
- record important decisions in the body when needed.

The repository-local author name must be `Teyocesu`. A verified GitHub `noreply` address should be used when available; an email address must never be invented.

## Pull Requests and review

Each release uses one Pull Request titled:

```text
vX.Y.Z — English Release Name
```

The Pull Request must:

- be written in English;
- remain a Draft while implementation or review is incomplete;
- link the release Issues and Milestone;
- describe the goal, scope, validation, known limitations, and release status; and
- receive mandatory external review before merge.

An automated or self-authored implementation report is not the external review. The Pull Request must not be marked ready or merged until the project owner explicitly authorizes the next step.

## Tags and GitHub Releases

Tags and GitHub Releases are created only after review and explicit approval. Previous tags and Releases must never be deleted.

- Package version: `X.Y.Z`
- Git tag: `vX.Y.Z`
- Release name: `Avatar Doctor vX.Y.Z — English Release Name`
- Every version before `v1.0.0` is a prerelease.

Release notes use these sections:

```text
## Goal
## Added
## Changed
## Validation
## Known Limitations
## Next Step
```

Official automation must not create duplicate tags or Releases.

## Distribution gates through v0.0.4

Releases `v0.0.1` through `v0.0.4` are development milestones and are not VCC-installable package releases. During this period:

- package release automation is manual and requires both `main` and `ENABLE_PACKAGE_RELEASE == 'true'`;
- listing automation is manual and requires both `main` and `ENABLE_PACKAGE_LISTING == 'true'`;
- both enablement variables remain unset;
- the package manifest `url` does not yet point to a distributable ZIP;
- the VPM listing and GitHub Pages remain disabled; and
- a reviewed GitHub Release, if explicitly authorized, must not claim VCC installability.

The existing `PACKAGE_NAME` variable does not enable distribution by itself. Missing, empty, or non-`true` enablement variables must keep the jobs skipped.

Version `v0.0.5 — Release Pipeline` owns ZIP and `.unitypackage` validation, distributable manifest validation, listing generation, GitHub Pages configuration, automatic listing triggers, artifact checks, automated enforcement of release naming and structured notes, and automatic prerelease detection. These capabilities must not be reported as validated earlier.

## Language policy

All persistent repository and user-facing product content is written in English, including code, identifiers, comments, documentation, package metadata, workflows, Issues, Milestones, Pull Requests, tags, Releases, test data, and examples.

Development conversation with the project owner and the final delivery diagnosis are written in Spanish outside the repository. No internal Spanish-language files are stored in the repository.

## Definition of Done

A release is complete only when all applicable conditions are proven:

- only the authorized scope was implemented;
- every acceptance criterion is satisfied;
- the code compiles when the environment permits verification;
- applicable tests pass;
- no secrets, credentials, personal data, paid services, or unintended external connections were added;
- no improper temporary or generated files remain;
- `git diff --check` passes;
- affected documentation is current and written in English;
- `CHANGELOG.md` and `package.json` contain the release version;
- the branch is pushed and its Draft Pull Request is open;
- the mandatory delivery diagnosis was provided outside the repository in Spanish;
- an external reviewer authorized completion;
- the Pull Request was merged only after authorization; and
- the GitHub Release was created and verified only after authorization.

Conditions that belong to a later approval stage remain explicitly pending; they must never be reported as completed early.

## Required delivery evidence

The final delivery diagnosis must report factual evidence for:

- implemented and excluded scope;
- created and modified files;
- technical decisions and rejected alternatives;
- repository language and public identity checks;
- commands executed and validations not executed;
- Unity version, compilation, errors, and warnings when available;
- repository, remote, branch, working tree, commits, push, and Draft Pull Request;
- release status, risks, limitations, deviations, security, cost, and the next planned release; and
- commands needed to reproduce verification.

Unknown or unavailable results must be labeled honestly. A check must never be reported as passed when it was not executed.
