# Avatar Doctor Architecture

## Current implementation

Version `0.0.5` contains an Editor-only Unity package with:

- assembly `Teyocesu.AvatarDoctor.Editor`;
- internal package identity and version constants;
- one code-only UI Toolkit Editor window;
- menu entry `Tools → Avatar Doctor`; and
- deterministic repository validation.

The window is a presentation-only shell. It does not inspect scenes, access assets, discover avatars, run diagnostics, apply repairs, use SDK APIs, build, or publish.

## Package boundary

Avatar Doctor is designed as a Unity Editor package for VRChat avatar inspection, rule-based diagnostics, safe repairs, Quest preparation, build validation, and multi-platform publishing assistance.

Evidence collection and project changes remain inside the Unity project. Findings will be based on deterministic rules and traceable evidence. Changes will be previewable, reviewable, and reversible through Unity-supported mechanisms.

The package root is:

```text
Packages/com.teyocesu.avatar-doctor/
```

## Repository layout

```text
Packages/com.teyocesu.avatar-doctor/
├── Editor/
│   ├── Teyocesu.AvatarDoctor.Editor.asmdef
│   ├── Core/
│   │   └── AvatarDoctorPackageInfo.cs
│   ├── UI/
│   │   └── AvatarDoctorWindow.cs
│   ├── Scanning/        # Planned
│   ├── Rules/           # Planned
│   ├── Diagnostics/     # Planned
│   ├── Correlation/     # Planned
│   ├── Repairs/         # Planned
│   ├── Quest/           # Planned
│   ├── Publishing/      # Planned
│   └── Integrations/    # Planned
├── Tests/               # Planned
│   ├── Editor/
│   └── Fixtures/
├── CHANGELOG.md
├── LICENSE.md
├── README.md
└── package.json
```

Only `Core` and the current `UI` shell are implemented. Future directories are added only with the release that implements and validates them.

## Layers

### Core

Owns stable package identity, version information, shared result types, and package-level contracts. Core types should avoid unnecessary Unity state and mutable global data.

### UI

Presents package status, evidence, findings, repair previews, and navigation. UI remains separate from scanning and rule evaluation. The current implementation contains only the window shell.

### Scanning

Will collect immutable snapshots of avatar hierarchy, components, assets, references, and relevant configuration without changing the project.

### Rules

Will evaluate focused deterministic conditions against snapshots. Rules produce structured evidence and do not mutate Unity state.

### Diagnostics

Will convert rule results into explainable findings with location, evidence, impact, probable cause, confidence, and available repair options.

### Correlation

Will connect evidence through dependency graphs, group related symptoms, identify probable root causes, and calculate confidence from documented inputs.

### Repairs

Will plan and apply safe operations with preview, diff, Undo, backup where appropriate, post-change validation, and rollback paths. Ambiguous changes remain manual.

### Quest

Will assess compatibility and prepare non-destructive platform variants while preserving the PC configuration and identifying every changed asset.

### Publishing

Will validate builds and assist sequential PC and Quest publishing under the same Avatar ID using supported public APIs. Credentials will not be stored by the package.

### Integrations

Will provide optional adapters for supported installed tools. Adapters remain decoupled and do not modify generated third-party outputs unexpectedly.

### Tests

Will contain Editor tests, rule fixtures, repair scenarios, regression cases, and compatibility matrices as the corresponding modules are implemented.

### Distribution

The package is not currently available from a public VCC listing. `v0.0.6 — Release Pipeline` will validate package archives, clean installation, listing generation, and recovery procedures before distribution is enabled.

## Diagnostic model

The planned diagnostic flow is:

1. collect an immutable snapshot;
2. evaluate individual rules;
3. record traceable evidence;
4. build dependency and evidence graphs;
5. correlate related findings;
6. calculate documented confidence scores;
7. propose ordered repairs;
8. preview and apply approved changes; and
9. validate the resulting project state.

Rules use documented Unity and VRChat APIs. Findings must remain explainable and reproducible from the captured evidence.

## Open decisions

Future releases will document decisions for snapshot schemas, rule registration, evidence graphs, confidence calculations, repair transactions, localization, SDK compatibility, Quest asset ownership, build orchestration, and integration adapters.
