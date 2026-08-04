#!/usr/bin/env python3
"""Deterministic, non-mutating repository policy validation."""

from __future__ import print_function

import argparse
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple


CHECK_ORDER = (
    "MANIFEST",
    "VERSION",
    "IDENTITY",
    "STRUCTURE",
    "ASSEMBLY",
    "SOURCE",
    "UNITY_METADATA",
    "TEXT_HYGIENE",
    "LANGUAGE",
    "PRIVACY",
    "SECRETS",
    "PROHIBITED_FILES",
    "WORKFLOWS",
    "ROADMAP_GUARD",
)

PASS_MESSAGES = {
    "MANIFEST": "Package manifest is valid.",
    "VERSION": "Package version references are consistent.",
    "IDENTITY": "Package identity is consistent.",
    "STRUCTURE": "Required repository structure is valid.",
    "ASSEMBLY": "Editor assembly configuration is valid.",
    "SOURCE": "Package source remains within the authorized scope.",
    "UNITY_METADATA": "Unity metadata is structurally valid.",
    "TEXT_HYGIENE": "Tracked text files satisfy the active hygiene policy.",
    "LANGUAGE": "No basic non-English language markers were found.",
    "PRIVACY": "No personal path or unapproved email patterns were found.",
    "SECRETS": "No high-signal secret patterns were found.",
    "PROHIBITED_FILES": "No prohibited tracked files were found.",
    "WORKFLOWS": "Protected workflow conditions are valid.",
    "ROADMAP_GUARD": "Required roadmap boundaries are present.",
}

EMAIL_PATTERN = re.compile(
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*"
    r"\.[A-Za-z]{2,63}"
)
SEMVER_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
GUID_PATTERN = re.compile(r"^[0-9a-fA-F]{32}$")
CONFLICT_PATTERN = re.compile(r"^(?:<{7}|={7}|>{7})(?: .*)?$", re.MULTILINE)


class ValidatorConfigurationError(Exception):
    """Raised when validation cannot execute reliably."""


class DuplicateJsonKeyError(ValueError):
    """Raised when a JSON object contains an ambiguous duplicate key."""


def reject_duplicate_json_keys(pairs: Sequence[Tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKeyError("Duplicate JSON key: {0}.".format(key))
        result[key] = value
    return result


@dataclass(frozen=True)
class Finding:
    check_id: str
    path: str
    message: str
    expected: str = ""

    def sort_key(self) -> Tuple[str, str, str]:
        return (self.path, self.message, self.expected)

    def render(self) -> str:
        rendered = "[FAIL] {0} — {1}: {2}".format(
            self.check_id, self.path, self.message
        )
        if self.expected:
            rendered += " Expected: {0}".format(self.expected)
        return rendered


class RepositoryContext:
    def __init__(
        self, root: Path, policy: Dict[str, Any], tracked_files: Sequence[str]
    ) -> None:
        self.root = root
        self.policy = policy
        self.tracked_files = tuple(sorted(tracked_files))
        self.tracked_set = set(self.tracked_files)
        self._bytes_cache: Dict[str, bytes] = {}
        self._text_cache: Dict[str, str] = {}

    def absolute(self, relative_path: str) -> Path:
        return self.root.joinpath(*PurePosixPath(relative_path).parts)

    def read_bytes(self, relative_path: str) -> bytes:
        if relative_path not in self._bytes_cache:
            absolute_path = self.absolute(relative_path)
            if absolute_path.is_symlink():
                raise ValidatorConfigurationError(
                    "Tracked symbolic links are not supported: {0}.".format(
                        relative_path
                    )
                )
            self._bytes_cache[relative_path] = absolute_path.read_bytes()
        return self._bytes_cache[relative_path]

    def read_text(self, relative_path: str) -> str:
        if relative_path not in self._text_cache:
            self._text_cache[relative_path] = self.read_bytes(relative_path).decode(
                "utf-8"
            )
        return self._text_cache[relative_path]

    def is_tracked(self, relative_path: str) -> bool:
        return relative_path in self.tracked_set

    def text_paths(self) -> Iterable[str]:
        approved_binary_files = {
            str(entry["path"]): str(entry["sha256"])
            for entry in self.policy["approvedBinaryFiles"]
        }
        for relative_path in self.tracked_files:
            expected_sha256 = approved_binary_files.get(relative_path)
            if expected_sha256 is not None:
                actual_sha256 = hashlib.sha256(self.read_bytes(relative_path)).hexdigest()
                if actual_sha256 == expected_sha256:
                    continue
            yield relative_path


def run_git(root: Path, arguments: Sequence[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root)] + list(arguments),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def resolve_repository_root(root_argument: Optional[str]) -> Path:
    start = Path(root_argument).resolve() if root_argument else Path.cwd().resolve()
    result = run_git(start, ["rev-parse", "--show-toplevel"])
    if result.returncode != 0:
        raise ValidatorConfigurationError(
            "The repository root could not be resolved with Git."
        )
    try:
        resolved = Path(result.stdout.decode("utf-8").strip()).resolve()
    except UnicodeDecodeError as error:
        raise ValidatorConfigurationError(
            "Git returned a repository root that is not valid UTF-8."
        ) from error
    if root_argument and resolved != start:
        raise ValidatorConfigurationError(
            "--root must identify the repository root, not a nested directory."
        )
    return resolved


def load_policy(root: Path) -> Dict[str, Any]:
    policy_path = root / "ci" / "validation-policy.json"
    if policy_path.is_symlink():
        raise ValidatorConfigurationError(
            "ci/validation-policy.json must not be a symbolic link."
        )
    try:
        policy = json.loads(
            policy_path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_json_keys,
        )
    except FileNotFoundError as error:
        raise ValidatorConfigurationError(
            "ci/validation-policy.json is missing."
        ) from error
    except DuplicateJsonKeyError as error:
        raise ValidatorConfigurationError(str(error)) from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValidatorConfigurationError(
            "ci/validation-policy.json is not valid UTF-8 JSON: {0}".format(error)
        ) from error

    required_keys = (
        "schemaVersion",
        "packageRoot",
        "expectedVersion",
        "previousVersion",
        "expectedIdentity",
        "requiredRootFiles",
        "requiredPackageFiles",
        "allowedAssemblyDefinitions",
        "allowedNamespaces",
        "approvedBinaryFiles",
        "forbiddenFilePatterns",
        "forbiddenDirectoryNames",
        "forbiddenPaths",
        "forbiddenPathPrefixes",
        "allowedPackageJsonPaths",
        "allowedEmails",
        "personalPathPatterns",
        "secretPatterns",
        "spanishCharacters",
        "spanishMarkers",
        "definitionFiles",
        "prohibitedCodePatterns",
        "protectedWorkflows",
        "roadmapGuard",
    )
    missing = [key for key in required_keys if key not in policy]
    if missing:
        raise ValidatorConfigurationError(
            "Validation policy is missing required keys: {0}.".format(
                ", ".join(sorted(missing))
            )
        )
    if policy["schemaVersion"] != 1:
        raise ValidatorConfigurationError(
            "Unsupported validation policy schemaVersion; expected 1."
        )
    non_empty_lists = (
        "requiredRootFiles",
        "requiredPackageFiles",
        "allowedAssemblyDefinitions",
        "allowedNamespaces",
        "approvedBinaryFiles",
        "forbiddenFilePatterns",
        "forbiddenDirectoryNames",
        "forbiddenPaths",
        "forbiddenPathPrefixes",
        "allowedPackageJsonPaths",
        "allowedEmails",
        "personalPathPatterns",
        "secretPatterns",
        "spanishMarkers",
        "definitionFiles",
        "prohibitedCodePatterns",
    )
    for key in non_empty_lists:
        if not isinstance(policy[key], list) or not policy[key]:
            raise ValidatorConfigurationError(
                "Validation policy key {0} must be a non-empty list.".format(key)
            )
    for entry in policy["approvedBinaryFiles"]:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("path"), str)
            or PurePosixPath(entry["path"]).is_absolute()
            or ".." in PurePosixPath(entry["path"]).parts
            or not re.fullmatch(r"[0-9a-f]{64}", str(entry.get("sha256", "")))
        ):
            raise ValidatorConfigurationError(
                "approvedBinaryFiles contains an invalid entry."
            )
    for key in (
        "packageRoot",
        "expectedVersion",
        "previousVersion",
        "spanishCharacters",
    ):
        if not isinstance(policy[key], str) or not policy[key]:
            raise ValidatorConfigurationError(
                "Validation policy key {0} must be a non-empty string.".format(key)
            )
    identity_keys = (
        "packageId",
        "displayName",
        "author",
        "authorEmail",
        "authorUrl",
        "repository",
        "repositoryUrl",
        "rootNamespace",
        "unity",
        "license",
    )
    identity = policy["expectedIdentity"]
    if not isinstance(identity, dict) or any(
        not isinstance(identity.get(key), str) or not identity.get(key)
        for key in identity_keys
    ):
        raise ValidatorConfigurationError(
            "Validation policy expectedIdentity is incomplete."
        )
    protected = policy["protectedWorkflows"]
    if not isinstance(protected, dict) or set(protected) != {
        "listing",
        "release",
        "validation",
    }:
        raise ValidatorConfigurationError(
            "Validation policy protectedWorkflows must define listing, release, and validation."
        )
    for workflow_name, configuration in protected.items():
        if (
            not isinstance(configuration, dict)
            or not isinstance(configuration.get("path"), str)
            or not re.fullmatch(
                r"[0-9a-f]{64}", str(configuration.get("sha256", ""))
            )
        ):
            raise ValidatorConfigurationError(
                "Protected workflow configuration is incomplete: {0}.".format(
                    workflow_name
                )
            )
    roadmap_guard = policy["roadmapGuard"]
    if (
        not isinstance(roadmap_guard, dict)
        or not isinstance(roadmap_guard.get("requiredReleases"), list)
        or not roadmap_guard["requiredReleases"]
        or not isinstance(roadmap_guard.get("requiredBoundaries"), list)
        or not roadmap_guard["requiredBoundaries"]
    ):
        raise ValidatorConfigurationError(
            "Validation policy roadmapGuard is incomplete."
        )
    for collection_key in (
        "personalPathPatterns",
        "secretPatterns",
        "prohibitedCodePatterns",
    ):
        for entry in policy[collection_key]:
            if not isinstance(entry, dict) or not entry.get("name") or not entry.get(
                "pattern"
            ):
                raise ValidatorConfigurationError(
                    "Policy entries in {0} require name and pattern.".format(
                        collection_key
                    )
                )
            try:
                re.compile(entry["pattern"])
            except re.error as error:
                raise ValidatorConfigurationError(
                    "Invalid regular expression in {0}: {1}.".format(
                        collection_key, error
                    )
                ) from error

    allowed_hygiene_rules = {"bom", "finalNewline", "trailingWhitespace"}
    hygiene_exceptions = policy.get("legacyTextHygieneExceptions", {})
    if not isinstance(hygiene_exceptions, dict):
        raise ValidatorConfigurationError(
            "legacyTextHygieneExceptions must be an object."
        )
    for path, entry in hygiene_exceptions.items():
        if (
            not isinstance(path, str)
            or PurePosixPath(path).is_absolute()
            or ".." in PurePosixPath(path).parts
            or not isinstance(entry, dict)
            or not re.fullmatch(r"[0-9a-f]{64}", str(entry.get("sha256", "")))
            or not isinstance(entry.get("rules"), list)
            or not entry["rules"]
            or not set(entry["rules"]).issubset(allowed_hygiene_rules)
        ):
            raise ValidatorConfigurationError(
                "Invalid legacy text hygiene exception for {0}.".format(path)
            )
    return policy


def load_tracked_files(root: Path) -> List[str]:
    result = run_git(root, ["ls-files", "-z"])
    if result.returncode != 0:
        raise ValidatorConfigurationError("git ls-files failed.")
    tracked_files: List[str] = []
    for raw_path in result.stdout.split(b"\0"):
        if not raw_path:
            continue
        try:
            relative_path = raw_path.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValidatorConfigurationError(
                "A tracked path is not valid UTF-8."
            ) from error
        pure_path = PurePosixPath(relative_path)
        if pure_path.is_absolute() or ".." in pure_path.parts:
            raise ValidatorConfigurationError(
                "Git returned an unsafe tracked path."
            )
        if any(ord(character) < 32 or ord(character) == 127 for character in relative_path):
            raise ValidatorConfigurationError(
                "A tracked path contains unsupported control characters."
            )
        tracked_files.append(pure_path.as_posix())
    return sorted(tracked_files)


def validate_tracked_paths(root: Path, tracked_files: Sequence[str]) -> None:
    for relative_path in tracked_files:
        absolute_path = root.joinpath(*PurePosixPath(relative_path).parts)
        if absolute_path.is_symlink():
            raise ValidatorConfigurationError(
                "Tracked symbolic links are not supported: {0}.".format(relative_path)
            )
        if not absolute_path.exists():
            continue
        try:
            absolute_path.resolve().relative_to(root)
        except ValueError as error:
            raise ValidatorConfigurationError(
                "Tracked path resolves outside the repository: {0}.".format(
                    relative_path
                )
            ) from error


def finding(
    check_id: str, path: str, message: str, expected: str = ""
) -> Finding:
    return Finding(check_id, path, message, expected)


def policy_scan_text(
    context: RepositoryContext,
    relative_path: str,
    excluded_policy_keys: Set[str],
) -> str:
    if relative_path != "ci/validation-policy.json":
        return context.read_text(relative_path)
    filtered_policy: Dict[str, Any] = {
        key: value
        for key, value in context.policy.items()
        if key not in excluded_policy_keys
    }

    strings: List[str] = []

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            for key in sorted(value):
                strings.append(str(key))
                collect(value[key])
        elif isinstance(value, list):
            for item in value:
                collect(item)
        elif isinstance(value, str):
            strings.append(value)

    collect(filtered_policy)
    return "\n".join(strings)


def parse_json_document(
    context: RepositoryContext, relative_path: str
) -> Tuple[Optional[Any], Optional[str]]:
    if not context.is_tracked(relative_path) or not context.absolute(relative_path).is_file():
        return None, "The required JSON file is not tracked."
    try:
        return (
            json.loads(
                context.read_text(relative_path),
                object_pairs_hook=reject_duplicate_json_keys,
            ),
            None,
        )
    except UnicodeDecodeError:
        return None, "The JSON file is not valid UTF-8."
    except json.JSONDecodeError as error:
        return None, "Invalid JSON at line {0}, column {1}.".format(
            error.lineno, error.colno
        )
    except DuplicateJsonKeyError as error:
        return None, str(error)


def expected_manifest_urls(policy: Dict[str, Any]) -> Dict[str, str]:
    repository_url = policy["expectedIdentity"]["repositoryUrl"]
    package_root = policy["packageRoot"]
    return {
        "licensesUrl": repository_url + "/blob/main/LICENSE",
        "changelogUrl": repository_url
        + "/blob/main/"
        + package_root
        + "/CHANGELOG.md",
        "documentationUrl": repository_url
        + "/blob/main/"
        + package_root
        + "/README.md",
    }


def check_manifest(context: RepositoryContext) -> List[Finding]:
    check_id = "MANIFEST"
    policy = context.policy
    identity = policy["expectedIdentity"]
    manifest_path = policy["packageRoot"] + "/package.json"
    manifest, error = parse_json_document(context, manifest_path)
    if error:
        return [finding(check_id, manifest_path, error, "Valid package JSON")]
    if not isinstance(manifest, dict):
        return [
            finding(check_id, manifest_path, "Manifest root must be an object.", "object")
        ]

    findings: List[Finding] = []
    expected_values = {
        "name": identity["packageId"],
        "displayName": identity["displayName"],
        "unity": identity["unity"],
        "license": identity["license"],
        "url": "",
    }
    expected_values.update(expected_manifest_urls(policy))
    for key, expected_value in expected_values.items():
        if manifest.get(key) != expected_value:
            findings.append(
                finding(
                    check_id,
                    manifest_path,
                    "Manifest field {0} is {1!r}.".format(key, manifest.get(key)),
                    repr(expected_value),
                )
            )

    author = manifest.get("author")
    if not isinstance(author, dict):
        findings.append(
            finding(check_id, manifest_path, "Manifest author must be an object.", "object")
        )
    else:
        author_expectations = {
            "name": identity["author"],
            "email": identity["authorEmail"],
            "url": identity["authorUrl"],
        }
        for key, expected_value in author_expectations.items():
            if author.get(key) != expected_value:
                findings.append(
                    finding(
                        check_id,
                        manifest_path,
                        "Manifest author.{0} is {1!r}.".format(key, author.get(key)),
                        repr(expected_value),
                    )
                )
        if isinstance(author.get("email"), str) and not author["email"].endswith(
            "@users.noreply.github.com"
        ):
            findings.append(
                finding(
                    check_id,
                    manifest_path,
                    "Manifest author email is not the approved public noreply address.",
                    identity["authorEmail"],
                )
            )

    version = manifest.get("version")
    if not isinstance(version, str) or not SEMVER_PATTERN.fullmatch(version):
        findings.append(
            finding(
                check_id,
                manifest_path,
                "Manifest version is not simple Semantic Versioning.",
                "X.Y.Z",
            )
        )

    dependencies = manifest.get("dependencies", {})
    if not isinstance(dependencies, dict) or dependencies:
        findings.append(
            finding(
                check_id,
                manifest_path,
                "Unauthorized package dependencies are present.",
                "No dependencies",
            )
        )
    return findings


def parse_package_constants(source: str) -> Dict[str, str]:
    return {
        name: value
        for name, value in re.findall(
            r'internal\s+const\s+string\s+([A-Za-z][A-Za-z0-9_]*)\s*=\s*"([^"]*)"\s*;',
            source,
        )
    }


def check_version(context: RepositoryContext) -> List[Finding]:
    check_id = "VERSION"
    policy = context.policy
    package_root = policy["packageRoot"]
    expected_version = policy["expectedVersion"]
    previous_version = policy["previousVersion"]
    manifest_path = package_root + "/package.json"
    source_path = package_root + "/Editor/Core/AvatarDoctorPackageInfo.cs"
    changelog_path = package_root + "/CHANGELOG.md"
    findings: List[Finding] = []

    manifest, error = parse_json_document(context, manifest_path)
    manifest_version = manifest.get("version") if isinstance(manifest, dict) else None
    if error or manifest_version != expected_version:
        findings.append(
            finding(
                check_id,
                manifest_path,
                "Manifest version is {0!r}.".format(manifest_version),
                expected_version,
            )
        )

    if context.is_tracked(source_path):
        try:
            constants = parse_package_constants(context.read_text(source_path))
        except UnicodeDecodeError:
            constants = {}
        if constants.get("Version") != expected_version:
            findings.append(
                finding(
                    check_id,
                    source_path,
                    "Version constant is {0!r}.".format(constants.get("Version")),
                    expected_version,
                )
            )
    else:
        findings.append(
            finding(check_id, source_path, "Version source is not tracked.", expected_version)
        )

    if context.is_tracked(changelog_path):
        try:
            changelog = context.read_text(changelog_path)
        except UnicodeDecodeError:
            changelog = ""
        required_lines = (
            "## [{0}] - 2026-08-03".format(expected_version),
            "[Unreleased]: {0}/compare/v{1}...HEAD".format(
                policy["expectedIdentity"]["repositoryUrl"], expected_version
            ),
            "[{0}]: {1}/compare/v{2}...v{0}".format(
                expected_version,
                policy["expectedIdentity"]["repositoryUrl"],
                previous_version,
            ),
        )
        for required_line in required_lines:
            if required_line not in changelog:
                findings.append(
                    finding(
                        check_id,
                        changelog_path,
                        "Required version reference is missing.",
                        required_line,
                    )
                )
    else:
        findings.append(
            finding(check_id, changelog_path, "Changelog is not tracked.", "Tracked file")
        )
    return findings


def check_identity(context: RepositoryContext) -> List[Finding]:
    check_id = "IDENTITY"
    policy = context.policy
    identity = policy["expectedIdentity"]
    package_root = policy["packageRoot"]
    manifest_path = package_root + "/package.json"
    source_path = package_root + "/Editor/Core/AvatarDoctorPackageInfo.cs"
    assembly_path = policy["allowedAssemblyDefinitions"][0]["path"]
    findings: List[Finding] = []

    manifest, _ = parse_json_document(context, manifest_path)
    if isinstance(manifest, dict):
        manifest_expectations = {
            "name": identity["packageId"],
            "displayName": identity["displayName"],
        }
        for key, expected_value in manifest_expectations.items():
            if manifest.get(key) != expected_value:
                findings.append(
                    finding(
                        check_id,
                        manifest_path,
                        "Identity field {0} is {1!r}.".format(key, manifest.get(key)),
                        repr(expected_value),
                    )
                )
        author = manifest.get("author")
        if not isinstance(author, dict) or author.get("name") != identity["author"]:
            findings.append(
                finding(
                    check_id,
                    manifest_path,
                    "Manifest author does not match policy.",
                    identity["author"],
                )
            )

    constants: Dict[str, str] = {}
    source = ""
    if context.is_tracked(source_path):
        try:
            source = context.read_text(source_path)
            constants = parse_package_constants(source)
        except UnicodeDecodeError:
            pass
    constant_expectations = {
        "PackageId": identity["packageId"],
        "DisplayName": identity["displayName"],
        "Author": identity["author"],
        "Repository": identity["repository"],
    }
    for name, expected_value in constant_expectations.items():
        if constants.get(name) != expected_value:
            findings.append(
                finding(
                    check_id,
                    source_path,
                    "Constant {0} is {1!r}.".format(name, constants.get(name)),
                    repr(expected_value),
                )
            )
    namespace_match = re.search(r"\bnamespace\s+([A-Za-z_][A-Za-z0-9_.]*)", source)
    if not namespace_match or not namespace_match.group(1).startswith(
        identity["rootNamespace"]
    ):
        findings.append(
            finding(
                check_id,
                source_path,
                "Source namespace does not use the approved root.",
                identity["rootNamespace"],
            )
        )

    assembly, error = parse_json_document(context, assembly_path)
    if error or not isinstance(assembly, dict):
        findings.append(
            finding(check_id, assembly_path, "Assembly identity could not be read.")
        )
    elif assembly.get("rootNamespace") != identity["rootNamespace"]:
        findings.append(
            finding(
                check_id,
                assembly_path,
                "Assembly rootNamespace does not match policy.",
                identity["rootNamespace"],
            )
        )
    return findings


def check_structure(context: RepositoryContext) -> List[Finding]:
    check_id = "STRUCTURE"
    policy = context.policy
    package_root = policy["packageRoot"]
    findings: List[Finding] = []
    required_paths = list(policy["requiredRootFiles"])
    required_paths.extend(
        package_root + "/" + relative_path
        for relative_path in policy["requiredPackageFiles"]
    )
    for relative_path in sorted(required_paths):
        if not context.is_tracked(relative_path):
            findings.append(
                finding(
                    check_id,
                    relative_path,
                    "Required file is not tracked.",
                    "Tracked file",
                )
            )
        elif not context.absolute(relative_path).is_file() or context.absolute(
            relative_path
        ).is_symlink():
            findings.append(
                finding(
                    check_id,
                    relative_path,
                    "Required tracked path is not available as a regular file.",
                    "Regular file",
                )
            )

    forbidden_directories = {
        "Correlation",
        "Diagnostics",
        "Integrations",
        "Publishing",
        "Quest",
        "Repairs",
        "Rules",
        "Runtime",
        "Scanning",
        "Tests",
        "UI",
    }
    package_prefix = package_root + "/"
    for relative_path in context.tracked_files:
        if not relative_path.startswith(package_prefix):
            continue
        package_parts = PurePosixPath(relative_path[len(package_prefix) :]).parts
        matched = sorted(forbidden_directories.intersection(package_parts))
        if matched:
            findings.append(
                finding(
                    check_id,
                    relative_path,
                    "Future package directory is present: {0}.".format(matched[0]),
                    "Directory absent until an authorized release",
                )
            )
        if relative_path.endswith(".gitkeep"):
            findings.append(
                finding(
                    check_id,
                    relative_path,
                    "Empty-folder placeholder is not allowed in the Unity package.",
                )
            )

    own_asmdefs = [
        path
        for path in context.tracked_files
        if path.startswith(package_prefix) and path.endswith(".asmdef")
    ]
    if any("/Runtime/" in "/" + path for path in own_asmdefs):
        findings.append(
            finding(
                check_id,
                package_root,
                "A Runtime assembly is present.",
                "No Runtime assembly",
            )
        )
    if any("/Tests/" in "/" + path for path in own_asmdefs):
        findings.append(
            finding(
                check_id,
                package_root,
                "A Unity test assembly is present.",
                "No test assembly",
            )
        )
    return findings


def check_assembly(context: RepositoryContext) -> List[Finding]:
    check_id = "ASSEMBLY"
    policy = context.policy
    package_prefix = policy["packageRoot"] + "/"
    allowed = policy["allowedAssemblyDefinitions"]
    allowed_paths = {entry["path"] for entry in allowed}
    own_asmdefs = sorted(
        path
        for path in context.tracked_files
        if path.startswith(package_prefix) and path.endswith(".asmdef")
    )
    findings: List[Finding] = []
    if len(own_asmdefs) != 1:
        findings.append(
            finding(
                check_id,
                policy["packageRoot"],
                "Found {0} package assembly definitions.".format(len(own_asmdefs)),
                "Exactly 1",
            )
        )
    for unexpected_path in sorted(set(own_asmdefs) - allowed_paths):
        findings.append(
            finding(check_id, unexpected_path, "Assembly definition is not allowed by policy.")
        )

    for expected in allowed:
        assembly_path = expected["path"]
        assembly, error = parse_json_document(context, assembly_path)
        if error or not isinstance(assembly, dict):
            findings.append(
                finding(check_id, assembly_path, error or "Assembly JSON must be an object.")
            )
            continue
        expectations = {
            "name": expected["name"],
            "rootNamespace": expected["rootNamespace"],
            "includePlatforms": expected["includePlatforms"],
            "references": [],
            "allowUnsafeCode": False,
            "overrideReferences": False,
            "precompiledReferences": [],
        }
        for key, expected_value in expectations.items():
            if assembly.get(key) != expected_value:
                findings.append(
                    finding(
                        check_id,
                        assembly_path,
                        "Assembly field {0} is {1!r}.".format(key, assembly.get(key)),
                        repr(expected_value),
                    )
                )
        serialized = json.dumps(assembly, sort_keys=True)
        if re.search(r"VRChat|VRC(?:SDK|\.)", serialized, re.IGNORECASE):
            findings.append(
                finding(
                    check_id,
                    assembly_path,
                    "Assembly contains a VRChat SDK reference.",
                    "No SDK references",
                )
            )
    return findings


def check_source(context: RepositoryContext) -> List[Finding]:
    check_id = "SOURCE"
    policy = context.policy
    package_prefix = policy["packageRoot"] + "/"
    allowed_namespaces = tuple(policy["allowedNamespaces"])
    source_paths = sorted(
        path
        for path in context.tracked_files
        if path.startswith(package_prefix) and path.endswith(".cs")
    )
    findings: List[Finding] = []
    if len(source_paths) != 1:
        findings.append(
            finding(
                check_id,
                policy["packageRoot"],
                "Found {0} package C# source files.".format(len(source_paths)),
                "Exactly 1",
            )
        )
    compiled_patterns = [
        (entry["name"], re.compile(entry["pattern"]))
        for entry in policy["prohibitedCodePatterns"]
    ]
    for source_path in source_paths:
        try:
            source = context.read_text(source_path)
        except UnicodeDecodeError:
            findings.append(
                finding(check_id, source_path, "C# source is not valid UTF-8.", "UTF-8")
            )
            continue
        identity = policy["expectedIdentity"]
        approved_constants = (
            ("PackageId", identity["packageId"]),
            ("DisplayName", identity["displayName"]),
            ("Version", policy["expectedVersion"]),
            ("Author", identity["author"]),
            ("Repository", identity["repository"]),
        )
        skeleton_parts = [
            r"\s*namespace\s+{0}\.Core\s*\{{".format(
                re.escape(identity["rootNamespace"])
            ),
            r"\s*internal\s+static\s+class\s+AvatarDoctorPackageInfo\s*\{",
        ]
        for constant_name, constant_value in approved_constants:
            skeleton_parts.append(
                r'\s*internal\s+const\s+string\s+{0}\s*=\s*"{1}"\s*;'.format(
                    re.escape(constant_name), re.escape(constant_value)
                )
            )
        skeleton_parts.append(r"\s*\}\s*\}\s*")
        if not re.fullmatch("".join(skeleton_parts), source):
            findings.append(
                finding(
                    check_id,
                    source_path,
                    "C# source differs from the approved metadata-only skeleton.",
                    "Namespace, internal static class, and five approved constants only",
                )
            )
        namespaces = re.findall(
            r"\bnamespace\s+([A-Za-z_][A-Za-z0-9_.]*)", source
        )
        if not namespaces:
            findings.append(
                finding(check_id, source_path, "C# source has no namespace declaration.")
            )
        for namespace in namespaces:
            if not any(
                namespace == allowed or namespace.startswith(allowed + ".")
                for allowed in allowed_namespaces
            ):
                findings.append(
                    finding(
                        check_id,
                        source_path,
                        "Namespace {0} is outside the allowed root.".format(namespace),
                        allowed_namespaces[0],
                    )
                )
        if re.search(
            r"\bpublic(?:\s+(?:abstract|new|partial|readonly|ref|sealed|static|unsafe))*"
            r"\s+(?:class|struct|interface|enum|record|delegate)\b",
            source,
        ):
            findings.append(
                finding(
                    check_id,
                    source_path,
                    "Public C# type declarations are not authorized.",
                    "Internal types only",
                )
            )
        if re.search(r"\bunsafe\b", source):
            findings.append(
                finding(check_id, source_path, "Unsafe C# code is not authorized.")
            )
        for name, pattern in compiled_patterns:
            match = pattern.search(source)
            if match:
                line = source.count("\n", 0, match.start()) + 1
                findings.append(
                    finding(
                        check_id,
                        source_path,
                        "Prohibited {0} pattern found at line {1}.".format(name, line),
                        "Pattern absent for the current release scope",
                    )
                )
    return findings


def metadata_value(text: str, key: str) -> Optional[str]:
    match = re.search(r"^{0}:\s*(.*?)\s*$".format(re.escape(key)), text, re.MULTILINE)
    return match.group(1) if match else None


def check_unity_metadata(context: RepositoryContext) -> List[Finding]:
    check_id = "UNITY_METADATA"
    package_root = context.policy["packageRoot"]
    editor_prefix = package_root + "/Editor"
    findings: List[Finding] = []
    all_meta_paths = sorted(
        path for path in context.tracked_files if path.endswith(".meta")
    )
    guid_paths: Dict[str, List[str]] = {}
    metadata_texts: Dict[str, str] = {}

    for meta_path in all_meta_paths:
        try:
            text = context.read_text(meta_path)
        except UnicodeDecodeError:
            findings.append(
                finding(check_id, meta_path, "Unity metadata is not valid UTF-8.")
            )
            continue
        metadata_texts[meta_path] = text
        format_version = metadata_value(text, "fileFormatVersion")
        guid = metadata_value(text, "guid")
        if format_version != "2":
            findings.append(
                finding(
                    check_id,
                    meta_path,
                    "fileFormatVersion is {0!r}.".format(format_version),
                    "2",
                )
            )
        if guid is None or not GUID_PATTERN.fullmatch(guid):
            findings.append(
                finding(
                    check_id,
                    meta_path,
                    "Unity GUID is missing or invalid.",
                    "32 hexadecimal characters",
                )
            )
        else:
            guid_paths.setdefault(guid.lower(), []).append(meta_path)

    for guid, paths in sorted(guid_paths.items()):
        if len(paths) > 1:
            joined_paths = ", ".join(sorted(paths))
            findings.append(
                finding(
                    check_id,
                    paths[0],
                    "Duplicate Unity GUID {0} appears in: {1}.".format(
                        guid, joined_paths
                    ),
                    "Unique GUID",
                )
            )

    code_assets = sorted(
        path
        for path in context.tracked_files
        if path.startswith(editor_prefix + "/")
        and (path.endswith(".cs") or path.endswith(".asmdef"))
    )
    relevant_directories: Set[str] = set()
    for asset_path in code_assets:
        meta_path = asset_path + ".meta"
        if not context.is_tracked(meta_path):
            findings.append(
                finding(
                    check_id,
                    asset_path,
                    "Code asset has no tracked metadata file.",
                    meta_path,
                )
            )
        elif meta_path in metadata_texts:
            text = metadata_texts[meta_path]
            importer = "MonoImporter:" if asset_path.endswith(".cs") else "AssemblyDefinitionImporter:"
            if importer not in text:
                findings.append(
                    finding(
                        check_id,
                        meta_path,
                        "Metadata uses the wrong importer.",
                        importer.rstrip(":"),
                    )
                )
        parent = PurePosixPath(asset_path).parent
        package_path = PurePosixPath(package_root)
        while parent != package_path and str(parent).startswith(package_root + "/"):
            relevant_directories.add(parent.as_posix())
            parent = parent.parent

    for directory in sorted(relevant_directories):
        meta_path = directory + ".meta"
        if not context.is_tracked(meta_path):
            findings.append(
                finding(
                    check_id,
                    directory,
                    "Code directory has no tracked folder metadata.",
                    meta_path,
                )
            )
            continue
        if meta_path not in metadata_texts:
            continue
        text = metadata_texts[meta_path]
        if metadata_value(text, "folderAsset") != "yes":
            findings.append(
                finding(
                    check_id,
                    meta_path,
                    "Folder metadata is missing folderAsset: yes.",
                    "folderAsset: yes",
                )
            )

    for meta_path in all_meta_paths:
        if not (meta_path == editor_prefix + ".meta" or meta_path.startswith(editor_prefix + "/")):
            continue
        asset_path = meta_path[: -len(".meta")]
        has_tracked_asset = context.is_tracked(asset_path)
        has_tracked_descendant = any(
            path.startswith(asset_path + "/") for path in context.tracked_files
        )
        if not has_tracked_asset and not has_tracked_descendant:
            findings.append(
                finding(
                    check_id,
                    meta_path,
                    "Metadata file has no tracked asset or directory content.",
                    "Matching tracked asset",
                )
            )
    return findings


def legacy_hygiene_rules(
    context: RepositoryContext, relative_path: str, data: bytes
) -> Set[str]:
    entry = context.policy.get("legacyTextHygieneExceptions", {}).get(relative_path)
    if not isinstance(entry, dict):
        return set()
    if entry.get("sha256") != hashlib.sha256(data).hexdigest():
        return set()
    rules = entry.get("rules", [])
    return {str(rule) for rule in rules}


def check_text_hygiene(context: RepositoryContext) -> List[Finding]:
    check_id = "TEXT_HYGIENE"
    findings: List[Finding] = []
    for entry in context.policy["approvedBinaryFiles"]:
        relative_path = str(entry["path"])
        if not context.is_tracked(relative_path) or not context.absolute(
            relative_path
        ).is_file():
            findings.append(
                finding(
                    check_id,
                    relative_path,
                    "Approved binary file is missing or not tracked.",
                    "Tracked binary with SHA-256 {0}".format(entry["sha256"]),
                )
            )
            continue
        actual_sha256 = hashlib.sha256(context.read_bytes(relative_path)).hexdigest()
        if actual_sha256 != entry["sha256"]:
            findings.append(
                finding(
                    check_id,
                    relative_path,
                    "Approved binary content does not match policy.",
                    "SHA-256 {0}".format(entry["sha256"]),
                )
            )
    for relative_path in context.text_paths():
        data = context.read_bytes(relative_path)
        exceptions = legacy_hygiene_rules(context, relative_path, data)
        if b"\0" in data:
            findings.append(
                finding(
                    check_id,
                    relative_path,
                    "Tracked text file contains a NUL byte.",
                    "No NUL bytes",
                )
            )
            continue
        if data.startswith(b"\xef\xbb\xbf") and "bom" not in exceptions:
            findings.append(
                finding(check_id, relative_path, "Tracked text file contains a UTF-8 BOM.")
            )
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as error:
            findings.append(
                finding(
                    check_id,
                    relative_path,
                    "Tracked text file is not valid UTF-8 at byte {0}.".format(
                        error.start
                    ),
                    "UTF-8",
                )
            )
            continue
        if "trailingWhitespace" not in exceptions:
            for line_number, line in enumerate(text.splitlines(), 1):
                if line.endswith(" ") or line.endswith("\t"):
                    findings.append(
                        finding(
                            check_id,
                            relative_path,
                            "Trailing whitespace at line {0}.".format(line_number),
                            "No trailing whitespace",
                        )
                    )
        if data and not data.endswith(b"\n") and "finalNewline" not in exceptions:
            findings.append(
                finding(
                    check_id,
                    relative_path,
                    "Tracked text file has no final newline.",
                    "Final newline",
                )
            )
        if CONFLICT_PATTERN.search(text):
            findings.append(
                finding(
                    check_id,
                    relative_path,
                    "Git conflict marker is present.",
                    "No conflict markers",
                )
            )
    return findings


def check_language(context: RepositoryContext) -> List[Finding]:
    check_id = "LANGUAGE"
    characters = set(context.policy["spanishCharacters"])
    markers = [str(value) for value in context.policy["spanishMarkers"]]
    findings: List[Finding] = []
    for relative_path in context.text_paths():
        try:
            text = policy_scan_text(
                context,
                relative_path,
                {"spanishCharacters", "spanishMarkers"},
            )
        except UnicodeDecodeError:
            continue
        detected_characters = sorted(set(text).intersection(characters))
        if detected_characters:
            findings.append(
                finding(
                    check_id,
                    relative_path,
                    "Basic Spanish character marker detected: {0}.".format(
                        "".join(detected_characters)
                    ),
                    "English public content or a documented exception",
                )
            )
        folded = text.casefold()
        for marker in markers:
            if marker.casefold() in folded:
                findings.append(
                    finding(
                        check_id,
                        relative_path,
                        "Basic Spanish marker detected: {0}.".format(marker),
                        "English public content or a documented exception",
                    )
                )
    return findings


def check_privacy(context: RepositoryContext) -> List[Finding]:
    check_id = "PRIVACY"
    allowed_emails = {str(value).casefold() for value in context.policy["allowedEmails"]}
    path_patterns = [
        (entry["name"], re.compile(entry["pattern"]))
        for entry in context.policy["personalPathPatterns"]
    ]
    findings: List[Finding] = []
    for relative_path in context.text_paths():
        try:
            text = policy_scan_text(
                context,
                relative_path,
                {"personalPathPatterns"},
            )
        except UnicodeDecodeError:
            continue
        for name, pattern in path_patterns:
            if pattern.search(text):
                findings.append(
                    finding(
                        check_id,
                        relative_path,
                        "Personal path pattern detected: {0}.".format(name),
                        "Relative paths or <repo-root>",
                    )
                )
        for email in sorted(set(EMAIL_PATTERN.findall(text))):
            if email.casefold() not in allowed_emails:
                findings.append(
                    finding(
                        check_id,
                        relative_path,
                        "Unapproved email address detected and redacted.",
                        "An explicitly allowed public address",
                    )
                )
    return findings


def check_secrets(context: RepositoryContext) -> List[Finding]:
    check_id = "SECRETS"
    patterns = [
        (entry["name"], re.compile(entry["pattern"]))
        for entry in context.policy["secretPatterns"]
    ]
    findings: List[Finding] = []
    for relative_path in context.text_paths():
        try:
            text = policy_scan_text(
                context,
                relative_path,
                {"secretPatterns"},
            )
        except UnicodeDecodeError:
            continue
        for name, pattern in patterns:
            if pattern.search(text):
                findings.append(
                    finding(
                        check_id,
                        relative_path,
                        "High-signal secret pattern detected: {0}.".format(name),
                        "No embedded credentials",
                    )
                )
    return findings


def check_prohibited_files(context: RepositoryContext) -> List[Finding]:
    check_id = "PROHIBITED_FILES"
    patterns = [
        str(value).casefold() for value in context.policy["forbiddenFilePatterns"]
    ]
    forbidden_directories = {
        str(value).casefold() for value in context.policy["forbiddenDirectoryNames"]
    }
    forbidden_paths = {
        str(value).casefold() for value in context.policy["forbiddenPaths"]
    }
    forbidden_prefixes = tuple(
        str(value).casefold() for value in context.policy["forbiddenPathPrefixes"]
    )
    allowed_package_json_paths = {
        str(value) for value in context.policy["allowedPackageJsonPaths"]
    }
    findings: List[Finding] = []
    for relative_path in context.tracked_files:
        pure_path = PurePosixPath(relative_path)
        folded_path = relative_path.casefold()
        if (
            pure_path.name.casefold() == "package.json"
            and relative_path not in allowed_package_json_paths
        ):
            findings.append(
                finding(
                    check_id,
                    relative_path,
                    "Package manifest path is not approved for the current release.",
                    "One of the explicitly allowed package.json paths",
                )
            )
        if folded_path in forbidden_paths or folded_path.startswith(
            forbidden_prefixes
        ):
            findings.append(
                finding(
                    check_id,
                    relative_path,
                    "Tracked path is explicitly prohibited for the current release.",
                    "Path absent from tracking",
                )
            )
        if any(
            fnmatch.fnmatchcase(pure_path.name.casefold(), pattern)
            for pattern in patterns
        ):
            findings.append(
                finding(
                    check_id,
                    relative_path,
                    "Tracked file matches a prohibited file pattern.",
                    "File removed from tracking",
                )
            )
        matched_directories = sorted(
            part for part in pure_path.parts[:-1] if part.casefold() in forbidden_directories
        )
        if matched_directories:
            findings.append(
                finding(
                    check_id,
                    relative_path,
                    "Tracked file is inside prohibited directory {0}.".format(
                        matched_directories[0]
                    ),
                    "Generated directory absent from tracking",
                )
            )
    return findings


def workflow_text(
    context: RepositoryContext, check_id: str, relative_path: str
) -> Tuple[Optional[str], List[Finding]]:
    if not context.is_tracked(relative_path):
        return None, [
            finding(check_id, relative_path, "Protected workflow is not tracked.")
        ]
    try:
        return context.read_text(relative_path), []
    except UnicodeDecodeError:
        return None, [
            finding(check_id, relative_path, "Protected workflow is not valid UTF-8.")
        ]


def top_level_block(text: str, key: str) -> List[str]:
    lines = text.splitlines()
    start: Optional[int] = None
    key_pattern = re.compile(r"^{0}:\s*$".format(re.escape(key)))
    for index, line in enumerate(lines):
        if key_pattern.fullmatch(line):
            start = index
            break
    if start is None:
        return []

    block = [lines[start].rstrip()]
    for line in lines[start + 1 :]:
        if line and not line[0].isspace() and not line.lstrip().startswith("#"):
            break
        if line.strip() and not line.lstrip().startswith("#"):
            block.append(line.rstrip())
    return block


def check_manual_workflow(
    context: RepositoryContext, configuration: Dict[str, Any]
) -> List[Finding]:
    check_id = "WORKFLOWS"
    path = configuration["path"]
    text, findings = workflow_text(context, check_id, path)
    if text is None:
        return findings
    expected_sha256 = configuration.get("sha256")
    actual_sha256 = hashlib.sha256(context.read_bytes(path)).hexdigest()
    if expected_sha256 != actual_sha256:
        findings.append(
            finding(
                check_id,
                path,
                "Protected distribution workflow differs from the approved base.",
                "SHA-256 {0}".format(expected_sha256),
            )
        )
    if top_level_block(text, "on") != ["on:", "  workflow_dispatch:"]:
        findings.append(
            finding(
                check_id,
                path,
                "Protected distribution workflow triggers are not manual-only.",
                "on: workflow_dispatch only",
            )
        )
    for condition in configuration["requiredConditions"]:
        if not re.search(
            r"^[ \t]+if:\s*[^#\n]*{0}[^#\n]*$".format(re.escape(condition)),
            text,
            re.MULTILINE,
        ):
            findings.append(
                finding(
                    check_id,
                    path,
                    "Required distribution gate is missing.",
                    condition,
                )
            )
    required_tag = configuration.get("requiredTagTemplate")
    if required_tag and not re.search(
        r"^[ \t]+(?:tag|tag_name):\s*[\"']?{0}[\"']?\s*$".format(
            re.escape(required_tag)
        ),
        text,
        re.MULTILINE,
    ):
        findings.append(
            finding(
                check_id,
                path,
                "Required release tag template is missing.",
                required_tag,
            )
        )
    return findings


def check_validation_workflow(
    context: RepositoryContext, configuration: Dict[str, Any]
) -> List[Finding]:
    check_id = "WORKFLOWS"
    path = configuration["path"]
    text, findings = workflow_text(context, check_id, path)
    if text is None:
        return findings

    actual_sha256 = hashlib.sha256(context.read_bytes(path)).hexdigest()
    if configuration.get("sha256") != actual_sha256:
        findings.append(
            finding(
                check_id,
                path,
                "Validation workflow differs from the versioned approved definition.",
                "SHA-256 {0}".format(configuration.get("sha256")),
            )
        )

    top_level_keys = re.findall(
        r"^([A-Za-z][A-Za-z0-9_-]*):", text, re.MULTILINE
    )
    expected_top_level_keys = ["name", "on", "permissions", "concurrency", "jobs"]
    if top_level_keys != expected_top_level_keys:
        findings.append(
            finding(
                check_id,
                path,
                "Validation workflow top-level structure is not the approved exact set.",
                ", ".join(expected_top_level_keys),
            )
        )

    expected_triggers = [
        "on:",
        "  pull_request:",
        "  push:",
        "    branches:",
        "      - main",
        "  workflow_dispatch:",
    ]
    if top_level_block(text, "on") != expected_triggers:
        findings.append(
            finding(
                check_id,
                path,
                "Validation workflow triggers are not the approved exact set.",
                "Pull Requests, pushes only to main, and manual dispatch",
            )
        )

    if top_level_block(text, "permissions") != [
        "permissions:",
        "  contents: read",
    ]:
        findings.append(
            finding(
                check_id,
                path,
                "Validation workflow permissions are not read-only contents access.",
                "permissions: contents: read",
            )
        )

    job_identifiers = re.findall(r"^\s{2}([A-Za-z0-9_-]+):\s*$", "\n".join(top_level_block(text, "jobs")), re.MULTILINE)
    if job_identifiers != [configuration["job"]]:
        findings.append(
            finding(
                check_id,
                path,
                "Validation workflow jobs are not the approved exact set: {0}.".format(
                    ", ".join(job_identifiers) if job_identifiers else "none"
                ),
                configuration["job"],
            )
        )

    required_patterns = (
        (r"^name:\s*Repository Validation\s*$", "name: Repository Validation"),
        (r"^\s{2}pull_request:\s*$", "pull_request trigger"),
        (r"^\s{2}push:\s*$", "push trigger"),
        (r"^\s{4}branches:\s*$", "push branches list"),
        (r"^\s{6}- main\s*$", "push branch main"),
        (r"^\s{2}workflow_dispatch:\s*$", "workflow_dispatch trigger"),
        (r"^permissions:\s*$", "top-level permissions"),
        (r"^\s{2}contents:\s*read\s*$", "contents: read"),
        (r"^\s{2}validate:\s*$", "validate job identifier"),
        (r"^\s{4}name:\s*validate\s*$", "validate job name"),
        (r"^\s{4}runs-on:\s*ubuntu-latest\s*$", "ubuntu-latest runner"),
        (
            r"^\s{{4}}timeout-minutes:\s*{0}\s*$".format(
                configuration["timeoutMinutes"]
            ),
            "job timeout",
        ),
        (
            r"^\s{{8}}uses:\s*{0}\s*$".format(re.escape(configuration["checkout"])),
            "pinned checkout",
        ),
        (r"^\s{10}fetch-depth:\s*0\s*$", "fetch-depth: 0"),
        (
            r"^\s{10}persist-credentials:\s*false\s*$",
            "persist-credentials: false",
        ),
        (r"^\s{8}run:\s*python3 --version\s*$", "python3 --version step"),
        (
            r"^\s{{8}}run:\s*{0}\s*$".format(re.escape(configuration["command"])),
            "repository validator command",
        ),
        (r"^\s{2}cancel-in-progress:\s*true\s*$", "concurrency cancellation"),
        (
            r"^\s{2}group:\s*repository-validation-\$\{\{ github\.workflow \}\}-\$\{\{ github\.event\.pull_request\.number \|\| github\.ref \}\}\s*$",
            "stable validation concurrency group",
        ),
    )
    for pattern, expected in required_patterns:
        if not re.search(pattern, text, re.MULTILINE):
            findings.append(
                finding(
                    check_id,
                    path,
                    "Required validation workflow setting is missing.",
                    expected,
                )
            )

    forbidden_patterns = (
        (r"\bpull_request_target\b", "pull_request_target"),
        (r"\bsecrets\s*\.", "secret reference"),
        (r"\bcontinue-on-error\s*:\s*true\b", "continue-on-error"),
        (r"^[ \t]+[^#\n]+:\s*write\s*$", "write permission"),
        (r"^[ \t]+permissions\s*:", "job-level permissions"),
        (r"^permissions\s*:\s*write-all\s*$", "write-all permission"),
        (
            r"^[ \t]+(?:container|defaults|env|environment|services|shell|working-directory)\s*:",
            "execution-altering setting",
        ),
        (r"actions/upload-artifact", "artifact upload"),
        (r"actions/deploy-pages", "Pages deployment"),
        (r"\bworkflow_call\s*:", "reusable workflow trigger"),
    )
    for pattern, description in forbidden_patterns:
        if re.search(pattern, text, re.MULTILINE):
            findings.append(
                finding(
                    check_id,
                    path,
                    "Forbidden validation workflow setting found: {0}.".format(
                        description
                    ),
                    "Setting absent",
                )
            )

    uses_values = re.findall(r"^\s*uses:\s*(\S+)\s*$", text, re.MULTILINE)
    if uses_values != [configuration["checkout"]]:
        findings.append(
            finding(
                check_id,
                path,
                "Validation workflow uses unexpected actions: {0}.".format(
                    ", ".join(uses_values) if uses_values else "none"
                ),
                configuration["checkout"],
            )
        )

    run_values = re.findall(r"^\s*run:\s*(.*?)\s*$", text, re.MULTILINE)
    expected_run_values = ["python3 --version", configuration["command"]]
    if run_values != expected_run_values:
        findings.append(
            finding(
                check_id,
                path,
                "Validation workflow commands are not the approved exact set: {0}.".format(
                    ", ".join(run_values) if run_values else "none"
                ),
                ", ".join(expected_run_values),
            )
        )
    return findings


def check_workflows(context: RepositoryContext) -> List[Finding]:
    protected = context.policy["protectedWorkflows"]
    findings: List[Finding] = []
    configured_paths = {
        str(configuration["path"]) for configuration in protected.values()
    }
    workflow_paths = {
        path
        for path in context.tracked_files
        if path.startswith(".github/workflows/")
        and PurePosixPath(path).suffix.casefold() in {".yml", ".yaml"}
    }
    for unexpected_path in sorted(workflow_paths - configured_paths):
        findings.append(
            finding(
                "WORKFLOWS",
                unexpected_path,
                "Workflow is not approved by the validation policy.",
                "Remove it or review and add it deliberately to policy",
            )
        )
    findings.extend(check_manual_workflow(context, protected["release"]))
    findings.extend(check_manual_workflow(context, protected["listing"]))
    findings.extend(check_validation_workflow(context, protected["validation"]))
    return findings


def check_roadmap_guard(context: RepositoryContext) -> List[Finding]:
    check_id = "ROADMAP_GUARD"
    path = "docs/ROADMAP.md"
    if not context.is_tracked(path):
        return [finding(check_id, path, "Roadmap is not tracked.")]
    try:
        roadmap = context.read_text(path)
    except UnicodeDecodeError:
        return [finding(check_id, path, "Roadmap is not valid UTF-8.")]
    guard = context.policy["roadmapGuard"]
    findings: List[Finding] = []
    for release in guard["requiredReleases"]:
        if release not in roadmap:
            findings.append(
                finding(
                    check_id,
                    path,
                    "Required roadmap release is missing.",
                    release,
                )
            )
    for boundary in guard["requiredBoundaries"]:
        if boundary not in roadmap:
            findings.append(
                finding(
                    check_id,
                    path,
                    "Required roadmap scope boundary is missing.",
                    boundary,
                )
            )
    return findings


CHECKS: Dict[str, Callable[[RepositoryContext], List[Finding]]] = {
    "MANIFEST": check_manifest,
    "VERSION": check_version,
    "IDENTITY": check_identity,
    "STRUCTURE": check_structure,
    "ASSEMBLY": check_assembly,
    "SOURCE": check_source,
    "UNITY_METADATA": check_unity_metadata,
    "TEXT_HYGIENE": check_text_hygiene,
    "LANGUAGE": check_language,
    "PRIVACY": check_privacy,
    "SECRETS": check_secrets,
    "PROHIBITED_FILES": check_prohibited_files,
    "WORKFLOWS": check_workflows,
    "ROADMAP_GUARD": check_roadmap_guard,
}


def sanitize_internal_message(message: str, root: Path) -> str:
    sanitized = message.replace(str(root), "<repo-root>")
    return sanitized.replace(str(root).replace("/", "\\"), "<repo-root>")


def execute_validation(context: RepositoryContext) -> int:
    results: Dict[str, List[Finding]] = {}
    internal_errors: List[Tuple[str, str]] = []
    for check_id in CHECK_ORDER:
        try:
            results[check_id] = sorted(
                CHECKS[check_id](context), key=lambda item: item.sort_key()
            )
        except Exception as error:  # Internal failures must use exit code 2.
            results[check_id] = []
            internal_errors.append(
                (
                    check_id,
                    sanitize_internal_message(
                        "{0}: {1}".format(type(error).__name__, error), context.root
                    ),
                )
            )

    internal_error_map = dict(internal_errors)
    for check_id in CHECK_ORDER:
        if check_id in internal_error_map:
            print(
                "[ERROR] {0} — {1}".format(
                    check_id, internal_error_map[check_id]
                ),
                file=sys.stderr,
            )
            continue
        check_findings = results[check_id]
        if check_findings:
            for check_finding in check_findings:
                print(check_finding.render())
        else:
            print("[PASS] {0} — {1}".format(check_id, PASS_MESSAGES[check_id]))

    failed_checks = sum(1 for check_id in CHECK_ORDER if results[check_id])
    passed_checks = len(CHECK_ORDER) - failed_checks - len(internal_errors)
    print()
    if internal_errors:
        print("Repository validation could not complete.")
    elif failed_checks:
        print("Repository validation failed.")
    else:
        print("Repository validation passed.")
    print("Checks: {0}".format(len(CHECK_ORDER)))
    print("Passed: {0}".format(passed_checks))
    print("Failed: {0}".format(failed_checks))
    if internal_errors:
        print("Errors: {0}".format(len(internal_errors)))
        return 2
    return 1 if failed_checks else 0


def parse_arguments(arguments: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate tracked repository files against versioned policy."
    )
    parser.add_argument(
        "--root",
        help="Repository root. Git auto-detection is used when omitted.",
    )
    return parser.parse_args(arguments)


def main(arguments: Optional[Sequence[str]] = None) -> int:
    parsed = parse_arguments(arguments)
    root: Optional[Path] = None
    try:
        root = resolve_repository_root(parsed.root)
        policy = load_policy(root)
        tracked_files = load_tracked_files(root)
        validate_tracked_paths(root, tracked_files)
        context = RepositoryContext(root, policy, tracked_files)
        return execute_validation(context)
    except ValidatorConfigurationError as error:
        message = str(error)
        if root is not None:
            message = sanitize_internal_message(message, root)
        print("[ERROR] CONFIG — {0}".format(message), file=sys.stderr)
        print(file=sys.stderr)
        print("Repository validation could not complete.", file=sys.stderr)
        print("Checks: 0", file=sys.stderr)
        print("Passed: 0", file=sys.stderr)
        print("Failed: 0", file=sys.stderr)
        print("Errors: 1", file=sys.stderr)
        return 2
    except Exception as error:  # Last-resort execution failure handling.
        message = "{0}: {1}".format(type(error).__name__, error)
        if root is not None:
            message = sanitize_internal_message(message, root)
        print("[ERROR] VALIDATOR — {0}".format(message), file=sys.stderr)
        print(file=sys.stderr)
        print("Repository validation could not complete.", file=sys.stderr)
        print("Checks: 0", file=sys.stderr)
        print("Passed: 0", file=sys.stderr)
        print("Failed: 0", file=sys.stderr)
        print("Errors: 1", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
