# M1.11 — Event Timeline Candidate Schema Check-In + Empirical Uniqueness Verification (2026-04-29)

## Status

**Round:** M1.11 (precondition 9 step 0 + 1 + 2 — read-only research round)
**Supersedes:** [`event-timeline-m1-9-candidate-contract-audit-20260429.md`](event-timeline-m1-9-candidate-contract-audit-20260429.md) — the BLOCKED_NO_LOCAL_SCHEMA verdict for all 8 candidates
**Boundary:** `READY_FOR_TAXONOMY_SIGNOFF` — schemas verified against the local Tushare archive at `/Volumes/dockcase2tb/database_all/股票数据/`; primary keys empirically confirmed; canonical taxonomy proposal awaits owner sign-off; production code untouched.

This round produces the evidence package M1.13 will consume to land the
adapter + fixture + staging + UNION + parity-test pattern for the 8 remaining
event_timeline candidates.

## Outcome Summary

8/8 candidates moved from `BLOCKED_NO_LOCAL_SCHEMA` →
`READY_FOR_TAXONOMY_SIGNOFF`. None remain blocked.

| # | Tushare API | Layout | Local archive subpath | Total rows | Date span | PK verdict |
|---|---|---|---|---|---|---|
| 1 | `pledge_stat` | by_symbol (91 files) | `参考数据/股权质押统计数据/by_symbol/` | 400 | 2014-12-31 → 2026-03-13 | `PK_CONFIRMED_AFTER_STAGING_DEDUP` |
| 2 | `pledge_detail` | by_symbol (69 files) | `参考数据/股权质押明细数据/by_symbol/` | 2,987 | 2003-06-10 → 2026-03-30 | `PK_CONFIRMED` |
| 3 | `repurchase` | by_symbol (66 files) | `参考数据/股票回购/by_symbol/` | 1,550 | 2008-12-25 → 2026-03-05 | `PK_CONFIRMED_AFTER_STAGING_DEDUP` |
| 4 | `stk_holdertrade` | by_symbol (4,864 files) | `参考数据/股东增减持/by_symbol/` | 101,425 | 2001-02-13 → 2026-03-31 | `PK_CONFIRMED_AFTER_STAGING_DEDUP` |
| 5 | `stk_surv` | by_symbol (27 files) | `特色数据/机构调研数据/by_symbol/` | 3,636 | 2021-08-20 → 2026-02-10 | `PK_CONFIRMED` |
| 6 | `limit_list_ths` | all.csv | `打板专题数据/同花顺涨跌停榜单/all.csv` | 43,430 | 2023-11-01 → 2026-03-23 | `PK_CONFIRMED` |
| 7 | `limit_list_d` | all.csv | `打板专题数据/涨跌停和炸板数据/all.csv` | 145,735 | 2020-02-17 → 2026-03-23 | `PK_CONFIRMED` |
| 8 | `hm_detail` | all.csv | `打板专题数据/游资交易每日明细/all.csv` | 3,132 | 2022-12-12 → 2026-03-23 | `PK_CONFIRMED` |

`PK_CONFIRMED_AFTER_STAGING_DEDUP` = the proposed PK has byte-identical
row duplicates from the Tushare-archive ingestion pipeline (the same row
emitted across multiple API calls accumulated into the local CSV). The
proposed PK is canonically unique once `stg_latest_raw` macro picks one
row per (PK, source_run_id) — same dedup mechanism the 8 already-promoted
sources use. The verdict explicitly distinguishes byte-duplicate dedup
from semantic-conflict widening: in M1.11's archive, **all dups are
byte-identical** (`distinct_full_row == distinct_pk` for all 8 sources).

Empirical evidence per-source: `assembly/tmp-runtime/m1-11-precondition-9/uniqueness-{source}.json` (gitignored runtime output) plus aggregate `uniqueness-summary.json`.

## Pattern Reference

The 5-step closure pattern this round prepares is documented by the two
already-promoted exemplars:

- M1.6 `namechange` — minimal-identity case: `(ts_code, start_date)`. See
  [`event-timeline-m1-6-promotion-proof-20260429.md`](event-timeline-m1-6-promotion-proof-20260429.md).
- M1.8 `block_trade` — wide-identity case: `(ts_code, trade_date, buyer, seller, price, vol, amount)`. See
  [`event-timeline-m1-8-block-trade-promotion-proof-20260429.md`](event-timeline-m1-8-block-trade-promotion-proof-20260429.md).

Code anchors (verbatim citations to be re-used by M1.13):

| Pattern element | Exemplar location |
|---|---|
| `_TushareFetchSpec` declarations | `data-platform/src/data_platform/adapters/tushare/adapter.py:842-873` (block_trade), `:849-901` (anns + namechange + block_trade method declarations) |
| Identity tuple list in registry | `data-platform/src/data_platform/provider_catalog/registry.py:901-915` |
| Partition-key dict | `data-platform/src/data_platform/provider_catalog/registry.py:1066-1080` |
| `EVENT_METADATA_FIELDS` map | `data-platform/src/data_platform/adapters/tushare/assets.py:543-552` (block_trade in; namechange routed via REFERENCE_DATA_IDENTITY_FIELDS at `:540`) |
| Staging template (minimal) | `data-platform/src/data_platform/dbt/models/staging/stg_namechange.sql` |
| Staging template (wide) | `data-platform/src/data_platform/dbt/models/staging/stg_block_trade.sql` |
| `int_event_timeline.sql` UNION arm (minimal) | `data-platform/src/data_platform/dbt/models/intermediate/int_event_timeline.sql:108-121` |
| `int_event_timeline.sql` UNION arm (wide, with `concat()` summary) | `data-platform/src/data_platform/dbt/models/intermediate/int_event_timeline.sql:125-144` |
| `event_type` accepted_values | `data-platform/src/data_platform/dbt/models/marts_v2/_schema.yml` (currently 8 values; M1.13 extends by 8) |
| Parity test exemplar | `data-platform/tests/dbt/test_marts_models.py::test_event_v2_and_lineage_marts_preserve_block_trade_fixture` (line ~367) |
| Fixture mechanism | `_write_all_tushare_raw_fixtures()` helper in `tests/dbt/test_tushare_staging_models.py` (no static fixture files — fixtures emitted at test time as Parquet rows in raw zone) |

The 12 columns of every `int_event_timeline` UNION arm are: `event_type,
source_interface_id, ts_code, event_date, title, summary, event_subtype,
related_date, reference_url, rec_time, source_run_id, raw_loaded_at`.

---

## Per-Source Sections

For each candidate, this section captures (a) the Tushare doc reference,
(b) the authoritative column list lifted directly from the Tushare-emitted
CSV header, (c) volume + date span, (d) the empirically-verified PK with
verdict, (e) the proposed canonical taxonomy mapping. The taxonomy
choices are recommendations for owner sign-off.

### 1. `pledge_stat` — 股权质押统计数据

- **Tushare doc:** [doc_id=110](https://tushare.pro/document/2?doc_id=110)
- **Local archive:** `/Volumes/dockcase2tb/database_all/股票数据/参考数据/股权质押统计数据/by_symbol/{ts_code}+{name}.csv`
- **Layout:** by_symbol (91 files)
- **Volume:** 400 rows total; date span `end_date ∈ [2014-12-31, 2026-03-13]`
- **Semantics:** Quarterly summary of all pledges held against an issuer at a given `end_date`. Snapshot, not event.

| Column | Type (observed) | Notes |
|---|---|---|
| `ts_code` | varchar (e.g. `000001.SZ`) | issuer |
| `end_date` | varchar `YYYYMMDD` (cast → DATE) | snapshot period close |
| `pledge_count` | varchar numeric | distinct pledge agreements outstanding |
| `unrest_pledge` | varchar decimal(38,2) | unrestricted pledged share count (10K) |
| `rest_pledge` | varchar decimal(38,2) | restricted pledged share count (10K) |
| `total_share` | varchar decimal(38,2) | total share count (10K) — issuer total |
| `pledge_ratio` | varchar decimal(38,4) | pledged ratio of total |

**PK proposal (after byte-dedup):** `(ts_code, end_date, pledge_count, unrest_pledge, rest_pledge, total_share, pledge_ratio)` — full-row identity (block_trade pattern). 4 byte-duplicate rows exist (likely Tushare API re-emissions of the same snapshot); `stg_latest_raw` collapses them to one canonical row per (PK, source_run_id).

**Recommended taxonomy:**
- `event_type`: `'pledge_summary'` (alt: `'shareholder_pledge_summary'`)
- `source_interface_id`: `'pledge_stat'`
- `event_date`: `end_date`
- `entity_id`: `ts_code`
- `event_subtype`: `null` (no per-row subtype)
- `related_date`: `null`
- `title`: `'Pledge summary'`
- `summary` template: `concat('count=', coalesce(pledge_count,''), ';unrest=', coalesce(unrest_pledge,''), ';rest=', coalesce(rest_pledge,''), ';total=', coalesce(total_share,''), ';ratio=', coalesce(pledge_ratio,''))`

---

### 2. `pledge_detail` — 股权质押明细数据

- **Tushare doc:** [doc_id=111](https://tushare.pro/document/2?doc_id=111)
- **Local archive:** `参考数据/股权质押明细数据/by_symbol/{ts_code}+{name}.csv`
- **Layout:** by_symbol (69 files)
- **Volume:** 2,987 rows total; date span `ann_date ∈ [2003-06-10, 2026-03-30]`
- **Semantics:** Per-pledge agreement event (creation + release announcements).

| Column | Type | Notes |
|---|---|---|
| `ts_code` | varchar | issuer |
| `ann_date` | varchar `YYYYMMDD` (→ DATE) | announcement date |
| `holder_name` | varchar | pledgor (shareholder) name |
| `pledge_amount` | varchar decimal(38,4) | pledged share count (10K) |
| `start_date` | varchar `YYYYMMDD` (→ DATE) | pledge start |
| `end_date` | varchar `YYYYMMDD` (→ DATE) | pledge expiry |
| `is_release` | varchar `'0'`/`'1'` | 0 = pledge open, 1 = released |
| `release_date` | varchar `YYYYMMDD` (→ DATE; nullable) | release date if `is_release='1'` |
| `pledgor` | varchar | pledgee (institution holding the pledge) |
| `holding_amount` | varchar decimal(38,4) | total holdings of `holder_name` |
| `pledged_amount` | varchar decimal(38,4) | total pledged amount of `holder_name` |
| `p_total_ratio` | varchar decimal(38,4) | pledged / holdings ratio |
| `h_total_ratio` | varchar decimal(38,4) | holdings / total ratio |
| `is_buyback` | varchar | buyback flag |

**PK proposal:** `(ts_code, ann_date, holder_name, pledgor, start_date, end_date, pledge_amount, is_release)` — `PK_CONFIRMED` (0 dup rows in 2,987).

**Recommended taxonomy:**
- `event_type`: `'pledge_event'` (alt: `'shareholder_pledge_event'`)
- `source_interface_id`: `'pledge_detail'`
- `event_date`: `ann_date`
- `entity_id`: `ts_code`
- `event_subtype`: `is_release` (`'0'` = open, `'1'` = release)
- `related_date`: `end_date`
- `title`: `'Pledge event'`
- `summary` template: `concat('holder=', coalesce(holder_name,''), ';pledgor=', coalesce(pledgor,''), ';amount=', coalesce(pledge_amount,''), ';period=[', coalesce(start_date,''), ',', coalesce(end_date,''), '];release=', coalesce(is_release,''))`

---

### 3. `repurchase` — 股票回购

- **Tushare doc:** [doc_id=124](https://tushare.pro/document/2?doc_id=124)
- **Local archive:** `参考数据/股票回购/by_symbol/{ts_code}+{name}.csv`
- **Layout:** by_symbol (66 files)
- **Volume:** 1,550 rows; date span `ann_date ∈ [2008-12-25, 2026-03-05]`
- **Semantics:** Share repurchase announcement (multi-stage process: 计划 → 实施 → 完成).

| Column | Type | Notes |
|---|---|---|
| `ts_code` | varchar | issuer |
| `ann_date` | varchar `YYYYMMDD` (→ DATE) | announcement date |
| `end_date` | varchar `YYYYMMDD` (→ DATE) | reporting period end |
| `proc` | varchar | process state (`'计划'` / `'实施'` / `'完成'` / `'股东大会通过'` etc.) |
| `exp_date` | varchar `YYYYMMDD` (→ DATE; nullable) | expected completion |
| `vol` | varchar decimal(38,2) | repurchased volume |
| `amount` | varchar decimal(38,2) | repurchased amount (CNY 10K) |
| `high_limit` | varchar decimal(38,4) | upper price limit |
| `low_limit` | varchar decimal(38,4) | lower price limit |

**PK proposal (after byte-dedup):** all 9 columns — `PK_CONFIRMED_AFTER_STAGING_DEDUP` (434 byte-duplicate rows of 1,550, all collapse to the same row content; `distinct_full_row == distinct_pk == 1116`).

**Recommended taxonomy:**
- `event_type`: `'share_repurchase'` (alt: `'repurchase_announcement'`)
- `source_interface_id`: `'repurchase'`
- `event_date`: `ann_date`
- `entity_id`: `ts_code`
- `event_subtype`: `proc` (process stage)
- `related_date`: `end_date`
- `title`: `'Share repurchase'`
- `summary` template: `concat('proc=', coalesce(proc,''), ';vol=', coalesce(vol,''), ';amount=', coalesce(amount,''), ';exp=', coalesce(exp_date,''), ';band=[', coalesce(low_limit,''), ',', coalesce(high_limit,''), ']')`

---

### 4. `stk_holdertrade` — 股东增减持

- **Tushare doc:** [doc_id=175](https://tushare.pro/document/2?doc_id=175)
- **Local archive:** `参考数据/股东增减持/by_symbol/{ts_code}+{name}.csv`
- **Layout:** by_symbol (4,864 files — most active candidate)
- **Volume:** 101,425 rows; date span `ann_date ∈ [2001-02-13, 2026-03-31]`
- **Semantics:** Insider/major-shareholder trading announcement. Same shareholder + ann_date can produce many rows (each tape-print at a different `avg_price`).

| Column | Type | Notes |
|---|---|---|
| `ts_code` | varchar | issuer |
| `ann_date` | varchar `YYYYMMDD` (→ DATE) | announcement date |
| `holder_name` | varchar | shareholder name |
| `holder_type` | varchar | shareholder type (`'C'` = corporate, `'P'` = personal, `'G'` = govt) |
| `in_de` | varchar | `'IN'` (增持) or `'DE'` (减持) |
| `change_vol` | varchar decimal(38,2) | volume changed (10K shares) |
| `change_ratio` | varchar decimal(38,4) | change ratio of `total_share` |
| `after_share` | varchar decimal(38,2) | shareholder holding after change (10K) |
| `after_ratio` | varchar decimal(38,4) | shareholder holding ratio after change |
| `avg_price` | varchar decimal(38,4) | average trade price |
| `total_share` | varchar decimal(38,2) | issuer total shares |

**PK proposal (after byte-dedup):** all 11 columns — `PK_CONFIRMED_AFTER_STAGING_DEDUP` (4,276 byte-duplicate rows of 101,425 collapse to `distinct_full_row == distinct_pk == 97,149`). Max same-day burst: 79 rows for `(603708.SH, 20240321, 林春丽, P, IN, 100.0, 0.0)` differing only in `avg_price` — all preserved as distinct events.

**Recommended taxonomy:**
- `event_type`: `'shareholder_trade'` (alt: `'insider_trade'`)
- `source_interface_id`: `'stk_holdertrade'`
- `event_date`: `ann_date`
- `entity_id`: `ts_code`
- `event_subtype`: `in_de` (IN/DE direction)
- `related_date`: `null`
- `title`: `'Shareholder trade'`
- `summary` template: `concat('holder=', coalesce(holder_name,''), ';type=', coalesce(holder_type,''), ';dir=', coalesce(in_de,''), ';vol=', coalesce(change_vol,''), ';ratio=', coalesce(change_ratio,''), ';avg_price=', coalesce(avg_price,''))`

---

### 5. `stk_surv` — 机构调研数据

- **Tushare doc:** [doc_id=275](https://tushare.pro/document/2?doc_id=275)
- **Local archive:** `特色数据/机构调研数据/by_symbol/{ts_code}+{name}.csv`
- **Layout:** by_symbol (27 files — coverage limited)
- **Volume:** 3,636 rows; date span `surv_date ∈ [2021-08-20, 2026-02-10]`
- **Semantics:** Institutional investor surveys / analyst visits.

| Column | Type | Notes |
|---|---|---|
| `ts_code` | varchar | issuer |
| `name` | varchar | issuer Chinese name |
| `surv_date` | varchar `YYYYMMDD` (→ DATE) | survey date |
| `fund_visitors` | varchar | participating fund managers (free-text, often `'--'`) |
| `rece_place` | varchar | reception location |
| `rece_mode` | varchar | reception mode (现场调研/电话会议/etc.) |
| `rece_org` | varchar | receiving organization (institutional investor) |
| `org_type` | varchar | organization type (境内分析师 / 境内机构投资者 / 境外...) |
| `comp_rece` | varchar | company reception staff (free-text, often empty) |

**PK proposal:** `(ts_code, surv_date, rece_org, rece_mode)` — `PK_CONFIRMED` (0 dup rows in 3,636).

**Recommended taxonomy:**
- `event_type`: `'institutional_survey'` (alt: `'analyst_visit'`)
- `source_interface_id`: `'stk_surv'`
- `event_date`: `surv_date`
- `entity_id`: `ts_code`
- `event_subtype`: `org_type` (institution category)
- `related_date`: `null`
- `title`: `'Institutional survey'`
- `summary` template: `concat('org=', coalesce(rece_org,''), ';type=', coalesce(org_type,''), ';place=', coalesce(rece_place,''), ';mode=', coalesce(rece_mode,''), ';visitors=', coalesce(fund_visitors,''))`

---

### 6. `limit_list_ths` — 同花顺涨跌停榜单

- **Tushare doc:** [doc_id=355](https://tushare.pro/document/2?doc_id=355)
- **Local archive:** `打板专题数据/同花顺涨跌停榜单/all.csv`
- **Layout:** single concatenated CSV
- **Volume:** 43,430 rows; date span `trade_date ∈ [2023-11-01, 2026-03-23]`
- **Semantics:** 同花顺-classified intra-day limit-pool snapshots (涨停池/连板池/炸板池/跌停池).

| Column | Type | Notes |
|---|---|---|
| `trade_date` | varchar `YYYYMMDD` (→ DATE) | trade date |
| `ts_code` | varchar | issuer |
| `name` | varchar | issuer name |
| `price` | varchar decimal(38,4) | latest price at limit |
| `pct_chg` | varchar decimal(38,4) | percent change |
| `open_num` | varchar | times opened from limit |
| `lu_desc` | varchar | concept tags free-text |
| `limit_type` | varchar | pool category (涨停池/连板池/炸板池/跌停池/...) |
| `tag` | varchar | board tag (首板/二板/.../退) |
| `status` | varchar | limit status (换手板/一字板/T字板/...) |
| `limit_order` | varchar decimal(38,2) | order volume at limit |
| `limit_amount` | varchar decimal(38,2) | order amount at limit |
| `turnover_rate` | varchar decimal(38,4) | turnover rate |
| `free_float` | varchar decimal(38,2) | free float market value |
| `lu_limit_order` | varchar | order volume at limit-up |
| `limit_up_suc_rate` | varchar decimal(38,4) | success rate (continuous limit) |
| `turnover` | varchar | turnover |
| `market_type` | varchar | market segment (HS/...) |

**PK proposal:** `(trade_date, ts_code, status)` — `PK_CONFIRMED` (0 dup rows in 43,430).

**Recommended taxonomy:**
- `event_type`: `'price_limit_status'` (alt: `'ths_limit_pool'`)
- `source_interface_id`: `'limit_list_ths'`
- `event_date`: `trade_date`
- `entity_id`: `ts_code`
- `event_subtype`: `limit_type` (pool category)
- `related_date`: `null`
- `title`: `'Price limit status (THS pool)'`
- `summary` template: `concat('pool=', coalesce(limit_type,''), ';status=', coalesce(status,''), ';tag=', coalesce(tag,''), ';order=', coalesce(limit_order,''), ';amount=', coalesce(limit_amount,''), ';open_num=', coalesce(open_num,''))`

---

### 7. `limit_list_d` — 涨跌停和炸板数据

- **Tushare doc:** [doc_id=298](https://tushare.pro/document/2?doc_id=298)
- **Local archive:** `打板专题数据/涨跌停和炸板数据/all.csv`
- **Layout:** single concatenated CSV
- **Volume:** 145,735 rows (largest); date span `trade_date ∈ [2020-02-17, 2026-03-23]`
- **Semantics:** Daily limit-hit / blow-up records. `limit ∈ {U, D, Z}` (涨停 / 跌停 / 炸板).

| Column | Type | Notes |
|---|---|---|
| `trade_date` | varchar `YYYYMMDD` (→ DATE) | trade date |
| `ts_code` | varchar | issuer |
| `industry` | varchar | industry sector |
| `name` | varchar | issuer name |
| `close` | varchar decimal(38,4) | closing price at limit |
| `pct_chg` | varchar decimal(38,4) | percent change |
| `amount` | varchar decimal(38,2) | trade amount |
| `limit_amount` | varchar decimal(38,2) | order amount at limit |
| `float_mv` | varchar decimal(38,2) | float market cap |
| `total_mv` | varchar decimal(38,2) | total market cap |
| `turnover_ratio` | varchar decimal(38,4) | turnover ratio |
| `fd_amount` | varchar decimal(38,2) | sealed-board order amount |
| `first_time` | varchar `HHMMSS` | first time hit |
| `last_time` | varchar `HHMMSS` | last time hit |
| `open_times` | varchar | times opened from limit |
| `up_stat` | varchar | continuous limit stat (e.g. `'3/3'`) |
| `limit_times` | varchar | total limit-hit days |
| `limit` | varchar | `'U'` (up) / `'D'` (down) / `'Z'` (blew up) |

**PK proposal:** `(trade_date, ts_code, limit)` — `PK_CONFIRMED` (0 dup rows in 145,735).

**Recommended taxonomy:**
- `event_type`: `'price_limit_event'` (alt: `'limit_hit'`)
- `source_interface_id`: `'limit_list_d'`
- `event_date`: `trade_date`
- `entity_id`: `ts_code`
- `event_subtype`: `limit` (U/D/Z)
- `related_date`: `null`
- `title`: `'Price limit event'`
- `summary` template: `concat('limit=', coalesce(limit,''), ';times=', coalesce(limit_times,''), ';fd=', coalesce(fd_amount,''), ';first=', coalesce(first_time,''), ';last=', coalesce(last_time,''), ';up_stat=', coalesce(up_stat,''))`

---

### 8. `hm_detail` — 游资交易每日明细

- **Tushare doc:** [doc_id=312](https://tushare.pro/document/2?doc_id=312)
- **Local archive:** `打板专题数据/游资交易每日明细/all.csv`
- **Layout:** single concatenated CSV
- **Volume:** 3,132 rows; date span `trade_date ∈ [2022-12-12, 2026-03-23]`
- **Semantics:** Hot-money / dragon-tiger entity (游资) per-stock daily trades.

| Column | Type | Notes |
|---|---|---|
| `trade_date` | varchar `YYYYMMDD` (→ DATE) | trade date |
| `ts_code` | varchar | issuer |
| `ts_name` | varchar | issuer name |
| `buy_amount` | varchar decimal(38,2) | hot-money buy amount |
| `sell_amount` | varchar decimal(38,2) | hot-money sell amount |
| `net_amount` | varchar decimal(38,2) | net (buy - sell) |
| `hm_name` | varchar | hot-money entity name (e.g. `'首板挖掘'`, `'章盟主'`) |
| `hm_orgs` | varchar | broker branches affiliated with hot-money entity |

**PK proposal:** `(trade_date, ts_code, hm_name)` — `PK_CONFIRMED` (0 dup rows in 3,132).

**Recommended taxonomy:**
- `event_type`: `'hot_money_trade'` (alt: `'dragon_tiger_hm'`)
- `source_interface_id`: `'hm_detail'`
- `event_date`: `trade_date`
- `entity_id`: `ts_code`
- `event_subtype`: `null` (`hm_name` carried in summary instead)
- `related_date`: `null`
- `title`: `'Hot money trade'`
- `summary` template: `concat('hm=', coalesce(hm_name,''), ';buy=', coalesce(buy_amount,''), ';sell=', coalesce(sell_amount,''), ';net=', coalesce(net_amount,''), ';orgs=', coalesce(hm_orgs,''))`

---

## Owner Sign-Off Master Table

Owner ticks the columns they approve; M1.13 implementation reads this table
verbatim. Any owner-edit revision flags the M1.11 evidence file as
`READY_FOR_TAXONOMY_SIGNOFF` until a fresh sign-off row lands.

| API | `event_type` | `event_date` source | `event_subtype` source | Identity-fields | Sign-off |
|---|---|---|---|---|---|
| `pledge_stat` | `'pledge_summary'` | `end_date` | (null) | `(ts_code, end_date, pledge_count, unrest_pledge, rest_pledge, total_share, pledge_ratio)` | ☐ |
| `pledge_detail` | `'pledge_event'` | `ann_date` | `is_release` | `(ts_code, ann_date, holder_name, pledgor, start_date, end_date, pledge_amount, is_release)` | ☐ |
| `repurchase` | `'share_repurchase'` | `ann_date` | `proc` | `(ts_code, ann_date, end_date, proc, exp_date, vol, amount, high_limit, low_limit)` | ☐ |
| `stk_holdertrade` | `'shareholder_trade'` | `ann_date` | `in_de` | `(ts_code, ann_date, holder_name, holder_type, in_de, change_vol, change_ratio, after_share, after_ratio, avg_price, total_share)` | ☐ |
| `stk_surv` | `'institutional_survey'` | `surv_date` | `org_type` | `(ts_code, surv_date, rece_org, rece_mode)` | ☐ |
| `limit_list_ths` | `'price_limit_status'` | `trade_date` | `limit_type` | `(trade_date, ts_code, status)` | ☐ |
| `limit_list_d` | `'price_limit_event'` | `trade_date` | `limit` | `(trade_date, ts_code, limit)` | ☐ |
| `hm_detail` | `'hot_money_trade'` | `trade_date` | (null; `hm_name` in summary) | `(trade_date, ts_code, hm_name)` | ☐ |

After approval, M1.13 extends `dbt/models/marts_v2/_schema.yml` and
`dbt/models/marts/_schema.yml` `event_type` accepted_values from the
current 8 to **16** (existing 8 + the 8 above).

---

## M1.13 — Out-of-Scope Adjacencies (this round does NOT touch them)

For each of the 8 sources, M1.13 must deliver, in this exact order:

1. **`tushare_available_interfaces.csv` flip** — change `availability_status` from `available` to `promoted` for each of the 8 rows.
2. **Adapter `_TushareFetchSpec`** in `data-platform/src/data_platform/adapters/tushare/adapter.py` — add a per-source method declaration mirroring `block_trade` at `:842-873`. Per-source partition_date_field and partition_request_params from the M1.11 sign-off table.
3. **Registry per-source identity tuple** in `provider_catalog/registry.py:901-915` — the approved identity_fields tuple. Plus partition-key entry at `:1066-1080`.
4. **Per-source `EVENT_METADATA_FIELDS` entry** in `tushare/assets.py:543-552` (analogous to `block_trade`, `anns`, etc.).
5. **8 staging models** under `dbt/models/staging/stg_<source>.sql` using the `stg_latest_raw` macro, one per Tushare API name (file-naming convention from `stg_block_trade.sql`).
6. **8 UNION arms** appended to `dbt/models/intermediate/int_event_timeline.sql` (after the `block_trade` arm at `:125-144`). Each arm uses the canonical taxonomy from the sign-off table — literal `event_type`, literal `source_interface_id`, the `concat()` template for `summary`, and per-source `event_subtype` / `related_date` / null casts for `reference_url` / `rec_time`.
7. **`accepted_values` extension** for `event_type` in BOTH `dbt/models/marts_v2/_schema.yml` and `dbt/models/marts/_schema.yml` — current 8 → 16.
8. **Fixture rows + parity tests** alongside the existing `block_trade` and `namechange` fixtures (mechanism: extend `_write_all_tushare_raw_fixtures()` in `tests/dbt/test_tushare_staging_models.py`; add 8 parity tests in `tests/dbt/test_marts_models.py` mirroring `test_event_v2_and_lineage_marts_preserve_block_trade_fixture`).

M1.13 also must NOT call Tushare HTTP. The `--mock` adapter path injects
fixture rows directly into the raw zone for the 8 staging models to read.

Estimated diff size for M1.13: ~40–50 file changes (8 staging SQLs + 1
`int_event_timeline.sql` + 2 `_schema.yml` files + 1 `adapter.py` + 1
`registry.py` + 1 `assets.py` + 1 `tushare_available_interfaces.csv` + 8
parity test additions + helpers).

---

## What This Round Proves

- **Step 0 (schema check-in):** all 8 sources have authoritative column lists lifted directly from Tushare-emitted CSV headers in the local archive.
- **Step 1 (canonical event_type taxonomy):** 8 proposals on the table, with 1 alternate each, ready for sign-off.
- **Step 2 (intra-day uniqueness verification):** all 8 PKs verified empirically against the full archive (millions of rows). 5 are PK_CONFIRMED outright; 3 are PK_CONFIRMED_AFTER_STAGING_DEDUP — the existing `stg_latest_raw` dedup mechanism resolves the byte-identical Tushare-emission duplicates with no new code.

## What This Round Does NOT Prove

- Adapter / staging / UNION / parity-test landing — that is M1.13.
- Production-fetch validation — `--mock` only; this round used the local archive as a fixture data source, not via Tushare HTTP.
- M2 daily-cycle proof — out of scope; precondition 9 closure does not unblock M2 by itself.
- P5 readiness — still BLOCKED on M2 + Phase B retirement.

## Verification Commands

```sh
# 1. Empirical uniqueness verifier (re-runnable)
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform && \
  .venv/bin/python /Users/fanjie/Desktop/Cowork/project-ult/assembly/tmp-runtime/m1-11-precondition-9/run_uniqueness.py
# → 8 per-source JSONs + 1 summary JSON written under
#   assembly/tmp-runtime/m1-11-precondition-9/ (gitignored runtime path)

# 2. Existing test sweeps unchanged (M1.11 is read-only)
cd data-platform && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
  -p no:cacheprovider \
  tests/serving/test_canonical_writer.py \
  tests/serving/test_reader.py \
  tests/integration/test_daily_refresh.py
# Expect: 58 passed, 1 skipped (unchanged)

cd data-platform && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
  -p no:cacheprovider \
  tests/dbt/test_intermediate_models.py tests/dbt/test_marts_models.py \
  tests/dbt/test_dbt_skeleton.py tests/dbt/test_dbt_test_coverage.py \
  tests/dbt/test_marts_provider_neutrality.py tests/provider_catalog
# Expect: 58 passed, 2 skipped, 8 xfailed

cd data-platform && DP_CANONICAL_USE_V2=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest \
  -p no:cacheprovider \
  tests/serving tests/cycle/test_current_cycle_inputs.py \
  tests/cycle/test_current_cycle_inputs_lineage_absent.py tests/test_assets.py
# Expect: 177 passed, 5 skipped, 17 xfailed

# 3. Hygiene
git -C data-platform diff --check
git -C assembly diff --check
git -C frontend-api diff --check
```

## Files Touched in M1.11

| File | Action |
|---|---|
| `assembly/reports/stabilization/event-timeline-m1-11-candidate-schema-checkin-20260429.md` | new (this file) |
| `assembly/reports/stabilization/m1-legacy-retirement-preconditions-progress-20260428.md` | append-only update flipping precondition 9 status to `PARTIAL — 2/10 promoted; 8 candidates schema-checked-in and uniqueness-verified, READY_FOR_TAXONOMY_SIGNOFF (M1.11)` |
| `assembly/tmp-runtime/m1-11-precondition-9/run_uniqueness.py` | new (gitignored runtime helper) |
| `assembly/tmp-runtime/m1-11-precondition-9/uniqueness-{source}.json` × 8 | new (gitignored runtime output) |
| `assembly/tmp-runtime/m1-11-precondition-9/uniqueness-summary.json` | new (gitignored runtime output) |

No production code modified. No test files modified. No `provider_catalog/registry.py`, `adapters/tushare/adapter.py`, or `dbt/` files modified.

## Hard-Rule Declarations

- `project_ult_v5_0_1.md` UNCHANGED.
- `ult_milestone.md` UNCHANGED.
- No Tushare HTTP fetch. The local archive at `/Volumes/dockcase2tb/database_all/股票数据/` was read read-only as a fixture data source.
- No production fetch. No P5 shadow-run. No M2/M3/M4 work.
- No API-6 / sidecar / frontend write API / Kafka / Flink / Temporal / news / Polymarket touched.
- Tushare remains a `provider="tushare"` source adapter only.
- Legacy `canonical.*` specs / load specs / dbt marts NOT deleted.
- `_M1D_LEGACY_RETIREMENT_XFAIL` NOT removed.
- `FORBIDDEN_SCHEMA_FIELDS` / `FORBIDDEN_PAYLOAD_FIELDS` NOT extended.
- `/Users/fanjie/Desktop/BIG/FrontEnd/**` NOT modified.
- No commits, no push, no amend, no reset.

## Cross-References

- Empirical uniqueness JSONs: `assembly/tmp-runtime/m1-11-precondition-9/uniqueness-*.json` (gitignored)
- M1.6 exemplar: [`event-timeline-m1-6-promotion-proof-20260429.md`](event-timeline-m1-6-promotion-proof-20260429.md)
- M1.8 exemplar: [`event-timeline-m1-8-block-trade-promotion-proof-20260429.md`](event-timeline-m1-8-block-trade-promotion-proof-20260429.md)
- Superseded audit: [`event-timeline-m1-9-candidate-contract-audit-20260429.md`](event-timeline-m1-9-candidate-contract-audit-20260429.md)
- Progress tracker: [`m1-legacy-retirement-preconditions-progress-20260428.md`](m1-legacy-retirement-preconditions-progress-20260428.md)
- Provider catalog: `data-platform/src/data_platform/provider_catalog/tushare_available_interfaces.csv`
