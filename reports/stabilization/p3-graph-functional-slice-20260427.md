# P3 Graph Functional Slice Evidence - 2026-04-27

## Verdict

Status: PARTIAL PASS / GDS live proof blocked.

This closes the code-level and Neo4j promotion parts of the P3 functional
slice. It does not claim full P3 scale, full P3 performance, or a complete
GDS-backed production graph proof. The configured Neo4j instance is reachable,
but does not have the GDS plugin, so the GDS-backed propagation snapshot and
cold reload integration tests are skipped by their own environment gates.

## Scoped Repo And Commit

- graph-engine: `53a8c6e90e9bc9daac80e4544a5349b8ee1947a4`

## What Changed

- CandidateGraphDelta promotion now accepts the Ex-3 terms observed from
  subsystem producers:
  - `add_edge` and `add` map to internal `edge_add`.
  - `supply_contract` and `supplier_of` map to `SUPPLY_CHAIN`.
  - Unsupported delta and relation types still fail closed.
- Promotion live sync now refreshes ready status from actual live graph metrics
  before releasing the writer lock, instead of restoring stale pre-sync counts.
- The Neo4j promotion integration test now uses `contracts.schemas.CandidateGraphDelta`
  for the candidate reader path, not legacy `FrozenGraphDelta`.
- A GraphSnapshot-to-reload metrics bridge was added for graph-engine generated,
  live-metric-shaped snapshots. It rejects compact snapshots and multi-label
  nodes to avoid false cold reload consistency claims.

## Verified Closure Surface

- Candidate graph deltas can be normalized into canonical edge promotion plans.
- Canonical write still precedes live graph sync.
- Promotion status reflects post-sync live metrics and bumps generation.
- Neo4j promotion sync idempotency runs against the configured Neo4j instance
  when assembly `.env` is loaded.
- GraphSnapshot reload bridge fails closed for compact formal snapshots and
  multi-label nodes, avoiding checksum and label overclaims found in review.

## Validation Commands

- Focused promotion/reload tests:
  - Command:
    `cd /Users/fanjie/Desktop/Cowork/project-ult/graph-engine && /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q tests/unit/test_reload.py tests/unit/test_promotion.py`
  - Result: `47 passed`.

- P3 requested graph suite with Neo4j env loaded:
  - Command:
    `cd /Users/fanjie/Desktop/Cowork/project-ult/graph-engine && set -a; source /Users/fanjie/Desktop/Cowork/project-ult/assembly/.env; set +a; /Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q -rs tests/unit tests/integration/test_promotion_sync.py tests/integration/test_full_propagation.py tests/integration/test_propagation_snapshot.py tests/integration/test_reload.py tests/contract/test_runtime_contract.py tests/contract/test_contracts_alignment.py`
  - Result: pass with three GDS skips.
  - Skips:
    - `tests/integration/test_full_propagation.py`: GDS plugin is not available.
    - `tests/integration/test_propagation_snapshot.py`: GDS plugin is not available.
    - `tests/integration/test_reload.py`: GDS plugin is not available.

- Independent P3 follow-up review:
  - P0/P1/P2/P3 findings: none.
  - Reviewer commands passed:
    - `git diff --check`
    - `tests/unit/test_reload.py tests/unit/test_promotion.py`
    - `tests/unit/test_status.py tests/unit/test_snapshots.py tests/regression/test_with_shared_fixtures_graph.py`
    - `tests/unit/test_contract_schemas.py`

## Findings

- P0: none.
- P1: none remaining. Initial review found the reload bridge could compute a
  checksum from compact snapshot properties that live reload would not reproduce;
  the bridge now requires live-metric-shaped properties and identity validation.
- P2: none remaining. Initial review found multi-label snapshots were
  over-accepted; the bridge now rejects multi-label nodes because reload records
  carry one label.
- P3: GDS-backed integration remains unavailable in this local Neo4j instance.

## Residual Risk

- This is not a P3 scale gate. The 100k node / 50-100万 edge target remains a
  later P3 performance gate.
- GDS-backed propagation snapshot and cold reload live proof require a Neo4j
  instance with the GDS plugin. Until that runs without skips, this evidence
  must not be used to unlock P5 shadow-run.
- The new reload bridge is exported and tested, but a concrete data-platform
  `CanonicalReader` that materializes `ColdReloadPlan` from persisted graph
  snapshots remains future integration work.
