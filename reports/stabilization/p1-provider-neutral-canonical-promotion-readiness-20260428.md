# P1 Provider-Neutral Canonical Promotion Readiness Audit (C6)

- **Task**: C6 — Data-Platform Canonical Promotion Readiness
- **Date**: 2026-04-28
- **Repo(s)**: `data-platform` + `assembly`
- **Output**: `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/p1-provider-neutral-canonical-promotion-readiness-20260428.md`
- **Plan**: `/Users/fanjie/.claude/plans/project-ult-v5-0-1-cosmic-milner.md` (C6 section)
- **Declaration**: This audit reports **PROMOTION READINESS only**. It does NOT enable
  any production fetch, does NOT modify the canonical writer, does NOT change Iceberg DDL,
  does NOT promote any candidate, and does NOT touch source code. Tushare remains a
  `provider=tushare` source adapter. Nothing was committed; `git init` was not run.

## 1. Validation block (all 4 commands required by C6)

### 1.1 `wc -l tushare_available_interfaces.csv`

```text
$ wc -l /Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/provider_catalog/tushare_available_interfaces.csv
     139 .../tushare_available_interfaces.csv
```

**Interpretation**: 139 lines = 1 header + **138 data rows**. Matches plan's "138 inventory".
CSV columns (15): `provider, source_interface_id, doc_api, label, level1, level2, level3,
level4, doc_url, storage_mode, split_by_symbol, access_status, access_reason,
completeness_status, check_confidence`. (CSV header read, line 1.)

### 1.2 `pytest -q tests/provider_catalog`

```text
$ cd data-platform && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python \
    -m pytest -p no:cacheprovider -q tests/provider_catalog 2>&1 | tail -10
..........                                                               [100%]
```

**Result**: **PASS** — 10 tests passed, 0 failed.
**Interpretation**: catalog test suite green at this moment. Per C6 hard rule this confirms
the catalog itself behaves as today; it does NOT confirm the candidate batch is promoted.

### 1.3 `rg -n 'status[[:space:]]*=' registry.py | head -200`

```text
370:        access_status=row["access_status"].strip(),
372:        completeness_status=row["completeness_status"].strip(),
443:        status=status,                                   # _mapping() default param wiring
791:        status="legacy_typed_not_in_catalog",            # adj_factor
828:        status="legacy_typed_not_in_catalog",            # index_daily
841:            status=cast(MappingStatus, status),          # index_membership comprehension
884:            status=cast(MappingStatus, status),          # event_timeline comprehension
908:            status="legacy_typed_not_in_catalog",        # income/balancesheet/cashflow loop
922:            status="legacy_typed_not_in_catalog",        # fina_indicator
949:        status="candidate",                              # index_dailybasic
961:        status="candidate",                              # margin
973:        status="candidate",                              # margin_detail
986:            status="candidate",                          # event_timeline candidate loop
1009:        status="candidate",                             # express
1021:        status="candidate",                             # fina_mainbz
1165:        promotion_status=(...)                          # registry-entry projection
1189:        promotion_status=mapping.status,                # registry-entry projection
```

**Interpretation**: exact status labels in use are
`promoted` (default in `_mapping`), `legacy_typed_not_in_catalog`, and `candidate`.
**The candidate-equivalent label is exactly `"candidate"`** (per `MappingStatus` literal in
`PROMOTION_CANDIDATE_MAPPINGS`, lines 949–1021). No other variant such as
`promotion_candidate` is used.

### 1.4 `rg -n 'canonical_dataset[[:space:]]*=' registry.py | wc -l`

```text
$ rg -n 'canonical_dataset[[:space:]]*=' .../registry.py | wc -l
       3
```

**Interpretation**: `wc -l` reports 3, but this is **misleading**. The grep matches only the
literal `canonical_dataset =` form, which appears at:
- line 161 — dataclass field declaration in `ProviderDatasetMapping`
- line 210 — dataclass field declaration in `TushareInterfaceRegistryEntry`
- line 425 — `_mapping()` helper signature

The actual canonical datasets are constructed via the `_dataset(dataset_id, ...)` helper
(17 invocations at lines 458, 476, 492, 513, 528, 548, 564, 581, 597, 613, 629, 646, 663,
680, 697, 713, 729; counted by `rg -n '_dataset\\('`). Per-mapping
`canonical_dataset` values are passed positionally to `_mapping(...)` so they are not visible
to this regex. The authoritative count comes from `len(CANONICAL_DATASETS) == 17`,
verified live (see §3 derivation).

## 2. Per-subrepo git state (mandatory probe)

| Subrepo | toplevel | rev-parse HEAD | branch | status -s |
|---------|----------|----------------|--------|-----------|
| `data-platform` | `/Users/fanjie/Desktop/Cowork/project-ult/data-platform` | `330f6b4d82a96d36c8fd150cc1a0a432d7c6cb9c` | `main` | ` M src/data_platform/raw/writer.py` / ` M tests/raw/test_writer.py` (pre-existing dirty, NOT touched by this audit) |
| `assembly` | `/Users/fanjie/Desktop/Cowork/project-ult/assembly` | `a7f19c5994f807b2cf32eb2f45ef48f6fe23095f` | `main` | `?? reports/stabilization/frontend-raw-route-alignment-fix-20260428.md` / `?? reports/stabilization/production-daily-cycle-gap-audit-20260428.md` / `?? reports/stabilization/project-ult-v5-0-1-supervisor-review-20260428.md` / `?? reports/stabilization/raw-manifest-source-interface-hardening-20260428.md` (this report adds one more `??` entry; not committed, not pushed) |

No push performed. No `git init` run.

## 3. Inventory state (re-derived live, no quoted prior numbers)

Derived by importing the registry and counting its in-memory constants:

| Metric | Value | Derivation |
|--------|-------|------------|
| Total provider interface inventory | **138** | `wc -l tushare_available_interfaces.csv` minus header (`139 - 1`); also `len(load_tushare_provider_catalog()) == 138`, registry.py:286 |
| Canonical datasets defined | **17** | `len(CANONICAL_DATASETS) == 17`, registry.py:455–747 |
| Promoted mappings (`PROVIDER_MAPPINGS`) | **28** | `len(PROVIDER_MAPPINGS) == 28`, registry.py:750–942. Of these: 18 with `status="promoted"`, 10 with `status="legacy_typed_not_in_catalog"`. |
| Candidate mappings (`PROMOTION_CANDIDATE_MAPPINGS`) | **13** | `len(PROMOTION_CANDIDATE_MAPPINGS) == 13`, registry.py:945–1030; all carry `status="candidate"`. **Plan-quoted "13 candidate mappings" is confirmed by re-derivation; no discrepancy.** |
| Generic unpromoted (CSV interfaces with no mapping) | **107** | `catalog_summary()['generic_unpromoted_count'] == 107`, registry.py:283–309 |
| Mapped CSV interfaces (promoted-status + candidate, intersected with CSV) | **31** | 18 (promoted) + 13 (candidate) = 31 CSV rows; the 10 `legacy_typed_not_in_catalog` mappings reference doc-api ids not present in this CSV (`adj_factor`, `index_daily`, `index_weight`, `index_member`, `anns`, `suspend_d`, `income`, `balancesheet`, `cashflow`, `fina_indicator`) and therefore do not subtract from the 138-row CSV inventory. |

**CONFIRMED count check**: 138 (CSV) − 18 (promoted in CSV) − 13 (candidate in CSV) = 107
generic-unpromoted, matching `catalog_summary()`.

**Discrepancy note**: the prior audit report
(`p1-provider-neutral-tushare-catalog-20260428.md`) does NOT pre-state these splits in the
exact form above; this report re-derives them rather than quoting that file. The `13`
candidate count matches the plan's expectation, so no count discrepancy was discovered
that requires escalation.

## 4. Promoted (in production today)

The `PROVIDER_MAPPINGS` tuple (registry.py:750–942) drives the production catalog. All
entries below were re-derived; `status` is read directly from registry.py and `access_status`
/ `completeness_status` are cross-checked against
`tushare_available_interfaces.csv`. Status labels in use: `promoted`,
`legacy_typed_not_in_catalog`. (`legacy_typed_not_in_catalog` indicates a typed mapping that
exists in code but whose source `interface_id` is intentionally absent from the current CSV
inventory snapshot.)

### 4.1 Status = `promoted` (18 entries, CSV-resident)

| canonical_dataset | source_interface_id | doc_api | line | CSV access | CSV completeness |
|---|---|---|---|---|---|
| security_master | stock_basic | stock_basic | 752 | available | 未见明显遗漏 |
| trading_calendar | trade_cal_stock | trade_cal | 762 | available | 未见明显遗漏 |
| price_bar | daily | daily | 775 | available | 未见明显遗漏 |
| price_bar | weekly | weekly | 775 | available | 未见明显遗漏 |
| price_bar | monthly | monthly | 775 | available | 未见明显遗漏 |
| market_daily_feature | daily_basic | daily_basic | 801 | available | 未见明显遗漏 |
| market_daily_feature | stk_limit | stk_limit | 801 | available | 未见明显遗漏 |
| market_daily_feature | moneyflow | moneyflow | 801 | available | 未见明显遗漏 |
| index_master | index_basic | index_basic | 814 | available | 未见明显遗漏 |
| industry_classification | index_classify | index_classify | 855 | available | 未见明显遗漏 |
| security_profile | stock_company | stock_company | 867 | available | 未见明显遗漏 |
| event_timeline | namechange | namechange | 881 | available | 未见明显遗漏 |
| event_timeline | dividend | dividend | 881 | available | 未见明显遗漏 |
| event_timeline | share_float | share_float | 881 | available | 未见明显遗漏 |
| event_timeline | stk_holdernumber | stk_holdernumber | 881 | available | 未见明显遗漏 |
| event_timeline | disclosure_date | disclosure_date | 881 | available | 未见明显遗漏 |
| event_timeline | block_trade | block_trade | 881 | available | 未见明显遗漏 |
| financial_forecast_event | forecast | forecast | 931 | available | 未见明显遗漏 |

### 4.2 Status = `legacy_typed_not_in_catalog` (10 entries, NOT in current CSV)

| canonical_dataset | source_interface_id (= doc_api) | line | CSV cross-check |
|---|---|---|---|
| adjustment_factor | adj_factor | 788 | NOT IN CSV |
| index_price_bar | index_daily | 825 | NOT IN CSV |
| index_membership | index_weight | 838 | NOT IN CSV |
| index_membership | index_member | 838 | NOT IN CSV |
| event_timeline | anns | 881 | NOT IN CSV |
| event_timeline | suspend_d | 881 | NOT IN CSV |
| financial_statement | income | 905 | NOT IN CSV |
| financial_statement | balancesheet | 905 | NOT IN CSV |
| financial_statement | cashflow | 905 | NOT IN CSV |
| financial_indicator | fina_indicator | 919 | NOT IN CSV |

**CONFIRMED**: status labels `legacy_typed_not_in_catalog` and `promoted` are the labels for
production mappings; `legacy_typed_not_in_catalog` indicates the typed mapping is present in
code but its interface is not represented in the current CSV inventory snapshot. No
candidate-status entries appear in `PROVIDER_MAPPINGS`.

## 5. Candidate batch (re-derived from `PROMOTION_CANDIDATE_MAPPINGS`)

13 entries in `PROMOTION_CANDIDATE_MAPPINGS` (registry.py:945–1030), all
`status="candidate"`. The `ProviderDatasetMapping` dataclass exposes
`unit_policy / date_policy / adjustment_policy / update_policy / null_policy / coverage`
plus `field_mapping / source_primary_key`. **Note on `late_arriving_policy`**: the dataclass
has no separate `late_arriving_policy` field; late-arriving handling is encoded in
`update_policy`. Where `update_policy` mentions "late corrections" / "late-arriving", the
tag is recorded as such; otherwise marked "n/a (per `update_policy`)". The
canonical-dataset's `null_policy` (`CanonicalDataset.null_policy`, registry.py:405) acts as
the canonical default; per-mapping `null_policy` here is the provider-side passthrough rule.

### 5.1 `index_dailybasic` → `index_price_bar` (line 946)

- **canonical_dataset**: `index_price_bar`
- **source_interface_id**: `index_dailybasic`
- **field_mapping**: `(ts_code → index_id, trade_date → trade_date)`
- **source primary_key**: `(ts_code, trade_date)` ; **canonical primary_key**: `(index_id, trade_date, frequency)` — **GAP: candidate mapping does not project `frequency`** (canonical PK requires it; promotion will need a default or projected value)
- **date_policy**: trade_date
- **unit_policy**: index valuation and turnover metrics
- **adjustment_policy**: raw index metrics
- **update_policy**: daily refresh
- **late_arriving_policy**: n/a (per `update_policy`)
- **null_policy**: Provider nulls pass through as canonical nulls with source lineage.
- **coverage**: CN_A indices
- **CSV cross-check**: `access_status=available`, `completeness_status=未见明显遗漏`, `level1=指数专题`, `level2=大盘指数每日指标`

### 5.2 `margin` → `market_leverage_daily` (line 958)

- **canonical_dataset**: `market_leverage_daily`
- **source_interface_id**: `margin`
- **field_mapping**: `(trade_date → trade_date)` — **GAP: no `market` mapping** (canonical PK is `(market, trade_date)`; promotion will need a constant or derived `market` value)
- **source primary_key**: `(trade_date,)` ; **canonical primary_key**: `(market, trade_date)`
- **date_policy**: trade_date
- **unit_policy**: reported financing and lending currency amounts
- **adjustment_policy**: reported values; no market adjustment
- **update_policy**: daily refresh
- **late_arriving_policy**: n/a (per `update_policy`)
- **null_policy**: Provider nulls pass through as canonical nulls with source lineage.
- **coverage**: CN_A margin market
- **CSV cross-check**: `access_status=available`, `completeness_status=未见明显遗漏`, `level1=股票数据`, `level2=两融及转融通`

### 5.3 `margin_detail` → `security_leverage_detail` (line 970)

- **canonical_dataset**: `security_leverage_detail`
- **source_interface_id**: `margin_detail`
- **field_mapping**: `(ts_code → security_id, trade_date → trade_date)`
- **source primary_key**: `(ts_code, trade_date)` ; **canonical primary_key**: `(security_id, trade_date)`
- **date_policy**: trade_date
- **unit_policy**: reported financing and lending currency amounts
- **adjustment_policy**: reported values; no market adjustment
- **update_policy**: daily refresh
- **late_arriving_policy**: n/a (per `update_policy`)
- **null_policy**: Provider nulls pass through as canonical nulls with source lineage.
- **coverage**: CN_A margin securities
- **CSV cross-check**: `access_status=available`, `completeness_status=未见明显遗漏`, `level1=股票数据`, `level2=两融及转融通`

### 5.4 `pledge_stat` → `event_timeline` (loop at line 982; pair line 996)

- **canonical_dataset**: `event_timeline`
- **source_interface_id**: `pledge_stat`
- **field_mapping**: `(ts_code → entity_id)` — **GAP: candidate does not project `event_type`, `event_date`, or `event_key`** (all required by canonical PK `(event_type, entity_id, event_date, event_key)`)
- **source primary_key**: `(ts_code, end_date)` ; **canonical primary_key**: `(event_type, entity_id, event_date, event_key)`
- **date_policy**: event or announcement date
- **unit_policy**: event text/date/amount fields
- **adjustment_policy**: not applicable
- **update_policy**: event-time with late corrections
- **late_arriving_policy**: late corrections accepted (derived from `update_policy`)
- **null_policy**: Provider nulls pass through as canonical nulls with source lineage.
- **coverage**: CN_A
- **CSV cross-check**: `access_status=available`, `completeness_status=未见明显遗漏`, `level1=股票数据`, `level2=参考数据`

### 5.5 `pledge_detail` → `event_timeline` (loop at line 982; pair line 997)

- **canonical_dataset**: `event_timeline`
- **source_interface_id**: `pledge_detail`
- **field_mapping**: `(ts_code → entity_id)` — same gap as 5.4
- **source primary_key**: `(ts_code, ann_date)` ; **canonical primary_key**: `(event_type, entity_id, event_date, event_key)`
- **date_policy / unit_policy / adjustment_policy / update_policy / null_policy / coverage**: identical to 5.4 (shared loop)
- **late_arriving_policy**: late corrections accepted (derived from `update_policy`)
- **CSV cross-check**: `access_status=available`, `completeness_status=未见明显遗漏`, `level1=股票数据`, `level2=参考数据`

### 5.6 `repurchase` → `event_timeline` (loop pair line 998)

- **canonical_dataset**: `event_timeline`
- **source_interface_id**: `repurchase`
- **field_mapping**: `(ts_code → entity_id)` — same gap as 5.4
- **source primary_key**: `(ts_code, ann_date)` ; **canonical primary_key**: `(event_type, entity_id, event_date, event_key)`
- **policies**: identical to 5.4 (shared loop)
- **late_arriving_policy**: late corrections accepted (derived from `update_policy`)
- **CSV cross-check**: `access_status=available`, `completeness_status=未见明显遗漏`, `level1=股票数据`, `level2=参考数据`

### 5.7 `stk_holdertrade` → `event_timeline` (loop pair line 999)

- **canonical_dataset**: `event_timeline`
- **source_interface_id**: `stk_holdertrade`
- **field_mapping**: `(ts_code → entity_id)` — same gap as 5.4
- **source primary_key**: `(ts_code, ann_date)` ; **canonical primary_key**: `(event_type, entity_id, event_date, event_key)`
- **policies**: identical to 5.4 (shared loop)
- **late_arriving_policy**: late corrections accepted (derived from `update_policy`)
- **CSV cross-check**: `access_status=available`, `completeness_status=未见明显遗漏`, `level1=股票数据`, `level2=参考数据`

### 5.8 `limit_list_ths` → `event_timeline` (loop pair line 1000)

- **canonical_dataset**: `event_timeline`
- **source_interface_id**: `limit_list_ths`
- **field_mapping**: `(ts_code → entity_id)` — same gap as 5.4
- **source primary_key**: `(trade_date, ts_code)` ; **canonical primary_key**: `(event_type, entity_id, event_date, event_key)`
- **policies**: identical to 5.4 (shared loop)
- **late_arriving_policy**: late corrections accepted (derived from `update_policy`)
- **CSV cross-check**: `access_status=available`, `completeness_status=未见明显遗漏`, `level1=股票数据`, `level2=打板专题数据`

### 5.9 `limit_list_d` → `event_timeline` (loop pair line 1001)

- **canonical_dataset**: `event_timeline`
- **source_interface_id**: `limit_list_d`
- **field_mapping**: `(ts_code → entity_id)` — same gap as 5.4
- **source primary_key**: `(trade_date, ts_code)` ; **canonical primary_key**: `(event_type, entity_id, event_date, event_key)`
- **policies**: identical to 5.4 (shared loop)
- **late_arriving_policy**: late corrections accepted (derived from `update_policy`)
- **CSV cross-check**: `access_status=available`, `completeness_status=未见明显遗漏`, `level1=股票数据`, `level2=打板专题数据`

### 5.10 `hm_detail` → `event_timeline` (loop pair line 1002)

- **canonical_dataset**: `event_timeline`
- **source_interface_id**: `hm_detail`
- **field_mapping**: `(ts_code → entity_id)` — same gap as 5.4
- **source primary_key**: `(trade_date, ts_code)` ; **canonical primary_key**: `(event_type, entity_id, event_date, event_key)`
- **policies**: identical to 5.4 (shared loop)
- **late_arriving_policy**: late corrections accepted (derived from `update_policy`)
- **CSV cross-check**: `access_status=available`, `completeness_status=未见明显遗漏`, `level1=股票数据`, `level2=打板专题数据`

### 5.11 `stk_surv` → `event_timeline` (loop pair line 1003)

- **canonical_dataset**: `event_timeline`
- **source_interface_id**: `stk_surv`
- **field_mapping**: `(ts_code → entity_id)` — same gap as 5.4
- **source primary_key**: `(ts_code, ann_date)` ; **canonical primary_key**: `(event_type, entity_id, event_date, event_key)`
- **policies**: identical to 5.4 (shared loop)
- **late_arriving_policy**: late corrections accepted (derived from `update_policy`)
- **CSV cross-check**: `access_status=available`, `completeness_status=未见明显遗漏`, `level1=股票数据`, `level2=特色数据`

### 5.12 `express` → `financial_forecast_event` (line 1006)

- **canonical_dataset**: `financial_forecast_event`
- **source_interface_id**: `express`
- **field_mapping**: `(ts_code → security_id, ann_date → announcement_date, end_date → report_period)` — **GAP: candidate does not project `forecast_type`** (required by canonical PK; promotion will need a constant such as `"express"` or a derivation)
- **source primary_key**: `(ts_code, ann_date, end_date)` ; **canonical primary_key**: `(security_id, announcement_date, report_period, forecast_type)`
- **date_policy**: announcement date plus report period
- **unit_policy**: reported express financial amounts
- **adjustment_policy**: reported values; no market adjustment
- **update_policy**: event-time with version retention
- **late_arriving_policy**: not specified (`update_policy` mentions version retention, not late-arriving)
- **null_policy**: Provider nulls pass through as canonical nulls with source lineage.
- **coverage**: CN_A
- **CSV cross-check**: `access_status=available`, `completeness_status=未见明显遗漏`, `level1=股票数据`, `level2=财务数据`

### 5.13 `fina_mainbz` → `business_segment_exposure` (line 1018)

- **canonical_dataset**: `business_segment_exposure`
- **source_interface_id**: `fina_mainbz`
- **field_mapping**: `(ts_code → security_id, end_date → report_period, bz_item → segment_name)`
- **source primary_key**: `(ts_code, end_date, bz_item)` ; **canonical primary_key**: `(security_id, report_period, segment_name)`
- **date_policy**: report period
- **unit_policy**: reported currency and percent values
- **adjustment_policy**: reported values; no market adjustment
- **update_policy**: quarterly/annual late-arriving updates
- **late_arriving_policy**: late-arriving updates accepted (per `update_policy`)
- **null_policy**: Provider nulls pass through as canonical nulls with source lineage.
- **coverage**: CN_A
- **CSV cross-check**: `access_status=available`, `completeness_status=未见明显遗漏`, `level1=股票数据`, `level2=财务数据`

### 5.14 Candidate batch summary

- **All 13 candidates have `access_status=available` and `completeness_status=未见明显遗漏`** in the CSV inventory snapshot — i.e., none is blocked at the provider-availability layer.
- **8 of 13 candidates target `event_timeline`** (a high-cardinality dataset) and share the
  same minimal `(ts_code → entity_id)` projection — none of them currently project the
  remaining canonical PK columns `event_type`, `event_date`, or `event_key`. Promotion
  needs a per-source rule that supplies `event_type`, picks `event_date` (vs `ann_date`),
  and computes `event_key`.
- **Other PK gaps** (5.1, 5.2, 5.12) require constant/derived values for fields not in the
  source projection.
- **No candidate is yet wired through the canonical writer or Iceberg DDL** (per hard rule
  this audit makes no such change).

## 6. Unpromoted (107 generic-unpromoted CSV interfaces) — high-level summary

Computed by intersecting the 138 CSV rows with the union of
`PROVIDER_MAPPINGS.source_interface_id` and
`PROMOTION_CANDIDATE_MAPPINGS.source_interface_id`. All 107 unpromoted entries have
`access_status=available` and `completeness_status=未见明显遗漏` in the current CSV.

| level1 (CSV `level1`) | count | notable level2 categories |
|---|---|---|
| 股票数据 (stocks) | 38 | 打板专题数据 (14), 基础数据 (7), 特色数据 (6), 资金流向数据 (6), 行情数据 (3), 两融及转融通 (2) |
| 宏观经济 (macro) | 17 | 国内宏观 (12), 国际宏观 (5) |
| 债券专题 (bonds) | 11 | 可转债行情/基础信息/技术因子/票面利率/赎回信息, 大宗交易/交易明细, 债券回购日行情, 全球财经事件, 柜台流通式债券报价(2) |
| 指数专题 (indices) | 10 | 中信/申万行业成分及指数行情, 国际主要指数, 指数周/月线行情, 指数技术面因子, 沪深/深圳市场每日交易统计 |
| 公募基金 (mutual funds) | 5 | 基金净值, 基金分红, 基金列表, 基金管理人, 基金经理 |
| 期货数据 (futures) | 5 | 交易日历, 合约信息, 日线行情, 主力与连续合约, 主要品种交易周报 |
| 港股数据 (HK stocks) | 5 | 交易日历, 基础信息, 利润表, 资产负债表, 现金流量表 |
| 美股数据 (US stocks) | 5 | 交易日历, 基础信息, 利润表, 资产负债表, 现金流量表 |
| ETF专题 (ETF) | 4 | 基本信息, 日线行情, 份额规模, 基准指数 |
| 大模型语料专题数据 (LLM corpus) | 2 | 上证 e 互动, 深证易互动 |
| 现货数据 (spot) | 2 | 上海黄金基础信息, 上海黄金现货日行情 |
| 外汇数据 (forex) | 2 | 外汇基础信息(海外), 外汇日线行情 |
| 期权数据 (options) | 1 | 期权合约信息 |

**Total**: 107. **Per C6 hard rule** — this report does NOT propose individual promotion
of any of these 107 interfaces. The above is descriptive inventory only.

## 7. Hard rule restated

**This audit covers PROMOTION READINESS only.** Specifically and explicitly:

- No production fetch is enabled or scheduled by this report.
- No canonical-writer (`canonical_writer.py`) field/required-columns change is proposed.
- No Iceberg DDL change (`ddl/iceberg_tables.py`) is proposed.
- No source code in `data-platform/src/data_platform/provider_catalog/` was modified.
- The 13 candidate mappings remain **candidate** (`status="candidate"`); none is upgraded
  to `promoted` by this report.
- Tushare remains a `provider=tushare` source adapter only. No alternate provider was
  added.

## 8. Findings tally

- **CONFIRMED** (5):
  1. CSV inventory = 138 rows / 15 columns (validation §1.1).
  2. `tests/provider_catalog` PASS, 10/10 (validation §1.2).
  3. Status labels in use are exactly `promoted` / `legacy_typed_not_in_catalog` / `candidate` (validation §1.3, registry.py:443/791/828/841/884/908/922/949/961/973/986/1009/1021).
  4. Counts: 17 canonical / 28 promoted / 13 candidate / 107 generic-unpromoted (§3, derived live).
  5. All 13 candidates re-derived with full policy + CSV cross-check (§5.1–5.13); all show CSV `access=available` and `completeness=未见明显遗漏`.
- **PARTIAL** (3):
  1. The candidate `field_mapping` for **8 event_timeline sources** (5.4–5.11) does not project `event_type`/`event_date`/`event_key` — promotion blocked until the per-source rule is defined. Read directly from registry.py:984–987 (loop body).
  2. Candidate 5.1 (`index_dailybasic`) does not project canonical `frequency`; candidate 5.2 (`margin`) does not project canonical `market`; candidate 5.12 (`express`) does not project canonical `forecast_type`. Promotion blocked until those derivations are specified. (registry.py:950, 962, 1010.)
  3. The 10 `legacy_typed_not_in_catalog` mappings (§4.2) reference doc-api ids absent from the current CSV — these are typed in code but cannot be cross-validated against the current CSV inventory.
- **INFERRED** (2):
  1. The "candidate-equivalent" status label is exactly `"candidate"` (string literal) — INFERRED from the absence of any other label in `PROMOTION_CANDIDATE_MAPPINGS` and from `MappingStatus` literal usage; confirmed by `_mapping(... status="candidate", ...)` invocations.
  2. `late_arriving_policy` is not a separate field on `ProviderDatasetMapping`; the value reported per candidate is INFERRED from the `update_policy` text where it mentions "late corrections" / "late-arriving" (registry.py:155–199 — dataclass declaration; per-candidate `update_policy` strings in §5).

## 9. Outstanding risks

- **Per-source `event_timeline` derivation rule is undefined** for 8 of 13 candidates; without it the candidate batch cannot be promoted because canonical PK is incomplete.
- **No CSV row exists for the 10 `legacy_typed_not_in_catalog` mappings** (`adj_factor`, `index_daily`, `index_weight`, `index_member`, `anns`, `suspend_d`, `income`, `balancesheet`, `cashflow`, `fina_indicator`); these mappings are valid in code but unverifiable against this CSV snapshot. Consumers relying on these (financials, adjustment factor, index daily/weights) must be prepared for an inventory refresh.
- **Pre-existing dirty files** in `data-platform` (`src/data_platform/raw/writer.py`, `tests/raw/test_writer.py`) were not touched by this audit but represent uncommitted work whose state should be reconciled before any C6 follow-up promotion work.
- **The "13 candidate" count is exact today** (registry.py is at HEAD `330f6b4`). Any subsequent registry edit will invalidate this count; per re-derivation rule the count must be re-checked at promotion time.
- **All 107 unpromoted interfaces show `access=available`** in the CSV; promotion is gated by canonical-dataset design and downstream contracts, not by provider availability.

## 10. Per-task handoff block

```
Task: C6
Repo(s): data-platform + assembly
Output report: /Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/p1-provider-neutral-canonical-promotion-readiness-20260428.md
Validation commands:
  1) wc -l /Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/provider_catalog/tushare_available_interfaces.csv
  2) cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -p no:cacheprovider -q tests/provider_catalog 2>&1 | tail -10
  3) cd /Users/fanjie/Desktop/Cowork/project-ult && rg -n 'status[[:space:]]*=' data-platform/src/data_platform/provider_catalog/registry.py | head -200
  4) cd /Users/fanjie/Desktop/Cowork/project-ult && rg -n 'canonical_dataset[[:space:]]*=' data-platform/src/data_platform/provider_catalog/registry.py | wc -l
Validation results:
  1) 139 lines (1 header + 138 data rows) — PASS (matches expected 138 inventory)
  2) 10 tests passed in tests/provider_catalog — PASS
  3) 17 hits; status labels in use: promoted / legacy_typed_not_in_catalog / candidate (no `promotion_candidate` variant) — INFORMATIONAL
  4) 3 hits (only literal `canonical_dataset =` form; positional usage in `_mapping()` not matched). Authoritative count via len(CANONICAL_DATASETS) == 17 — INFORMATIONAL
Per-subrepo git state:
  data-platform: rev-parse HEAD = 330f6b4d82a96d36c8fd150cc1a0a432d7c6cb9c; status =  M src/data_platform/raw/writer.py /  M tests/raw/test_writer.py (pre-existing, NOT touched by this audit); push = not pushed; interpreter = data-platform/.venv/bin/python with PYTHONPATH=src
  assembly:      rev-parse HEAD = a7f19c5994f807b2cf32eb2f45ef48f6fe23095f; status = ?? reports/stabilization/frontend-raw-route-alignment-fix-20260428.md /  ?? reports/stabilization/production-daily-cycle-gap-audit-20260428.md /  ?? reports/stabilization/project-ult-v5-0-1-supervisor-review-20260428.md /  ?? reports/stabilization/raw-manifest-source-interface-hardening-20260428.md (this report adds one more); push = not pushed
Dirty files: data-platform/src/data_platform/raw/writer.py (pre-existing, unrelated); data-platform/tests/raw/test_writer.py (pre-existing, unrelated); assembly/reports/stabilization/p1-provider-neutral-canonical-promotion-readiness-20260428.md (this report, untracked)
Findings: 5 CONFIRMED, 3 PARTIAL, 2 INFERRED
Outstanding risks:
  - Per-source `event_timeline` derivation rule undefined for 8 of 13 candidates (PK columns event_type/event_date/event_key not projected).
  - 3 other candidates (index_dailybasic, margin, express) miss a canonical PK column each (frequency / market / forecast_type).
  - 10 `legacy_typed_not_in_catalog` mappings reference doc-api ids absent from the current CSV; cross-validation impossible against this CSV snapshot.
  - Pre-existing dirty data-platform files unrelated to this audit; reconcile before any promotion follow-up.
  - 13-candidate count is current as of registry HEAD 330f6b4; must be re-derived at promotion time.
Declaration: I did not mark any PARTIAL or PREFLIGHT finding as PASS. I did not commit any forbidden files. Tushare remains a provider=tushare adapter only. I did not run `git init`. I did not push without approval. No production fetch was enabled.
```
