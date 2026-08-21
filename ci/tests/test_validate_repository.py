#!/usr/bin/env python3
"""Focused standard-library tests for the repository planning contract."""

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


if __name__ == "__main__":
    unittest.main()
