# Repository Validation

## Purpose

Avatar Doctor uses a deterministic, non-mutating repository validator to enforce versioned project policy. The validator inspects tracked files only, uses the Python standard library, performs no network access, and makes no automatic changes.

Repository validation protects development infrastructure. It is not part of the avatar diagnostic engine and does not compile or import the Unity project.

## Requirements

- Python 3
- Git
- No third-party Python packages

## Local execution

From the repository root:

```shell
python3 ci/validate_repository.py
```

From another directory:

```shell
python3 <repo-root>/ci/validate_repository.py --root <repo-root>
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
- `STRUCTURE` enforces required files and current-release package boundaries.
- `ASSEMBLY` enforces the single Editor-only assembly definition.
- `SOURCE` applies conservative source-pattern restrictions for the current release.
- `UNITY_METADATA` validates code-asset metadata structure and GUID uniqueness without importing Unity.
- `TEXT_HYGIENE` validates tracked text encoding, whitespace, final newlines, and conflict markers.
- `LANGUAGE` applies basic Spanish-character and marker guardrails to public text.
- `PRIVACY` detects common personal path formats and unapproved email addresses.
- `SECRETS` detects a narrow set of high-signal credential patterns.
- `PROHIBITED_FILES` rejects tracked operating-system clutter, archives, and generated files.
- `WORKFLOWS` protects distribution gates and the read-only validation workflow.
- `ROADMAP_GUARD` preserves required release and scope boundaries.

## Success output

A valid repository ends with output equivalent to:

```text
[PASS] MANIFEST — Package manifest is valid.
[PASS] VERSION — Package version references are consistent.
[PASS] IDENTITY — Package identity is consistent.
[PASS] STRUCTURE — Required repository structure is valid.
[PASS] ASSEMBLY — Editor assembly configuration is valid.
[PASS] SOURCE — Package source remains within the authorized scope.
[PASS] UNITY_METADATA — Unity metadata is structurally valid.
[PASS] TEXT_HYGIENE — Tracked text files satisfy the active hygiene policy.
[PASS] LANGUAGE — No basic non-English language markers were found.
[PASS] PRIVACY — No personal path or unapproved email patterns were found.
[PASS] SECRETS — No high-signal secret patterns were found.
[PASS] PROHIBITED_FILES — No prohibited tracked files were found.
[PASS] WORKFLOWS — Protected workflow conditions are valid.
[PASS] ROADMAP_GUARD — Required roadmap boundaries are present.

Repository validation passed.
Checks: 14
Passed: 14
Failed: 0
```

## Failure output

Policy violations include the check identifier, affected relative path, explanation, and expected value when useful. For example:

```text
[FAIL] VERSION — Packages/com.teyocesu.avatar-doctor/Editor/Core/AvatarDoctorPackageInfo.cs: Version constant is '9.9.9'. Expected: 0.0.3

Repository validation failed.
Checks: 14
Passed: 13
Failed: 1
```

The full output also includes pass results for checks without findings.

## Error aggregation

The validator executes every available check and reports all policy violations in a stable order before returning a final exit code. This makes related problems visible together instead of hiding later findings behind the first failure.

## Troubleshooting

1. Read the check identifier and affected relative path.
2. Compare the reported value with the expected value.
3. Correct only the authorized repository content.
4. Run the validator again.
5. Do not disable or weaken a check only to obtain a passing result.

Unexpected execution or policy-loading failures return exit code `2`.

## Policy changes

Changes to `ci/validation-policy.json` alter repository acceptance rules and require focused review. Policy changes must remain deterministic, readable, narrowly scoped, and consistent with the authorized release.

The initial policy contains hash-bound hygiene exceptions for inherited files that already violated whitespace or final-newline rules at the approved base. Each exception identifies one relative path, the exact SHA-256 of its unchanged content, and only the inherited rule. Editing an excepted file invalidates its exception; new violations are never accepted automatically.

## Scope limitations

Repository validation does not:

- compile or import Unity;
- validate VPM or VCC installation;
- provide complete secret scanning;
- guarantee that natural-language content is English;
- access the network;
- modify files;
- create commits;
- execute workflows;
- publish artifacts; or
- replace external review.
