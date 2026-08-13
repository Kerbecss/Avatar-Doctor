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
    "EDITOR_WINDOW",
    "UNITY_METADATA",
    "TEXT_HYGIENE",
    "LANGUAGE",
    "PRIVACY",
    "SECRETS",
    "PROHIBITED_FILES",
    "WORKFLOWS",
    "ROADMAP_GUARD",
    "PUBLIC_CONTENT",
)

PASS_MESSAGES = {
    "MANIFEST": "Package manifest is valid.",
    "VERSION": "Package version references are consistent.",
    "IDENTITY": "Package identity is consistent.",
    "STRUCTURE": "Required repository structure is valid.",
    "ASSEMBLY": "Editor assembly configuration is valid.",
    "SOURCE": "Package source matches the active policy.",
    "EDITOR_WINDOW": "The Editor window shell matches the active policy.",
    "UNITY_METADATA": "Unity metadata is structurally valid.",
    "TEXT_HYGIENE": "Tracked text files satisfy the active hygiene policy.",
    "LANGUAGE": "No basic non-English language markers were found.",
    "PRIVACY": "No personal path or unapproved email patterns were found.",
    "SECRETS": "No high-signal secret patterns were found.",
    "PROHIBITED_FILES": "No prohibited tracked files were found.",
    "WORKFLOWS": "Protected workflow conditions are valid.",
    "ROADMAP_GUARD": "The roadmap release sequence is valid.",
    "PUBLIC_CONTENT": "Maintained public content matches the active policy.",
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
        "releaseDate",
        "expectedPackageUrl",
        "expectedIdentity",
        "requiredRootFiles",
        "requiredPackageFiles",
        "allowedAssemblyDefinitions",
        "allowedNamespaces",
        "sourceProfiles",
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
        "publicContent",
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
        "releaseDate",
        "spanishCharacters",
    ):
        if not isinstance(policy[key], str) or not policy[key]:
            raise ValidatorConfigurationError(
                "Validation policy key {0} must be a non-empty string.".format(key)
            )
    if not isinstance(policy["expectedPackageUrl"], str):
        raise ValidatorConfigurationError(
            "Validation policy expectedPackageUrl must be a string."
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
    if not SEMVER_PATTERN.fullmatch(policy["expectedVersion"]) or not SEMVER_PATTERN.fullmatch(
        policy["previousVersion"]
    ):
        raise ValidatorConfigurationError(
            "Validation policy versions must use simple Semantic Versioning."
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
    protected_keys = {
        "release": {
            "path",
            "name",
            "job",
            "runner",
            "timeoutMinutes",
            "expectedVersion",
            "checkout",
            "uploadArtifact",
            "artifactName",
            "artifactFiles",
            "retentionDays",
        },
        "listing": {
            "path",
            "name",
            "job",
            "runner",
            "timeoutMinutes",
            "expectedVersion",
            "checkout",
            "uploadArtifact",
            "packageListRepository",
            "packageListRef",
            "artifactName",
            "artifactFile",
            "retentionDays",
        },
        "validation": {
            "path",
            "name",
            "job",
            "runner",
            "timeoutMinutes",
            "expectedVersion",
            "checkout",
            "validatorCommand",
            "testCommand",
        },
    }
    for workflow_name, configuration in protected.items():
        if not isinstance(configuration, dict) or set(configuration) != protected_keys[
            workflow_name
        ]:
            raise ValidatorConfigurationError(
                "Protected workflow configuration is incomplete: {0}.".format(
                    workflow_name
                )
            )
        string_keys = protected_keys[workflow_name] - {
            "artifactFiles",
            "retentionDays",
            "timeoutMinutes",
        }
        if any(
            not isinstance(configuration.get(key), str) or not configuration[key]
            for key in string_keys
        ):
            raise ValidatorConfigurationError(
                "Protected workflow strings are incomplete: {0}.".format(workflow_name)
            )
        if (
            not isinstance(configuration["timeoutMinutes"], int)
            or configuration["timeoutMinutes"] <= 0
        ):
            raise ValidatorConfigurationError(
                "Protected workflow timeout is invalid: {0}.".format(workflow_name)
            )
        workflow_path = PurePosixPath(configuration["path"])
        if (
            workflow_path.is_absolute()
            or ".." in workflow_path.parts
            or workflow_path.parts[:2] != (".github", "workflows")
            or workflow_path.suffix.casefold() not in {".yml", ".yaml"}
            or not SEMVER_PATTERN.fullmatch(configuration["expectedVersion"])
        ):
            raise ValidatorConfigurationError(
                "Protected workflow path or version is invalid: {0}.".format(
                    workflow_name
                )
            )
        for action_key in ("checkout", "uploadArtifact"):
            action = configuration.get(action_key)
            if action is not None and not re.fullmatch(
                r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}", action
            ):
                raise ValidatorConfigurationError(
                    "Protected workflow action is not pinned to a full commit: {0}.".format(
                        workflow_name
                    )
                )
    release_configuration = protected["release"]
    if (
        not isinstance(release_configuration["artifactFiles"], list)
        or not release_configuration["artifactFiles"]
        or len(release_configuration["artifactFiles"])
        != len(set(release_configuration["artifactFiles"]))
        or any(
            not isinstance(value, str)
            or not value
            or PurePosixPath(value).name != value
            for value in release_configuration["artifactFiles"]
        )
        or not isinstance(release_configuration["retentionDays"], int)
        or release_configuration["retentionDays"] <= 0
    ):
        raise ValidatorConfigurationError(
            "Protected release workflow artifact configuration is invalid."
        )
    listing_configuration = protected["listing"]
    if (
        not re.fullmatch(r"[0-9a-f]{40}", listing_configuration["packageListRef"])
        or not isinstance(listing_configuration["retentionDays"], int)
        or listing_configuration["retentionDays"] <= 0
    ):
        raise ValidatorConfigurationError(
            "Protected listing workflow dependency configuration is invalid."
        )
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", policy["releaseDate"]):
        raise ValidatorConfigurationError(
            "Validation policy releaseDate must use YYYY-MM-DD."
        )
    if len({configuration["path"] for configuration in protected.values()}) != 3:
        raise ValidatorConfigurationError(
            "Protected workflow paths must be unique."
        )
    expected_version_tuple = tuple(
        int(component) for component in policy["expectedVersion"].split(".")
    )
    if expected_version_tuple >= (0, 0, 6):
        expected_package_url = expected_release_zip_url(policy)
        if policy["expectedPackageUrl"] != expected_package_url:
            raise ValidatorConfigurationError(
                "Validation policy expectedPackageUrl is not the exact release ZIP URL."
            )
        if any(
            configuration["expectedVersion"] != policy["expectedVersion"]
            for configuration in protected.values()
        ):
            raise ValidatorConfigurationError(
                "Protected workflow versions must match expectedVersion."
            )
    roadmap_guard = policy["roadmapGuard"]
    roadmap_keys = (
        "requiredStages",
        "orderedReleaseHeadings",
        "forbiddenHeadings",
        "requiredStableCapabilities",
    )
    if not isinstance(roadmap_guard, dict) or any(
        not isinstance(roadmap_guard.get(key), list) or not roadmap_guard[key]
        for key in roadmap_keys
    ):
        raise ValidatorConfigurationError("Validation policy roadmapGuard is incomplete.")
    for key in roadmap_keys:
        values = roadmap_guard[key]
        if any(not isinstance(value, str) or not value for value in values):
            raise ValidatorConfigurationError(
                "Validation policy roadmapGuard.{0} must contain strings.".format(key)
            )
        if len(values) != len(set(values)):
            raise ValidatorConfigurationError(
                "Validation policy roadmapGuard.{0} contains duplicates.".format(key)
            )
    expected_versions = []
    for heading in roadmap_guard["orderedReleaseHeadings"]:
        match = re.fullmatch(
            r"(v[0-9]+\.[0-9]+\.[0-9]+(?:-rc\.[0-9]+)?) — .+", heading
        )
        if not match:
            raise ValidatorConfigurationError(
                "Validation policy contains an invalid roadmap release heading."
            )
        expected_versions.append(match.group(1))
    if len(expected_versions) != len(set(expected_versions)):
        raise ValidatorConfigurationError(
            "Validation policy roadmap release versions must be unique."
        )

    public_content = policy["publicContent"]
    public_content_keys = (
        "requiredPaths",
        "includeGlobs",
        "requiredSections",
    )
    if not isinstance(public_content, dict) or set(public_content) != set(
        public_content_keys
    ):
        raise ValidatorConfigurationError(
            "Validation policy publicContent is incomplete."
        )
    for key in ("requiredPaths", "includeGlobs"):
        if not isinstance(public_content[key], list) or not public_content[key]:
            raise ValidatorConfigurationError(
                "Validation policy publicContent.{0} must be a non-empty list.".format(
                    key
                )
            )
    for path in public_content["requiredPaths"]:
        pure_path = PurePosixPath(str(path))
        if (
            not isinstance(path, str)
            or not path
            or pure_path.is_absolute()
            or ".." in pure_path.parts
        ):
            raise ValidatorConfigurationError(
                "Validation policy publicContent contains an invalid required path."
            )
    if any(
        not isinstance(pattern, str) or not pattern
        for pattern in public_content["includeGlobs"]
    ):
        raise ValidatorConfigurationError(
            "Validation policy publicContent includeGlobs must contain strings."
        )
    required_sections = public_content["requiredSections"]
    if not isinstance(required_sections, dict) or not required_sections:
        raise ValidatorConfigurationError(
            "Validation policy publicContent.requiredSections must be an object."
        )
    for path, sections in required_sections.items():
        if (
            path not in public_content["requiredPaths"]
            or not isinstance(sections, list)
            or not sections
            or any(not isinstance(section, str) or not section for section in sections)
        ):
            raise ValidatorConfigurationError(
                "Validation policy publicContent required sections are invalid."
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

    source_profiles = policy["sourceProfiles"]
    expected_source_profiles = {
        policy["packageRoot"] + "/Editor/Core/AvatarDoctorPackageInfo.cs": "constantsOnly",
        policy["packageRoot"] + "/Editor/UI/AvatarDoctorWindow.cs": "editorWindowShell",
    }
    if not isinstance(source_profiles, dict) or set(source_profiles) != set(
        expected_source_profiles
    ):
        raise ValidatorConfigurationError(
            "sourceProfiles must define exactly the two package source files allowed by policy."
        )
    prohibited_pattern_names = {
        entry["name"] for entry in policy["prohibitedCodePatterns"]
    }
    required_window_exceptions = {
        "Unity Editor API",
        "Unity runtime API",
        "Editor window",
        "Menu item",
        "Method or invocation syntax",
    }
    for path, expected_profile in sorted(expected_source_profiles.items()):
        configuration = source_profiles[path]
        if (
            not isinstance(configuration, dict)
            or set(configuration) != {"profile", "allowedProhibitedCodePatterns"}
            or configuration.get("profile") != expected_profile
            or not isinstance(configuration.get("allowedProhibitedCodePatterns"), list)
            or len(configuration["allowedProhibitedCodePatterns"])
            != len(set(configuration["allowedProhibitedCodePatterns"]))
            or not set(configuration["allowedProhibitedCodePatterns"]).issubset(
                prohibited_pattern_names
            )
        ):
            raise ValidatorConfigurationError(
                "Invalid source profile configuration for {0}.".format(path)
            )
        allowed_patterns = set(configuration["allowedProhibitedCodePatterns"])
        expected_patterns = (
            set() if expected_profile == "constantsOnly" else required_window_exceptions
        )
        if allowed_patterns != expected_patterns:
            raise ValidatorConfigurationError(
                "Source profile exceptions are not exact for {0}.".format(path)
            )

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


def expected_release_zip_url(policy: Dict[str, Any]) -> str:
    identity = policy["expectedIdentity"]
    version = policy["expectedVersion"]
    package_id = identity["packageId"]
    return "{0}/releases/download/v{1}/{2}-{1}.zip".format(
        identity["repositoryUrl"], version, package_id
    )


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
        "url": policy["expectedPackageUrl"],
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
                "Package dependencies are outside the active policy.",
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
            "## [{0}] - {1}".format(expected_version, policy["releaseDate"]),
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
                    "Directory absent until its planned implementation release",
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

    own_sources = sorted(
        path
        for path in context.tracked_files
        if path.startswith(package_prefix) and path.endswith(".cs")
    )
    if len(own_sources) != 2:
        findings.append(
            finding(
                check_id,
                package_root,
                "Found {0} package C# source files.".format(len(own_sources)),
                "Exactly 2",
            )
        )
    editor_window_count = 0
    menu_item_count = 0
    for source_path in own_sources:
        try:
            source = context.read_text(source_path)
        except UnicodeDecodeError:
            continue
        editor_window_count += len(
            re.findall(r"\bclass\s+[A-Za-z_][A-Za-z0-9_]*\s*:\s*EditorWindow\b", source)
        )
        menu_item_count += len(re.findall(r"\[\s*MenuItem\s*\(", source))
    if editor_window_count != 1:
        findings.append(
            finding(
                check_id,
                package_root,
                "Found {0} Editor window classes.".format(editor_window_count),
                "Exactly 1",
            )
        )
    if menu_item_count != 1:
        findings.append(
            finding(
                check_id,
                package_root,
                "Found {0} MenuItem attributes.".format(menu_item_count),
                "Exactly 1",
            )
        )

    for extension, label in ((".uxml", "UXML"), (".uss", "USS")):
        matching_assets = sorted(
            path
            for path in context.tracked_files
            if path.startswith(package_prefix) and path.lower().endswith(extension)
        )
        if matching_assets:
            findings.append(
                finding(
                    check_id,
                    matching_assets[0],
                    "Found {0} package {1} files.".format(
                        len(matching_assets), label
                    ),
                    "Exactly 0",
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


def check_constants_only_source(
    context: RepositoryContext, source_path: str, source: str
) -> List[Finding]:
    check_id = "SOURCE"
    policy = context.policy
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
    if re.fullmatch("".join(skeleton_parts), source):
        return []
    return [
        finding(
            check_id,
            source_path,
            "C# source differs from the constants-only source profile.",
            "Namespace, internal static class, and five approved constants only",
        )
    ]


def expected_editor_window_lines() -> Tuple[str, ...]:
    return (
        "using Teyocesu.AvatarDoctor.Editor.Core;",
        "using UnityEditor;",
        "using UnityEngine;",
        "using UnityEngine.UIElements;",
        "namespace Teyocesu.AvatarDoctor.Editor.UI",
        "{",
        "internal sealed class AvatarDoctorWindow : EditorWindow",
        "{",
        'private const string MenuPath = "Tools/Avatar Doctor";',
        "private const int MenuPriority = 2000;",
        "private const float MinimumWidth = 420f;",
        "private const float MinimumHeight = 220f;",
        'private const string StatusText = "Pre-alpha - Window shell";',
        'private const string UnavailableAnalysisMessage = "Avatar analysis is not available in this version.";',
        'private const string VersionPrefix = "Version ";',
        "[MenuItem(MenuPath, false, MenuPriority)]",
        "private static void OpenWindow()",
        "{",
        "AvatarDoctorWindow window = GetWindow<AvatarDoctorWindow>();",
        "window.titleContent = new GUIContent(AvatarDoctorPackageInfo.DisplayName);",
        "window.minSize = new Vector2(MinimumWidth, MinimumHeight);",
        "window.Show();",
        "}",
        "private void OnEnable()",
        "{",
        "titleContent = new GUIContent(AvatarDoctorPackageInfo.DisplayName);",
        "minSize = new Vector2(MinimumWidth, MinimumHeight);",
        "}",
        "public void CreateGUI()",
        "{",
        "VisualElement root = rootVisualElement;",
        "rootVisualElement.Clear();",
        "root.style.flexDirection = FlexDirection.Column;",
        "root.style.flexGrow = 1;",
        "root.style.paddingTop = 16;",
        "root.style.paddingRight = 16;",
        "root.style.paddingBottom = 16;",
        "root.style.paddingLeft = 16;",
        "VisualElement content = new VisualElement();",
        "content.style.flexDirection = FlexDirection.Column;",
        "content.style.flexGrow = 1;",
        "Label heading = new Label(AvatarDoctorPackageInfo.DisplayName);",
        "heading.style.fontSize = 20;",
        "heading.style.unityFontStyleAndWeight = FontStyle.Bold;",
        "heading.style.whiteSpace = WhiteSpace.Normal;",
        "heading.style.marginBottom = 8;",
        "content.Add(heading);",
        "Label status = new Label(StatusText);",
        "status.style.unityFontStyleAndWeight = FontStyle.Bold;",
        "status.style.whiteSpace = WhiteSpace.Normal;",
        "status.style.marginBottom = 8;",
        "content.Add(status);",
        "Label unavailableAnalysis = new Label(UnavailableAnalysisMessage);",
        "unavailableAnalysis.style.whiteSpace = WhiteSpace.Normal;",
        "unavailableAnalysis.style.marginBottom = 8;",
        "content.Add(unavailableAnalysis);",
        "Label version = new Label(VersionPrefix + AvatarDoctorPackageInfo.Version);",
        "version.style.whiteSpace = WhiteSpace.Normal;",
        "content.Add(version);",
        "root.Add(content);",
        "}",
        "}",
        "}",
    )


def check_editor_window_source_profile(
    source_path: str, source: str
) -> List[Finding]:
    check_id = "SOURCE"
    findings: List[Finding] = []
    actual_lines = tuple(line.strip() for line in source.splitlines() if line.strip())
    if actual_lines != expected_editor_window_lines():
        findings.append(
            finding(
                check_id,
                source_path,
                "Editor window source differs from the exact shell profile.",
                "Only the approved using directives, constants, lifecycle methods, and UI statements",
            )
        )
    required_usings = {
        "Teyocesu.AvatarDoctor.Editor.Core",
        "UnityEditor",
        "UnityEngine",
        "UnityEngine.UIElements",
    }
    actual_usings = re.findall(r"^\s*using\s+([^;]+?)\s*;", source, re.MULTILINE)
    if len(actual_usings) != len(required_usings) or set(actual_usings) != required_usings:
        findings.append(
            finding(
                check_id,
                source_path,
                "Editor window using directives are outside the active profile.",
                "Exactly the package Core, UnityEditor, UnityEngine, and UIElements namespaces",
            )
        )

    allowed_new_types = {"GUIContent", "Label", "Vector2", "VisualElement"}
    created_types = set(
        re.findall(r"\bnew\s+([A-Za-z_][A-Za-z0-9_.]*)\s*\(", source)
    )
    unexpected_new_types = sorted(created_types - allowed_new_types)
    if unexpected_new_types:
        findings.append(
            finding(
                check_id,
                source_path,
                "Constructed type is outside the active profile: {0}.".format(
                    unexpected_new_types[0]
                ),
                "GUIContent, Label, Vector2, or VisualElement",
            )
        )

    allowed_invocations = {
        "Add",
        "Clear",
        "CreateGUI",
        "GetWindow",
        "GUIContent",
        "Label",
        "MenuItem",
        "OnEnable",
        "OpenWindow",
        "Show",
        "Vector2",
        "VisualElement",
    }
    invocations = set(
        re.findall(
            r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:<[^>\n]+>)?\s*\(", source
        )
    )
    unexpected_invocations = sorted(invocations - allowed_invocations)
    if unexpected_invocations:
        findings.append(
            finding(
                check_id,
                source_path,
                "Method or constructor invocation is outside the active profile: {0}.".format(
                    unexpected_invocations[0]
                ),
                "Only the Editor window shell invocation set",
            )
        )

    allowed_style_properties = {
        "flexDirection",
        "flexGrow",
        "fontSize",
        "marginBottom",
        "paddingBottom",
        "paddingLeft",
        "paddingRight",
        "paddingTop",
        "unityFontStyleAndWeight",
        "whiteSpace",
    }
    style_properties = set(
        re.findall(r"\.style\.([A-Za-z_][A-Za-z0-9_]*)", source)
    )
    unexpected_style_properties = sorted(style_properties - allowed_style_properties)
    if unexpected_style_properties:
        findings.append(
            finding(
                check_id,
                source_path,
                "UI style property is outside the active profile: {0}.".format(
                    unexpected_style_properties[0]
                ),
                "Only layout, spacing, wrapping, and font emphasis",
            )
        )

    prohibited_controls = re.search(
        r"\b(?:Button|Toggle|TextField|ObjectField|ListView|ScrollView|"
        r"ProgressBar|Toolbar|Image)\b",
        source,
    )
    if prohibited_controls:
        findings.append(
            finding(
                check_id,
                source_path,
                "Functional or graphical control is outside the active profile: {0}.".format(
                    prohibited_controls.group(0)
                ),
                "VisualElement and Label only",
            )
        )
    if re.search(r"\bTODO\b", source):
        findings.append(
            finding(check_id, source_path, "Future-functionality TODO is outside the active profile.")
        )
    if re.search(
        r"\bstatic\s+(?!void\s+OpenWindow\b)[A-Za-z_][A-Za-z0-9_<>,.?\[\] ]*\s+"
        r"[A-Za-z_][A-Za-z0-9_]*\s*(?:=|;)",
        source,
    ):
        findings.append(
            finding(check_id, source_path, "Mutable static state is outside the active profile.")
        )
    return findings


def check_source(context: RepositoryContext) -> List[Finding]:
    check_id = "SOURCE"
    policy = context.policy
    package_prefix = policy["packageRoot"] + "/"
    allowed_namespaces = tuple(policy["allowedNamespaces"])
    source_profiles = policy["sourceProfiles"]
    expected_source_paths = set(source_profiles)
    source_paths = sorted(
        path
        for path in context.tracked_files
        if path.startswith(package_prefix) and path.endswith(".cs")
    )
    findings: List[Finding] = []
    for missing_path in sorted(expected_source_paths - set(source_paths)):
        findings.append(
            finding(check_id, missing_path, "Policy-defined C# source is not tracked.")
        )
    for unexpected_path in sorted(set(source_paths) - expected_source_paths):
        findings.append(
            finding(
                check_id,
                unexpected_path,
                "C# source has no file-specific policy profile.",
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

        profile_configuration = source_profiles.get(source_path)
        if profile_configuration is not None:
            profile_name = profile_configuration["profile"]
            if profile_name == "constantsOnly":
                findings.extend(
                    check_constants_only_source(context, source_path, source)
                )
            elif profile_name == "editorWindowShell":
                findings.extend(check_editor_window_source_profile(source_path, source))

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
                    "Public C# type declarations are outside the active profile.",
                    "Internal types only",
                )
            )
        if re.search(r"\bunsafe\b", source):
            findings.append(
                finding(check_id, source_path, "Unsafe C# code is outside the active profile.")
            )

        allowed_patterns = (
            set(profile_configuration["allowedProhibitedCodePatterns"])
            if profile_configuration is not None
            else set()
        )
        for name, pattern in compiled_patterns:
            if name in allowed_patterns:
                continue
            match = pattern.search(source)
            if match:
                line = source.count("\n", 0, match.start()) + 1
                findings.append(
                    finding(
                        check_id,
                        source_path,
                        "Prohibited {0} pattern found at line {1}.".format(name, line),
                        "Pattern absent for the file-specific source profile",
                    )
                )
    return findings


def extract_method_body(source: str, signature: str) -> Optional[str]:
    signature_index = source.find(signature)
    if signature_index < 0:
        return None
    opening_brace = source.find("{", signature_index + len(signature))
    if opening_brace < 0:
        return None
    depth = 0
    for index in range(opening_brace, len(source)):
        character = source[index]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return source[opening_brace + 1 : index]
    return None


def check_editor_window(context: RepositoryContext) -> List[Finding]:
    check_id = "EDITOR_WINDOW"
    package_root = context.policy["packageRoot"]
    source_path = package_root + "/Editor/UI/AvatarDoctorWindow.cs"
    folder_meta_path = package_root + "/Editor/UI.meta"
    script_meta_path = source_path + ".meta"
    findings: List[Finding] = []

    if not context.is_tracked(source_path):
        return [
            finding(
                check_id,
                source_path,
                "Policy-defined Editor window source is not tracked.",
            )
        ]
    try:
        source = context.read_text(source_path)
    except UnicodeDecodeError:
        return [
            finding(check_id, source_path, "Editor window source is not valid UTF-8.")
        ]

    actual_lines = tuple(line.strip() for line in source.splitlines() if line.strip())
    if actual_lines != expected_editor_window_lines():
        findings.append(
            finding(
                check_id,
                source_path,
                "Editor window source differs from the exact shell shape.",
                "Only the approved declarations and UI statements",
            )
        )

    expected_namespace = "Teyocesu.AvatarDoctor.Editor.UI"
    namespaces = re.findall(
        r"\bnamespace\s+([A-Za-z_][A-Za-z0-9_.]*)", source
    )
    if namespaces != [expected_namespace]:
        findings.append(
            finding(
                check_id,
                source_path,
                "Editor window namespace is not exact.",
                expected_namespace,
            )
        )
    class_declaration = "internal sealed class AvatarDoctorWindow : EditorWindow"
    if source.count(class_declaration) != 1:
        findings.append(
            finding(
                check_id,
                source_path,
                "Editor window class declaration is not exact.",
                class_declaration,
            )
        )
    type_declarations = re.findall(
        r"\b(?:class|struct|interface|enum|record)\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)\b",
        source,
    )
    if type_declarations != ["AvatarDoctorWindow"]:
        findings.append(
            finding(
                check_id,
                source_path,
                "Editor window source must contain exactly one type declaration.",
                "AvatarDoctorWindow only",
            )
        )

    package_sources = sorted(
        path
        for path in context.tracked_files
        if path.startswith(package_root + "/") and path.endswith(".cs")
    )
    editor_window_count = 0
    menu_item_count = 0
    for package_source_path in package_sources:
        try:
            package_source = context.read_text(package_source_path)
        except UnicodeDecodeError:
            continue
        editor_window_count += len(
            re.findall(
                r"\bclass\s+[A-Za-z_][A-Za-z0-9_]*\s*:\s*EditorWindow\b",
                package_source,
            )
        )
        menu_item_count += len(re.findall(r"\[\s*MenuItem\s*\(", package_source))
    if editor_window_count != 1:
        findings.append(
            finding(
                check_id,
                package_root,
                "Package contains {0} Editor window classes.".format(
                    editor_window_count
                ),
                "Exactly 1",
            )
        )
    if menu_item_count != 1:
        findings.append(
            finding(
                check_id,
                package_root,
                "Package contains {0} MenuItem attributes.".format(menu_item_count),
                "Exactly 1",
            )
        )

    required_constants = (
        'private const string MenuPath = "Tools/Avatar Doctor";',
        "private const int MenuPriority = 2000;",
        "private const float MinimumWidth = 420f;",
        "private const float MinimumHeight = 220f;",
        'private const string StatusText = "Pre-alpha - Window shell";',
        'private const string UnavailableAnalysisMessage = "Avatar analysis is not available in this version.";',
        'private const string VersionPrefix = "Version ";',
    )
    for required_constant in required_constants:
        if source.count(required_constant) != 1:
            findings.append(
                finding(
                    check_id,
                    source_path,
                    "Required private constant is missing or duplicated.",
                    required_constant,
                )
            )
    field_declarations = re.findall(
        r"^\s*(?:private|protected|internal|public)\s+"
        r"(?:(?:static|readonly|const)\s+)*"
        r"[A-Za-z_][A-Za-z0-9_<>,.?\[\] ]*\s+"
        r"[A-Za-z_][A-Za-z0-9_]*\s*(?:=[^;\n]*)?;\s*$",
        source,
        re.MULTILINE,
    )
    if len(field_declarations) != len(required_constants):
        findings.append(
            finding(
                check_id,
                source_path,
                "Editor window fields differ from the seven policy-defined constants.",
                "Exactly 7 private constants and no mutable fields",
            )
        )

    menu_attribute = "[MenuItem(MenuPath, false, MenuPriority)]"
    if source.count(menu_attribute) != 1:
        findings.append(
            finding(
                check_id,
                source_path,
                "MenuItem declaration is not exact.",
                menu_attribute,
            )
        )
    signatures = {
        "OpenWindow": "private static void OpenWindow()",
        "OnEnable": "private void OnEnable()",
        "CreateGUI": "public void CreateGUI()",
    }
    method_declarations = re.findall(
        r"^\s*(?:private|protected|internal|public)\s+(?:static\s+)?"
        r"[A-Za-z_][A-Za-z0-9_<>,.?\[\] ]*\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*\)\s*$",
        source,
        re.MULTILINE,
    )
    if sorted(method_declarations) != sorted(signatures):
        findings.append(
            finding(
                check_id,
                source_path,
                "Editor window methods differ from the policy-defined lifecycle.",
                "OpenWindow, OnEnable, and CreateGUI only",
            )
        )
    method_bodies: Dict[str, Optional[str]] = {}
    for method_name, signature in signatures.items():
        if source.count(signature) != 1:
            findings.append(
                finding(
                    check_id,
                    source_path,
                    "Required method signature is missing or duplicated.",
                    signature,
                )
            )
        method_bodies[method_name] = extract_method_body(source, signature)
        if method_bodies[method_name] is None:
            findings.append(
                finding(
                    check_id,
                    source_path,
                    "Required method body could not be read: {0}.".format(method_name),
                )
            )

    open_window = method_bodies["OpenWindow"] or ""
    required_open_window_fragments = (
        "AvatarDoctorWindow window = GetWindow<AvatarDoctorWindow>();",
        "window.titleContent = new GUIContent(AvatarDoctorPackageInfo.DisplayName);",
        "window.minSize = new Vector2(MinimumWidth, MinimumHeight);",
        "window.Show();",
    )
    for fragment in required_open_window_fragments:
        if open_window.count(fragment) != 1:
            findings.append(
                finding(
                    check_id,
                    source_path,
                    "OpenWindow does not implement the exact reusable window setup.",
                    fragment,
                )
            )
    if "new AvatarDoctorWindow" in source:
        findings.append(
            finding(
                check_id,
                source_path,
                "Editor window must be reused through GetWindow.",
            )
        )

    on_enable = method_bodies["OnEnable"] or ""
    required_on_enable_fragments = (
        "titleContent = new GUIContent(AvatarDoctorPackageInfo.DisplayName);",
        "minSize = new Vector2(MinimumWidth, MinimumHeight);",
    )
    for fragment in required_on_enable_fragments:
        if on_enable.count(fragment) != 1:
            findings.append(
                finding(
                    check_id,
                    source_path,
                    "OnEnable does not restore the exact window identity and size.",
                    fragment,
                )
            )
    if re.search(r"(?:new\s+(?:Label|VisualElement)|\.Add\s*\(|\.Clear\s*\()", on_enable):
        findings.append(
            finding(
                check_id,
                source_path,
                "OnEnable must not construct or duplicate the visual tree.",
            )
        )

    create_gui = method_bodies["CreateGUI"] or ""
    required_create_gui_fragments = (
        "VisualElement root = rootVisualElement;",
        "rootVisualElement.Clear();",
        "VisualElement content = new VisualElement();",
        "root.Add(content);",
    )
    for fragment in required_create_gui_fragments:
        if create_gui.count(fragment) != 1:
            findings.append(
                finding(
                    check_id,
                    source_path,
                    "CreateGUI is missing required deterministic tree construction.",
                    fragment,
                )
            )
    clear_index = create_gui.find("rootVisualElement.Clear();")
    first_add_index = create_gui.find(".Add(")
    if clear_index < 0 or first_add_index < 0 or clear_index > first_add_index:
        findings.append(
            finding(
                check_id,
                source_path,
                "CreateGUI must clear the root before adding elements.",
                "rootVisualElement.Clear() before the first Add()",
            )
        )

    label_expressions = (
        "new Label(AvatarDoctorPackageInfo.DisplayName)",
        "new Label(StatusText)",
        "new Label(UnavailableAnalysisMessage)",
        "new Label(VersionPrefix + AvatarDoctorPackageInfo.Version)",
    )
    label_positions = [create_gui.find(expression) for expression in label_expressions]
    if (
        any(position < 0 for position in label_positions)
        or label_positions != sorted(label_positions)
        or len(re.findall(r"\bnew\s+Label\s*\(", create_gui)) != 4
    ):
        findings.append(
            finding(
                check_id,
                source_path,
                "Visible labels are missing, duplicated, or out of order.",
                "Display name, status, unavailable-analysis message, then package version",
            )
        )
    add_expressions = (
        "content.Add(heading);",
        "content.Add(status);",
        "content.Add(unavailableAnalysis);",
        "content.Add(version);",
        "root.Add(content);",
    )
    add_positions = [create_gui.find(expression) for expression in add_expressions]
    if (
        any(position < 0 for position in add_positions)
        or add_positions != sorted(add_positions)
        or len(re.findall(r"\.Add\s*\(", create_gui)) != 5
    ):
        findings.append(
            finding(
                check_id,
                source_path,
                "Visual elements are not added exactly once in the policy-defined order.",
                "Heading, status, message, version, then the content container",
            )
        )
    if '"0.0.4"' in source:
        findings.append(
            finding(
                check_id,
                source_path,
                "Visible package version is hardcoded in the Editor window.",
                "AvatarDoctorPackageInfo.Version",
            )
        )

    prohibited_tokens = re.search(
        r"\b(?:AssetDatabase|Selection|SerializedObject|SerializedProperty|"
        r"EditorPrefs|SessionState|EditorApplication|Undo|PrefabUtility|"
        r"BuildPipeline|SceneManager|EditorSceneManager|GameObject|Component|"
        r"Transform|Resources|Task|Thread|Socket|VRCAvatarDescriptor|PhysBone|"
        r"Contacts?|Update|OnInspectorUpdate|OnHierarchyChange|OnSelectionChange|"
        r"OnProjectChange|Button|Toggle|TextField|ObjectField|ListView|ScrollView|"
        r"ProgressBar|Toolbar|Image)\b",
        source,
    )
    if prohibited_tokens:
        findings.append(
            finding(
                check_id,
                source_path,
                "Editor window token is outside the active profile: {0}.".format(
                    prohibited_tokens.group(0)
                ),
                "Token absent",
            )
        )
    if re.search(
        r"(?:\bSystem\.(?:IO|Net|Reflection|Threading)\b|\bVRC\.SDK\b|"
        r"\basync\b|\+=|-=|\bRegisterCallback\s*\(|\.clicked\b|\bevent\b)",
        source,
    ):
        findings.append(
            finding(
                check_id,
                source_path,
                "File, network, reflection, asynchronous, SDK, or event behavior is outside the active profile.",
            )
        )

    for meta_path, expected_marker in (
        (folder_meta_path, "folderAsset: yes"),
        (script_meta_path, "MonoImporter:"),
    ):
        if not context.is_tracked(meta_path):
            findings.append(
                finding(
                    check_id,
                    meta_path,
                    "Required Editor window metadata is not tracked.",
                )
            )
            continue
        try:
            metadata = context.read_text(meta_path)
        except UnicodeDecodeError:
            findings.append(
                finding(check_id, meta_path, "Editor window metadata is not UTF-8.")
            )
            continue
        if expected_marker not in metadata:
            findings.append(
                finding(
                    check_id,
                    meta_path,
                    "Editor window metadata uses the wrong importer shape.",
                    expected_marker,
                )
            )
        if metadata_value(metadata, "fileFormatVersion") != "2":
            findings.append(
                finding(
                    check_id,
                    meta_path,
                    "Editor window metadata has an invalid file format version.",
                    "2",
                )
            )
        guid = metadata_value(metadata, "guid")
        if guid is None or not GUID_PATTERN.fullmatch(guid):
            findings.append(
                finding(
                    check_id,
                    meta_path,
                    "Editor window metadata has an invalid GUID.",
                    "32 hexadecimal characters",
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


def workflow_step_blocks(text: str) -> List[str]:
    lines = text.splitlines()
    starts = [
        index
        for index, line in enumerate(lines)
        if re.match(r"^\s{6}-\s+", line)
    ]
    blocks: List[str] = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        blocks.append("\n".join(lines[start:end]))
    return blocks


def workflow_uses(text: str) -> List[str]:
    return re.findall(r"^\s*uses:\s*(\S+)\s*$", text, re.MULTILINE)


def step_for_action(text: str, action: str) -> List[str]:
    pattern = re.compile(r"^\s*uses:\s*{0}\s*$".format(re.escape(action)), re.MULTILINE)
    return [block for block in workflow_step_blocks(text) if pattern.search(block)]


def step_with_keys(block: str) -> List[str]:
    return re.findall(r"^\s{10}([A-Za-z0-9_-]+):", block, re.MULTILINE)


def multiline_step_values(block: str, key: str) -> List[str]:
    lines = block.splitlines()
    marker = re.compile(r"^(\s+){0}:\s*\|\s*$".format(re.escape(key)))
    for index, line in enumerate(lines):
        match = marker.match(line)
        if not match:
            continue
        indentation = len(line) - len(line.lstrip())
        values: List[str] = []
        for value_line in lines[index + 1 :]:
            if not value_line.strip():
                continue
            value_indentation = len(value_line) - len(value_line.lstrip())
            if value_indentation <= indentation:
                break
            values.append(value_line.strip())
        return values
    return []


def append_missing_patterns(
    findings: List[Finding],
    path: str,
    text: str,
    requirements: Sequence[Tuple[str, str]],
) -> None:
    for pattern, description in requirements:
        if not re.search(pattern, text, re.MULTILINE):
            findings.append(
                finding(
                    "WORKFLOWS",
                    path,
                    "Required workflow invariant is missing.",
                    description,
                )
            )


def append_forbidden_patterns(
    findings: List[Finding],
    path: str,
    text: str,
    patterns: Sequence[Tuple[str, str]],
) -> None:
    for pattern, description in patterns:
        if re.search(pattern, text, re.MULTILINE | re.IGNORECASE):
            findings.append(
                finding(
                    "WORKFLOWS",
                    path,
                    "Forbidden workflow capability found: {0}.".format(description),
                    "Capability absent",
                )
            )


def check_workflow_common(
    path: str,
    text: str,
    configuration: Dict[str, Any],
    *,
    manual_only: bool,
) -> List[Finding]:
    findings: List[Finding] = []
    if not re.search(
        r"^name:\s*{0}\s*$".format(re.escape(configuration["name"])),
        text,
        re.MULTILINE,
    ):
        findings.append(
            finding("WORKFLOWS", path, "Workflow name does not match policy.", configuration["name"])
        )
    if top_level_block(text, "permissions") != ["permissions:", "  contents: read"]:
        findings.append(
            finding(
                "WORKFLOWS",
                path,
                "Workflow permissions are not exact read-only contents access.",
                "permissions: contents: read",
            )
        )
    jobs_block = "\n".join(top_level_block(text, "jobs"))
    job_identifiers = re.findall(r"^\s{2}([A-Za-z0-9_-]+):\s*$", jobs_block, re.MULTILINE)
    if job_identifiers != [configuration["job"]]:
        findings.append(
            finding(
                "WORKFLOWS",
                path,
                "Workflow jobs are not the approved exact set.",
                configuration["job"],
            )
        )
    append_missing_patterns(
        findings,
        path,
        text,
        (
            (
                r"^\s{{4}}name:\s*{0}\s*$".format(re.escape(configuration["job"])),
                "job name {0}".format(configuration["job"]),
            ),
            (
                r"^\s{{4}}runs-on:\s*{0}\s*$".format(re.escape(configuration["runner"])),
                "runner {0}".format(configuration["runner"]),
            ),
            (
                r"^\s{{4}}timeout-minutes:\s*{0}\s*$".format(configuration["timeoutMinutes"]),
                "timeout-minutes: {0}".format(configuration["timeoutMinutes"]),
            ),
            (r"^\s{8}run:\s*python3 --version\s*$", "Python version step"),
        ),
    )
    if manual_only:
        trigger_block = "\n".join(top_level_block(text, "on"))
        triggers = re.findall(r"^\s{2}([A-Za-z0-9_-]+):\s*$", trigger_block, re.MULTILINE)
        input_names = re.findall(r"^\s{6}([A-Za-z0-9_-]+):\s*$", trigger_block, re.MULTILINE)
        if triggers != ["workflow_dispatch"] or input_names != ["expected_version"]:
            findings.append(
                finding(
                    "WORKFLOWS",
                    path,
                    "Distribution workflow is not manual-only with one version input.",
                    "workflow_dispatch with expected_version only",
                )
            )
        append_missing_patterns(
            findings,
            path,
            trigger_block,
            (
                (r"^\s{8}required:\s*true\s*$", "required expected_version input"),
                (
                    r"^\s{{8}}default:\s*[\"']?{0}[\"']?\s*$".format(
                        re.escape(configuration["expectedVersion"])
                    ),
                    "expected_version default {0}".format(configuration["expectedVersion"]),
                ),
                (r"^\s{8}type:\s*string\s*$", "string expected_version input"),
            ),
        )
        if not re.search(
            r"^\s{4}if:\s*github\.ref\s*==\s*'refs/heads/main'\s*$",
            text,
            re.MULTILINE,
        ):
            findings.append(
                finding(
                    "WORKFLOWS",
                    path,
                    "Distribution workflow is not restricted exactly to main.",
                    "github.ref == 'refs/heads/main'",
                )
            )

    checkout_blocks = step_for_action(text, configuration["checkout"])
    if not checkout_blocks:
        findings.append(
            finding("WORKFLOWS", path, "Pinned repository checkout is missing.", configuration["checkout"])
        )
    else:
        first_checkout = checkout_blocks[0]
        if step_with_keys(first_checkout) != ["fetch-depth", "persist-credentials"]:
            findings.append(
                finding(
                    "WORKFLOWS",
                    path,
                    "Primary checkout settings are not exact.",
                    "fetch-depth: 0 and persist-credentials: false",
                )
            )
        append_missing_patterns(
            findings,
            path,
            first_checkout,
            (
                (r"^\s{10}fetch-depth:\s*0\s*$", "fetch-depth: 0"),
                (r"^\s{10}persist-credentials:\s*false\s*$", "persist-credentials: false"),
            ),
        )

    append_forbidden_patterns(
        findings,
        path,
        text,
        (
            (r"\bpull_request_target\b", "pull_request_target"),
            (r"\bworkflow_call\s*:", "reusable workflow trigger"),
            (r"\bvars\s*\.", "repository variable gate"),
            (r"\bcontinue-on-error\s*:\s*true\b", "ignored failure"),
            (r"^[ \t]+permissions\s*:", "job-level permissions"),
            (r"^[ \t]+[^#\n]+:\s*write\s*$", "write permission"),
            (r"^permissions\s*:\s*write-all\s*$", "write-all permissions"),
            (r"\bgit[^\n#]*\s(?:tag|push)(?:\s|$)", "Git tag or push command"),
            (r"\bgh\s+(?:release\b|api[^\n]*/releases\b)", "GitHub Release command"),
            (r"api\.github\.com/[^\s]+/releases\b", "GitHub Releases API write"),
            (r"\bpages\s*:\s*", "Pages permission"),
            (r"\bid-token\s*:\s*", "identity token permission"),
            (r"^\s+environment\s*:", "deployment environment"),
            (r"actions/(?:configure|upload|deploy)-pages", "Pages action"),
        ),
    )
    return findings


def check_release_workflow(
    context: RepositoryContext, configuration: Dict[str, Any]
) -> List[Finding]:
    path = configuration["path"]
    text, findings = workflow_text(context, "WORKFLOWS", path)
    if text is None:
        return findings
    findings.extend(check_workflow_common(path, text, configuration, manual_only=True))
    expected_uses = [configuration["checkout"], configuration["uploadArtifact"]]
    if workflow_uses(text) != expected_uses:
        findings.append(
            finding(
                "WORKFLOWS",
                path,
                "Release workflow actions are not the approved exact set.",
                ", ".join(expected_uses),
            )
        )
    append_missing_patterns(
        findings,
        path,
        text,
        (
            (re.escape("python3 ci/validate_repository.py --root ."), "repository validator"),
            (re.escape('python3 -B -m unittest discover -s ci/tests -p "test_*.py"'), "release pipeline tests"),
            (r"\$RUNNER_TEMP/avatar-doctor-release", "temporary artifact root"),
            (r"\$GITHUB_STEP_SUMMARY", "release verification summary"),
            (r"cat \"\$build_a/SHA256SUMS\.txt\"", "verified SHA-256 summary"),
        ),
    )
    command_counts = (
        (r"^\s*python3 ci/release_pipeline\.py build\b", 2, "two artifact builds"),
        (r"^\s*python3 ci/release_pipeline\.py verify\b", 2, "two artifact verifications"),
        (r"^\s*cmp\s+", 3, "three byte comparisons"),
    )
    for pattern, expected_count, description in command_counts:
        if len(re.findall(pattern, text, re.MULTILINE)) != expected_count:
            findings.append(
                finding("WORKFLOWS", path, "Release workflow command count is invalid.", description)
            )

    upload_blocks = step_for_action(text, configuration["uploadArtifact"])
    if len(upload_blocks) != 1:
        findings.append(
            finding("WORKFLOWS", path, "Release workflow must contain one artifact upload.")
        )
    else:
        upload = upload_blocks[0]
        expected_keys = ["name", "path", "if-no-files-found", "retention-days"]
        expected_paths = [
            "${{ runner.temp }}/avatar-doctor-release/build-a/" + name
            for name in configuration["artifactFiles"]
        ]
        if step_with_keys(upload) != expected_keys or multiline_step_values(upload, "path") != expected_paths:
            findings.append(
                finding(
                    "WORKFLOWS",
                    path,
                    "Release artifact upload does not contain the exact approved files.",
                    ", ".join(configuration["artifactFiles"]),
                )
            )
        append_missing_patterns(
            findings,
            path,
            upload,
            (
                (r"^\s{{10}}name:\s*{0}\s*$".format(re.escape(configuration["artifactName"])), "release artifact name"),
                (r"^\s{10}if-no-files-found:\s*error\s*$", "artifact absence failure"),
                (r"^\s{{10}}retention-days:\s*{0}\s*$".format(configuration["retentionDays"]), "artifact retention"),
            ),
        )
    append_forbidden_patterns(
        findings,
        path,
        text,
        (
            (r"\bsecrets\s*\.", "secret reference"),
            (r"action-create-tag|action-gh-release|create-release|release-action", "tag or Release action"),
        ),
    )
    return findings


def check_listing_workflow(
    context: RepositoryContext, configuration: Dict[str, Any]
) -> List[Finding]:
    path = configuration["path"]
    text, findings = workflow_text(context, "WORKFLOWS", path)
    if text is None:
        return findings
    findings.extend(check_workflow_common(path, text, configuration, manual_only=True))
    expected_uses = [
        configuration["checkout"],
        configuration["checkout"],
        configuration["uploadArtifact"],
    ]
    if workflow_uses(text) != expected_uses:
        findings.append(
            finding(
                "WORKFLOWS",
                path,
                "Listing workflow actions are not the approved exact set.",
                ", ".join(expected_uses),
            )
        )
    checkout_blocks = step_for_action(text, configuration["checkout"])
    if len(checkout_blocks) != 2:
        findings.append(
            finding("WORKFLOWS", path, "Listing workflow must contain two pinned checkouts.")
        )
    else:
        dependency_checkout = checkout_blocks[1]
        if step_with_keys(dependency_checkout) != [
            "repository",
            "ref",
            "path",
            "persist-credentials",
        ]:
            findings.append(
                finding(
                    "WORKFLOWS",
                    path,
                    "Listing dependency checkout settings are not exact.",
                    "repository, ref, path, and disabled credentials",
                )
            )
        append_missing_patterns(
            findings,
            path,
            dependency_checkout,
            (
                (r"^\s{{10}}repository:\s*{0}\s*$".format(re.escape(configuration["packageListRepository"])), "package-list repository"),
                (r"^\s{{10}}ref:\s*{0}\s*$".format(configuration["packageListRef"]), "pinned package-list commit"),
                (r"^\s{10}path:\s*\.package-list-action\s*$", "isolated package-list checkout"),
                (r"^\s{10}persist-credentials:\s*false\s*$", "disabled dependency checkout credentials"),
            ),
        )
    append_missing_patterns(
        findings,
        path,
        text,
        (
            (re.escape("python3 ci/validate_repository.py --root ."), "repository validator"),
            (re.escape('python3 -B -m unittest discover -s ci/tests -p "test_*.py"'), "release pipeline tests"),
            (r"bash \.package-list-action/build\.sh BuildRepoListing", "pinned listing builder"),
            (r"--current-package-name com\.teyocesu\.avatar-doctor", "exact package identity"),
            (r"python3 ci/release_pipeline\.py normalize-listing", "local listing normalization"),
            (r"python3 ci/release_pipeline\.py verify-listing", "local listing verification"),
            (r"^\s*--root \. \\$", "repository source for ZIP verification"),
            (r"--source-ref \"refs/tags/v\$EXPECTED_VERSION\"", "version tag source for ZIP verification"),
            (r"^\s*--remote\s*$", "remote release ZIP verification"),
            (r"\$RUNNER_TEMP/avatar-doctor-listing", "temporary listing root"),
            (r"trap 'rm -rf -- \.package-list-action' EXIT", "temporary dependency cleanup"),
        ),
    )
    if len(re.findall(r"\bsecrets\.GITHUB_TOKEN\b", text)) != 1 or re.search(
        r"\bsecrets\.(?!GITHUB_TOKEN\b)", text
    ):
        findings.append(
            finding(
                "WORKFLOWS",
                path,
                "Listing workflow secret references are not limited to the built-in token.",
                "secrets.GITHUB_TOKEN once",
            )
        )
    upload_blocks = step_for_action(text, configuration["uploadArtifact"])
    if len(upload_blocks) != 1:
        findings.append(
            finding("WORKFLOWS", path, "Listing workflow must contain one artifact upload.")
        )
    else:
        upload = upload_blocks[0]
        expected_path = (
            "${{ runner.temp }}/avatar-doctor-listing/local/"
            + configuration["artifactFile"]
        )
        if step_with_keys(upload) != ["name", "path", "if-no-files-found", "retention-days"]:
            findings.append(
                finding("WORKFLOWS", path, "Listing artifact upload settings are not exact.")
            )
        append_missing_patterns(
            findings,
            path,
            upload,
            (
                (r"^\s{{10}}name:\s*{0}\s*$".format(re.escape(configuration["artifactName"])), "listing artifact name"),
                (r"^\s{{10}}path:\s*{0}\s*$".format(re.escape(expected_path)), "local index.json only"),
                (r"^\s{10}if-no-files-found:\s*error\s*$", "artifact absence failure"),
                (r"^\s{{10}}retention-days:\s*{0}\s*$".format(configuration["retentionDays"]), "artifact retention"),
            ),
        )
    append_forbidden_patterns(
        findings,
        path,
        text,
        (
            (r"(?:^|[/\s])Website(?:/|\s|$)", "tracked Website output"),
            (r"upload-pages-artifact|deploy-pages|configure-pages", "Pages deployment action"),
        ),
    )
    return findings


def check_validation_workflow(
    context: RepositoryContext, configuration: Dict[str, Any]
) -> List[Finding]:
    path = configuration["path"]
    text, findings = workflow_text(context, "WORKFLOWS", path)
    if text is None:
        return findings
    findings.extend(check_workflow_common(path, text, configuration, manual_only=False))
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
                "WORKFLOWS",
                path,
                "Validation triggers are not the approved exact set.",
                "Pull Requests, pushes to main, and manual dispatch",
            )
        )
    if workflow_uses(text) != [configuration["checkout"]]:
        findings.append(
            finding(
                "WORKFLOWS",
                path,
                "Validation workflow uses unexpected actions.",
                configuration["checkout"],
            )
        )
    append_missing_patterns(
        findings,
        path,
        text,
        (
            (re.escape(configuration["validatorCommand"]), "repository validator"),
            (re.escape(configuration["testCommand"]), "release pipeline tests"),
            (r"\$RUNNER_TEMP/avatar-doctor-validation", "temporary validation artifact root"),
            (r"Release artifact reproducibility passed\.", "reproducibility result"),
            (r"^\s{2}cancel-in-progress:\s*true\s*$", "concurrency cancellation"),
            (r"^\s{2}group:\s*repository-validation-", "stable validation concurrency group"),
        ),
    )
    command_counts = (
        (r"^\s*python3 ci/release_pipeline\.py build\b", 2, "two artifact builds"),
        (r"^\s*python3 ci/release_pipeline\.py verify\b", 2, "two artifact verifications"),
        (r"^\s*cmp\s+", 3, "three byte comparisons"),
    )
    for pattern, expected_count, description in command_counts:
        if len(re.findall(pattern, text, re.MULTILINE)) != expected_count:
            findings.append(
                finding("WORKFLOWS", path, "Validation workflow command count is invalid.", description)
            )
    append_forbidden_patterns(
        findings,
        path,
        text,
        (
            (r"\bsecrets\s*\.", "secret reference"),
            (r"actions/upload-artifact", "artifact upload"),
            (r"\benvironment\s*:", "execution environment override"),
        ),
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
    findings.extend(check_release_workflow(context, protected["release"]))
    findings.extend(check_listing_workflow(context, protected["listing"]))
    findings.extend(check_validation_workflow(context, protected["validation"]))
    return findings


def validate_roadmap_structure(
    context: RepositoryContext, check_id: str
) -> List[Finding]:
    path = "docs/ROADMAP.md"
    if not context.is_tracked(path):
        return [finding(check_id, path, "Roadmap is not tracked.")]
    try:
        roadmap = context.read_text(path)
    except UnicodeDecodeError:
        return [finding(check_id, path, "Roadmap is not valid UTF-8.")]
    guard = context.policy["roadmapGuard"]
    findings: List[Finding] = []

    actual_stages = re.findall(r"^###\s+(Stage [A-Z] — .+?)\s*$", roadmap, re.MULTILINE)
    expected_stages = list(guard["requiredStages"])
    if actual_stages != expected_stages:
        findings.append(
            finding(
                check_id,
                path,
                "Roadmap stages do not match the required sequence.",
                "Exactly {0} ordered stages".format(len(expected_stages)),
            )
        )

    release_matches = re.findall(
        r"^#{2,6}\s+(v[0-9]+\.[0-9]+\.[0-9]+(?:-rc\.[0-9]+)?)\s+—\s+(.+?)\s*$",
        roadmap,
        re.MULTILINE,
    )
    actual_headings = [
        "{0} — {1}".format(version, title)
        for version, title in release_matches
    ]
    expected_headings = list(guard["orderedReleaseHeadings"])
    version_counts: Dict[str, int] = {}
    for version, _ in release_matches:
        version_counts[version] = version_counts.get(version, 0) + 1
    for version in sorted(version_counts):
        if version_counts[version] > 1:
            findings.append(
                finding(
                    check_id,
                    path,
                    "Roadmap release version is duplicated: {0}.".format(version),
                    "One release heading per version",
                )
            )

    missing_headings = sorted(set(expected_headings) - set(actual_headings))
    unexpected_headings = sorted(set(actual_headings) - set(expected_headings))
    for heading in missing_headings:
        findings.append(
            finding(
                check_id,
                path,
                "Required roadmap release heading is missing.",
                heading,
            )
        )
    for heading in unexpected_headings:
        findings.append(
            finding(
                check_id,
                path,
                "Unexpected roadmap release heading: {0}.".format(heading),
                "A heading from the active release sequence",
            )
        )
    if (
        not missing_headings
        and not unexpected_headings
        and actual_headings != expected_headings
    ):
        findings.append(
            finding(
                check_id,
                path,
                "Roadmap release headings are out of order.",
                "The policy-defined release sequence",
            )
        )

    for heading in guard["forbiddenHeadings"]:
        if heading in roadmap:
            findings.append(
                finding(
                    check_id,
                    path,
                    "Obsolete roadmap release heading is present: {0}.".format(
                        heading
                    ),
                    "Heading absent",
                )
            )

    stable_match = re.search(
        r"^#### v1\.0\.0 — Stable Release\s*$", roadmap, re.MULTILINE
    )
    if not stable_match:
        findings.append(
            finding(
                check_id,
                path,
                "Stable release definition is missing.",
                "#### v1.0.0 — Stable Release",
            )
        )
    else:
        next_heading = re.search(
            r"^####\s+", roadmap[stable_match.end() :], re.MULTILINE
        )
        section_end = (
            stable_match.end() + next_heading.start()
            if next_heading
            else len(roadmap)
        )
        stable_section = roadmap[stable_match.end() : section_end]
        stable_capabilities = re.findall(
            r"^- (.+?)\s*$", stable_section, re.MULTILINE
        )
        if stable_capabilities != guard["requiredStableCapabilities"]:
            findings.append(
                finding(
                    check_id,
                    path,
                    "Stable release capabilities do not match the public scope.",
                    "Exactly {0} ordered capabilities".format(
                        len(guard["requiredStableCapabilities"])
                    ),
                )
            )
    return findings


def check_roadmap_guard(context: RepositoryContext) -> List[Finding]:
    return validate_roadmap_structure(context, "ROADMAP_GUARD")


def maintained_public_paths(context: RepositoryContext) -> List[str]:
    configuration = context.policy["publicContent"]
    paths = set(configuration["requiredPaths"])
    for relative_path in context.tracked_files:
        if any(
            fnmatch.fnmatch(relative_path, pattern)
            for pattern in configuration["includeGlobs"]
        ):
            paths.add(relative_path)
    return sorted(paths)


def check_public_content(context: RepositoryContext) -> List[Finding]:
    check_id = "PUBLIC_CONTENT"
    configuration = context.policy["publicContent"]
    required_sections = configuration["requiredSections"]
    findings: List[Finding] = []

    for relative_path in maintained_public_paths(context):
        if not context.is_tracked(relative_path):
            findings.append(
                finding(
                    check_id,
                    relative_path,
                    "Required public-content file is not tracked.",
                    "Tracked UTF-8 text",
                )
            )
            continue
        try:
            text = context.read_text(relative_path)
        except UnicodeDecodeError:
            findings.append(
                finding(
                    check_id,
                    relative_path,
                    "Maintained public content is not valid UTF-8.",
                    "UTF-8",
                )
            )
            continue

        for section in required_sections.get(relative_path, []):
            if section not in text:
                findings.append(
                    finding(
                        check_id,
                        relative_path,
                        "Required public section is missing.",
                        section,
                    )
                )

    findings.extend(validate_roadmap_structure(context, check_id))
    return findings


CHECKS: Dict[str, Callable[[RepositoryContext], List[Finding]]] = {
    "MANIFEST": check_manifest,
    "VERSION": check_version,
    "IDENTITY": check_identity,
    "STRUCTURE": check_structure,
    "ASSEMBLY": check_assembly,
    "SOURCE": check_source,
    "EDITOR_WINDOW": check_editor_window,
    "UNITY_METADATA": check_unity_metadata,
    "TEXT_HYGIENE": check_text_hygiene,
    "LANGUAGE": check_language,
    "PRIVACY": check_privacy,
    "SECRETS": check_secrets,
    "PROHIBITED_FILES": check_prohibited_files,
    "WORKFLOWS": check_workflows,
    "ROADMAP_GUARD": check_roadmap_guard,
    "PUBLIC_CONTENT": check_public_content,
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
