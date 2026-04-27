# New Data Interface Vertical Slice Evidence - 2026-04-27

## Verdict

Status: PASS for controlled vertical-slice proof.

This is not a new external-source production integration. It proves the current
Project ULT design can carry a newly extracted event signal through existing
contracts and read-only ports without changing the Ex-1/Ex-2/Ex-3 public
schemas.

## Commit

- main-core: `57b202efbdb669b6dc3766bde8cfa2694d01799f`
  - Adds
    `tests/integration/test_new_data_interface_vertical_slice.py`.

## Validated Path

The test constructs a controlled event-impact payload:

- Ex-1 fact: event summary for `ENT_STOCK_600519.SH`.
- Ex-2 signal: `event_industry_price_impact`, bullish direction, affected
  company `ENT_STOCK_600519.SH`, affected sector `SECTOR_BAIJIU`.
- Ex-3 graph delta: anchored event node
  `ENT_EVENT_tushare_notice_5b6f6d42` impacts the sector node.
- Graph snapshot: includes the anchored event node, stock node, sector node,
  and event-to-sector edge.
- Graph impact snapshot: exposes impact score, direction, affected sector,
  affected entity, and evidence refs.
- L3 feature bundle: consumes Layer B candidate signal plus graph impact.
- L4 world state: constructs a `reasoner_runtime.ReasonerRequest` with
  `configured_provider="openai-codex"` and carries evidence refs in
  `input_refs`.
- L7 recommendation: produces a current-cycle recommendation from the enriched
  L3/L4 context.

## Validation

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/main-core
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/main-core/src:/Users/fanjie/Desktop/Cowork/project-ult/contracts/src:/Users/fanjie/Desktop/Cowork/project-ult/reasoner-runtime \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q \
  tests/integration/test_new_data_interface_vertical_slice.py \
  tests/integration/test_layer_b_candidate_signals.py \
  tests/integration/test_l6_multi_agent_enriched_inputs.py \
  tests/l4_world_state/test_graph_adapter.py

result:
12 passed
```

Frontend read-only graph route check:

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/frontend-api
PATH=/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin:$PATH \
PYTHONPATH=/Users/fanjie/Desktop/Cowork/project-ult/frontend-api/src \
/Users/fanjie/Desktop/Cowork/project-ult/assembly/.venv-py312/bin/python -m pytest -q \
  tests/test_graph_routes.py

result:
6 passed
```

System `python3` in `frontend-api` lacks `fastapi`; the project venv contains
the needed runtime dependencies and passed.

## Design Confirmation

- Pure structured data still enters through adapter/dbt/Layer A and can be
  read by L3 as market/entity inputs.
- Extracted facts/signals enter through Ex-1/Ex-2 and can influence L3/L4/L6/L7
  through `CandidateSignalPort`, `FeatureSignalBundle`, and
  `ReasonerRequest.input_refs`.
- Extracted graph effects enter through Ex-3 as graph deltas and can influence
  graph snapshots and graph impact snapshots.
- A brand-new event that must appear as a graph node should be anchored first
  as a deterministic Layer A/entity-registry node, then referenced by Ex-3.
  This evidence keeps Ex-3 as an edge contract and does not expand public
  schemas.
- Frontend display remains read-only through existing frontend-api graph/formal
  artifact routes.

## Non-Claims

- This is not Polymarket or news production ingestion.
- This does not add a frontend write interface.
- This does not replace the production `daily_cycle_job` proof.
- This does not claim P5 readiness.

## Findings

- P0: none.
- P1: none.
- P2: none.
- P3: the proof uses controlled in-test ports and artifacts; production use
  still depends on P3 live graph closure and production daily-cycle providers.
