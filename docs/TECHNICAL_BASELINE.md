# Technical Baseline

Last reviewed: 2026-08-04.

## Package baseline

| Item | Current value |
| --- | --- |
| Package | Avatar Doctor |
| Package ID | `com.teyocesu.avatar-doctor` |
| Current version | `0.0.5` |
| Unity | `2022.3.22f1` |
| Assembly | `Teyocesu.AvatarDoctor.Editor` |
| Assembly scope | Editor only |
| License | MIT |
| Distribution | Not available from a public VCC listing |

The package contains no Runtime assembly and no public API. The implemented source consists of package identity constants and a code-only UI Toolkit Editor window shell.

## Development environment

- Git is required for repository operations and tracked-file discovery.
- Python 3 is required for deterministic repository validation.
- VCC is the recommended way to open the project on Windows.
- Unity `2022.3.22f1` is required for the project's Unity validation.
- GitHub Actions runs the same repository validator for Pull Requests and `main`.

Repository validation uses only the Python standard library and does not install dependencies or access the network.

## Unity status

The Editor window shell introduced in `v0.0.4` was imported and compiled with Unity `2022.3.22f1`. The menu entry `Tools → Avatar Doctor` opens one dockable window, and the window remains presentation-only in `v0.0.5`.

The package declares no VRChat SDK dependency. The inherited `com.vrchat.core.bootstrap` package is a project bootstrap component and must not be interpreted as an installed Avatars SDK.

## Distribution status

The package manifest keeps an empty `url` field because no distributable archive exists. The repository does not publish a VPM listing or GitHub Pages site, and distribution enablement variables remain unset.

Artifact generation, clean-install verification, listing generation, and recovery procedures are planned for `v0.0.6 — Release Pipeline`.

## Validation boundaries

Repository validation checks tracked source, metadata, documentation, and workflow policy. Unity validation separately checks import, compilation, menu availability, visible window behavior, and generated changes. VPM installation and release artifacts remain unverified until the release pipeline is implemented.
