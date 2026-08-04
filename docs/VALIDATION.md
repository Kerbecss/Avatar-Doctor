# Repository Validation

## Purpose

Avatar Doctor uses a deterministic, non-mutating repository validator to enforce versioned project policy. It inspects tracked files, uses only the Python standard library, performs no network access, and makes no automatic changes.

Repository validation does not compile Unity and does not replace human review.

## Requirements

- Python 3.
- Git.
- No third-party Python packages.

## Local execution

From the repository root:

```shell
python ci/validate_repository.py --root .
```

From another directory:

```shell
python <repo-root>/ci/validate_repository.py --root <repo-root>
```

The `--root` value must identify the Git repository root. Without it, the validator asks Git to resolve the repository containing the current directory.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Validation passed. |
| `1` | Repository policy violations were found. |
| `2` | Validator execution or configuration failed. |

## Checks

- `MANIFEST` validates package metadata, URLs, version syntax, and dependency policy.
- `VERSION` compares the manifest, C# constant, changelog heading, and comparison links.
- `IDENTITY` compares package, source, assembly, and policy identity.
- `STRUCTURE` enforces required repository and package files, the current source count, the Editor-only assembly, and the absence of future package directories.
- `ASSEMBLY` validates the single Editor-only assembly definition.
- `SOURCE` applies exact profiles to the two authorized C# source files.
- `EDITOR_WINDOW` validates the current window shell, menu path, visible labels, minimum size, metadata, and absence of functional controls.
- `UNITY_METADATA` validates code-asset metadata and GUID uniqueness without importing Unity.
- `TEXT_HYGIENE` validates UTF-8 text, whitespace, final newlines, and conflict markers.
- `LANGUAGE` applies basic English-language guardrails to maintained text.
- `PRIVACY` detects local path formats and unapproved email addresses.
- `SECRETS` detects a narrow set of high-signal credential patterns.
- `PROHIBITED_FILES` rejects generated files, operating-system clutter, and archives.
- `WORKFLOWS` protects distribution gates and the read-only validation workflow.
- `ROADMAP_GUARD` validates the public roadmap release order, headings, and unique versions.
- `PUBLIC_CONTENT` validates maintained public documentation and the active package scope.

## Success output

A valid repository ends with:

```text
Repository validation passed.
Checks: 16
Passed: 16
Failed: 0
```

## Findings and troubleshooting

Each policy finding reports a check identifier, relative path, explanation, and expected value when useful. The validator aggregates findings in a stable order so related problems remain visible together.

To resolve a failure:

1. Read the check identifier and path.
2. Compare the observed value with the expected value.
3. Correct the maintained source or policy without weakening unrelated checks.
4. Run validation again.
5. Record the command and result in the Pull Request.

Unexpected execution or policy-loading failures return exit code `2`.

## Public content validation

`PUBLIC_CONTENT` scans the root README, contribution guide, package README and changelog, documentation Markdown, GitHub Markdown templates, and maintained Website text files. It protects the public documentation structure, current product scope, roadmap numbering, and contributor identity guidance.

The check does not inspect Git history, historical Releases, closed Pull Requests, closed Issues, third-party licenses, binaries, temporary logs, or inherited third-party packages.

Public-content policy is intentionally narrow. Positive technical language such as `rule-based diagnostics`, `deterministic evidence`, `maintainer review`, `privacy`, `secrets`, `MIT License`, and `VPM/VCC` is supported.

## Privacy and security

`PRIVACY` detects common local path formats and email addresses that are not explicitly approved public metadata. `SECRETS` detects high-signal private-key, access-token, cloud-key, API-key, and assigned-credential patterns. `PROHIBITED_FILES` rejects generated caches and packaged artifacts that do not belong in the tracked development tree.

These checks are focused guardrails and do not replace dedicated security review.

## Source profiles

The source policy is bound to exact package paths:

- `Editor/Core/AvatarDoctorPackageInfo.cs` permits the current internal package constants.
- `Editor/UI/AvatarDoctorWindow.cs` permits only the current Editor window shell.

The window profile narrowly authorizes the required UI Toolkit construction. Unimplemented product behavior, additional source files, mutable state, event handlers, asset access, build operations, and SDK types remain outside the current source profile.

## Protected workflow

The validation workflow remains named `Repository Validation`, and its only job remains `validate`. It runs for Pull Requests, pushes to `main`, and manual dispatch with read-only contents permission, disabled checkout credential persistence, and no secrets or artifacts.

The required status context is `Repository Validation / validate`.

## Unity validation

Unity changes require a separate pass with Unity `2022.3.22f1`. A batch import can validate compilation:

```powershell
<Unity-2022.3.22f1> -batchmode -nographics -quit -projectPath <repo-root> -logFile <unity-log>
```

Visible validation for the current shell confirms:

1. Import completes and the Editor assembly compiles without Avatar Doctor errors.
2. `Tools → Avatar Doctor` opens one window titled `Avatar Doctor`.
3. The window is dockable and keeps a minimum size of `420 × 220`.
4. The heading, pre-alpha status, unavailable-analysis message, and `Version 0.0.5` appear once and in order.
5. No buttons or functional controls exist.
6. Reopening the menu reuses the existing window.
7. Domain Reload does not duplicate visual elements.
8. Unity creates no unauthorized tracked changes.

## Scope limitations

Repository validation does not:

- import or compile Unity;
- validate VPM or VCC installation;
- provide complete secret scanning;
- guarantee natural-language quality;
- access the network;
- modify files;
- publish artifacts; or
- replace human review.
