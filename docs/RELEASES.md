# Release Verification and Recovery

Avatar Doctor separates artifact construction, human-controlled publication, and post-publication verification. This preserves an exact relationship between the reviewed commit, package version, release files, and published history.

## Build

Run repository validation and the release-pipeline unit tests before building:

```shell
python ci/validate_repository.py --root .
python -m unittest discover -s ci/tests -p "test_*.py"
```

Build twice from the reviewed `main` commit into separate empty directories outside the repository. Compare these files byte-for-byte between both builds:

- `com.teyocesu.avatar-doctor-0.0.6.zip`
- `package.json`
- `SHA256SUMS.txt`

Verify both artifact directories with `ci/release_pipeline.py verify`. The ZIP must contain exactly the tracked package blobs from the reviewed commit, with `package.json` at the archive root and normalized archive metadata.

The manual `Build Release Artifacts` workflow performs the same validation, testing, two-build comparison, and artifact verification on `main`. It uploads one short-lived Actions artifact and does not publish anything.

## Pre-publication verification

Record the exact `main` commit used by the build. Confirm that the package version, C# version constant, ZIP filename, embedded manifest, manifest copy, checksum file, and planned tag all identify `0.0.6`.

Recalculate the ZIP and manifest SHA-256 values and compare them with `SHA256SUMS.txt`. Confirm that the artifact directory contains no additional file. Before the prerelease is published, the versioned package URL is expected not to resolve.

Do not publish if the artifact set, commit, version, or reproducibility evidence differs.

## Publication

After the reviewed Pull Request is merged and the post-merge required check passes:

1. Run `Build Release Artifacts` on the exact reviewed `main` commit.
2. Download and verify the three generated files.
3. Create an annotated `v0.0.6` tag on that exact commit.
4. Publish a GitHub prerelease for the annotated tag.
5. Attach only the verified VPM ZIP, `package.json`, and `SHA256SUMS.txt`.

Publication remains a deliberate human action. The artifact workflow does not create or move tags, create or modify Releases, push repository changes, or create deployments.

## Post-publication verification

After the prerelease asset exists, run `Build VPM Verification Listing` for `0.0.6` on `main`. The upstream listing builder may discover multiple installable versions from release history. The normalization step selects only the requested `expected_version` and writes a non-public local `index.json` that intentionally contains one Avatar Doctor release with:

- package ID `com.teyocesu.avatar-doctor`;
- version `0.0.6`;
- the exact GitHub Release ZIP URL; and
- a lowercase `zipSHA256` value.

Remote verification downloads the ZIP as untrusted input, compares its SHA-256 with the listing, validates its manifest and archive safety, and compares every entry with the package tree at tag `v0.0.6`.

Isolating one requested version makes the resulting `index.json` suitable for verifying that release independently of other published versions. It is a temporary verification artifact, not the future public VPM repository. It is not written to `Website`, published through GitHub Pages, or enabled for public VPM distribution.

## Clean installation

Clean-install verification occurs on Windows only after the prerelease and local verification listing exist:

1. Download the verified local `index.json` artifact.
2. Create a clean compatible Unity project through VCC.
3. Add the local listing with the supported VPM tooling.
4. Install `com.teyocesu.avatar-doctor` version `0.0.6` from the listing.
5. Open the project in Unity `2022.3.22f1` and confirm import and compilation complete without Avatar Doctor errors.
6. Confirm `Tools → Avatar Doctor` opens the window and displays `Version 0.0.6`.
7. Remove and reinstall the package, then repeat the import and menu checks.
8. Record the listing, ZIP hash, project state, tool versions, result, and any warnings.

Do not claim successful VCC, VPM, or Unity verification until these steps have actually completed.

## Recovery

Recovery preserves published history and keeps public distribution disabled until verification succeeds.

### Failure before publication

Before publication, no historical tag or Release needs to be preserved. Correct the release branch with a new commit and repeat all validation.

### Failure after merge but before tagging

After merge but before tagging, do not rewrite `main`. Prepare the correction through a follow-up Pull Request and rebuild artifacts from the corrected commit.

### Failure after tagging but before Release publication

After tagging but before Release publication, do not move or silently replace the tag. Block publication and evaluate a subsequent fix release.

### Failure after publication

After publication, do not delete or silently replace the Release, do not move the tag, and do not enable the public listing. Prepare a later hotfix release through the normal Pull Request process.
