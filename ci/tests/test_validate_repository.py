#!/usr/bin/env python3
"""Focused standard-library tests for repository policy contracts."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import validate_repository as validator  # noqa: E402


POLICY_PATH = Path(__file__).resolve().parents[1] / "validation-policy.json"


class PlanningContractTests(unittest.TestCase):
    def create_context(
        self,
        root: Path,
        *,
        omitted: tuple[str, ...] = (),
        plan_suffix: str = "",
        extra_files: dict[str, str] | None = None,
    ) -> validator.RepositoryContext:
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        contract = policy["planningContract"]
        contents = {
            contract["agents"]: "# Repository Instructions\n",
            contract["spec"]: "# v0.1.0 — Avatar Discovery\n",
            contract["plan"]: (
                "# v0.1.0 — Avatar Discovery Plan\n\n"
                f"Canonical specification: {contract['spec']}\n"
                f"{plan_suffix}"
            ),
            contract["handoff"]: (
                "# Handoff\n\n"
                f"Canonical spec: {contract['spec']}\n"
                f"Plan: {contract['plan']}\n"
            ),
        }
        if extra_files:
            contents.update(extra_files)

        tracked_files = []
        omitted_paths = set(omitted)
        for relative_path, content in contents.items():
            if relative_path in omitted_paths:
                continue
            destination = root.joinpath(*PurePosixPath(relative_path).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8", newline="\n")
            tracked_files.append(relative_path)
        return validator.RepositoryContext(root, policy, tracked_files)

    def assert_missing(self, contract_key: str) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
            missing_path = policy["planningContract"][contract_key]
            context = self.create_context(root, omitted=(missing_path,))
            findings = validator.validate_planning_contract(context)
            self.assertTrue(
                any(
                    item.path == missing_path and "is not tracked" in item.message
                    for item in findings
                )
            )

    def test_valid_planning_structure_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(Path(temporary))
            self.assertEqual(validator.validate_planning_contract(context), [])

    def test_missing_agents_fails(self) -> None:
        self.assert_missing("agents")

    def test_missing_spec_fails(self) -> None:
        self.assert_missing("spec")

    def test_missing_plan_fails(self) -> None:
        self.assert_missing("plan")

    def test_missing_handoff_fails(self) -> None:
        self.assert_missing("handoff")

    def test_personal_path_in_planning_fails_privacy_check(self) -> None:
        personal_path = str(PurePosixPath("/", "Users", "example", "project")) + "/"
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(
                Path(temporary),
                plan_suffix="Local checkout: {0}\n".format(personal_path),
            )
            findings = validator.check_privacy(context)
            self.assertTrue(
                any(
                    item.check_id == "PRIVACY"
                    and item.path == context.policy["planningContract"]["plan"]
                    for item in findings
                )
            )

    def test_active_release_spec_path_drift_fails(self) -> None:
        drift_path = "docs/specs/v0.1.0-renamed.md"
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(
                Path(temporary),
                extra_files={drift_path: "# Drift\n"},
            )
            findings = validator.validate_planning_contract(context)
            self.assertTrue(
                any(
                    item.path == drift_path and "drifts" in item.message
                    for item in findings
                )
            )


class SdkBoundaryContractTests(unittest.TestCase):
    def create_context(
        self,
        root: Path,
        *,
        package_dependencies: dict[str, str] | None = None,
        omit_package_dependencies: bool = False,
        development_manifest: dict[str, object] | None = None,
        include_source: bool = True,
        extra_files: dict[str, str] | None = None,
    ) -> validator.RepositoryContext:
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        boundary = policy["sdkBoundary"]
        package_manifest: dict[str, object] = {}
        if not omit_package_dependencies:
            package_manifest["vpmDependencies"] = (
                package_dependencies
                if package_dependencies is not None
                else boundary["packageDependencies"]
            )
        documents: dict[str, str] = {
            policy["packageRoot"] + "/package.json": json.dumps(
                package_manifest, indent=2
            )
            + "\n",
            boundary["developmentManifest"]: json.dumps(
                development_manifest
                if development_manifest is not None
                else {
                    "dependencies": boundary["developmentDependencies"],
                    "locked": boundary["developmentLocked"],
                },
                indent=2,
            )
            + "\n",
        }
        if include_source:
            documents[boundary["sourcePath"]] = (
                "\n".join(validator.expected_vrchat_sdk_boundary_lines(boundary))
                + "\n"
            )
        if extra_files:
            documents.update(extra_files)

        tracked_files = []
        for relative_path, content in documents.items():
            destination = root.joinpath(*PurePosixPath(relative_path).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8", newline="\n")
            tracked_files.append(relative_path)
        return validator.RepositoryContext(root, policy, tracked_files)

    def test_approved_sdk_dependency_contract_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(Path(temporary))
            self.assertEqual(validator.check_sdk_dependency_contract(context), [])

    def test_missing_sdk_dependency_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(
                Path(temporary), omit_package_dependencies=True
            )
            findings = validator.check_sdk_dependency_contract(context)
            self.assertTrue(
                any("VPM dependency com.vrchat.avatars" in item.message for item in findings)
            )

    def test_wrong_sdk_range_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(
                Path(temporary),
                package_dependencies={"com.vrchat.avatars": "3.11.x"},
            )
            findings = validator.check_sdk_dependency_contract(context)
            self.assertTrue(any(item.expected == "'3.10.x'" for item in findings))

    def test_unexpected_additional_vpm_dependency_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(
                Path(temporary),
                package_dependencies={
                    "com.vrchat.avatars": "3.10.x",
                    "com.vrchat.base": "3.10.x",
                },
            )
            findings = validator.check_sdk_dependency_contract(context)
            self.assertTrue(
                any("Unexpected Avatar Doctor VPM dependency" in item.message for item in findings)
            )

    def test_vrc_sdk3a_reference_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(Path(temporary))
            assembly_path = context.policy["allowedAssemblyDefinitions"][0]["path"]
            assembly = {
                "references": ["VRC.SDK3A"],
                "precompiledReferences": [],
            }
            self.assertEqual(
                validator.validate_sdk_assembly_references(
                    context, assembly_path, assembly
                ),
                [],
            )

    def test_additional_explicit_vrchat_reference_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(Path(temporary))
            assembly_path = context.policy["allowedAssemblyDefinitions"][0]["path"]
            assembly = {
                "references": ["VRC.SDK3A", "VRC.SDK3A.Editor"],
                "precompiledReferences": [],
            }
            findings = validator.validate_sdk_assembly_references(
                context, assembly_path, assembly
            )
            self.assertTrue(any("outside the approved SDK boundary" in item.message for item in findings))

    def test_vendored_dll_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(
                Path(temporary),
                extra_files={
                    "Packages/com.teyocesu.avatar-doctor/Editor/VRCSDK3A.dll": ""
                },
            )
            findings = validator.check_package_binaries(context)
            self.assertEqual(len(findings), 1)
            self.assertIn("Vendored DLL", findings[0].message)

    def test_missing_required_integration_source_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(Path(temporary), include_source=False)
            findings = validator.check_source(context)
            required_source = context.policy["sdkBoundary"]["sourcePath"]
            self.assertTrue(
                any(
                    item.path == required_source and "is not tracked" in item.message
                    for item in findings
                )
            )


if __name__ == "__main__":
    unittest.main()
