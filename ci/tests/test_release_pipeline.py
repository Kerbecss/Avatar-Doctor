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
