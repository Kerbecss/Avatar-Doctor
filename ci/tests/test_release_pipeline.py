#!/usr/bin/env python3
"""Standard-library tests for the Avatar Doctor release artifact pipeline."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import release_pipeline as pipeline  # noqa: E402
import validate_repository as validator  # noqa: E402


TEST_VERSION = "0.0.6"


class ReleasePipelineTests(unittest.TestCase):
    def create_repository(
        self,
        parent: Path,
        *,
        version: str = TEST_VERSION,
        package_id: str = pipeline.PACKAGE_ID,
        reverse_creation_order: bool = False,
    ) -> Path:
        root = parent / "repository"
        package = root.joinpath(*pipeline.PACKAGE_ROOT.parts)
        package.mkdir(parents=True)
        manifest = {
            "name": package_id,
            "displayName": "Avatar Doctor",
            "version": version,
            "unity": "2022.3",
            "url": pipeline.release_zip_url(TEST_VERSION),
            "license": "MIT",
        }
        files = [
            ("package.json", json.dumps(manifest, indent=2).encode("utf-8") + b"\n"),
            ("README.md", b"# Avatar Doctor\n"),
            ("Editor/Example.cs", b"namespace Example {}\n"),
            ("Editor/Example.cs.meta", b"fileFormatVersion: 2\n"),
        ]
        if reverse_creation_order:
            files.reverse()
        for relative_path, data in files:
            destination = package / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "Test Author"], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "config",
                "user.email",
                "80324652+Teyocesu@users.noreply.github.com",
            ],
            check=True,
        )
        subprocess.run(["git", "-C", str(root), "add", "--all"], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "test fixture"], check=True)
        subprocess.run(
            ["git", "-C", str(root), "tag", f"v{TEST_VERSION}"], check=True
        )
        return root

    def build(self, root: Path, output: Path) -> dict[str, str]:
        return pipeline.build_artifacts(root, output, TEST_VERSION)

    def write_listing(
        self,
        path: Path,
        *,
        version: str = TEST_VERSION,
        url: str | None = None,
        digest: str = "a" * 64,
        top_level_url: bool = False,
    ) -> None:
        manifest = {
            "name": pipeline.PACKAGE_ID,
            "displayName": "Avatar Doctor",
            "version": version,
            "unity": "2022.3",
            "url": url or pipeline.release_zip_url(TEST_VERSION),
            "zipSHA256": digest,
        }
        listing = {
            "name": "Avatar Doctor Verification",
            "id": "com.teyocesu.avatar-doctor.verification",
            "author": "Teyocesu",
            "packages": {
                pipeline.PACKAGE_ID: {
                    "versions": {version: manifest},
                }
            },
        }
        if top_level_url:
            listing["url"] = pipeline.EXPECTED_LISTING_URL
        path.write_text(json.dumps(listing), encoding="utf-8")

    def build_listing_from_local_zip(
        self, root: Path, output: Path, zip_path: Path
    ) -> dict[str, str]:
        return pipeline.build_listing(
            root,
            output,
            TEST_VERSION,
            f"refs/tags/v{TEST_VERSION}",
            False,
            zip_path=zip_path,
        )

    def listing_workflow_findings(self, text: str) -> list[validator.Finding]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            relative_path = ".github/workflows/build-listing.yml"
            workflow_path = root.joinpath(*Path(relative_path).parts)
            workflow_path.parent.mkdir(parents=True)
            workflow_path.write_text(text, encoding="utf-8", newline="\n")
            policy_path = Path(__file__).resolve().parents[1] / "validation-policy.json"
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
            context = validator.RepositoryContext(root, policy, [relative_path])
            return validator.check_listing_workflow(
                context, policy["protectedWorkflows"]["listing"]
            )

    def listing_workflow_text(self) -> str:
        return (
            Path(__file__).resolve().parents[2]
            / ".github"
            / "workflows"
            / "build-listing.yml"
        ).read_text(encoding="utf-8")

    def test_two_builds_are_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            root = self.create_repository(temp)
            first = temp / "first"
            second = temp / "second"
            self.build(root, first)
            self.build(root, second)
            for name in pipeline.expected_artifact_names(TEST_VERSION):
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())

    def test_built_artifacts_pass_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            root = self.create_repository(temp)
            output = temp / "artifacts"
            self.build(root, output)
            pipeline.verify_artifacts(root, output, TEST_VERSION)

    def test_file_creation_order_does_not_change_build(self) -> None:
        with tempfile.TemporaryDirectory() as first_temporary, tempfile.TemporaryDirectory() as second_temporary:
            first_temp = Path(first_temporary)
            second_temp = Path(second_temporary)
            first_root = self.create_repository(first_temp)
            second_root = self.create_repository(second_temp, reverse_creation_order=True)
            first_output = first_temp / "artifacts"
            second_output = second_temp / "artifacts"
            self.build(first_root, first_output)
            self.build(second_root, second_output)
            self.assertEqual(
                (first_output / pipeline.release_zip_name(TEST_VERSION)).read_bytes(),
                (second_output / pipeline.release_zip_name(TEST_VERSION)).read_bytes(),
            )

    def test_filesystem_timestamps_do_not_change_build(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            root = self.create_repository(temp)
            first = temp / "first"
            second = temp / "second"
            self.build(root, first)
            package = root.joinpath(*pipeline.PACKAGE_ROOT.parts)
            for path in package.rglob("*"):
                if path.is_file():
                    os.utime(path, (1_900_000_000, 1_900_000_000))
            self.build(root, second)
            self.assertEqual(
                (first / pipeline.release_zip_name(TEST_VERSION)).read_bytes(),
                (second / pipeline.release_zip_name(TEST_VERSION)).read_bytes(),
            )

    def test_zip_contains_only_expected_files_with_manifest_at_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            root = self.create_repository(temp)
            output = temp / "artifacts"
            self.build(root, output)
            with zipfile.ZipFile(output / pipeline.release_zip_name(TEST_VERSION)) as archive:
                expected = [name for name, _ in pipeline.tracked_package_files(root)]
                self.assertEqual(archive.namelist(), expected)
                self.assertIn("package.json", archive.namelist())
                self.assertNotIn(pipeline.PACKAGE_ROOT.as_posix(), archive.namelist())

    def test_untracked_package_file_is_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            root = self.create_repository(temp)
            package = root.joinpath(*pipeline.PACKAGE_ROOT.parts)
            (package / "untracked.txt").write_text("not released\n", encoding="utf-8")
            output = temp / "artifacts"
            self.build(root, output)
            with zipfile.ZipFile(output / pipeline.release_zip_name(TEST_VERSION)) as archive:
                self.assertNotIn("untracked.txt", archive.namelist())

    def test_source_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            root = self.create_repository(temp)
            package = root.joinpath(*pipeline.PACKAGE_ROOT.parts)
            symlink = package / "linked.md"
            try:
                symlink.symlink_to("README.md")
            except (OSError, NotImplementedError):
                self.skipTest("Symbolic links are unavailable on this platform.")
            subprocess.run(["git", "-C", str(root), "add", "--all"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "add symlink"], check=True)
            with self.assertRaises(pipeline.PipelineError):
                self.build(root, temp / "artifacts")

    def test_path_traversal_zip_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            malicious = Path(temporary) / "malicious.zip"
            with zipfile.ZipFile(malicious, "w", compression=zipfile.ZIP_STORED) as archive:
                archive.writestr(pipeline.zip_info("package.json"), b"{}")
                archive.writestr(pipeline.zip_info("../escape.txt"), b"escape")
            with self.assertRaises(pipeline.PipelineError):
                pipeline.verify_zip(malicious, TEST_VERSION)

    def test_windows_unsafe_archive_path_is_rejected(self) -> None:
        for name in ("CON.txt", "trailing. ", "invalid?.txt"):
            with self.subTest(name=name), self.assertRaises(pipeline.PipelineError):
                pipeline.validate_archive_name(name)

    def test_tampered_zip_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            root = self.create_repository(temp)
            output = temp / "artifacts"
            self.build(root, output)
            with (output / pipeline.release_zip_name(TEST_VERSION)).open("ab") as stream:
                stream.write(b"tampered")
            with self.assertRaises(pipeline.PipelineError):
                pipeline.verify_artifacts(root, output, TEST_VERSION)

    def test_extra_zip_entry_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            root = self.create_repository(temp)
            output = temp / "artifacts"
            self.build(root, output)
            zip_path = output / pipeline.release_zip_name(TEST_VERSION)
            with zipfile.ZipFile(zip_path, "a", compression=zipfile.ZIP_STORED) as archive:
                archive.writestr(pipeline.zip_info("unexpected.txt"), b"unexpected")
            zip_hash = pipeline.sha256_file(zip_path)
            manifest_hash = pipeline.sha256_file(output / "package.json")
            (output / "SHA256SUMS.txt").write_text(
                f"{manifest_hash}  package.json\n{zip_hash}  {zip_path.name}\n",
                encoding="utf-8",
            )
            with self.assertRaises(pipeline.PipelineError):
                pipeline.verify_artifacts(root, output, TEST_VERSION)

    def test_tampered_checksum_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            root = self.create_repository(temp)
            output = temp / "artifacts"
            self.build(root, output)
            checksum = output / "SHA256SUMS.txt"
            checksum_text = checksum.read_text(encoding="utf-8")
            replacement = "0" if checksum_text[0] != "0" else "1"
            checksum.write_text(replacement + checksum_text[1:], encoding="utf-8")
            with self.assertRaises(pipeline.PipelineError):
                pipeline.verify_artifacts(root, output, TEST_VERSION)

    def test_version_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            root = self.create_repository(temp, version="0.0.5")
            with self.assertRaises(pipeline.PipelineError):
                self.build(root, temp / "artifacts")

    def test_package_id_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            root = self.create_repository(temp, package_id="com.example.invalid")
            with self.assertRaises(pipeline.PipelineError):
                self.build(root, temp / "artifacts")

    def test_build_listing_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            root = self.create_repository(temp)
            artifacts = temp / "artifacts"
            self.build(root, artifacts)
            zip_path = artifacts / pipeline.release_zip_name(TEST_VERSION)
            first = temp / "first" / "index.json"
            second = temp / "second" / "index.json"

            self.build_listing_from_local_zip(root, first, zip_path)
            self.build_listing_from_local_zip(root, second, zip_path)

            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertTrue(first.read_bytes().endswith(b"\n"))
            self.assertNotIn(b"\r", first.read_bytes())

    def test_build_listing_has_exact_local_verification_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            root = self.create_repository(temp)
            artifacts = temp / "artifacts"
            self.build(root, artifacts)
            zip_path = artifacts / pipeline.release_zip_name(TEST_VERSION)
            listing_path = temp / "listing" / "index.json"

            self.build_listing_from_local_zip(root, listing_path, zip_path)

            document = json.loads(listing_path.read_text(encoding="utf-8"))
            self.assertEqual(
                set(document), {"author", "id", "name", "packages"}
            )
            self.assertNotIn("url", document)
            self.assertEqual(document["author"], pipeline.VERIFICATION_LISTING_AUTHOR)
            self.assertEqual(document["id"], pipeline.VERIFICATION_LISTING_ID)
            self.assertEqual(document["name"], pipeline.VERIFICATION_LISTING_NAME)
            self.assertEqual(set(document["packages"]), {pipeline.PACKAGE_ID})
            versions = document["packages"][pipeline.PACKAGE_ID]["versions"]
            self.assertEqual(set(versions), {TEST_VERSION})
            manifest = versions[TEST_VERSION]
            tagged_manifest = pipeline.load_json_bytes(
                dict(
                    pipeline.tracked_package_files(
                        root, f"refs/tags/v{TEST_VERSION}"
                    )
                )["package.json"],
                "tagged package.json",
            )
            expected_manifest = dict(tagged_manifest)
            expected_manifest["zipSHA256"] = pipeline.sha256_file(zip_path)
            self.assertEqual(manifest, expected_manifest)
            self.assertEqual(manifest["url"], pipeline.release_zip_url(TEST_VERSION))
            self.assertRegex(manifest["zipSHA256"], r"^[0-9a-f]{64}$")

    def test_build_listing_rejects_zip_that_does_not_match_tag_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            root = self.create_repository(temp)
            artifacts = temp / "artifacts"
            self.build(root, artifacts)
            zip_path = artifacts / pipeline.release_zip_name(TEST_VERSION)
            with zip_path.open("ab") as stream:
                stream.write(b"tampered")
            output = temp / "listing" / "index.json"

            with self.assertRaises(pipeline.PipelineError):
                self.build_listing_from_local_zip(root, output, zip_path)

            self.assertFalse(output.exists())

    def test_build_listing_rejects_wrong_or_missing_source_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            root = self.create_repository(temp)
            artifacts = temp / "artifacts"
            self.build(root, artifacts)
            zip_path = artifacts / pipeline.release_zip_name(TEST_VERSION)

            with self.subTest("wrong source tag"):
                with self.assertRaises(pipeline.PipelineError):
                    pipeline.build_listing(
                        root,
                        temp / "wrong-source" / "index.json",
                        TEST_VERSION,
                        "refs/tags/v0.0.5",
                        False,
                        zip_path=zip_path,
                    )

            subprocess.run(
                ["git", "-C", str(root), "tag", "-d", f"v{TEST_VERSION}"],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            with self.subTest("missing expected tag"):
                with self.assertRaises(pipeline.PipelineError):
                    self.build_listing_from_local_zip(
                        root, temp / "missing-tag" / "index.json", zip_path
                    )

            wrong_version_root = self.create_repository(
                temp / "wrong-version", version="0.0.5"
            )
            with self.subTest("tagged manifest version mismatch"):
                with self.assertRaises(pipeline.PipelineError):
                    self.build_listing_from_local_zip(
                        wrong_version_root,
                        temp / "wrong-version-listing" / "index.json",
                        zip_path,
                    )

    def test_build_listing_requires_exactly_one_zip_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            root = self.create_repository(temp)
            artifacts = temp / "artifacts"
            self.build(root, artifacts)
            zip_path = artifacts / pipeline.release_zip_name(TEST_VERSION)
            arguments = (
                root,
                temp / "listing" / "index.json",
                TEST_VERSION,
                f"refs/tags/v{TEST_VERSION}",
            )
            with self.assertRaises(pipeline.PipelineError):
                pipeline.build_listing(*arguments, False)
            with self.assertRaises(pipeline.PipelineError):
                pipeline.build_listing(*arguments, True, zip_path=zip_path)

    def test_listing_workflow_self_contained_python_is_accepted(self) -> None:
        self.assertEqual(self.listing_workflow_findings(self.listing_workflow_text()), [])

    def test_listing_workflow_rejects_external_package_list_action(self) -> None:
        text = self.listing_workflow_text().replace(
            "python3 ci/release_pipeline.py build-listing",
            "bash .package-list-action/build.sh BuildRepoListing",
            1,
        )
        findings = self.listing_workflow_findings(text)
        self.assertTrue(
            any("external listing runtime builder" in item.message for item in findings)
        )

    def test_listing_workflow_rejects_dotnet_invocation(self) -> None:
        text = self.listing_workflow_text().replace(
            "python3 ci/release_pipeline.py build-listing",
            "dotnet run && python3 ci/release_pipeline.py build-listing",
            1,
        )
        findings = self.listing_workflow_findings(text)
        self.assertTrue(any(".NET listing runtime" in item.message for item in findings))

    def test_listing_workflow_rejects_write_permission(self) -> None:
        text = self.listing_workflow_text().replace("contents: read", "contents: write", 1)
        findings = self.listing_workflow_findings(text)
        self.assertTrue(any("read-only" in item.message for item in findings))

    def test_listing_workflow_rejects_pages_or_deployment(self) -> None:
        text = self.listing_workflow_text().replace(
            "    runs-on: ubuntu-latest",
            "    runs-on: ubuntu-latest\n    environment: github-pages",
            1,
        )
        findings = self.listing_workflow_findings(text)
        self.assertTrue(any("deployment environment" in item.message for item in findings))

    def test_listing_workflow_rejects_builder_source_ref_without_tag(self) -> None:
        text = self.listing_workflow_text().replace(
            '--source-ref "refs/tags/v$EXPECTED_VERSION"',
            '--source-ref "HEAD"',
            1,
        )
        findings = self.listing_workflow_findings(text)
        self.assertTrue(any("builder command" in item.message for item in findings))

    def test_listing_workflow_rejects_removed_verifier(self) -> None:
        text = self.listing_workflow_text().replace(
            "python3 ci/release_pipeline.py verify-listing",
            "python3 -c \"print('verification removed')\"",
            1,
        )
        findings = self.listing_workflow_findings(text)
        self.assertTrue(any("verifier" in item.message for item in findings))

    def test_listing_normalization_removes_only_top_level_url(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            source = temp / "source.json"
            output = temp / "index.json"
            self.write_listing(source, top_level_url=True)
            pipeline.normalize_listing(source, output, TEST_VERSION)
            document = json.loads(output.read_text(encoding="utf-8"))
            self.assertNotIn("url", document)
            manifest = document["packages"][pipeline.PACKAGE_ID]["versions"][TEST_VERSION]
            self.assertEqual(manifest["url"], pipeline.release_zip_url(TEST_VERSION))

    def test_listing_normalization_selects_expected_version_from_history(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            source = temp / "source.json"
            output = temp / "index.json"
            self.write_listing(source, digest="b" * 64, top_level_url=True)
            raw_listing = json.loads(source.read_text(encoding="utf-8"))
            versions = raw_listing["packages"][pipeline.PACKAGE_ID]["versions"]
            versions["0.0.5"] = {
                "name": pipeline.PACKAGE_ID,
                "displayName": "Avatar Doctor",
                "version": "0.0.5",
                "unity": "2022.3",
                "url": pipeline.release_zip_url("0.0.5"),
                "zipSHA256": "a" * 64,
            }
            source.write_text(json.dumps(raw_listing), encoding="utf-8")

            pipeline.normalize_listing(source, output, TEST_VERSION)

            normalized = json.loads(output.read_text(encoding="utf-8"))
            self.assertNotIn("url", normalized)
            self.assertEqual(set(normalized["packages"]), {pipeline.PACKAGE_ID})
            normalized_versions = normalized["packages"][pipeline.PACKAGE_ID][
                "versions"
            ]
            self.assertEqual(set(normalized_versions), {TEST_VERSION})
            manifest = normalized_versions[TEST_VERSION]
            self.assertEqual(manifest["url"], pipeline.release_zip_url(TEST_VERSION))
            self.assertEqual(manifest["zipSHA256"], "b" * 64)

    def test_listing_normalization_rejects_missing_expected_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            source = temp / "source.json"
            output = temp / "index.json"
            self.write_listing(
                source,
                version="0.0.5",
                url=pipeline.release_zip_url("0.0.5"),
            )
            with self.assertRaises(pipeline.PipelineError):
                pipeline.normalize_listing(source, output, TEST_VERSION)

    def test_listing_version_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "index.json"
            self.write_listing(path, version="0.0.5")
            with self.assertRaises(pipeline.PipelineError):
                pipeline.verify_listing(path, TEST_VERSION, False)

    def test_listing_url_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "index.json"
            self.write_listing(path, url="https://example.invalid/package.zip")
            with self.assertRaises(pipeline.PipelineError):
                pipeline.verify_listing(path, TEST_VERSION, False)

    def test_listing_hash_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "index.json"
            self.write_listing(path, digest="A" * 64)
            with self.assertRaises(pipeline.PipelineError):
                pipeline.verify_listing(path, TEST_VERSION, False)

    def test_remote_listing_zip_matches_git_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            root = self.create_repository(temp)
            artifacts = temp / "artifacts"
            self.build(root, artifacts)
            zip_bytes = (artifacts / pipeline.release_zip_name(TEST_VERSION)).read_bytes()
            listing = temp / "index.json"
            self.write_listing(listing, digest=pipeline.sha256_bytes(zip_bytes))
            with mock.patch.object(pipeline, "download_remote_zip", return_value=zip_bytes):
                pipeline.verify_listing(
                    listing,
                    TEST_VERSION,
                    True,
                    root=root,
                    source_ref="HEAD",
                )

    def test_remote_listing_rejects_extra_zip_entry_with_matching_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            root = self.create_repository(temp)
            artifacts = temp / "artifacts"
            self.build(root, artifacts)
            altered = temp / "altered.zip"
            altered.write_bytes(
                (artifacts / pipeline.release_zip_name(TEST_VERSION)).read_bytes()
            )
            with zipfile.ZipFile(altered, "a", compression=zipfile.ZIP_STORED) as archive:
                archive.writestr(pipeline.zip_info("unexpected.txt"), b"unexpected")
            zip_bytes = altered.read_bytes()
            listing = temp / "index.json"
            self.write_listing(listing, digest=pipeline.sha256_bytes(zip_bytes))
            with mock.patch.object(pipeline, "download_remote_zip", return_value=zip_bytes):
                with self.assertRaises(pipeline.PipelineError):
                    pipeline.verify_listing(
                        listing,
                        TEST_VERSION,
                        True,
                        root=root,
                        source_ref="HEAD",
                    )


if __name__ == "__main__":
    unittest.main()
