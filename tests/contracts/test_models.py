from __future__ import annotations

from datetime import datetime, timezone
from math import inf, nan

import pytest
from pydantic import ValidationError

from assembly.contracts import (
    HealthResult,
    HealthStatus,
    IntegrationRunRecord,
    SmokeResult,
    VersionInfo,
)


def test_health_status_values_are_frozen() -> None:
    assert {status.value for status in HealthStatus} == {
        "healthy",
        "degraded",
        "blocked",
    }


def test_health_result_accepts_required_fields_and_default_details() -> None:
    result = HealthResult.model_validate(
        {
            "module_id": "assembly",
            "probe_name": "self-check",
            "status": "healthy",
            "latency_ms": 1.5,
            "message": "ready",
        }
    )

    assert result.status == HealthStatus.healthy
    assert result.details == {}


def test_health_result_requires_message_field() -> None:
    data = {
        "module_id": "assembly",
        "probe_name": "self-check",
        "status": "healthy",
        "latency_ms": 1.5,
    }

    with pytest.raises(ValidationError):
        HealthResult.model_validate(data)


@pytest.mark.parametrize("latency_ms", [-1.0, nan, inf])
def test_health_result_rejects_negative_or_non_finite_latency(
    latency_ms: float,
) -> None:
    with pytest.raises(ValidationError):
        HealthResult.model_validate(
            {
                "module_id": "assembly",
                "probe_name": "self-check",
                "status": "healthy",
                "latency_ms": latency_ms,
                "message": "ready",
            }
        )


def test_degraded_health_result_with_empty_message_warns() -> None:
    with pytest.warns(UserWarning, match="degraded HealthResult"):
        result = HealthResult.model_validate(
            {
                "module_id": "assembly",
                "probe_name": "optional-check",
                "status": "degraded",
                "latency_ms": 2.0,
                "message": "",
            }
        )

    assert result.status == HealthStatus.degraded


def test_smoke_result_allows_success_without_failure_reason() -> None:
    result = SmokeResult.model_validate(
        {
            "module_id": "assembly",
            "hook_name": "lite-smoke",
            "passed": True,
            "duration_ms": 3.25,
        }
    )

    assert result.failure_reason is None


@pytest.mark.parametrize("duration_ms", [-1.0, nan, inf])
def test_smoke_result_rejects_negative_or_non_finite_duration(
    duration_ms: float,
) -> None:
    with pytest.raises(ValidationError):
        SmokeResult.model_validate(
            {
                "module_id": "assembly",
                "hook_name": "lite-smoke",
                "passed": True,
                "duration_ms": duration_ms,
            }
        )


@pytest.mark.parametrize("failure_reason", [None, "", "   "])
def test_failed_smoke_result_requires_failure_reason(
    failure_reason: str | None,
) -> None:
    with pytest.raises(ValidationError):
        SmokeResult.model_validate(
            {
                "module_id": "assembly",
                "hook_name": "lite-smoke",
                "passed": False,
                "duration_ms": 3.25,
                "failure_reason": failure_reason,
            }
        )


def test_smoke_result_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        SmokeResult.model_validate(
            {
                "module_id": "assembly",
                "hook_name": "lite-smoke",
                "passed": True,
                "duration_ms": 3.25,
                "extra": "not allowed",
            }
        )


def test_integration_run_record_accepts_documented_fields() -> None:
    started_at = datetime.now(timezone.utc)
    record = IntegrationRunRecord(
        run_id="smoke-lite-local-1",
        profile_id="lite-local",
        run_type="smoke",
        started_at=started_at,
        finished_at=started_at,
        status="success",
        artifacts=[{"kind": "smoke_report", "path": "reports/smoke/example.json"}],
        failing_modules=[],
        summary="Smoke succeeded",
    )

    assert record.run_type == "smoke"
    assert record.status == "success"


def test_version_info_accepts_basic_semver_range() -> None:
    version = VersionInfo.model_validate(
        {
            "module_id": "assembly",
            "module_version": "1.2.3",
            "contract_version": "v1.0.0",
            "compatible_contract_range": ">=1.0.0 <2.0.0",
        }
    )

    assert version.compatible_contract_range == ">=1.0.0 <2.0.0"


def test_version_info_rejects_non_semver_range() -> None:
    with pytest.raises(ValidationError):
        VersionInfo.model_validate(
            {
                "module_id": "assembly",
                "module_version": "1.2.3",
                "contract_version": "v1.0.0",
                "compatible_contract_range": "latest",
            }
        )
