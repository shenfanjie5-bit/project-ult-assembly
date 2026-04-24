# Version Lock

Release freeze turns a verified compatibility matrix entry into an auditable
YAML lockfile under `version-lock/`. Startup commands are listed in
[STARTUP_GUIDE.md](STARTUP_GUIDE.md), profile selection is summarized in
[PROFILE_COMPARISON.md](PROFILE_COMPARISON.md), and operational failure modes are
covered in [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Lock Fields

Each generated lockfile is named:

```text
version-lock/<YYYY-MM-DD>-<profile_id>.yaml
version-lock/<YYYY-MM-DD>-<profile_id>+<extra_bundle>[+<extra_bundle>].yaml
```

The default profile row keeps the short filename. Optional-bundle rows append a
stable sorted bundle suffix, for example
`version-lock/2026-04-18-full-dev+minio.yaml`.

The YAML fields are:

- `lock_version`: lockfile schema version for release-freeze artifacts.
- `profile_id`: frozen profile.
- `extra_bundles`: sorted optional bundle names for the frozen matrix row;
  `[]` means the default profile row.
- `matrix_version`: verified compatibility matrix version.
- `contract_version`: contract version declared by the matrix entry.
- `matrix_verified_at`: timestamp from the verified matrix entry.
- `frozen_at`: timestamp when the lockfile was generated.
- `required_tests`: matrix-required test names such as `contract-suite`,
  `smoke`, and `min-cycle-e2e`.
- `modules`: module id, module version, contract version, and integration
  status copied from the registry.
- `supporting_runs`: successful `contract`, `smoke`, and `e2e` run references
  loaded from `reports/contract`, `reports/smoke`, and `reports/e2e`.
- `source_artifacts`: registry and compatibility matrix artifact paths used to
  create the lock.
- `lock_file`: output path written by the freeze command.

## Preconditions

Release freeze does not promote matrix entries. Before freezing, the target
profile must have exactly one non-deprecated matrix entry with
`status: verified`, and that entry must match the modules resolved by
`resolve_for_profile(...)`.

Every module in the matrix `module_set` must have
`integration_status: verified` in `module-registry.yaml`. The required
`contract-suite`, `smoke`, and `min-cycle-e2e` runs must have successful
`IntegrationRunRecord` JSON files under the reports root.

## Command

```bash
PYTHONPATH=src python3 -m assembly.cli.main release-freeze \
  --profile lite-local \
  --registry-root . \
  --profiles-dir profiles \
  --reports-root reports \
  --out version-lock
```

Success prints:

```text
lock=version-lock/2026-04-18-lite-local.yaml profile=lite-local modules=14
```

If a precondition fails, the command exits non-zero and does not create the
lockfile.

## Replay and Audit

To audit a lockfile:

1. Read `source_artifacts` and confirm the registry and matrix files are the
   intended release inputs.
2. Confirm `matrix_verified_at` matches the verified matrix entry.
3. Confirm each `supporting_runs[*].path` points to a successful persisted
   `IntegrationRunRecord`.
4. Re-run `export-registry` to capture the current registry view for comparison.
5. Re-run `release-freeze` for the same profile and date when the source
   artifacts and reports are unchanged; the command overwrites the same path
   with stable field ordering.
