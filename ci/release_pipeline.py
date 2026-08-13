#!/usr/bin/env python3
"""Build and verify deterministic Avatar Doctor VPM release artifacts."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Sequence


PACKAGE_ID = "com.teyocesu.avatar-doctor"
PACKAGE_ROOT = PurePosixPath("Packages/com.teyocesu.avatar-doctor")
REPOSITORY = "Teyocesu/Avatar-Doctor"
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
ZIP_EXTERNAL_ATTR = 0o100644 << 16
EXPECTED_LISTING_URL = "https://Teyocesu.github.io/Avatar-Doctor/index.json"
CHECKSUM_PATTERN = re.compile(r"^([0-9a-f]{64})  ([^/\\]+)$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
MAX_REMOTE_ZIP_BYTES = 100 * 1024 * 1024
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


class PipelineError(Exception):
    """Raised when artifact construction or verification cannot proceed safely."""


def release_zip_name(version: str) -> str:
    return f"{PACKAGE_ID}-{version}.zip"


def release_zip_url(version: str) -> str:
    return (
        f"https://github.com/{REPOSITORY}/releases/download/"
        f"v{version}/{release_zip_name(version)}"
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reject_duplicate_json_keys(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PipelineError(f"JSON contains a duplicate key: {key}.")
        result[key] = value
    return result


def load_json_bytes(data: bytes, description: str) -> Any:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise PipelineError(f"{description} is not valid UTF-8.") from error
    try:
        return json.loads(text, object_pairs_hook=reject_duplicate_json_keys)
    except (json.JSONDecodeError, PipelineError) as error:
        if isinstance(error, PipelineError):
            raise
        raise PipelineError(f"{description} is not valid JSON: {error}.") from error


def load_json_file(path: Path, description: str) -> Any:
    try:
        return load_json_bytes(path.read_bytes(), description)
    except OSError as error:
        raise PipelineError(f"Cannot read {description}: {error}.") from error


def validate_manifest(
    manifest: Any, expected_version: str, *, listing_manifest: bool = False
) -> None:
    if not isinstance(manifest, dict):
        raise PipelineError("package.json must contain a JSON object.")
    if manifest.get("name") != PACKAGE_ID:
        raise PipelineError(f"Package ID must be {PACKAGE_ID}.")
    if manifest.get("version") != expected_version:
        raise PipelineError(f"Package version must be {expected_version}.")
    expected_url = release_zip_url(expected_version)
    if manifest.get("url") != expected_url:
        raise PipelineError(f"Package URL must be {expected_url}.")
    if not listing_manifest and "zipSHA256" in manifest:
        raise PipelineError("Package manifest must not contain listing-only zipSHA256.")


def validate_archive_name(name: str) -> None:
    if not name or "\\" in name or "\x00" in name:
        raise PipelineError(f"Unsafe archive path: {name!r}.")
    if name.startswith("/") or re.match(r"^[A-Za-z]:", name):
        raise PipelineError(f"Absolute archive path is not allowed: {name!r}.")
    parts = name.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise PipelineError(f"Unsafe archive path component in {name!r}.")
    for part in parts:
        if unicodedata.normalize("NFC", part) != part:
            raise PipelineError(f"Archive path is not Unicode-normalized: {name!r}.")
        if any(character in '<>:"|?*' for character in part):
            raise PipelineError(f"Archive path is not portable to Windows: {name!r}.")
        if part.endswith((" ", ".")):
            raise PipelineError(f"Archive path has an unsafe trailing character: {name!r}.")
        reserved_stem = part.split(".", 1)[0].upper()
        if reserved_stem in WINDOWS_RESERVED_NAMES:
            raise PipelineError(f"Archive path uses a reserved Windows name: {name!r}.")
    pure_name = PurePosixPath(name)
    if pure_name.is_absolute() or ".." in pure_name.parts:
        raise PipelineError(f"Unsafe archive path: {name!r}.")
    if any(ord(character) < 32 or ord(character) == 127 for character in name):
        raise PipelineError(f"Archive path contains a control character: {name!r}.")


def run_git(root: Path, arguments: Sequence[str]) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise PipelineError(f"Git command failed: {message or 'unknown error'}.")
    return result.stdout


def repository_root(root: Path) -> Path:
    resolved = root.resolve()
    discovered = run_git(resolved, ["rev-parse", "--show-toplevel"])
    try:
        git_root = Path(discovered.decode("utf-8").strip()).resolve()
    except UnicodeDecodeError as error:
        raise PipelineError("Git repository root is not valid UTF-8.") from error
    if git_root != resolved:
        raise PipelineError("--root must identify the Git repository root.")
    return resolved


def tracked_package_files(root: Path, source_ref: str = "HEAD") -> list[tuple[str, bytes]]:
    package_prefix = PACKAGE_ROOT.as_posix() + "/"
    resolved_ref = run_git(
        root, ["rev-parse", "--verify", f"{source_ref}^{{commit}}"]
    ).decode("ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", resolved_ref):
        raise PipelineError("Git did not resolve the package source to a commit.")
    raw_entries = run_git(
        root,
        [
            "ls-tree",
            "-r",
            "-z",
            "--full-tree",
            resolved_ref,
            "--",
            PACKAGE_ROOT.as_posix(),
        ],
    )
    entries: list[tuple[str, bytes]] = []
    seen_names: set[str] = set()
    seen_casefolded: set[str] = set()

    for raw_entry in raw_entries.split(b"\0"):
        if not raw_entry:
            continue
        try:
            metadata, raw_path = raw_entry.split(b"\t", 1)
            mode, object_type, object_id = metadata.decode("ascii").split(" ")
            repository_path = raw_path.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as error:
            raise PipelineError("Git returned an invalid package tree entry.") from error
        if object_type != "blob" or mode not in {"100644", "100755"}:
            if mode == "120000":
                raise PipelineError(f"Tracked package symlink is not allowed: {repository_path}.")
            raise PipelineError(f"Tracked package entry is not a regular file: {repository_path}.")
        if not repository_path.startswith(package_prefix):
            raise PipelineError(f"Tracked file is outside the package root: {repository_path}.")
        archive_name = repository_path[len(package_prefix) :]
        validate_archive_name(archive_name)
        folded = unicodedata.normalize("NFC", archive_name).casefold()
        if archive_name in seen_names or folded in seen_casefolded:
            raise PipelineError(f"Duplicate archive path: {archive_name}.")
        seen_names.add(archive_name)
        seen_casefolded.add(folded)
        entries.append((archive_name, run_git(root, ["cat-file", "blob", object_id])))

    entries.sort(key=lambda entry: entry[0])
    if not entries:
        raise PipelineError("No tracked package files were found.")
    if "package.json" not in {name for name, _ in entries}:
        raise PipelineError("The tracked package must contain package.json at its root.")
    return entries


def prepare_output_directory(root: Path, output_directory: Path) -> Path:
    output_directory.mkdir(parents=True, exist_ok=True)
    if output_directory.is_symlink() or not output_directory.is_dir():
        raise PipelineError("The artifact output path must be a regular directory.")
    if any(output_directory.iterdir()):
        raise PipelineError("The artifact output directory must be empty.")
    resolved = output_directory.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return resolved
    raise PipelineError("Release artifacts must be built outside the repository.")


def zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, ZIP_TIMESTAMP)
    # Stored entries avoid compressor-version differences between Python runtimes.
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.create_version = 20
    info.extract_version = 20
    info.external_attr = ZIP_EXTERNAL_ATTR
    info.internal_attr = 0
    info.extra = b""
    info.comment = b""
    return info


def canonical_zip_bytes(entries: Sequence[tuple[str, bytes]]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(
        stream,
        mode="w",
        compression=zipfile.ZIP_STORED,
        allowZip64=False,
    ) as archive:
        archive.comment = b""
        for archive_name, data in entries:
            archive.writestr(zip_info(archive_name), data)
    return stream.getvalue()


def build_artifacts(root: Path, output_directory: Path, expected_version: str) -> dict[str, str]:
    root = repository_root(root)
    entries = tracked_package_files(root)
    manifest_bytes = dict(entries)["package.json"]
    validate_manifest(load_json_bytes(manifest_bytes, "package.json"), expected_version)
    output_directory = prepare_output_directory(root, output_directory)

    zip_name = release_zip_name(expected_version)
    zip_path = output_directory / zip_name
    zip_path.write_bytes(canonical_zip_bytes(entries))

    manifest_copy = output_directory / "package.json"
    manifest_copy.write_bytes(manifest_bytes)
    hashes = {
        zip_name: sha256_file(zip_path),
        "package.json": sha256_file(manifest_copy),
    }
    checksum_text = "".join(
        f"{hashes[name]}  {name}\n" for name in sorted(hashes)
    )
    (output_directory / "SHA256SUMS.txt").write_text(checksum_text, encoding="utf-8", newline="\n")
    return hashes


def validate_zip_infos(infos: Sequence[zipfile.ZipInfo]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    seen_casefolded: set[str] = set()
    for info in infos:
        name = info.filename
        validate_archive_name(name)
        if info.is_dir() or name.endswith("/"):
            raise PipelineError(f"Directory entries are not allowed: {name}.")
        folded = unicodedata.normalize("NFC", name).casefold()
        if name in seen or folded in seen_casefolded:
            raise PipelineError(f"Duplicate archive entry: {name}.")
        seen.add(name)
        seen_casefolded.add(folded)
        mode = info.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise PipelineError(f"Archive symlink is not allowed: {name}.")
        if info.date_time != ZIP_TIMESTAMP:
            raise PipelineError(f"Archive timestamp is not normalized: {name}.")
        if info.compress_type != zipfile.ZIP_STORED:
            raise PipelineError(f"Archive entry is not stored deterministically: {name}.")
        if info.create_system != 3 or info.external_attr != ZIP_EXTERNAL_ATTR:
            raise PipelineError(f"Archive permissions are not normalized: {name}.")
        if info.create_version != 20 or info.extract_version != 20:
            raise PipelineError(f"Archive version metadata is not normalized: {name}.")
        if info.extra or info.comment:
            raise PipelineError(f"Archive entry contains variable metadata: {name}.")
        names.append(name)
    if names != sorted(names):
        raise PipelineError("Archive entries are not in lexicographic order.")
    if "package.json" not in seen:
        raise PipelineError("Archive does not contain package.json at its root.")
    return names


def verify_zip(
    zip_source: Path | bytes,
    expected_version: str,
    expected_files: Sequence[tuple[str, bytes]] | None = None,
) -> bytes:
    source: Path | io.BytesIO
    source = zip_source if isinstance(zip_source, Path) else io.BytesIO(zip_source)
    try:
        with zipfile.ZipFile(source, mode="r") as archive:
            if archive.comment:
                raise PipelineError("ZIP archive comments are not allowed.")
            infos = archive.infolist()
            names = validate_zip_infos(infos)
            if expected_files is not None:
                expected_names = [name for name, _ in expected_files]
                if names != expected_names:
                    raise PipelineError("ZIP entries do not match the tracked package files.")
                for name, source_bytes in expected_files:
                    if archive.read(name) != source_bytes:
                        raise PipelineError(f"ZIP entry bytes differ from the tracked file: {name}.")
            manifest_bytes = archive.read("package.json")
    except (OSError, zipfile.BadZipFile, RuntimeError) as error:
        raise PipelineError(f"Invalid ZIP archive: {error}.") from error
    validate_manifest(load_json_bytes(manifest_bytes, "ZIP package.json"), expected_version)
    if expected_files is not None:
        canonical = canonical_zip_bytes(expected_files)
        actual = zip_source.read_bytes() if isinstance(zip_source, Path) else zip_source
        if actual != canonical:
            raise PipelineError("ZIP bytes do not match the canonical deterministic archive.")
    return manifest_bytes


def expected_artifact_names(expected_version: str) -> list[str]:
    return ["SHA256SUMS.txt", "package.json", release_zip_name(expected_version)]


def verify_checksums(artifact_directory: Path, expected_version: str) -> dict[str, str]:
    checksum_path = artifact_directory / "SHA256SUMS.txt"
    try:
        checksum_bytes = checksum_path.read_bytes()
        checksum_text = checksum_bytes.decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise PipelineError("SHA256SUMS.txt is missing or not valid UTF-8.") from error
    if not checksum_text.endswith("\n") or "\r" in checksum_text:
        raise PipelineError("SHA256SUMS.txt must use LF lines and a final newline.")
    parsed: dict[str, str] = {}
    for line in checksum_text.splitlines():
        match = CHECKSUM_PATTERN.fullmatch(line)
        if not match:
            raise PipelineError("SHA256SUMS.txt contains an invalid line.")
        digest, name = match.groups()
        if name in parsed:
            raise PipelineError(f"SHA256SUMS.txt contains a duplicate file: {name}.")
        parsed[name] = digest
    expected_names = sorted(["package.json", release_zip_name(expected_version)])
    if list(parsed) != expected_names:
        raise PipelineError("SHA256SUMS.txt entries are not the exact sorted artifact set.")
    for name in expected_names:
        if sha256_file(artifact_directory / name) != parsed[name]:
            raise PipelineError(f"SHA-256 mismatch for {name}.")
    expected_text = "".join(f"{parsed[name]}  {name}\n" for name in expected_names)
    if checksum_text != expected_text:
        raise PipelineError("SHA256SUMS.txt is not in deterministic form.")
    return parsed


def verify_artifacts(root: Path, artifact_directory: Path, expected_version: str) -> dict[str, str]:
    root = repository_root(root)
    if artifact_directory.is_symlink() or not artifact_directory.is_dir():
        raise PipelineError("Artifact directory is missing or invalid.")
    actual_names = sorted(path.name for path in artifact_directory.iterdir())
    if actual_names != expected_artifact_names(expected_version):
        raise PipelineError("Artifact directory does not contain the exact expected files.")
    if any(not path.is_file() or path.is_symlink() for path in artifact_directory.iterdir()):
        raise PipelineError("Every artifact must be a regular file.")
    checksums = verify_checksums(artifact_directory, expected_version)
    entries = tracked_package_files(root)
    manifest_bytes = verify_zip(
        artifact_directory / release_zip_name(expected_version),
        expected_version,
        entries,
    )
    manifest_copy = (artifact_directory / "package.json").read_bytes()
    if manifest_copy != manifest_bytes:
        raise PipelineError("Artifact package.json differs from the ZIP manifest.")
    root_manifest = dict(entries)["package.json"]
    if manifest_copy != root_manifest:
        raise PipelineError("Artifact package.json differs from the tracked manifest.")
    return checksums


def normalize_listing(input_path: Path, output_path: Path, expected_version: str) -> None:
    document = load_json_file(input_path, "VPM listing")
    if not isinstance(document, dict):
        raise PipelineError("VPM listing must contain a JSON object.")
    repository_url = document.get("url")
    if repository_url is not None and not is_expected_listing_url(repository_url):
        raise PipelineError("Generated listing contains an unexpected repository URL.")
    document.pop("url", None)
    listing_manifest(document, expected_version)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.is_symlink():
        raise PipelineError("Listing output cannot be a symbolic link.")
    rendered = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    output_path.write_text(rendered, encoding="utf-8", newline="\n")


def is_expected_listing_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    actual = urllib.parse.urlsplit(value)
    expected = urllib.parse.urlsplit(EXPECTED_LISTING_URL)
    return (
        actual.scheme.casefold() == expected.scheme.casefold()
        and actual.hostname is not None
        and actual.hostname.casefold() == str(expected.hostname).casefold()
        and actual.port is None
        and actual.username is None
        and actual.password is None
        and actual.path == expected.path
        and not actual.query
        and not actual.fragment
    )


def listing_manifest(document: Any, expected_version: str) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise PipelineError("VPM listing must contain a JSON object.")
    if "url" in document:
        raise PipelineError("Local VPM listing must omit the top-level repository URL.")
    packages = document.get("packages")
    if not isinstance(packages, dict) or set(packages) != {PACKAGE_ID}:
        raise PipelineError("VPM listing must contain exactly the Avatar Doctor package.")
    package = packages[PACKAGE_ID]
    if not isinstance(package, dict):
        raise PipelineError("VPM listing package entry must be an object.")
    versions = package.get("versions")
    if not isinstance(versions, dict) or set(versions) != {expected_version}:
        raise PipelineError("VPM listing must contain exactly the expected release version.")
    manifest = versions[expected_version]
    if not isinstance(manifest, dict):
        raise PipelineError("VPM listing version entry must be a package manifest.")
    validate_manifest(manifest, expected_version, listing_manifest=True)
    digest = manifest.get("zipSHA256")
    if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
        raise PipelineError("VPM listing zipSHA256 must be 64 lowercase hexadecimal characters.")
    return manifest


def download_remote_zip(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "AvatarDoctorReleaseVerifier/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_REMOTE_ZIP_BYTES:
                raise PipelineError("Remote ZIP exceeds the verification size limit.")
            data = response.read(MAX_REMOTE_ZIP_BYTES + 1)
    except (OSError, ValueError) as error:
        raise PipelineError(f"Cannot download the release ZIP: {error}.") from error
    if len(data) > MAX_REMOTE_ZIP_BYTES:
        raise PipelineError("Remote ZIP exceeds the verification size limit.")
    return data


def verify_listing(
    listing_path: Path,
    expected_version: str,
    remote: bool,
    *,
    root: Path | None = None,
    source_ref: str = "HEAD",
    zip_path: Path | None = None,
) -> dict[str, str]:
    document = load_json_file(listing_path, "VPM listing")
    manifest = listing_manifest(document, expected_version)
    result = {
        "url": str(manifest["url"]),
        "zipSHA256": str(manifest["zipSHA256"]),
    }
    if remote and zip_path is not None:
        raise PipelineError("Choose either remote ZIP verification or a local ZIP, not both.")
    if remote or zip_path is not None:
        if root is None:
            raise PipelineError("ZIP verification requires the repository root.")
        root = repository_root(root)
        expected_files = tracked_package_files(root, source_ref)
        zip_bytes = (
            download_remote_zip(result["url"])
            if remote
            else zip_path.read_bytes()
        )
        if sha256_bytes(zip_bytes) != result["zipSHA256"]:
            raise PipelineError("Release ZIP does not match listing zipSHA256.")
        verify_zip(zip_bytes, expected_version, expected_files)
    return result


def parser() -> argparse.ArgumentParser:
    root_parser = argparse.ArgumentParser(
        description="Build and verify deterministic Avatar Doctor VPM artifacts."
    )
    subparsers = root_parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Build the exact release artifact set.")
    build_parser.add_argument("--root", type=Path, required=True)
    build_parser.add_argument("--output-dir", type=Path, required=True)
    build_parser.add_argument("--expected-version", required=True)

    verify_parser = subparsers.add_parser("verify", help="Verify a release artifact bundle.")
    verify_parser.add_argument("--root", type=Path, required=True)
    verify_parser.add_argument("--artifacts-dir", type=Path, required=True)
    verify_parser.add_argument("--expected-version", required=True)

    normalize_parser = subparsers.add_parser(
        "normalize-listing", help="Normalize a generated listing for local verification."
    )
    normalize_parser.add_argument("--input", type=Path, required=True)
    normalize_parser.add_argument("--output", type=Path, required=True)
    normalize_parser.add_argument("--expected-version", required=True)

    listing_parser = subparsers.add_parser(
        "verify-listing", help="Verify a local VPM listing and optionally its remote ZIP."
    )
    listing_parser.add_argument("--listing", type=Path, required=True)
    listing_parser.add_argument("--expected-version", required=True)
    listing_parser.add_argument("--remote", action="store_true")
    listing_parser.add_argument("--root", type=Path)
    listing_parser.add_argument("--source-ref", default="HEAD")
    listing_parser.add_argument("--zip", type=Path)
    return root_parser


def main(arguments: Iterable[str] | None = None) -> int:
    arguments_list = list(arguments) if arguments is not None else None
    parsed = parser().parse_args(arguments_list)
    try:
        if parsed.command == "build":
            hashes = build_artifacts(parsed.root, parsed.output_dir, parsed.expected_version)
            print("Release artifact build passed.")
            print(f"Version: {parsed.expected_version}")
            print(f"ZIP SHA-256: {hashes[release_zip_name(parsed.expected_version)]}")
        elif parsed.command == "verify":
            verify_artifacts(parsed.root, parsed.artifacts_dir, parsed.expected_version)
            print("Release artifact verification passed.")
        elif parsed.command == "normalize-listing":
            normalize_listing(parsed.input, parsed.output, parsed.expected_version)
            print("Local VPM listing normalization passed.")
        elif parsed.command == "verify-listing":
            verify_listing(
                parsed.listing,
                parsed.expected_version,
                parsed.remote,
                root=parsed.root,
                source_ref=parsed.source_ref,
                zip_path=parsed.zip,
            )
            print("VPM listing verification passed.")
        else:
            raise PipelineError("Unsupported command.")
    except PipelineError as error:
        print(f"Release pipeline error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
