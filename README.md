# Avatar Doctor

Avatar Doctor is a planned local-first Unity Editor package for explainable diagnostics, safe repairs, Quest conversion, and multi-platform publishing assistance for VRChat avatars.

> [!WARNING]
> Avatar Doctor is in **pre-alpha**. Version `v0.0.3` adds automated repository validation, but no functional avatar tooling or scanner exists yet. It is not recommended for production use and is not installable through VCC.

## Vision

Avatar Doctor is planned to help avatar creators:

- inspect VRChat avatars inside Unity;
- connect symptoms to probable root causes using verifiable evidence;
- explain detected problems, affected objects, risks, and possible repairs;
- apply only safe, reversible changes with preview, Undo, backup, or rollback;
- prepare non-destructive Quest variants and compare PC and Quest behavior;
- validate and publish both platforms under the same Avatar ID; and
- later use a separate local mobile interface for VRChat OSC controls.

These capabilities are roadmap goals, not features available in version `0.0.3`.

## Core principles

- **Local first:** avatar analysis and project modification will run only on the computer where Unity is open.
- **Explainable by design:** diagnostics will come from a deterministic expert system and objective evidence, not invented confidence values.
- **Safe changes:** ambiguous repairs will never be applied automatically, and original third-party assets will be preserved whenever a copy can be used.
- **Mandatory cost of USD 0:** the project and its required operation must remain free of charge.
- **No paid AI APIs:** generative AI services are not a runtime dependency or part of the diagnostic engine.
- **No required servers:** the project will not require project-owned hosting, databases, SaaS accounts, or remote telemetry.
- **Unity-only project work:** inspection, diagnosis, repair, conversion, building, and publishing will happen exclusively on the PC running Unity.

## Scope boundaries

The future **Avatar Remote** is a separate local companion limited to controlling the active VRChat avatar through OSC. It will not read or modify Unity projects, create toggles, run builds, publish avatars, change project materials, or execute arbitrary code on the PC.

Blender, external rigging, weight painting, modeling, vertex modification, and mesh editing outside Unity are explicitly outside the project scope.

## Current repository status

Release `v0.0.3` adds a deterministic standard-library-only repository validator, a versioned validation policy, a read-only GitHub Actions check, and local validation documentation. These development safeguards validate repository structure and consistency; they do not compile Unity or provide avatar functionality.

The package still does not provide a Unity Editor window, menus, avatar discovery, scanning, diagnostics, repairs, VRChat SDK integration, Quest conversion, publishing, a runtime assembly, or a public API.

No distributable ZIP, `.unitypackage`, VPM listing, or GitHub Pages site is available yet. Distribution remains deliberately disabled until `v0.0.5 — Release Pipeline` validates the artifacts, manifest, listing, and publication workflow.

Read the complete [project roadmap](docs/ROADMAP.md), the [controlled release workflow](docs/WORKFLOW.md), and the [repository validation guide](docs/VALIDATION.md) before contributing.

## Author

Avatar Doctor is maintained publicly by **Teyocesu**.

## Disclaimer

Avatar Doctor is an independent project and is not affiliated with, endorsed by, or sponsored by VRChat Inc.

## License

Avatar Doctor is available under the [MIT License](LICENSE). Inherited third-party components retain their own license notices.
