# Avatar Doctor

Avatar Doctor is a planned local-first Unity Editor package for explainable VRChat avatar diagnostics, safe repairs, Quest conversion, and multi-platform publishing assistance.

## Status

Avatar Doctor is **pre-alpha**. Version `0.0.2` provides one Editor-only assembly named `Teyocesu.AvatarDoctor.Editor`, a stable root namespace, the initial `Editor/Core` source folder, and internal constants for package identity and version.

It does not contain a Unity Editor window, menus, avatar discovery, avatar analysis, a scanner, diagnostics, repairs, VRChat SDK integration, Quest conversion, publishing, a runtime assembly, or a public API.

Version `0.0.2` is not recommended for production projects and is not installable through VCC. Its manifest does not yet point to a distributable ZIP, and no VPM listing or GitHub Pages site is enabled. Artifact and distribution validation belongs to `v0.0.5 — Release Pipeline`.

## Principles

- Processing and project modification will remain local to the computer running Unity.
- The project must remain usable at a mandatory cost of USD 0.
- Paid AI APIs, required hosted servers, telemetry, and project-owned cloud services are outside the product design.
- Future Avatar Remote work will be limited to local VRChat OSC control and will not modify Unity projects.
- Blender, external rigging, weight painting, and mesh editing are outside the project scope.

See the repository [roadmap](../../docs/ROADMAP.md) for the planned release sequence.

## Author

Avatar Doctor is maintained publicly by **Teyocesu**.

## Disclaimer

Avatar Doctor is an independent project and is not affiliated with, endorsed by, or sponsored by VRChat Inc.

## License

Licensed under the [MIT License](LICENSE.md).
