# Avatar Doctor Roadmap

## Current status

Avatar Doctor is at version `0.0.5`. The repository contains public user and contributor documentation, deterministic repository validation, an Editor-only assembly, and a non-functional UI Toolkit window shell available through `Tools → Avatar Doctor`.

Avatar discovery, scanning, diagnostics, repairs, SDK integration, Quest preparation, build validation, publishing, and public VPM distribution remain planned.

## Released foundation

- `v0.0.1` established the repository, package identity, license, and initial documentation.
- `v0.0.2` added the Editor-only package skeleton, namespaces, and identity constants.
- `v0.0.3` added deterministic repository validation and read-only CI.
- `v0.0.4` added the first Unity Editor window shell and menu entry.
- `v0.0.5` refocuses public documentation, contributor guidance, roadmap structure, and active package scope.

## Planned releases

### Stage A — Foundation

#### v0.0.1 — Repository Foundation

- Establish the VPM package repository, identity, license, and initial documentation.

#### v0.0.2 — Package Skeleton

- Add the Editor-only assembly, namespace, and package identity constants.

#### v0.0.3 — Repository Validation

- Add deterministic local and CI validation for repository policy.

#### v0.0.4 — Editor Window Shell

- Add `Tools → Avatar Doctor` and the first non-functional Editor window.

#### v0.0.5 — Public Documentation Cleanup

- Provide clear public documentation and contributor guidance.
- Narrow the active roadmap and architecture to the Unity package.
- Guard the revised public-content contract.

#### v0.0.6 — Release Pipeline

- Verify VPM automation and reproducible package artifacts.
- Validate a clean installation from a GitHub Release.
- Document recovery from failed releases.

### Stage B — Avatar Scanner

#### v0.1.0 — Avatar Discovery

- Find Avatar Descriptors in the scene.
- Support manual and automatic selection.
- Handle zero, one, and multiple avatar states.

#### v0.1.1 — Hierarchy Snapshot

- Capture paths, objects, active state, and components.
- Produce an immutable analysis snapshot.

#### v0.1.2 — Component and Asset Inventory

- Inventory renderers, animators, materials, meshes, and assets.

#### v0.1.3 — Reference Graph

- Record incoming and outgoing references.
- Distinguish internal, external, null, and package references.

#### v0.1.4 — Results Interface and Export

- Display searchable and filterable results.
- Navigate to affected objects.
- Export JSON and HTML evidence.

### Stage C — Structural Diagnostics

#### v0.2.0 — Descriptor Diagnostics

- Detect missing, duplicated, misplaced, or incomplete Avatar Descriptors.

#### v0.2.1 — Rig and Animator Diagnostics

- Detect missing Animators, incomplete humanoid rigs, unassigned bones, and suspicious transforms.

#### v0.2.2 — Missing and External References

- Detect Missing Scripts, null references, external references, and inaccessible assets.

#### v0.2.3 — Renderer and Root Bone Diagnostics

- Detect invalid Root Bones, cross-armature renderers, and empty material slots.

#### v0.2.4 — Bone Mapping Diagnostics

- Detect null or external bones, exact path candidates, and previous-armature remnants.

#### v0.2.5 — Mesh and Blendshape Diagnostics

- Detect invalid blendshape bindings, suspicious bounds, duplicate meshes, and missing meshes.

### Stage D — Menus, Parameters, and Animators

#### v0.3.0 — Expression Inventory

- Read expression parameters, menus, controls, and submenus.

#### v0.3.1 — Parameter Diagnostics

- Detect missing, incompatible, duplicated, or inconsistent parameters.

#### v0.3.2 — Menu Diagnostics

- Detect null controls, empty submenus, cycles, unreachable controls, and broken references.

#### v0.3.3 — Animator Graph Extraction

- Extract layers, states, motions, transitions, and conditions into a navigable graph.

#### v0.3.4 — Animator Flow Diagnostics

- Detect unreachable states, missing exits, impossible transitions, and contradictory conditions.

#### v0.3.5 — Animation Binding Diagnostics

- Detect invalid paths, properties, material slots, and blendshape bindings.
- Trace complete toggle behavior.

### Stage E — Repair Engine

#### v0.4.0 — Repair Transactions

- Add preview, diff, Undo, backup, validation, and rollback foundations.

#### v0.4.1 — Safe Reference Repairs

- Repair null references only when evidence identifies an unambiguous match.

#### v0.4.2 — Root Bone and Bone Remapping

- Assign safe Root Bones and remap bones by exact paths with post-change validation.

#### v0.4.3 — Expressions Repairs

- Create missing parameters, correct compatible types, and repair menu references.

#### v0.4.4 — Animation Repairs

- Repair unambiguous bindings using copies of shared animation clips.

#### v0.4.5 — Safe Toggle Builder and Rollback

- Build complete toggles inside Unity and roll back changes that introduce new errors.

### Stage F — Materials, Dynamics, and Performance

#### v0.5.0 — Material and Shader Inspection

- Inventory material properties and detect missing or duplicated materials and shaders.

#### v0.5.1 — Animated Shader Properties

- Detect invalid animated properties and mismatched material bindings.

#### v0.5.2 — Texture Audit

- Record texture resolution, format, memory estimates, duplicates, and relevant import settings.

#### v0.5.3 — PhysBones and Contacts

- Detect invalid roots, colliders, chains, parameters, and Contact configuration.

#### v0.5.4 — Constraints and Performance

- Detect invalid sources and circular constraints.
- Provide prioritized performance recommendations.

### Stage G — Explainable Intelligence

This stage builds documented evidence graphs, rule correlation, and confidence scoring. Every finding remains traceable to deterministic inputs and explicit rules.

#### v0.6.0 — Evidence Graph

- Connect findings, objects, assets, and dependencies through reusable evidence.

#### v0.6.1 — Root Cause Correlation

- Group related symptoms under probable causes and reduce duplicate findings.

#### v0.6.2 — Confidence Scoring

- Define a documented formula and explain each confidence level.

#### v0.6.3 — Repair Planning

- Order repairs by dependency and recalculate plans after each change.

#### v0.6.4 — Scenario Library

- Add representative regression scenarios for structural, animation, material, dynamics, and platform issues.

### Stage H — Quest Preparation and Conversion

#### v0.7.0 — Quest Environment Readiness

- Check Unity, SDK, Android support, platform, and required tooling readiness.

#### v0.7.1 — Quest Compatibility Report

- Report incompatible components and shaders, limits, rank, size estimates, and dependencies.

#### v0.7.2 — Non-Destructive Quest Variant

- Create a platform variant while keeping the PC configuration intact.

#### v0.7.3 — Shader and Material Conversion

- Convert supported materials through adapters with preview and rollback.

#### v0.7.4 — Texture and Component Conversion Plan

- Plan texture reduction, Android overrides, component replacement, and dependency repairs.

#### v0.7.5 — Quest Priority Profiles

- Provide visual-similarity, balanced, and performance profiles with user priorities.

#### v0.7.6 — Dynamic Quest Budget

- Recalculate geometry, materials, textures, and components after each decision.

#### v0.7.7 — Quest Conversion Execution

- Apply safe grouped changes and report everything preserved, converted, or removed.

### Stage I — Multi-Platform Comparison and Publishing

#### v0.8.0 — PC and Quest Functional Parity

- Compare menus, parameters, animations, toggles, objects, and priority features.

#### v0.8.1 — Local Visual Comparison

- Produce comparable local captures and identify material and appearance differences.

#### v0.8.2 — Build Guardian

- Analyze before builds, report risks, capture evidence, and require a user decision to continue.

#### v0.8.3 — Build and Test

- Support PC and Android test builds with recorded results and manual checks.

#### v0.8.4 — Multi-Platform Publisher

- Validate and publish PC and Quest sequentially under the same Avatar ID.
- Keep local publishing evidence without storing credentials.

### Stage J — Ecosystem and Stabilization

#### v0.9.0 — Integration Adapter API

- Provide a documented, decoupled adapter API.

#### v0.9.1 — VRCFury and Modular Avatar Awareness

- Detect supported source components while preserving generated outputs.

#### v0.9.2 — Shader Integrations

- Add optional adapters for supported installed shaders without redistributing their assets.

#### v0.9.3 — Rule Packs and Compatibility Matrix

- Version rule packs, fixtures, and Unity, SDK, and package compatibility data.

#### v0.9.4 — Security, Accessibility and Documentation

- Review security and privacy, improve accessibility, and complete installation and recovery guidance.

### Stage K — Beta and Stable Release

#### v0.10.0 — Public Beta

- Provide public VPM installation and controlled real-world testing.

#### v0.10.1 — Beta Reliability

- Fix critical failures, reduce false positives, and improve rollback.

#### v0.10.2 — Beta Performance

- Support large avatars, cancelable scans, caching, and improved memory use.

#### v0.10.3 — Release Candidate Preparation

- Freeze functionality, finalize documentation, prepare migrations, and validate compatibility.

#### v1.0.0-rc.1 — First Release Candidate

- Perform complete validation without adding functionality.

#### v1.0.0-rc.2 — Final Release Candidate

- Apply blocking fixes and validate distribution.

#### v1.0.0 — Stable Release

- Explainable diagnostics.
- Safe repairs.
- Quest conversion.
- PC and Quest comparison.
- Multi-platform publishing assistance.
- VPM installation.
- Complete user and contributor documentation.
