# P1 Tushare 40 API Target-List Decision - 2026-04-27

## Scope

This evidence records the current target-list decision after reviewing the
v5.0.1 blueprint and the code-grounded Tushare adapter/staging inventory. It
does not authorize implementers to guess additional APIs.

## Current Implemented List

`data-platform` currently declares 28 Tushare assets and has matching staging
models:

1. `stock_basic`
2. `daily`
3. `weekly`
4. `monthly`
5. `adj_factor`
6. `daily_basic`
7. `index_basic`
8. `index_daily`
9. `index_weight`
10. `index_member`
11. `index_classify`
12. `trade_cal`
13. `stock_company`
14. `namechange`
15. `anns`
16. `suspend_d`
17. `dividend`
18. `share_float`
19. `stk_holdernumber`
20. `disclosure_date`
21. `income`
22. `balancesheet`
23. `cashflow`
24. `fina_indicator`
25. `stk_limit`
26. `block_trade`
27. `moneyflow`
28. `forecast`

## Decision

- Blueprint target: approximately 40 Tushare APIs and 40 staging dbt models.
- Code-grounded state: 28 declared assets and 28 staging models.
- Remaining count gap: 12 APIs.
- The reviewed v5.0.1 blueprint names the 40-API scale target but does not
  enumerate the missing 12 API names.
- Therefore the missing 12 are a P1 planning gap, not an implementation task
  for this batch. Implementers must not select endpoints by guesswork.

## MVP Classification

| Class | Decision | Notes |
| --- | --- | --- |
| Implemented and downstream required | MVP | The six known downstream gaps were closed in `p1-tushare-mvp-downstream-gap-closure-20260427.md`. |
| Implemented but deferrable downstream | Deferrable | `weekly`, `monthly`, `index_classify`, and `block_trade` already have raw/staging coverage; additional marts can be scoped later from product requirements. |
| Missing APIs 29-40 | Planning gap | Cannot be classified endpoint-by-endpoint until the authoritative target list is named. |

## Dependency And Risk Notes

- The missing 12 may affect update-frequency grouping, dependency ordering,
  and Tushare point/rate limits, but exact dependencies cannot be verified
  without named endpoints.
- Production daily-cycle proof can proceed on the bounded implemented MVP
  slice, but P5 cannot be claimed complete against the v5.0.1 P1 target until
  the 40-API list is formalized or explicitly descoped.
- News and alternative data remain out of scope for this P1 decision.

## Evidence Sources

- Blueprint: `/Users/fanjie/Desktop/Cowork/project-ult/project_ult_v5_0_1.md`
- Prior coverage table:
  `/Users/fanjie/Desktop/Cowork/project-ult/assembly/reports/stabilization/p1-tushare-coverage-table-20260427.md`
- Adapter inventory:
  `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/adapters/tushare/assets.py`
- Staging models:
  `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/dbt/models/staging/`
