# Development and Release Workflow

Avatar Doctor uses small, reviewable changes with explicit scope and reproducible evidence.

## Branches

`main` is protected. Project changes are developed on branches and merged through Pull Requests.

Common branch names are:

```text
feature/<short-description>
fix/<short-description>
docs/<short-description>
release/vX.Y.Z-english-slug
```

Shared history must not be rewritten or force-pushed.

## Issues and milestones

Issues describe goals and acceptance criteria. Milestones group related work for a version. Acceptance criteria are marked complete only after supporting evidence exists.

Labels identify the change type, affected area, and risk when those classifications are useful.

## Commits

Commit messages use Conventional Commits in English:

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

Each commit should have one responsibility and leave the branch in a reviewable state. Contributors use their own Git identity. Maintainers control official package metadata, tags, and Releases.

## Pull Requests

Pull Requests describe the goal, scope, related Issues, validation evidence, screenshots when applicable, known limitations, and release status. Draft Pull Requests are used while implementation or review is incomplete.

Every change receives human review before merge. A successful CI result supports review but does not replace it. Review conversations should be resolved before merging.

## Repository validation

Run the validator from the repository root:

```shell
python ci/validate_repository.py --root .
```

The protected `Repository Validation / validate` check runs for Pull Requests and pushes to `main`. Validation failures must be investigated rather than skipped or downgraded. Changes to `ci/validation-policy.json` require focused review because they change repository acceptance rules.

## Unity validation

Changes that affect Unity code, metadata, or visible behavior are validated with Unity `2022.3.22f1`. The Pull Request records import, compilation, menu, window, errors, warnings, and generated-file results. Repository validation does not replace this Editor pass.

## Merge and release

Releases are prepared from reviewed commits and merged into `main` through a Pull Request. Release preparation includes:

1. confirming acceptance criteria and validation evidence;
2. updating package version references and the changelog;
3. completing review and required checks;
4. merging through the protected branch workflow;
5. creating a versioned tag from the reviewed `main` commit; and
6. publishing release notes that state capabilities and limitations accurately.

Versions before `v1.0.0` are published as prereleases. Existing tags, Releases, and published history are preserved.

## Distribution

The current package is not installable from a public VCC listing. Distribution variables, listing generation, GitHub Pages, and package artifacts remain disabled. The release pipeline is planned for `v0.0.6` and will be reviewed separately before distribution is enabled.

## Release checklist

- The change matches its Issues and milestone.
- Repository validation passes for the Pull Request head.
- Required Unity validation is recorded.
- Documentation and changelog entries are current.
- Generated files, credentials, local paths, and unrelated changes are absent.
- Human review is complete.
- The package version, tag, and release notes agree.
- Distribution claims match the functionality that was actually verified.
