# Technical Baseline

Last reviewed: 2026-08-12.

## Package baseline

| Item | Current value |
| --- | --- |
| Package | Avatar Doctor |
| Package ID | `com.teyocesu.avatar-doctor` |
| Current version | `0.0.6` |
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
- GitHub Actions runs the repository validator, release-pipeline unit tests, and a two-build reproducibility comparison for Pull Requests and `main`.

Repository validation uses only the Python standard library and does not install dependencies or access the network.

## Unity status

The Editor window shell introduced in `v0.0.4` was imported and compiled with Unity `2022.3.22f1`. The menu entry `Tools → Avatar Doctor` opens one dockable window, and the window remains presentation-only in `v0.0.6`.

The package declares no VRChat SDK dependency. The inherited `com.vrchat.core.bootstrap` package is a project bootstrap component and must not be interpreted as an installed Avatars SDK.

## Distribution status

The package manifest points to the versioned `v0.0.6` GitHub prerelease ZIP. Before the prerelease is published, that URL is expected not to resolve.

`ci/release_pipeline.py` builds the VPM ZIP from tracked package blobs at `HEAD`, sorts archive paths, normalizes ZIP metadata, copies `package.json`, and writes lowercase SHA-256 checksums. Stored ZIP entries avoid compressor-version differences between supported Python runtimes.

The manual `Build Release Artifacts` workflow validates the repository, runs the release-pipeline tests, compares two independent builds byte-for-byte, verifies the exact artifact set, and uploads only a short-lived GitHub Actions artifact.

The separate manual `Build VPM Verification Listing` workflow is intended for post-publication verification. It produces a non-public local listing, validates the expected package version, release URL, ZIP hash, and tagged package tree, and uploads only the listing artifact. Public VPM listing and GitHub Pages deployment remain disabled.

## Validation boundaries

Repository validation checks tracked source, metadata, documentation, and workflow policy. Release-pipeline tests separately validate deterministic artifact construction, archive safety, checksums, listing structure, and remote artifact verification. Unity validation remains responsible for import, compilation, menu availability, visible window behavior, and generated changes.

A clean VPM installation on Windows remains pending until the `v0.0.6` prerelease and verification listing exist.
