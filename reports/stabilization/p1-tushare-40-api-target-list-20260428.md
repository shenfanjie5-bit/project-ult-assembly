# P1 Tushare 40 API Target-List And Current-Cycle Evidence - 2026-04-28

## Scope

This Backend-B evidence covers the `data-platform` P1 current-cycle selector,
the PostgreSQL freeze wrapper proof, and the P1 40-API target-list decision. It
does not start P5 and does not add API-6, sidecar, frontend write API, Kafka,
Flink, Temporal, news, or Polymarket production flow.

## Environment Status

Command:

```bash
for k in DP_PG_DSN DP_TUSHARE_TOKEN DATABASE_URL; do
  if [ -n "${(P)k}" ]; then echo "$k=set"; else echo "$k=missing"; fi
done
```

Result:

```text
DP_PG_DSN=missing
DP_TUSHARE_TOKEN=missing
DATABASE_URL=missing
```

Impact:

- Live Tushare ingestion cannot be rerun in this shell.
- Real PostgreSQL freeze execution cannot be rerun in this shell.
- Evidence below is therefore PARTIAL for live runtime and explicit about
  skipped/blocked checks.

## Current-Cycle Selection

Code reference:

- `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/cycle/current_selection.py`
  lines 255-391.

Observed behavior:

- `select_current_cycle()` reads already-ingested Raw Zone Tushare
  `trade_cal` manifests.
- It parses `trade_cal.cal_date` rows, keeps rows where `is_open` is truthy,
  chooses `max(open_trade_dates)`, then derives `cycle_id` with
  `cycle_id_for_date(trade_date)`.
- It then requires matching `daily` artifact rows for that trade date and a
  latest `stock_basic` artifact. Missing refs fail closed with
  `CurrentCycleSelectionError`; no fixed cycle fallback is present in the
  production module.

Archived Raw Zone proof command:

```bash
.venv/bin/python - <<'PY'
from data_platform.cycle.current_selection import select_current_cycle
selection = select_current_cycle(
    raw_zone_path="/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/real-data-mini-cycle-runtime-unblock-artifacts/raw"
)
print(selection.evidence)
PY
```

Result:

- Status: OK against archived ingested artifacts.
- Selected trade date: `2026-03-31`.
- Generated cycle ID: `CYCLE_20260331`.
- Input refs present: `trade_cal`, `daily`, `stock_basic`.
- Artifact rows: `trade_cal=1`, `daily=3`, `stock_basic=3`.

Additional blocked artifact checks:

- `live-tushare-mini-ingestion-artifacts/raw`: BLOCKED for selector because
  `stock_basic` artifact ref is missing after selecting `CYCLE_20260415`.
- `real-data-mini-cycle-pg-runtime-artifacts/.../raw`: BLOCKED for selector
  because no `trade_cal` artifact ref is present.

## PostgreSQL Freeze Wrapper

Code references:

- `freeze_current_cycle_candidates()`:
  `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/cycle/current_selection.py`
  lines 428-470.
- Underlying transaction:
  `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/cycle/freeze.py`
  uses `with repository.begin() as connection`.
- Repository transaction body:
  `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/cycle/repository.py`
  `freeze_selection()` performs row lock, `INSERT ... SELECT`, metadata update,
  and return in the caller transaction.

New wrapper evidence added:

- `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/tests/cycle/test_current_selection.py`
  lines 215-247: default wrapper uses real PG `get_cycle`,
  `freeze_cycle_candidates`, and `load_frozen_candidate_ids` when a DSN is
  available.
- Same file lines 250-297: forced trigger failure verifies the wrapper reports
  `pg_freeze_failed` and the PG transaction rolls back selection rows and
  metadata.
- Same file lines 300-370: test fixtures create an isolated PostgreSQL test
  database from `DATABASE_URL` or `DP_PG_DSN`; if no DSN is present, the tests
  skip with an explicit reason.

Verification command:

```bash
.venv/bin/python -m pytest tests/cycle/test_current_selection.py -q -rs
```

Result:

```text
........ss [100%]
SKIPPED [1] tests/cycle/test_current_selection.py:215: current-cycle PG wrapper tests require DATABASE_URL or DP_PG_DSN
SKIPPED [1] tests/cycle/test_current_selection.py:250: current-cycle PG wrapper tests require DATABASE_URL or DP_PG_DSN
```

Conclusion: PARTIAL. The code and tests now prove the real PG transaction path
when `DP_PG_DSN` or `DATABASE_URL` is available. This shell cannot execute that
path because no DSN is configured.

## 40-API Target-List Decision

Inventory command:

```bash
.venv/bin/python - <<'PY'
from pathlib import Path
from data_platform.adapters.tushare.assets import TUSHARE_ASSETS
staging = sorted(p.stem.removeprefix("stg_") for p in Path("src/data_platform/dbt/models/staging").glob("stg_*.sql"))
assets = [asset.dataset for asset in TUSHARE_ASSETS]
print(len(assets), len(staging), sorted(set(staging)-set(assets)), sorted(set(assets)-set(staging)))
PY
```

Result:

- Declared Tushare assets: 28.
- Staging dbt models: 28.
- Asset/staging mismatch: none.
- Current implemented list:
  `stock_basic`, `daily`, `weekly`, `monthly`, `adj_factor`, `daily_basic`,
  `index_basic`, `index_daily`, `index_weight`, `index_member`,
  `index_classify`, `trade_cal`, `stock_company`, `namechange`, `anns`,
  `suspend_d`, `dividend`, `share_float`, `stk_holdernumber`,
  `disclosure_date`, `income`, `balancesheet`, `cashflow`, `fina_indicator`,
  `stk_limit`, `block_trade`, `moneyflow`, `forecast`.

Decision:

- Blueprint target remains approximately 40 Tushare APIs.
- Code-grounded state remains 28 declared assets and 28 staging models.
- Remaining 12 APIs are still an authoritative target-list planning gap.
- Do not implement or classify missing APIs by guesswork in this batch.

## Verification Summary

Commands run:

- `.venv/bin/python -m pytest tests/cycle/test_current_selection.py -q -rs`
  -> PASS 8, SKIP 2 due missing `DATABASE_URL`/`DP_PG_DSN`.
- `.venv/bin/python -m ruff check tests/cycle/test_current_selection.py`
  -> PASS.
- Archived selector probe over
  `real-data-mini-cycle-runtime-unblock-artifacts/raw`
  -> OK, selected `CYCLE_20260331`.
- Asset/staging inventory script -> 28/28, no mismatch.

## Findings

- P0: None.
- P1: PARTIAL/BLOCKED live PG proof in this shell because `DP_PG_DSN` and
  `DATABASE_URL` are missing; tests now execute the real PG wrapper path when a
  DSN is supplied.
- P2: PARTIAL live Tushare proof because `DP_TUSHARE_TOKEN` is missing; archived
  Raw Zone artifact proof was used and incomplete archived roots were reported
  as blocked instead of faked.
- P3: The 12 missing Tushare APIs remain a planning decision gap, not an
  implementation task.
