"""Shared helpers for persisted integration report artifacts."""

from __future__ import annotations

import hashlib
import json

from assembly.contracts.models import IntegrationRunRecord
from assembly.registry.schema import CompatibilityMatrixEntry


def compatibility_context_artifact(
    matrix_entry: CompatibilityMatrixEntry,
) -> dict[str, str]:
    """Return the compatibility-context artifact for a matrix entry."""

    module_set = sorted(
        (
            {
                "module_id": module.module_id,
                "module_version": module.module_version,
            }
            for module in matrix_entry.module_set
        ),
        key=lambda item: (item["module_id"], item["module_version"]),
    )
    matrix_context = {
        "profile_id": matrix_entry.profile_id,
        "matrix_version": matrix_entry.matrix_version,
        "contract_version": matrix_entry.contract_version,
        "module_set": module_set,
    }
    return {
        "kind": "compatibility_context",
        "profile_id": matrix_entry.profile_id,
        "matrix_version": matrix_entry.matrix_version,
        "contract_version": matrix_entry.contract_version,
        "module_set_digest": _stable_digest(module_set),
        "matrix_digest": _stable_digest(matrix_context),
    }


def record_matches_matrix_context(
    record: IntegrationRunRecord,
    matrix_entry: CompatibilityMatrixEntry,
) -> bool:
    """Return whether a run record carries the selected matrix context."""

    expected = compatibility_context_artifact(matrix_entry)
    for artifact in record.artifacts:
        if artifact.get("kind") != expected["kind"]:
            continue

        return all(artifact.get(key) == value for key, value in expected.items())

    return False


def _stable_digest(payload: object) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
