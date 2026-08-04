# Repository Validation

## Purpose

Avatar Doctor uses a deterministic, non-mutating repository validator to enforce versioned project policy. The validator inspects tracked files only, uses the Python standard library, performs no network access, and makes no automatic changes.

Repository validation protects development infrastructure. It is not part of the avatar diagnostic engine and does not compile or import the Unity project. Unity import, compilation, and visible Editor behavior require a separate real-Editor validation pass.

## Requirements

- Python 3
- Git
- No third-party Python packages

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
- `STRUCTURE` enforces required files, exactly two package C# sources, one Editor window, one menu item, one Editor assembly, no Runtime assembly, and no UXML or USS files.
- `ASSEMBLY` enforces the single Editor-only assembly definition.
- `SOURCE` applies exact file-specific profiles. `AvatarDoctorPackageInfo.cs` remains constants-only, while `AvatarDoctorWindow.cs` permits only the authorized Editor window shell shape.
- `EDITOR_WINDOW` validates the exact namespace, class, menu path, priority, lifecycle methods, visible labels, minimum size, visual-tree rebuilding, metadata, and absence of controls, handlers, mutable state, and prohibited APIs.
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
[PASS] EDITOR_WINDOW — The authorized Editor window shell is valid.
[PASS] UNITY_METADATA — Unity metadata is structurally valid.
[PASS] TEXT_HYGIENE — Tracked text files satisfy the active hygiene policy.
[PASS] LANGUAGE — No basic non-English language markers were found.
[PASS] PRIVACY — No personal path or unapproved email patterns were found.
[PASS] SECRETS — No high-signal secret patterns were found.
[PASS] PROHIBITED_FILES — No prohibited tracked files were found.
[PASS] WORKFLOWS — Protected workflow conditions are valid.
[PASS] ROADMAP_GUARD — Required roadmap boundaries are present.

Repository validation passed.
Checks: 15
Passed: 15
Failed: 0
```

## Failure output

Policy violations include the check identifier, affected relative path, explanation, and expected value when useful. For example:

```text
[FAIL] VERSION — Packages/com.teyocesu.avatar-doctor/Editor/Core/AvatarDoctorPackageInfo.cs: Version constant is '9.9.9'. Expected: 0.0.4

Repository validation failed.
Checks: 15
Passed: 14
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

## Source profiles

The source policy is bound to exact package paths:

- `Editor/Core/AvatarDoctorPackageInfo.cs` uses the `constantsOnly` profile. It permits one internal static class, five approved string constants, no methods, and no Unity API use.
- `Editor/UI/AvatarDoctorWindow.cs` uses the `editorWindowShell` profile. It permits only the approved using directives, seven private constants, `OpenWindow`, `OnEnable`, `CreateGUI`, and the exact code-only UI Toolkit construction statements.

The window profile narrowly authorizes `EditorWindow`, `MenuItem`, `GUIContent`, `Vector2`, `VisualElement`, `Label`, the required UI Toolkit layout and font enums, `GetWindow`, `Show`, `Clear`, `Add`, and the approved style properties. The exact-shape check prevents these Unity namespace exceptions from becoming general Unity API authorization.

File I/O, networking, reflection, scene APIs, asset access, build APIs, asynchronous execution, event subscriptions, runtime object APIs, VRChat SDK types, Quest behavior, OSC behavior, public package types, and Runtime assemblies remain prohibited.

## Protected validation workflow

The protected workflow remains named `Repository Validation`, and its only job remains `validate`. It runs for Pull Requests, pushes to `main`, and manual dispatch with read-only contents permission, disabled checkout credential persistence, and no secrets or artifacts.

Checkout is pinned to:

```text
actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
```

GitHub Actions uses Python 3 and executes `python3 ci/validate_repository.py --root .`. The required status context remains `Repository Validation / validate`.

## Negative validation matrix

Negative tests run in isolated temporary repository copies. They must not modify the release branch or leave tracked fixtures.

| Case | Mutation | Expected exit | Required check |
| --- | --- | --- | --- |
| A | Inconsistent package version | `1` | `VERSION` |
| B | Duplicate Unity GUID | `1` | `UNITY_METADATA` |
| C | Tracked prohibited archive | `1` | `PROHIBITED_FILES` |
| D | Basic Spanish-language marker | `1` | `LANGUAGE` |
| E | Invalid validator configuration | `2` | `CONFIG` |
| F | Incorrect `Tools/Avatar Doctor` menu path | `1` | `EDITOR_WINDOW` |
| G | Missing `rootVisualElement.Clear()` | `1` | `EDITOR_WINDOW` |
| H | Unauthorized `AssetDatabase` access | `1` | `SOURCE` or `EDITOR_WINDOW` |
| I | Unauthorized `VRCAvatarDescriptor` type | `1` | `SOURCE` |
| J | Unauthorized `Button` control | `1` | `EDITOR_WINDOW` |
| K | Unmodified release tree | `0` | 15 of 15 checks pass |

## Unity validation

Static repository checks do not replace Unity import or compilation. Release validation for `v0.0.4` must use Unity `2022.3.22f1` and record the evidence in the Pull Request.

A batch import may be used for the compilation portion:

```powershell
<Unity-2022.3.22f1> -batchmode -nographics -quit -projectPath <repo-root> -logFile <unity-log>
```

The visible Editor validation must also confirm:

1. Import completes and the Editor assembly compiles with zero errors.
2. `Tools → Avatar Doctor` exists and opens one window titled `Avatar Doctor`.
3. The window is dockable and enforces a minimum size of `420 × 220`.
4. The header, pre-alpha status, unavailable-analysis message, and package version appear once and in the required order.
5. No buttons or other functional controls exist.
6. Invoking the menu again reuses the existing window.
7. Script recompilation and Domain Reload do not duplicate visual elements.
8. Closing and reopening the window reconstructs the same content.
9. The window does not modify scenes, assets, project data, or tracked files.
10. Console errors and warnings are recorded separately for Avatar Doctor, Unity or inherited dependencies, and GitHub Actions.

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
