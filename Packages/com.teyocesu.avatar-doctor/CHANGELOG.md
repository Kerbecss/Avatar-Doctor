# Changelog

All notable changes to Avatar Doctor will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

No unreleased changes.

## [0.0.6] - 2026-08-12

### Added

- Deterministic VPM release artifact building and verification.
- Release-pipeline unit tests and reproducibility validation.
- Non-public local VPM listing verification for published release artifacts.
- Release verification, clean-installation, and recovery documentation.

### Changed

- Hardened the manual release workflow to build read-only GitHub Actions artifacts without publishing.
- Removed automatic Git tag and GitHub Release creation from the release workflow.
- Removed GitHub Pages deployment from the listing-verification workflow.
- Updated package metadata and internal version constants to `0.0.6`.

## [0.0.5] - 2026-08-04

### Added

- Public contribution guidance focused on setup, validation, and Pull Requests.
- Repository validation for the active public documentation and roadmap structure.

### Changed

- Rewrote public project documentation for users and contributors.
- Refocused the architecture and roadmap on the Avatar Doctor Unity package.
- Renumbered unreleased ecosystem and beta milestones after narrowing the active product scope.
- Replaced internal process notes with conventional contributor and maintainer guidance.
- Updated package metadata and internal version constants to `0.0.5`.
- Moved release-pipeline planning to `v0.0.6`.

## [0.0.4] - 2026-08-04

### Added

- First code-only UI Toolkit Editor window shell.
- `Tools/Avatar Doctor` menu entry.
- Dedicated repository validation for the authorized Editor window shape.

### Changed

- Updated package metadata and internal version constants to `0.0.4`.
- Updated the commit-pinned checkout action used by repository validation.
- Extended source policy from a constants-only skeleton to the explicitly authorized window shell.

## [0.0.3] - 2026-08-03

### Added

- Deterministic standard-library-only repository validation.
- Read-only GitHub Actions validation for Pull Requests and `main`.
- Repository validation policy and local troubleshooting documentation.

### Changed

- Updated package metadata and internal version constants to `0.0.3`.
- Updated the controlled workflow to require successful repository validation before release approval.

## [0.0.2] - 2026-08-03

### Added

- Initial Editor-only assembly definition.
- Stable package namespace and internal package identity constants.
- Tracked Unity metadata for the initial source structure.

### Changed

- Updated package metadata to version `0.0.2`.

## [0.0.1] - 2026-08-03

### Added

- Initial VPM package metadata and public project identity.
- Package documentation and MIT license.

### Security

- Disabled Unity project analytics settings inherited from the template.
- Restricted manual release automation to the `main` branch.

[Unreleased]: https://github.com/Teyocesu/Avatar-Doctor/compare/v0.0.6...HEAD
[0.0.6]: https://github.com/Teyocesu/Avatar-Doctor/compare/v0.0.5...v0.0.6
[0.0.5]: https://github.com/Teyocesu/Avatar-Doctor/compare/v0.0.4...v0.0.5
[0.0.4]: https://github.com/Teyocesu/Avatar-Doctor/compare/v0.0.3...v0.0.4
[0.0.3]: https://github.com/Teyocesu/Avatar-Doctor/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/Teyocesu/Avatar-Doctor/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/Teyocesu/Avatar-Doctor/releases/tag/v0.0.1
