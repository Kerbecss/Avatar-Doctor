# Avatar Doctor — Master Roadmap and Development Contract

This document is the repository source of truth for the planned development of Avatar Doctor.

Do not implement the complete roadmap at once. Preserve it as planning and wait for a specific instruction authorizing each release. Every future task must identify exactly which version is authorized.

Development conversation, decisions, and delivery diagnoses for the project owner are written in Spanish outside this repository. Everything stored in the repository or shown to product users is written exclusively in English.

## 1. Public project identity

### Product name

```text
Avatar Doctor
```

### Repository name

```text
Avatar-Doctor
```

### Expected repository

```text
Teyocesu/Avatar-Doctor
```

### GitHub description

```text
Local-first, explainable diagnostics, safe repairs, Quest conversion, and multi-platform publishing tools for VRChat avatars.
```

### Public author identity

```text
Teyocesu
```

For contexts specifically related to a VRChat identity, this name may be used:

```text
Kerbecs__
```

The project owner's real name must not appear in commits, documentation, licenses, manifests, Issues, Pull Requests, Releases, credits, screenshots, fixtures, test data, package metadata, examples, or repository files.

Before creating commits, inspect the configured Git identity. The repository-local author name must be `Teyocesu`. If the configured email exposes personal information, use a verified or account-provided GitHub `noreply` address. Never invent an email address. If a safe identity cannot be configured without inventing information, stop before committing and document the blocker.

## 2. Language policy

### Content that must be in English

Everything that remains in the repository or is visible to users must be written in English, including:

- Unity interface text;
- buttons, menus, and tooltips;
- errors, warnings, and diagnostic explanations;
- recommendations, exported reports, and user-facing logs;
- code, identifiers, namespaces, class names, method names, and comments;
- tests, test names, and fixtures;
- documentation, README files, roadmap, Architecture Decision Records, and changelog;
- GitHub Issues, Milestones, Pull Requests, tags, Releases, and release notes;
- branch names and commit messages;
- package metadata, examples, and screenshots.

### Content that may be in Spanish

Spanish is permitted only outside the repository for:

- development conversation with the project owner;
- the final diagnosis delivered after each task;
- explanations of decisions to the project owner;
- necessary questions; and
- blocker warnings and internal instructions supplied to the development agent.

Do not add internal Spanish-language files to the repository. English is the source and default language for future localization.

## 3. Product vision

Avatar Doctor is planned as a free, local Unity tool for VRChat avatar creators. It is intended to:

- analyze an avatar deeply inside Unity;
- detect most common problems;
- connect symptoms to probable causes;
- explain every problem with verifiable evidence;
- navigate directly to affected objects;
- propose repairs;
- apply safe, reversible corrections;
- compare PC and Quest versions;
- prepare a non-destructive Quest variant;
- help reach a satisfactory Quest result;
- validate and publish both platforms under the same Avatar ID; and
- later provide a local mobile remote for VRChat OSC parameters.

## 4. Economic constraint

The mandatory cost of the project and its required operation is:

```text
USD 0
```

Do not use:

- paid artificial intelligence APIs;
- project-owned servers;
- hosted databases;
- mandatory SaaS services;
- paid domains;
- hosted telemetry;
- the App Store or Google Play as a requirement;
- external accounts owned by the project; or
- dependencies with incompatible licenses or mandatory fees.

Permitted resources include:

- Unity Personal;
- VRChat Creator Companion;
- the VRChat SDK;
- a public GitHub repository;
- GitHub Actions for public repositories;
- GitHub Releases and GitHub Pages;
- compatible open-source software;
- fully local processing;
- installable Progressive Web Apps; and
- VPM/VCC distribution.

## 5. Strict product boundaries

### Unity and PC

All inspection, diagnosis, repair, PC/Quest conversion, and publishing occurs exclusively on the PC where Unity is open.

### Mobile application

The future mobile application is limited to controlling the avatar currently used in VRChat through OSC. It must not:

- modify a Unity project;
- read project files;
- create Unity toggles;
- execute builds;
- publish avatars;
- change project materials;
- execute arbitrary code on the PC; or
- interact with the Unity Editor.

### Blender

Blender, Weight Paint, modeling, external rigging, vertex modification, and mesh editing outside Unity are not part of the project. Avatar Doctor may detect observable renderer, rig, or mesh problems, but it must not become a Blender tool.

## 6. Intelligence model

The core will not depend on generative artificial intelligence. Avatar Doctor intelligence will use a deterministic expert system:

1. evidence collection;
2. individual rules;
3. a dependency graph;
4. error correlation;
5. root-cause detection;
6. explainable confidence;
7. recommended repair ordering;
8. post-repair validation; and
9. false-positive control.

Every diagnosis must explain:

- what is wrong;
- where it is;
- which evidence proves it;
- which effect it may produce;
- the probable cause;
- which elements depend on the problem;
- the available corrections;
- the risk of each correction; and
- the confidence of the conclusion.

Confidence must never be an invented model output. It must be calculated from objective, documented evidence.

## 7. Technical principles

- Use public, documented Unity and VRChat APIs.
- Do not use reflection over private VRChat SDK internals.
- Do not modify files that belong to installed packages.
- Do not modify original third-party assets when a copy can be created.
- Do not store VRChat credentials.
- Do not use private VRChat APIs.
- Do not hide errors or warnings.
- Do not claim that a test passed when it was not executed.
- Do not apply ambiguous repairs automatically.
- Every repair must support Undo, backup, or rollback.
- Keep analysis separate from modification.
- Keep the rule core decoupled from the interface.
- Design optional adapters for external tools.
- Avoid unnecessary dependencies.
- Keep the project installable through VPM/VCC.
- Prepare all user-facing text for future localization.
- Use English as the source and default language.

## 8. Planned architecture

```text
Avatar-Doctor/
├── Packages/
│   └── com.teyocesu.avatar-doctor/
│       ├── Editor/
│       │   ├── UI/
│       │   ├── Scanning/
│       │   ├── Diagnostics/
│       │   ├── Rules/
│       │   ├── Correlation/
│       │   ├── Repairs/
│       │   ├── Quest/
│       │   ├── Publishing/
│       │   └── Integrations/
│       ├── Tests/
│       │   ├── Editor/
│       │   └── Fixtures/
│       ├── Documentation~/
│       ├── CHANGELOG.md
│       ├── LICENSE.md
│       └── package.json
├── AvatarRemote/
│   ├── Bridge/
│   └── Pwa/
├── ProjectSettings/
├── docs/
│   ├── ROADMAP.md
│   ├── WORKFLOW.md
│   ├── ARCHITECTURE.md
│   ├── TECHNICAL_BASELINE.md
│   └── decisions/
└── .github/
    ├── ISSUE_TEMPLATE/
    ├── pull_request_template.md
    └── workflows/
```

This structure may evolve, but every material change must be justified by an Architecture Decision Record written in English. Planned directories are not evidence that their features are implemented.

## 9. Git and GitHub strategy

### Stable branch

- The stable branch is `main`.
- Never push project changes directly to `main`.
- Never force-push.
- Never delete published tags or Releases.
- Work through Pull Requests.
- Keep the stable branch compilable.

### Working branches

Use this format:

```text
release/v<VERSION>-<english-description>
```

Example:

```text
release/v0.0.1-repository-foundation
```

### Commits

Use Conventional Commits in English:

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

Each release normally contains one to four commits. Each commit must have one clear responsibility, leave the tree in a reasonable state, exclude unrelated files and secrets, keep refactors separate from functionality, use an English message, and document important decisions in its body when needed.

### Pull Requests

Each release uses one Pull Request titled:

```text
v<VERSION> — <English release name>
```

The title and body are written in English. The Pull Request remains a Draft until review is complete and must not be merged without a later explicit instruction.

### Tags and Releases

- Package version: `X.Y.Z`.
- Git tag: `vX.Y.Z`.
- GitHub Release: `Avatar Doctor vX.Y.Z — English Release Name`.
- Every version before `v1.0.0` is a prerelease.
- Do not create tags manually if the official package automation already creates them.
- Do not create duplicate Releases.
- Do not delete old versions.
- Write all release notes in English.

Release notes use:

```text
## Goal
## Added
## Changed
## Validation
## Known Limitations
## Next Step
```

## 10. Goal system

Every release is a small, safe, verifiable goal with:

- a GitHub Milestone matching the version and name;
- between one and four Issues;
- one Pull Request;
- verifiable acceptance criteria;
- a Definition of Done; and
- a final diagnosis delivered in Spanish outside the repository.

Do not create every Milestone at once. Create only the current Milestone and, at most, the next two.

Recommended labels:

```text
type: feature
type: bug
type: tests
type: documentation
type: maintenance

area: foundation
area: scanner
area: diagnostics
area: animator
area: expressions
area: repairs
area: materials
area: dynamics
area: performance
area: intelligence
area: quest
area: publishing
area: remote
area: integrations

risk: low
risk: medium
risk: high
```

## 11. Definition of Done for every release

A release may finish only when:

- only the authorized scope was implemented;
- all acceptance criteria are satisfied;
- the code compiles when the environment permits verification;
- applicable tests pass;
- no secrets exist;
- no improper temporary or generated files remain;
- `git diff --check` passes;
- affected documentation is current;
- all repository content is in English;
- `CHANGELOG.md` is updated;
- `package.json` has the correct version;
- the branch is pushed;
- the Draft Pull Request is open;
- the mandatory Spanish diagnosis is delivered outside the repository;
- an external reviewer authorizes finalization;
- after authorization, the Pull Request is merged; and
- the GitHub Release is created and verified.

When a task explicitly prohibits merge, tags, or a GitHub Release, the implementation may be ready for review while those release-finalization gates remain pending.

## 12. Mandatory delivery diagnosis contract

At the end of every development task, respond to the project owner in Spanish using the required master diagnosis structure. The outline below is an English representation of the mandatory fields so that repository content remains English:

````text
# DELIVERY DIAGNOSIS

## Target release
Version:
Name:
Branch:

## Result
COMPLETED / PARTIAL / BLOCKED

## Summary
Brief factual description.

## Implemented scope
- ...

## Scope not implemented
- ...

## Files created
- ...

## Files modified
- ...

## Technical decisions
- Decision:
  Reason:
  Rejected alternatives:

## Language policy
Repository content in English:
Items found in another language:
Corrections made:

## Public identity
Author used:
Git identity used:
Personal data detected:

## Validations executed
- Command:
  Result:
  Evidence summary:

## Validations not executed
- Validation:
  Reason:

## Unity status
Detected version:
Compilation:
Errors:
Warnings:

## Git status
Repository:
Remote:
Branch:
Working tree:

## Commits
- HASH — message

## Push
Remote branch:
Result:

## Pull Request
URL:
Status:
Milestone:
Related Issues:

## GitHub Release
Created: no
Reason: pending review

## Risks and limitations
- ...

## Deviations from the instruction
- ...

## Security and costs
Secrets detected:
Paid services added:
External connections added:

## Next planned release
Version:
Goal:

## Commands to reproduce verification
```shell
...
```
````

Never hide a limitation. Mark every unavailable check as not executed.

## 13. Release roadmap

# Stage A — Foundation

## v0.0.1 — Repository Foundation

- Create the repository from the official VPM template.
- Establish identity, license, documentation, and roadmap.
- Remove demonstration content.
- Prepare the controlled work policy.

**Result:** a public repository with a valid minimal structure.

## v0.0.2 — Package Skeleton

- Create Editor assemblies.
- Define namespaces.
- Create the initial internal structure.
- Add identity and version constants.

**Result:** an empty but compilable package.

## v0.0.3 — Repository Validation

- Validate `package.json`.
- Validate the VPM structure.
- Check formatting and forbidden files.
- Add free GitHub Actions checks.

**Result:** basic errors are blocked automatically.

## v0.0.4 — Editor Window Shell

- Create `Tools → Avatar Doctor`.
- Add an empty window with a header and status.
- Support Domain Reload.
- Do not add real scanning yet.

**Result:** the first visible Unity Editor element.

## v0.0.5 — Release Pipeline

- Verify VPM automation.
- Generate `.zip`, `.unitypackage`, and listing artifacts.
- Verify a clean installation from a Release.
- Document recovery from failed Releases.

**Result:** the first reproducible installation channel.

# Stage B — Avatar Scanner

## v0.1.0 — Avatar Discovery

- Find Avatar Descriptors in the scene.
- Support manual and automatic selection.
- Handle zero, one, or multiple avatar states.

## v0.1.1 — Hierarchy Snapshot

- Capture paths, objects, active state, and components.
- Generate an immutable analysis snapshot.

## v0.1.2 — Component and Asset Inventory

- Inventory renderers, animators, materials, meshes, and assets.
- Do not emit complex diagnostics yet.

## v0.1.3 — Reference Graph

- Record incoming and outgoing references.
- Distinguish internal, external, null, and package references.

## v0.1.4 — Results Interface and Export

- Display a result list.
- Add filters and search.
- Navigate to an object.
- Export JSON and HTML.

# Stage C — Structural Diagnostics

## v0.2.0 — Descriptor Diagnostics

- Detect missing, duplicated, or misplaced Avatar Descriptors.
- Detect incomplete essential configuration.

## v0.2.1 — Rig and Animator Diagnostics

- Detect a missing Animator.
- Detect an incomplete humanoid rig.
- Detect unassigned essential humanoid bones.
- Detect suspicious scales and transforms.

## v0.2.2 — Missing and External References

- Detect Missing Scripts.
- Detect null references.
- Detect references outside the avatar.
- Detect deleted or inaccessible assets.

## v0.2.3 — Renderer and Root Bone Diagnostics

- Detect a null Root Bone.
- Detect an external Root Bone.
- Detect a renderer associated with another armature.
- Detect empty material slots.

## v0.2.4 — Bone Mapping Diagnostics

- Detect null bones.
- Detect external bones.
- Identify possible exact matches.
- Detect remnants of a previous armature.

## v0.2.5 — Mesh and Blendshape Diagnostics

- Detect animated but nonexistent blendshapes.
- Detect suspicious bounds.
- Detect duplicate meshes.
- Detect renderers without a mesh.
- Add structural test cases.

# Stage D — Menus, Parameters, and Animators

## v0.3.0 — Expression Inventory

- Read Expression Parameters.
- Read Expressions Menus.
- Record controls and submenus.

## v0.3.1 — Parameter Diagnostics

- Detect missing parameters.
- Detect incompatible types.
- Detect duplicates.
- Detect inconsistent default values.

## v0.3.2 — Menu Diagnostics

- Detect null controls.
- Detect empty submenus.
- Detect cycles.
- Detect unreachable controls.
- Detect broken references.

## v0.3.3 — Animator Graph Extraction

- Extract layers, states, motions, transitions, and conditions.
- Build a navigable graph.

## v0.3.4 — Animator Flow Diagnostics

- Detect unreachable states.
- Detect states without an exit.
- Detect impossible transitions.
- Detect contradictory conditions.
- Detect states without a Motion.

## v0.3.5 — Animation Binding Diagnostics

- Detect nonexistent paths.
- Detect nonexistent properties.
- Detect incorrect material slots.
- Detect nonexistent blendshapes.
- Trace the complete chain of a toggle.

# Stage E — Repair Engine

## v0.4.0 — Repair Transactions

- Add transactional operations.
- Add Undo.
- Add backups.
- Add preview.
- Add before-and-after diff.

## v0.4.1 — Safe Reference Repairs

- Repair null references only when the match is unambiguous.
- Do not modify ambiguous cases.

## v0.4.2 — Root Bone and Bone Remapping

- Assign a safe Root Bone.
- Remap bones by exact paths.
- Validate the renderer after a change.

## v0.4.3 — Expressions Repairs

- Create missing parameters.
- Correct parameter types.
- Repair controls and submenus.
- Update related references.

## v0.4.4 — Animation Repairs

- Repair unambiguous bindings.
- Create copies of animation clips.
- Never modify shared clips without duplicating them.

## v0.4.5 — Safe Toggle Builder and Rollback

- Create a complete toggle inside Unity.
- Reanalyze after every repair.
- Roll back when new errors appear.

# Stage F — Materials, Dynamics, and Performance

## v0.5.0 — Material and Shader Inspection

- Inventory properties.
- Detect missing materials.
- Detect missing shaders.
- Detect duplicate materials.

## v0.5.1 — Animated Shader Properties

- Detect animated properties that do not exist.
- Detect clips that modify a different material.
- Compare properties across materials.

## v0.5.2 — Texture Audit

- Record resolutions.
- Record formats.
- Estimate memory.
- Detect duplicate textures.
- Inspect relevant import settings.

## v0.5.3 — PhysBones and Contacts

- Detect invalid roots.
- Detect null colliders.
- Detect overlapping chains.
- Detect missing parameters.
- Detect misconfigured Contacts.

## v0.5.4 — Constraints and Performance

- Detect invalid Sources.
- Detect circular constraints.
- Add extended metrics.
- Provide prioritized recommendations without modifying meshes.

# Stage G — Explainable Intelligence

## v0.6.0 — Evidence Graph

- Connect problems, objects, assets, and dependencies.
- Record reusable evidence.

## v0.6.1 — Root Cause Correlation

- Group multiple errors under a probable cause.
- Avoid duplicate diagnoses.

## v0.6.2 — Confidence Scoring

- Define a documented formula.
- Distinguish high, medium, and low confidence.
- Show why a score was assigned.

## v0.6.3 — Repair Planning

- Order repairs by dependency.
- Detect incompatible operations.
- Recalculate the plan after every change.

## v0.6.4 — Scenario Library

Minimum scenarios:

- a partially replaced body;
- clothing connected to a previous armature;
- an incomplete toggle;
- a stuck animation;
- a material that does not change;
- a broken PhysBone; and
- misaligned PC and Quest variants.

# Stage H — Quest Preparation and Conversion

## v0.7.0 — Quest Environment Readiness

- Check compatible Unity.
- Check compatible SDK.
- Check Android Build Support.
- Check the available platform and tools.
- Provide exact instructions for missing requirements.

## v0.7.1 — Quest Compatibility Report

- Identify incompatible components.
- Identify incompatible shaders.
- Report hard limits.
- Report Performance Rank.
- Estimate sizes.
- Identify affected dependencies.

## v0.7.2 — Non-Destructive Quest Variant

- Create a Quest copy or variant.
- Keep PC intact.
- Duplicate only modified assets.
- Prepare Per-Platform Overrides.

## v0.7.3 — Shader and Material Conversion

- Add an adapter framework.
- Convert to compatible mobile shaders.
- Transfer known properties safely.
- Provide preview and rollback.

## v0.7.4 — Texture and Component Conversion Plan

- Plan texture reduction.
- Plan Android overrides.
- Remove or replace incompatible components.
- Repair dependencies.

## v0.7.5 — Quest Priority Profiles

Profiles:

- maximum visual similarity;
- balanced; and
- maximum performance.

Allow users to mark priority features.

## v0.7.6 — Dynamic Quest Budget

- Recalculate triangles, materials, textures, and components.
- Show the impact of every decision.
- Distinguish a recommended target from an absolute limit.

## v0.7.7 — Quest Conversion Execution

- Apply safe changes in groups.
- Validate after changes.
- Report everything preserved, converted, and removed.

# Stage I — Multi-Platform Comparison and Publishing

## v0.8.0 — PC and Quest Functional Parity

- Compare menus.
- Compare parameters.
- Compare animations.
- Compare toggles.
- Compare objects.
- Compare priority features.

## v0.8.1 — Local Visual Comparison

- Produce comparable local captures.
- Detect pink or missing materials.
- Identify relevant differences in the face, body, eyes, and clothing.
- Use no artificial intelligence or remote processing.

## v0.8.2 — Build Guardian

- Analyze before a build.
- Report critical errors.
- Report warnings.
- Capture a snapshot.
- Require an explicit decision to continue.

## v0.8.3 — Build and Test

- Support PC Build & Test.
- Support Android/Quest Build & Test.
- Run ADB checks.
- Read results.
- Provide a manual checklist.

## v0.8.4 — Multi-Platform Publisher

- Use the same Avatar ID.
- Support Per-Platform Overrides.
- Perform final validation.
- Publish PC and Quest sequentially.
- Do not store credentials.
- Keep a local publishing history.

# Stage J — Avatar Remote

## v0.9.0 — Desktop Bridge Foundation

- Create a local application.
- Add configuration.
- Add logs.
- Do not add Unity Remote functionality.

## v0.9.1 — OSC Output

- Send Bool, Int, and Float values to VRChat.
- Validate addresses and types.

## v0.9.2 — OSC Input and Discovery

- Receive changes.
- Support OSCQuery.
- Detect the current avatar.
- Reconnect safely.

## v0.9.3 — Secure Local Pairing

- Use a local WebSocket.
- Use a QR code.
- Use a temporary token.
- Reject unauthorized connections.

## v0.9.4 — Mobile PWA

- Make it installable on iPhone and Android.
- Generate controls automatically.
- Require no app stores.
- Require no remote server.

## v0.9.5 — Presets and Custom Panels

- Add presets.
- Add panels.
- Add sliders.
- Add buttons.
- Add gestures.
- Add reset behavior.

# Stage K — Ecosystem and Stabilization

## v0.10.0 — Integration Adapter API

- Provide a public, documented adapter API.
- Keep integrations decoupled.

## v0.10.1 — VRCFury and Modular Avatar Awareness

- Detect source components.
- Avoid modifying generated outputs.
- Keep initial diagnosis read-only.

## v0.10.2 — Shader Integrations

- Add optional adapters.
- Support Poiyomi and lilToon when installed.
- Do not redistribute external assets.

## v0.10.3 — Rule Packs and Compatibility Matrix

- Add rule packs.
- Add a Unity, SDK, and package compatibility matrix.
- Version fixtures.

## v0.10.4 — Security, Accessibility and Documentation

- Perform a local audit.
- Document privacy.
- Improve accessibility.
- Document installation, use, and recovery.

# Stage L — Beta and Stable Release

## v0.11.0 — Public Beta

- Provide public VPM installation.
- Provide error reporting.
- Add no automatic telemetry.
- Use controlled real-world cases.

## v0.11.1 — Beta Reliability

- Fix critical failures.
- Reduce false positives.
- Improve rollback.

## v0.11.2 — Beta Performance

- Support large avatars.
- Make scans cancelable.
- Add caching.
- Improve memory use.

## v0.11.3 — Release Candidate Preparation

- Freeze functionality.
- Finalize documentation.
- Prepare migrations.
- Validate compatibility.

## v1.0.0-rc.1 — First Release Candidate

- Perform complete validation.
- Add no new functionality.

## v1.0.0-rc.2 — Final Release Candidate

- Make blocking fixes only.
- Validate distribution.

## v1.0.0 — Stable Release

- Explainable diagnostics.
- Safe repairs.
- Quest conversion.
- PC/Quest publishing.
- Avatar Remote.
- VPM installation.
- Mandatory USD 0 cost.
- Complete documentation.

## 14. Final rule

Do not begin future release work early, even when it appears simple.

When a release instruction is received:

1. inspect the real state;
2. limit the scope;
3. implement;
4. verify;
5. create controlled commits;
6. push only the working branch;
7. open a Draft Pull Request; and
8. provide the final diagnosis in Spanish outside the repository.
