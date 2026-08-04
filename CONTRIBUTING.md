# Contributing to Avatar Doctor

Thank you for helping improve Avatar Doctor. Contributions should be focused, reviewable, and supported by reproducible validation evidence.

## Project status

Avatar Doctor is in pre-alpha. The current package contains an Editor-only window shell and repository validation infrastructure. Product capabilities described in the roadmap are implemented incrementally and should not be presented as available before their release work is complete.

## Development requirements

- Git.
- Python 3.
- Unity `2022.3.22f1` for changes that require Unity validation.
- VCC as the recommended way to open the project on Windows.

No third-party Python packages are required for repository validation.

## Getting started

1. Fork the repository, or create a branch directly when you have write access.
2. Clone the repository and enter its root directory.
3. Run the repository validator before making changes:

   ```shell
   python ci/validate_repository.py --root .
   ```

4. Open the project through VCC when changing Unity package code or assets.
5. Keep changes limited to one clear goal and run the relevant validation again before opening a Pull Request.

## Branches

Use a short, descriptive branch name:

```text
feature/<short-description>
fix/<short-description>
docs/<short-description>
```

Maintained release branches may use:

```text
release/vX.Y.Z-english-slug
```

Do not push project changes directly to the protected `main` branch, rewrite published history, or force-push shared branches.

## Commits

Use Conventional Commits with English subjects, for example:

```text
feat: add avatar selection
fix: preserve window state after reload
docs: clarify Unity validation
```

Each contributor uses their own Git identity. Keep each commit focused and exclude generated files, credentials, local paths, and unrelated changes.

## Validation

Run repository validation from the repository root:

```shell
python ci/validate_repository.py --root .
```

For Unity package changes, also use Unity `2022.3.22f1` to confirm import, compilation, visible behavior, and the absence of unexpected tracked changes. Report every validation performed and identify any validation that was not available.

## Pull Requests

A Pull Request should:

- explain its goal and scope;
- link related Issues;
- list validation commands and results;
- identify validation that was not executed;
- include screenshots for visible UI changes when useful;
- keep unrelated changes out of the diff; and
- remain open for maintainer review before merge.

A successful automated check supports review but does not replace human review.

## Reporting issues

Open an Issue with a concise title, reproduction steps, expected behavior, actual behavior, Unity version, relevant package versions, and logs or screenshots that do not contain credentials or personal data.

## License

By contributing, you agree that your contribution is provided under the repository's [MIT License](LICENSE).
