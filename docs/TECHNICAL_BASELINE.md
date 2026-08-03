# Technical Baseline

## Verification record

- **Verification date:** 2026-08-03
- **Template repository:** [`vrchat-community/template-package`](https://github.com/vrchat-community/template-package)
- **Exact template base commit:** [`591e23fe5175b8279cc3998f65e81add604aabc9`](https://github.com/vrchat-community/template-package/commit/591e23fe5175b8279cc3998f65e81add604aabc9)
- **Exact template base tree:** `fdd7c887fbada4ddada4142d95065fc13750560d`
- **Template branch at verification:** `main`

The [official VPM package documentation](https://vcc.docs.vrchat.com/vpm/packages/) directs package authors to the GitHub template above. The recorded commit is the head of its default branch on the verification date; repository files were initialized from that exact tree rather than reconstructed manually.

Status terms in this document have strict meanings:

- **Verified:** supported by an official source or directly inspected local evidence.
- **Not verified:** available evidence is insufficient to make the claim.
- **Unavailable in the current environment:** the relevant executable, module, or installed dependency was not found locally.

## Unity baseline

| Item | Status | Evidence |
| --- | --- | --- |
| Unity version currently supported by VRChat | **Verified** | `2022.3.22f1`, changeset `887be4894c44`, from the [VRChat current Unity version guide](https://creators.vrchat.com/sdk/upgrade/current-unity-version/) and the [Unity release record](https://unity.com/releases/editor/whats-new/2022.3.22f1). |
| Unity version declared by the template project | **Verified** | `ProjectSettings/ProjectVersion.txt` specifies `2022.3.22f1 (887be4894c44)` at the exact template base commit. |
| Unity Editor installed locally | **Unavailable in the current environment** | No Unity executable or Unity Hub editor installation was found during local inspection. |
| Project compilation | **Not verified** | Unity was unavailable, so the project was not opened or compiled. |
| Android Build Support installed locally | **Unavailable in the current environment** | No local Unity installation was found; Android Build Support could not be present or inspected through Unity Hub. |

## VRChat SDK baseline

| Item | Status | Evidence |
| --- | --- | --- |
| Latest stable VRChat SDK available from the official VPM registry | **Verified** | Version `3.10.4`, published 2026-06-17, documented in the [VRChat SDK 3.10.4 release notes](https://creators.vrchat.com/releases/release-3-10-4/), [official package release](https://github.com/vrchat/packages/releases/tag/3.10.4), and [official VPM registry](https://vrchat.github.io/packages/index.json). |
| VRChat SDK installed or pinned in this template/project | **Not verified** | No SDK is declared. `Packages/vpm-manifest.json` has empty `dependencies` and `locked` objects, and the package lock does not contain `com.vrchat.base`, `com.vrchat.avatars`, or `com.vrchat.worlds`. Version `3.10.4` must not be interpreted as installed. |
| Template bootstrap package | **Verified** | The inherited embedded package is `com.vrchat.core.bootstrap` version `0.1.15`. It is a package bootstrapper, not an installed Avatars or Worlds SDK. |

No SDK dependency was added in `v0.0.1`.

## Development operating systems

| Operating system | Status | Baseline |
| --- | --- | --- |
| Windows 10/11, 64-bit | **Verified** | Primary supported environment for VRChat Creator Companion according to the [VCC documentation](https://vcc.docs.vrchat.com/) and [VRChat SDK setup guide](https://creators.vrchat.com/sdk/). |
| macOS | **Verified with limitations** | Unity and parts of the VPM command-line workflow are documented, but this is not equivalent to full Creator Companion support. See the [VPM CLI documentation](https://vcc.docs.vrchat.com/vpm/cli/). |
| Linux | **Verified as not fully supported** | The VPM CLI documentation describes Linux as untested and requiring manual setup. |
| Current verification host | **Verified** | macOS `15.3.2` on Apple M1. No machine name, account name, or local personal path is recorded. |

Unity's platform requirements are documented in the [Unity 2022.3 system requirements](https://docs.unity3d.com/2022.3/Documentation/Manual/system-requirements.html).

## Locally available tools

| Tool | Status | Version |
| --- | --- | --- |
| Git | **Verified** | `2.39.5 (Apple Git-154)` |
| GitHub CLI | **Verified** | `2.96.0` |
| GitHub CLI authentication | **Verified** | Authenticated as `Teyocesu`; credentials are stored outside the repository and are not recorded here. |
| jq | **Verified** | `1.6-159-apple-gcff5336-dirty` |
| Node.js | **Verified** | `24.15.0` |
| npm | **Verified** | `11.12.1` |
| Python | **Verified** | `3.14.3` |
| Apple Command Line Tools | **Verified** | Installed; full Xcode was not verified. |
| Unity Editor | **Unavailable in the current environment** | No executable found. |
| VRChat Creator Companion | **Unavailable in the current environment** | No executable found. |
| .NET SDK | **Unavailable in the current environment** | No `dotnet` executable found. |

## Template automation baseline

The official template provides:

- a manually dispatched package release workflow; and
- a repository-listing workflow triggered by release activity or manual dispatch.

Avatar Doctor deliberately keeps both distribution paths disabled through `v0.0.4`:

- the package release job requires both `main` and `ENABLE_PACKAGE_RELEASE == 'true'`;
- the listing job requires both `main` and `ENABLE_PACKAGE_LISTING == 'true'`; and
- the listing workflow has only a manual trigger, with release and package-workflow triggers removed.

Neither enablement variable is configured for `v0.0.1`. A missing, empty, or differently valued variable leaves its job safely skipped. The existing `PACKAGE_NAME` variable identifies the package for future automation but does not enable either pipeline.

## Distribution status for v0.0.1

Version `v0.0.1` is a foundation release, not a VCC-installable package release. The package manifest retains its `url` field, but that field does not yet point to a distributable ZIP. No installable ZIP, `.unitypackage`, distributable manifest, VPM listing, or GitHub Pages site has been generated or validated.

GitHub Releases before `v0.0.5` may be used as reviewed development milestones, but they must not claim to be VPM packages installable through VCC. Complete artifact validation, distributable manifest validation, listing generation, Pages configuration, and restoration of automatic listing triggers belong to `v0.0.5 — Release Pipeline`.

## Unverified runtime items

- Unity import and compilation were not executed.
- VRChat SDK resolution was not executed because no SDK dependency is declared.
- Android tooling was not inspected through Unity Hub because Unity Hub and Unity were unavailable.
- VPM/VCC installation was not executed.
- Generated package archives, distributable manifests, and repository listings were not tested; no tag or GitHub Release is authorized for this release.
- GitHub Pages is not configured, and both distribution enablement variables remain intentionally unset until `v0.0.5`.
