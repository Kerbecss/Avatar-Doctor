# Planned Architecture

## Status

This document describes the intended architecture of Avatar Doctor. Version `0.0.4` implements an Editor-only package shell with one visible UI Toolkit window. All avatar-processing modules described below remain **not implemented**.

## Current implementation state

### Implemented through v0.0.4

- One Editor-only assembly: `Teyocesu.AvatarDoctor.Editor`.
- Stable root namespace: `Teyocesu.AvatarDoctor.Editor`.
- Internal package identity constants.
- Deterministic repository validation.
- One code-only UI Toolkit Editor window shell.
- One `Tools/Avatar Doctor` menu entry.
- Domain Reload-safe visual-tree rebuilding through `CreateGUI` and `Clear()`.

### Not implemented

- Avatar discovery.
- Scanner.
- Diagnostics.
- Repairs.
- VRChat SDK integration.
- Quest conversion.
- Publishing.
- Avatar Remote.

The current window is a presentation-only shell. It does not access scenes, assets, avatars, or other project data, and it contains no functional controls.

## System boundary

Avatar Doctor is planned as a local Unity Editor package for VRChat avatar inspection, deterministic diagnosis, safe repair, Quest preparation, and multi-platform publishing assistance.

All avatar analysis and project modification will occur locally on the computer where Unity is open. The project will not require paid AI APIs, project-owned servers, hosted databases, remote telemetry, or stored VRChat credentials.

External Blender workflows are outside the system boundary. The package may identify observable rig, renderer, or mesh problems, but it will not perform modeling, weight painting, external rigging, or vertex editing.

## Planned repository layout

```text
Avatar-Doctor/
├── Packages/
│   └── com.teyocesu.avatar-doctor/
│       ├── Editor/
│       │   ├── Teyocesu.AvatarDoctor.Editor.asmdef  # Implemented
│       │   ├── Core/                                # Implemented
│       │   │   └── AvatarDoctorPackageInfo.cs
│       │   ├── UI/                                  # Window shell implemented
│       │   │   └── AvatarDoctorWindow.cs
│       │   ├── Scanning/                            # Future
│       │   ├── Diagnostics/                         # Future
│       │   ├── Rules/                               # Future
│       │   ├── Correlation/                         # Future
│       │   ├── Repairs/                             # Future
│       │   ├── Quest/                               # Future
│       │   ├── Publishing/                          # Future
│       │   └── Integrations/                        # Future
│       ├── Tests/                                   # Future
│       │   ├── Editor/
│       │   └── Fixtures/
│       └── Documentation~/                          # Future package documentation
├── AvatarRemote/                   # Future, separate subsystem
│   ├── Bridge/
│   └── Pwa/
├── docs/
│   └── decisions/                  # Future Architecture Decision Records
└── .github/
```

The layout may evolve. A material architectural change requires an English Architecture Decision Record before implementation.

## Planned Unity package layers

The Unity package is expected to keep analysis separate from mutation:

1. **Scanning** will collect immutable evidence about hierarchy, components, assets, and references.
2. **Rules** will evaluate individual deterministic conditions without modifying project state.
3. **Diagnostics** will turn rule results into explainable findings with location, evidence, impact, probable cause, repair options, risk, and confidence.
4. **Correlation** will connect evidence and dependencies, group symptoms under probable root causes, and calculate documented confidence scores.
5. **Repairs** will plan and apply only safe operations using preview, diff, Undo, backup, validation, and rollback.
6. **Quest** will assess compatibility and create non-destructive platform variants.
7. **Publishing** will guard builds and coordinate PC and Android uploads under the same Avatar ID without storing credentials.
8. **UI** will present results and navigation while remaining decoupled from the rule engine.
9. **Integrations** will expose optional adapters for installed third-party tools without modifying their generated outputs or redistributing their assets.

The `UI` layer currently contains only the non-functional window shell. None of the scanning, diagnostic, repair, Quest, publishing, or integration behavior described above is implemented in `v0.0.4`. The Editor-only assembly contains the internal package information class and the internal window class only.

## Deterministic expert system

The planned diagnostic core will not depend on generative AI. Its reasoning pipeline is expected to use:

1. evidence collection;
2. individual rules;
3. a dependency graph;
4. error correlation;
5. root-cause detection;
6. explainable confidence derived from documented objective evidence;
7. repair ordering;
8. post-repair validation; and
9. false-positive controls.

Rules and correlation must use public, documented Unity and VRChat APIs. Reflection over private VRChat SDK internals is outside the design.

## Avatar Doctor and Avatar Remote separation

Avatar Remote is a future, separate local subsystem. It may provide a desktop bridge and installable mobile PWA for VRChat OSC parameters.

Avatar Remote will be allowed to:

- send and receive supported OSC values;
- discover the current VRChat avatar through local OSCQuery;
- use authenticated local pairing; and
- present presets and custom controls.

It will not:

- read or modify Unity project files;
- create Unity toggles;
- run builds or publish avatars;
- change project materials;
- execute arbitrary code on the PC; or
- control the Unity Editor remotely.

The two subsystems may share documented data contracts in the future, but Avatar Remote must not become a remote project editor.

## VPM packaging

Avatar Doctor is planned to become installable through VPM and VRChat Creator Companion after its distribution pipeline is validated. Version `v0.0.4` is not installable through VCC. The package root is:

```text
Packages/com.teyocesu.avatar-doctor/
```

Release artifacts are planned to include the package manifest, a package archive, and a Unity package when the release pipeline is authorized and validated. Release pipeline completion belongs to a later release and is not claimed here.

## Open technical decisions

The following decisions remain open and must be resolved in their authorized releases:

- future assembly boundaries and namespace organization below the stable `Teyocesu.AvatarDoctor.Editor` root;
- immutable snapshot data structures;
- rule registration and result schemas;
- evidence graph representation and confidence formula;
- repair transaction, backup, and rollback formats;
- localization resource format;
- SDK compatibility adapter boundaries;
- Quest variant asset ownership and override strategy;
- build and publishing orchestration using public SDK APIs; and
- local bridge technology and secure pairing for Avatar Remote.
