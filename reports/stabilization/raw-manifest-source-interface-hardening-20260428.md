# Raw Manifest Source Interface Hardening - 2026-04-28

## Verdict

Status: PASS for scoped Raw manifest v2 source-interface hardening.

This closes the narrow P2 finding that Raw manifest v2 copied
`provider/source_interface_id/doc_api` metadata without validating Tushare
source-interface consistency.

This does not claim full provider-neutral canonical completion, production
daily-cycle proof, or P5 readiness.

## Scope

Changed files:

- `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/src/data_platform/raw/writer.py`
- `/Users/fanjie/Desktop/Cowork/project-ult/data-platform/tests/raw/test_writer.py`

## What Changed

- `RawWriter` now validates Tushare v2 manifest metadata when provider metadata
  is supplied.
- Provider metadata must include `provider`, `source_interface_id`, and
  `doc_api` together.
- For `provider=tushare`, the writer checks
  `source_interface_id` against `TUSHARE_INTERFACE_REGISTRY`.
- The writer rejects:
  - unknown Tushare `source_interface_id`;
  - `doc_api` that does not match the registry row;
  - raw dataset that does not match the registry row.
- The duplicate `doc_api=trade_cal` path now fails closed for
  `trade_cal_futures` writing to stock `raw/tushare/trade_cal`, because that
  inventory-only interface has no production raw dataset mapping.

## Validation

```text
cd /Users/fanjie/Desktop/Cowork/project-ult/data-platform
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  -m pytest -p no:cacheprovider -q \
  tests/raw/test_writer.py tests/provider_catalog/test_provider_catalog.py

result:
32 passed
```

## Findings

- P0: none.
- P1: none for this scoped raw metadata validation.
- P2: none for Raw manifest v2 Tushare source-interface consistency.
- P3: validation is currently Tushare-specific because Tushare is the only
  implemented provider catalog. Future providers need equivalent registries
  before production selection.

## Residual Risk

This does not address the larger canonical physical schema alignment finding:
provider/raw lineage fields still need a separate audit and migration plan for
canonical marts, DDL, current-cycle loader, and formal serving surfaces.
