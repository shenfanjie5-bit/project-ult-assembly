# Canonical Candidate Derivation Rules Review (M1-F)

- Date: 2026-04-28
- Scope: M1-F per `ult_milestone.md`. Re-derive the 13 promotion candidates at current HEAD and assert each has a complete canonical PK derivation rule. **No M1.6 promotion batch.** No production fetch enabled. No generic Tushare inventory selection. Tushare remains a `provider="tushare"` adapter only.
- Mode: read-only re-derivation. Confirms or updates the C6 candidate inventory.
- Authority: `project_ult_v5_0_1.md` (NOT modified) + `ult_milestone.md` §M1.5 + C6 audit `p1-provider-neutral-canonical-promotion-readiness-20260428.md`.

---

## 1. Validation block

### 1.1 Re-derivation at current HEAD

```
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform && \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -c \
    "from data_platform.provider_catalog.registry import \
       PROMOTION_CANDIDATE_MAPPINGS, CANONICAL_DATASETS; \
     print(f'len(PROMOTION_CANDIDATE_MAPPINGS)={len(PROMOTION_CANDIDATE_MAPPINGS)}'); \
     print(f'len(CANONICAL_DATASETS)={len(CANONICAL_DATASETS)}')"
```

**Result**:
```
len(PROMOTION_CANDIDATE_MAPPINGS)=13
len(CANONICAL_DATASETS)=17
```

`registry.py` HEAD: `330f6b4d82a96d36c8fd150cc1a0a432d7c6cb9c` ("Require source interface ids for ambiguous provider mappings"). Last touched commit unchanged from C6 audit's snapshot, so the C6 derivation remains live and complete.

### 1.2 Provider-catalog test sweep (C6 baseline)

```
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform && \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
    -p no:cacheprovider -q tests/provider_catalog 2>&1 | tail -3
```

**Result**: `10 passed in 0.05s` (matches C6 baseline). Interpreter: `data-platform/.venv/bin/python` — Python 3.14.3.

### 1.3 138-row CSV inventory

```
wc -l /Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/provider_catalog/tushare_available_interfaces.csv
```

**Result**: `139` (1 header + 138 data rows). Matches C6.

---

## 2. The 13 candidates re-derived from `registry.py` (current HEAD)

Each entry below is read directly from `PROMOTION_CANDIDATE_MAPPINGS` (registry.py:945–1030). The format records:

- `source.doc_api → canonical.dataset` (the mapping pair).
- `source_primary_key`: provider-side PK columns.
- `field_mapping`: source → canonical column rename pairs.
- `canonical_primary_key`: read from the canonical dataset declaration.
- `Derivation rule status`: **complete** if `field_mapping` covers all canonical PK columns; **BLOCKER** otherwise — the canonical PK column(s) cannot be filled from the mapping alone and a per-source rule must be specified before promotion.

| # | doc_api | canonical_dataset | source_pk | field_mapping (provider → canonical) | canonical_pk | Status |
|---|---|---|---|---|---|---|
| 1 | `index_dailybasic` | `index_price_bar` | `(ts_code, trade_date)` | `ts_code→index_id, trade_date→trade_date` | `(index_id, trade_date, frequency)` | **BLOCKER** — `frequency` not projected |
| 2 | `margin` | `market_leverage_daily` | `(trade_date,)` | `trade_date→trade_date` | `(market, trade_date)` | **BLOCKER** — `market` not projected |
| 3 | `margin_detail` | `security_leverage_detail` | `(ts_code, trade_date)` | `ts_code→security_id, trade_date→trade_date` | `(security_id, trade_date)` | complete |
| 4 | `pledge_stat` | `event_timeline` | `(ts_code, end_date)` | `ts_code→entity_id` | `(event_type, entity_id, event_date, event_key)` | **BLOCKER** — `event_type`, `event_date`, `event_key` not projected |
| 5 | `pledge_detail` | `event_timeline` | `(ts_code, ann_date)` | `ts_code→entity_id` | same as #4 | **BLOCKER** — same shape |
| 6 | `repurchase` | `event_timeline` | `(ts_code, ann_date)` | `ts_code→entity_id` | same as #4 | **BLOCKER** — same shape |
| 7 | `stk_holdertrade` | `event_timeline` | `(ts_code, ann_date)` | `ts_code→entity_id` | same as #4 | **BLOCKER** — same shape |
| 8 | `limit_list_ths` | `event_timeline` | `(trade_date, ts_code)` | `ts_code→entity_id` | same as #4 | **BLOCKER** — same shape |
| 9 | `limit_list_d` | `event_timeline` | `(trade_date, ts_code)` | `ts_code→entity_id` | same as #4 | **BLOCKER** — same shape |
| 10 | `hm_detail` | `event_timeline` | `(trade_date, ts_code)` | `ts_code→entity_id` | same as #4 | **BLOCKER** — same shape |
| 11 | `stk_surv` | `event_timeline` | `(ts_code, ann_date)` | `ts_code→entity_id` | same as #4 | **BLOCKER** — same shape |
| 12 | `express` | `financial_forecast_event` | `(ts_code, ann_date, end_date)` | `ts_code→security_id, ann_date→announcement_date, end_date→report_period` | `(security_id, announcement_date, report_period, forecast_type)` | **BLOCKER** — `forecast_type` not projected |
| 13 | `fina_mainbz` | `business_segment_exposure` | `(ts_code, end_date, bz_item)` | `ts_code→security_id, end_date→report_period, bz_item→segment_name` | `(security_id, report_period, segment_name)` | complete |

**Summary**: **2 of 13 candidates have a complete canonical PK derivation rule** (`margin_detail`, `fina_mainbz`). **11 of 13 have a missing PK column or columns** — promotion BLOCKED until per-source derivation rules are specified.

---

## 3. Per-blocker derivation rule requirements

Each blocker below specifies what the M1.6 promotion-batch task must define before promotion can proceed. **This audit does NOT define the rules.** It enumerates what needs definition.

### 3.1 `event_timeline` blockers (8 candidates: #4–#11)

`event_timeline` canonical PK is `(event_type, entity_id, event_date, event_key)`. The 8 candidate sources project only `ts_code → entity_id`. They need:

- **`event_type`** — a constant per source. Suggested mapping (must be confirmed by domain):
  - `pledge_stat` → `"pledge_stat"` or `"pledge"` (need decision on grouping).
  - `pledge_detail` → `"pledge_detail"` or `"pledge"`.
  - `repurchase` → `"repurchase"`.
  - `stk_holdertrade` → `"holder_trade"`.
  - `limit_list_ths` → `"limit_up_ths"` (THS variant).
  - `limit_list_d` → `"limit_up"`.
  - `hm_detail` → `"hot_money_trade"` (or similar).
  - `stk_surv` → `"institution_survey"`.
  These are AT MOST suggestions — the canonical event taxonomy must be a single decision, not 8 independent strings.
- **`event_date`** — derived from one of the source date columns. Different sources use different date columns (`end_date`, `ann_date`, `trade_date`); the rule must specify which becomes `event_date` per source. Likely candidates:
  - `pledge_stat`: `end_date`.
  - `pledge_detail`/`repurchase`/`stk_holdertrade`/`stk_surv`: `ann_date`.
  - `limit_list_ths`/`limit_list_d`/`hm_detail`: `trade_date`.
- **`event_key`** — composite key for event-instance uniqueness. Often a hash or concatenation of source row identity (e.g., for `pledge_stat` the source PK extension is `end_date`; for `limit_list_d` it could be `(trade_date, ts_code, hour)` if intra-day; needs source-by-source decision).

### 3.2 `index_dailybasic` (#1) — `index_price_bar`

Missing canonical PK column: `frequency`. The Tushare `index_dailybasic` API returns daily index features. The derivation rule should be a **constant `'daily'`** per source. This is the simplest of the blockers and could be addressed with a single field-mapping addition (`(constant 'daily', frequency)` or equivalent in the canonical writer projection).

### 3.3 `margin` (#2) — `market_leverage_daily`

Missing canonical PK column: `market`. The Tushare `margin` API returns total market financing/lending balances; the source has no `market` column because it covers all of CN_A in a single row. The derivation rule should be a **constant `'CN_A'`** (or whatever market literal the canonical taxonomy uses).

### 3.4 `express` (#12) — `financial_forecast_event`

Missing canonical PK column: `forecast_type`. The Tushare `express` API is the "performance express" forecast type specifically; it's a single forecast variant. The derivation rule should be a **constant `'express'`** (matching the `forecast` candidate which is already promoted with `forecast_type='forecast'`).

---

## 4. Candidates with complete derivation (CONFIRMED)

| # | doc_api | canonical_dataset | Note |
|---|---|---|---|
| 3 | `margin_detail` | `security_leverage_detail` | Per-symbol margin detail; `(security_id, trade_date)` PK fully projected. Could be promoted in the next M1.6 batch without additional derivation work. |
| 13 | `fina_mainbz` | `business_segment_exposure` | Quarterly business-segment composition; `(security_id, report_period, segment_name)` PK fully projected. Could be promoted in the next M1.6 batch without additional derivation work. |

---

## 5. CSV inventory cross-check (per C6 §5.14)

All 13 candidates have `access_status=available` and `completeness_status=未见明显遗漏` in `tushare_available_interfaces.csv`. None is blocked at the provider availability layer. The blockers above are purely canonical-contract-side (PK derivation), not provider-side.

---

## 6. M1.6 promotion-batch readiness (NOT EXECUTED in this audit)

Per `ult_milestone.md` §M1.5 acceptance: "M1.6 是否可开由 evidence 决定，但本任务不执行 M1.6". This audit DOES NOT promote any candidate. The promotion-readiness signal:

- **Ready for M1.6 batch**: 2 candidates (`margin_detail`, `fina_mainbz`).
- **Blocked on per-source derivation rule definition**: 11 candidates (8 event_timeline + 3 single-column gaps).
- **Hard rule**: M1.6 must NOT promote any blocked candidate without first defining the derivation rule. The 2 ready candidates may be promoted as a small batch IF M1.6 is opened separately by the user; this audit does not request M1.6.

---

## 7. Hard-rule reaffirmation

- Generic Tushare inventory selection NOT enabled. The 107 unpromoted CSV interfaces remain provider inventory only.
- Production fetch NOT enabled.
- M1.6 promotion batch NOT executed.
- No source code change.
- No `git init`, no commits, no pushes.
- No forbidden files committed.
- Tushare remains a `provider="tushare"` adapter only.
- `project_ult_v5_0_1.md` NOT modified.
- P5 shadow-run NOT started.
- M2/M3/M4 NOT entered.

---

## 8. Findings tally

- **CONFIRMED** (4):
  1. `len(PROMOTION_CANDIDATE_MAPPINGS) == 13` at registry HEAD `330f6b4` (unchanged from C6).
  2. `len(CANONICAL_DATASETS) == 17` (unchanged from C6).
  3. `tests/provider_catalog` PASS — 10 passed (matches C6 baseline).
  4. 138-row CSV inventory unchanged.
- **PARTIAL** (1):
  1. 11 of 13 candidates have an incomplete canonical PK derivation rule. Per-source rules must be defined before any promotion (8 event_timeline + 3 single-column gaps).
- **INFERRED** (1):
  1. The suggested `event_type` constants in §3.1 are reasonable derivations from each source's domain meaning, but the canonical event taxonomy is a single normative decision that has not been recorded in `registry.py` or any other in-repo artifact. Treat the suggestions as starting points, not authoritative.

---

## 9. Per-task handoff block

```
Task: M1-F canonical candidate derivation rules review
Repo(s): data-platform + assembly
Output: /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/canonical-candidate-derivation-rules-20260428.md
Validation commands:
  1. cd data-platform && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -c "from data_platform.provider_catalog.registry import PROMOTION_CANDIDATE_MAPPINGS, CANONICAL_DATASETS; print(len(PROMOTION_CANDIDATE_MAPPINGS), len(CANONICAL_DATASETS))"
  2. cd data-platform && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -p no:cacheprovider -q tests/provider_catalog
  3. wc -l /Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/provider_catalog/tushare_available_interfaces.csv
Validation results:
  1. 13 17 (matches C6 baseline)
  2. 10 passed in 0.05s (matches C6 baseline)
  3. 139 lines (1 header + 138 rows; matches C6 baseline)
Per-subrepo git state:
  data-platform: rev-parse HEAD = 330f6b4d82a96d36c8fd150cc1a0a432d7c6cb9c; status =  M src/data_platform/raw/writer.py /  M tests/raw/test_writer.py (pre-existing) + new untracked files from M1-D + M1-E (this M1-F audit adds NO source code change); push = not pushed; branch = main; interpreter = data-platform/.venv/bin/python (Python 3.14.3)
  assembly:      rev-parse HEAD = a7f19c5; status = untracked stabilization reports include this M1-F report; push = not pushed; branch = main
Dirty files added by this task:
  assembly/reports/stabilization/canonical-candidate-derivation-rules-20260428.md (NEW)
Findings: 4 CONFIRMED, 1 PARTIAL, 1 INFERRED
Outstanding risks:
  - 11 of 13 candidates have an incomplete PK derivation rule and cannot be promoted in M1.6 without rule definition
  - The canonical event taxonomy (event_type values) is not recorded anywhere in repo
  - The 10 `legacy_typed_not_in_catalog` mappings (from C6 §4.2) are unchanged and still reference doc_api ids absent from the current 138-row CSV
Declaration: I did not modify project_ult_v5_0_1.md. I did not enter M2/M3/M4. I did not enable production fetch. I did not start P5 shadow-run. I did not start compose. I did not perform M1.6 promotion. I did not enable generic Tushare inventory selection. I did not commit any forbidden files. I did not run `git init`. I did not push without approval. Tushare remains a provider=tushare adapter only.
```
