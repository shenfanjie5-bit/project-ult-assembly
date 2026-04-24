"""Tests for ``assembly.contracts.reporting``.

Codex P2 follow-up on the MinIO pilot: before this round,
``compatibility_context_artifact`` digested only
``(profile_id, matrix_version, contract_version, module_set)``, so two
matrix rows with the same profile but different ``extra_bundles``
(default ``full-dev`` vs ``full-dev + extra_bundles=[minio]``) produced
identical ``matrix_digest`` values. The pilot's run record could not be
disambiguated from the default row's run record by digest alone. These
tests pin the fix: ``extra_bundles`` now participates in the digest.
"""

from __future__ import annotations

from datetime import datetime, timezone

from assembly.contracts.reporting import (
    compatibility_context_artifact,
    record_matches_matrix_context,
)
from assembly.contracts.models import IntegrationRunRecord
from assembly.registry import CompatibilityMatrixEntry


def _verified_matrix_entry(
    *,
    profile_id: str = "full-dev",
    extra_bundles: list[str] | None = None,
) -> CompatibilityMatrixEntry:
    return CompatibilityMatrixEntry.model_validate(
        {
            "matrix_version": "0.1.0",
            "profile_id": profile_id,
            "extra_bundles": extra_bundles or [],
            "module_set": [
                {"module_id": "contracts", "module_version": "0.1.0"},
                {"module_id": "assembly", "module_version": "0.1.0"},
            ],
            "contract_version": "v0.1.0",
            "required_tests": ["contract-suite", "smoke", "min-cycle-e2e"],
            "status": "verified",
            "verified_at": datetime(2026, 4, 24, tzinfo=timezone.utc),
        }
    )


def test_compatibility_context_artifact_emits_extra_bundles_field() -> None:
    """Artifact carries an ``extra_bundles`` field so run records are
    disambiguated at the persisted-report level, not only via digest."""
    default = _verified_matrix_entry()
    minio = _verified_matrix_entry(extra_bundles=["minio"])

    assert compatibility_context_artifact(default)["extra_bundles"] == ""
    assert compatibility_context_artifact(minio)["extra_bundles"] == "minio"


def test_default_and_minio_rows_have_different_matrix_digests() -> None:
    """The P2 codex finding: before the fix, these digests collided.
    After the fix, extra_bundles is part of the digest input so two
    rows with identical module_set but different opt-in bundles MUST
    produce different matrix_digest values."""
    default = _verified_matrix_entry()
    minio = _verified_matrix_entry(extra_bundles=["minio"])

    default_art = compatibility_context_artifact(default)
    minio_art = compatibility_context_artifact(minio)

    assert default_art["matrix_digest"] != minio_art["matrix_digest"], (
        "default full-dev and full-dev+minio produced identical "
        "matrix_digest — extra_bundles is still missing from the "
        "digest input"
    )
    # module_set is identical so module_set_digest stays the same; only
    # the matrix_digest (which wraps module_set + extra_bundles +
    # profile + versions) differs.
    assert default_art["module_set_digest"] == minio_art["module_set_digest"]


def test_multi_bundle_digest_is_order_independent() -> None:
    """Schema validator sorts extra_bundles on load, so the digest is
    invariant to the YAML author's ordering of the list."""
    ab = _verified_matrix_entry(extra_bundles=["minio", "grafana"])
    ba = _verified_matrix_entry(extra_bundles=["grafana", "minio"])

    assert (
        compatibility_context_artifact(ab)["matrix_digest"]
        == compatibility_context_artifact(ba)["matrix_digest"]
    )


def test_record_matches_matrix_context_agrees_with_extra_bundles() -> None:
    """A run record whose ``compatibility_context`` artifact was built
    from the MinIO row must NOT match the default full-dev row (and
    vice versa)."""
    default = _verified_matrix_entry()
    minio = _verified_matrix_entry(extra_bundles=["minio"])

    record_for_minio = IntegrationRunRecord(
        run_id="e2e-test-minio-0000",
        profile_id="full-dev",
        run_type="e2e",
        started_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
        finished_at=datetime(2026, 4, 24, tzinfo=timezone.utc),
        status="success",
        artifacts=[compatibility_context_artifact(minio)],
        failing_modules=[],
        summary="ok",
    )

    assert record_matches_matrix_context(record_for_minio, minio) is True
    assert record_matches_matrix_context(record_for_minio, default) is False
