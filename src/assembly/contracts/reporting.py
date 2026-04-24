"""Shared helpers for persisted integration report artifacts."""

from __future__ import annotations

import hashlib
import json

from assembly.contracts.models import IntegrationRunRecord
from assembly.registry.schema import CompatibilityMatrixEntry


def compatibility_context_artifact(
    matrix_entry: CompatibilityMatrixEntry,
) -> dict[str, str]:
    """Return the compatibility-context artifact for a matrix entry.

    Codex P2 follow-up on the MinIO pilot: ``extra_bundles`` is now part
    of the digest input and of the emitted artifact. Before this
    change, ``(full-dev, extra_bundles=[])`` and
    ``(full-dev, extra_bundles=[minio])`` produced identical
    ``matrix_digest`` values, so run records bound to different matrix
    rows looked indistinguishable. The schema validator guarantees
    ``extra_bundles`` is sorted + deduplicated on load, so the digest
    is author-order-independent.
    """

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
    extra_bundles = list(matrix_entry.extra_bundles)
    matrix_context = {
        "profile_id": matrix_entry.profile_id,
        "matrix_version": matrix_entry.matrix_version,
        "contract_version": matrix_entry.contract_version,
        "extra_bundles": extra_bundles,
        "module_set": module_set,
    }
    return {
        "kind": "compatibility_context",
        "profile_id": matrix_entry.profile_id,
        "matrix_version": matrix_entry.matrix_version,
        "contract_version": matrix_entry.contract_version,
        "extra_bundles": ",".join(extra_bundles),
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
