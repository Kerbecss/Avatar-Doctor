# Avatar Doctor

Avatar Doctor is a Unity Editor package for inspecting VRChat avatars, presenting explainable findings, planning safe repairs, preparing Quest variants, and assisting multi-platform publishing.

## Status

- Avatar Doctor is in pre-alpha.
- The current release is `0.0.5`.
- Open the package window through `Tools → Avatar Doctor`.
- The window is currently a presentation-only shell without avatar analysis.
- The package is not yet available from a public VCC listing.
- The release pipeline is planned for `v0.0.6`.

## Planned capabilities

- Avatar inspection.
- Explainable diagnostics.
- Safe repairs.
- PC and Quest comparison.
- Quest preparation.
- Build validation.
- Multi-platform publishing assistance.

## Current functionality

The package currently provides one Editor-only assembly and one code-only UI Toolkit window. The window displays the package name, pre-alpha status, unavailable-analysis message, and package version. It contains no buttons or functional controls, reuses a single window instance, and rebuilds its visual tree safely after a Domain Reload.

The repository also includes deterministic validation for package metadata, source structure, Unity metadata, workflows, public documentation, and roadmap consistency. Avatar discovery, scanning, diagnostics, repairs, SDK integration, Quest preparation, build validation, and publishing are not implemented yet.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, validation, branch, commit, and Pull Request guidance.

## Documentation

- [Roadmap](docs/ROADMAP.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Repository validation](docs/VALIDATION.md)
- [Development and release workflow](docs/WORKFLOW.md)
- [Technical baseline](docs/TECHNICAL_BASELINE.md)

## Author

Avatar Doctor is maintained by **Teyocesu**.

## Disclaimer

Avatar Doctor is an independent project and is not affiliated with, endorsed by, or sponsored by VRChat Inc.

## License

Avatar Doctor is available under the [MIT License](LICENSE). Inherited third-party components retain their own license notices.
