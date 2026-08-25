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
REPOSITORY_ROOT = POLICY_PATH.parent.parent


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
            self.assertTrue(
                any(
                    "outside the approved production SDK boundary" in item.message
                    for item in findings
                )
            )

    def test_vrchat_fixture_plugin_pair_passes_for_editor_tests_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(Path(temporary))
            assembly_path = context.policy["allowedAssemblyDefinitions"][1]["path"]
            assembly = {
                "references": ["Teyocesu.AvatarDoctor.Editor", "VRC.SDK3A"],
                "precompiledReferences": ["VRCSDK3A.dll", "VRCSDKBase.dll"],
            }
            self.assertEqual(
                validator.validate_sdk_assembly_references(
                    context, assembly_path, assembly
                ),
                [],
            )

    def test_descriptor_plugin_reference_fails_for_production(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(Path(temporary))
            assembly_path = context.policy["allowedAssemblyDefinitions"][0]["path"]
            assembly = {
                "references": ["VRC.SDK3A"],
                "precompiledReferences": ["VRCSDK3A.dll"],
            }
            findings = validator.validate_sdk_assembly_references(
                context, assembly_path, assembly
            )
            self.assertTrue(
                any(
                    "Precompiled assembly references" in item.message
                    for item in findings
                )
            )

    def test_editor_tests_missing_vrcsdk3a_plugin_reference_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(Path(temporary))
            assembly_path = context.policy["allowedAssemblyDefinitions"][1]["path"]
            assembly = {
                "references": ["Teyocesu.AvatarDoctor.Editor", "VRC.SDK3A"],
                "precompiledReferences": ["VRCSDKBase.dll"],
            }
            findings = validator.validate_sdk_assembly_references(
                context, assembly_path, assembly
            )
            self.assertTrue(
                any(
                    "Precompiled assembly references" in item.message
                    for item in findings
                )
            )

    def test_editor_tests_missing_vrcsdkbase_plugin_reference_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(Path(temporary))
            assembly_path = context.policy["allowedAssemblyDefinitions"][1]["path"]
            assembly = {
                "references": ["Teyocesu.AvatarDoctor.Editor", "VRC.SDK3A"],
                "precompiledReferences": ["VRCSDK3A.dll"],
            }
            findings = validator.validate_sdk_assembly_references(
                context, assembly_path, assembly
            )
            self.assertTrue(
                any(
                    "Precompiled assembly references" in item.message
                    for item in findings
                )
            )

    def test_editor_tests_with_extra_vrchat_plugin_reference_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(Path(temporary))
            assembly_path = context.policy["allowedAssemblyDefinitions"][1]["path"]
            assembly = {
                "references": ["Teyocesu.AvatarDoctor.Editor", "VRC.SDK3A"],
                "precompiledReferences": [
                    "VRCSDK3A.dll",
                    "VRCSDKBase.dll",
                    "VRCSDKBase-Editor.dll",
                ],
            }
            findings = validator.validate_sdk_assembly_references(
                context, assembly_path, assembly
            )
            self.assertTrue(
                any(
                    "Precompiled assembly references" in item.message
                    for item in findings
                )
            )

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


class Phase3PackageContractTests(unittest.TestCase):
    def create_context(
        self,
        root: Path,
        documents: dict[str, str],
    ) -> validator.RepositoryContext:
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        tracked_files = []
        for relative_path, content in documents.items():
            destination = root.joinpath(*PurePosixPath(relative_path).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8", newline="\n")
            tracked_files.append(relative_path)
        return validator.RepositoryContext(root, policy, tracked_files)

    def approved_source_documents(self) -> dict[str, str]:
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        return {
            relative_path: REPOSITORY_ROOT.joinpath(
                *PurePosixPath(relative_path).parts
            ).read_text(encoding="utf-8")
            for relative_path in policy["sourceProfiles"]
        }

    def approved_assembly_documents(self) -> dict[str, str]:
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        return {
            entry["path"]: REPOSITORY_ROOT.joinpath(
                *PurePosixPath(entry["path"]).parts
            ).read_text(encoding="utf-8")
            for entry in policy["allowedAssemblyDefinitions"]
        }

    def test_approved_phase3_source_structure_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(
                Path(temporary),
                self.approved_source_documents(),
            )
            self.assertEqual(validator.check_source(context), [])

    def test_unexpected_production_source_fails(self) -> None:
        documents = self.approved_source_documents()
        unexpected_path = (
            "Packages/com.teyocesu.avatar-doctor/Editor/Discovery/Future.cs"
        )
        documents[unexpected_path] = (
            "namespace Teyocesu.AvatarDoctor.Editor.Discovery\n"
            "{\n"
            "    internal sealed class Future { }\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(Path(temporary), documents)
            findings = validator.check_source(context)
            self.assertTrue(
                any(
                    item.path == unexpected_path
                    and "no file-specific policy profile" in item.message
                    for item in findings
                )
            )

    def test_unexpected_selection_source_path_fails(self) -> None:
        documents = self.approved_source_documents()
        unexpected_path = (
            "Packages/com.teyocesu.avatar-doctor/Editor/Selection/"
            "FutureSelection.cs"
        )
        documents[unexpected_path] = (
            "namespace Teyocesu.AvatarDoctor.Editor.Selection\n"
            "{\n"
            "    internal sealed class FutureSelection { }\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(Path(temporary), documents)
            findings = validator.check_structure(context)
            self.assertTrue(
                any(
                    item.path == unexpected_path
                    and "declarative allowlist" in item.message
                    for item in findings
                )
            )

    def test_forbidden_public_production_type_fails(self) -> None:
        documents = self.approved_source_documents()
        candidate_path = (
            "Packages/com.teyocesu.avatar-doctor/Editor/Discovery/"
            "AvatarDiscoveryCandidate.cs"
        )
        documents[candidate_path] = documents[candidate_path].replace(
            "internal sealed class AvatarDiscoveryCandidate",
            "public sealed class AvatarDiscoveryCandidate",
        )
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(Path(temporary), documents)
            findings = validator.check_source(context)
            self.assertTrue(
                any(
                    item.path == candidate_path
                    and "Public C# type declarations" in item.message
                    for item in findings
                )
            )

    def test_detectable_discovery_mutation_api_fails(self) -> None:
        documents = self.approved_source_documents()
        service_path = (
            "Packages/com.teyocesu.avatar-doctor/Editor/Discovery/"
            "AvatarDiscoveryService.cs"
        )
        documents[service_path] += "\n// Undo.RecordObject would mutate project state.\n"
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(Path(temporary), documents)
            findings = validator.check_source(context)
            self.assertTrue(
                any(
                    item.path == service_path
                    and "detectable" in item.message.casefold()
                    and "mutation" in item.message.casefold()
                    for item in findings
                )
            )

    def test_file_io_in_production_discovery_fails(self) -> None:
        documents = self.approved_source_documents()
        service_path = (
            "Packages/com.teyocesu.avatar-doctor/Editor/Discovery/"
            "AvatarDiscoveryService.cs"
        )
        documents[service_path] += "\n// System.IO.File.ReadAllBytes is forbidden.\n"
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(Path(temporary), documents)
            findings = validator.check_source(context)
            self.assertTrue(
                any(
                    item.path == service_path
                    and "Prohibited File I/O pattern" in item.message
                    for item in findings
                )
            )

    def test_vrchat_sdk_type_in_selection_source_fails(self) -> None:
        documents = self.approved_source_documents()
        model_path = (
            "Packages/com.teyocesu.avatar-doctor/Editor/Selection/"
            "AvatarSelectionModel.cs"
        )
        documents[model_path] += "\n// VRCAvatarDescriptor must not leak here.\n"
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(Path(temporary), documents)
            findings = validator.check_source(context)
            self.assertTrue(
                any(
                    item.path == model_path
                    and "Prohibited VRChat SDK type pattern" in item.message
                    for item in findings
                )
            )

    def test_persistence_in_selection_source_fails(self) -> None:
        documents = self.approved_source_documents()
        model_path = (
            "Packages/com.teyocesu.avatar-doctor/Editor/Selection/"
            "AvatarSelectionModel.cs"
        )
        documents[model_path] += "\n// SessionState.SetString would persist state.\n"
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(Path(temporary), documents)
            findings = validator.check_source(context)
            self.assertTrue(
                any(
                    item.path == model_path
                    and "persistent Editor state" in item.message
                    for item in findings
                )
            )

    def test_event_subscription_in_selection_source_fails(self) -> None:
        documents = self.approved_source_documents()
        model_path = (
            "Packages/com.teyocesu.avatar-doctor/Editor/Selection/"
            "AvatarSelectionModel.cs"
        )
        documents[model_path] += (
            "\n// Selection.selectionChanged += HandleSelection;\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(Path(temporary), documents)
            findings = validator.check_source(context)
            self.assertTrue(
                any(
                    item.path == model_path
                    and "callback or event subscription" in item.message
                    for item in findings
                )
            )

    def test_polling_in_selection_source_fails(self) -> None:
        documents = self.approved_source_documents()
        model_path = (
            "Packages/com.teyocesu.avatar-doctor/Editor/Selection/"
            "AvatarSelectionModel.cs"
        )
        documents[model_path] += "\n// void Update() would poll.\n"
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(Path(temporary), documents)
            findings = validator.check_source(context)
            self.assertTrue(
                any(
                    item.path == model_path
                    and "polling or lifecycle callback" in item.message
                    for item in findings
                )
            )

    def test_editor_selection_mutation_in_selection_source_fails(self) -> None:
        documents = self.approved_source_documents()
        model_path = (
            "Packages/com.teyocesu.avatar-doctor/Editor/Selection/"
            "AvatarSelectionModel.cs"
        )
        documents[model_path] += "\n// Selection.activeObject = avatarRoot;\n"
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(Path(temporary), documents)
            findings = validator.check_source(context)
            self.assertTrue(
                any(
                    item.path == model_path
                    and "Unity Editor selection mutation" in item.message
                    for item in findings
                )
            )

    def test_unity_mutation_in_selection_source_fails(self) -> None:
        documents = self.approved_source_documents()
        model_path = (
            "Packages/com.teyocesu.avatar-doctor/Editor/Selection/"
            "AvatarSelectionModel.cs"
        )
        documents[model_path] += "\n// gameObject.SetActive(false) would mutate.\n"
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(Path(temporary), documents)
            findings = validator.check_source(context)
            self.assertTrue(
                any(
                    item.path == model_path
                    and "GameObject or Component mutation" in item.message
                    for item in findings
                )
            )

    def test_approved_phase3_assembly_structure_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(
                Path(temporary),
                self.approved_assembly_documents(),
            )
            self.assertEqual(validator.check_assembly(context), [])

    def test_unexpected_runtime_assembly_fails(self) -> None:
        runtime_path = (
            "Packages/com.teyocesu.avatar-doctor/Runtime/Unexpected.asmdef"
        )
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(
                Path(temporary),
                {runtime_path: '{"name": "Unexpected"}\n'},
            )
            findings = validator.check_structure(context)
            self.assertTrue(
                any("Runtime assembly is present" in item.message for item in findings)
            )

    def test_unexpected_test_assembly_fails(self) -> None:
        documents = self.approved_assembly_documents()
        unexpected_path = (
            "Packages/com.teyocesu.avatar-doctor/Tests/Editor/"
            "Unexpected.Tests.asmdef"
        )
        documents[unexpected_path] = '{"name": "Unexpected.Tests"}\n'
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(Path(temporary), documents)
            findings = validator.check_assembly(context)
            self.assertTrue(
                any(
                    item.path == unexpected_path
                    and "not allowed by policy" in item.message
                    for item in findings
                )
            )

    def test_forbidden_future_scope_directory_fails(self) -> None:
        future_path = (
            "Packages/com.teyocesu.avatar-doctor/Editor/Scanning/Future.cs"
        )
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(
                Path(temporary),
                {
                    future_path: (
                        "namespace Teyocesu.AvatarDoctor.Editor.Scanning\n"
                        "{\n"
                        "    internal sealed class Future { }\n"
                        "}\n"
                    )
                },
            )
            findings = validator.check_structure(context)
            self.assertTrue(
                any(
                    item.path == future_path
                    and "Future package directory" in item.message
                    for item in findings
                )
            )

    def test_phase4_window_rejects_polling_and_uss(self) -> None:
        documents = self.approved_source_documents()
        window_path = (
            "Packages/com.teyocesu.avatar-doctor/Editor/UI/AvatarDoctorWindow.cs"
        )
        documents[window_path] += (
            "\nprivate void Update() { }\n"
            "// VisualTreeAsset and CloneTree are outside the code-only UI boundary.\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(Path(temporary), documents)
            findings = validator.check_source(context)
            messages = [item.message for item in findings if item.path == window_path]
            self.assertTrue(any("polling" in message for message in messages))
            self.assertTrue(any("UXML or USS" in message for message in messages))

    def test_phase4_controller_rejects_selection_mutation(self) -> None:
        documents = self.approved_source_documents()
        controller_path = (
            "Packages/com.teyocesu.avatar-doctor/Editor/UI/"
            "AvatarDoctorWindowController.cs"
        )
        documents[controller_path] += "\nSelection.activeObject = null;\n"
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(Path(temporary), documents)
            findings = validator.check_source(context)
            self.assertTrue(
                any(
                    item.path == controller_path
                    and "Unity Editor selection mutation" in item.message
                    for item in findings
                )
            )

    def test_phase4_controller_requires_supported_lifecycle_callbacks(self) -> None:
        documents = self.approved_source_documents()
        controller_path = (
            "Packages/com.teyocesu.avatar-doctor/Editor/UI/"
            "AvatarDoctorWindowController.cs"
        )
        documents[controller_path] = documents[controller_path].replace(
            "EditorApplication.delayCall += unityCallback;",
            "EditorApplication.delayCall = unityCallback;",
        )
        with tempfile.TemporaryDirectory() as temporary:
            context = self.create_context(Path(temporary), documents)
            findings = validator.check_source(context)
            self.assertTrue(
                any(
                    item.path == controller_path
                    and "lifecycle fragment" in item.message
                    for item in findings
                )
            )


if __name__ == "__main__":
    unittest.main()
