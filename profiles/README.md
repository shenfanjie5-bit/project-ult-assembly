# Profiles

This directory stores YAML files that validate as `EnvironmentProfile`.

Required schema fields:

- `profile_id`
- `mode`
- `enabled_modules`
- `enabled_service_bundles`
- `required_env_keys`
- `optional_env_keys`
- `storage_backends`
- `resource_expectation`
- `max_long_running_daemons`
- `notes`

Stage 0 freezes the schema and directory shape only. Real profile files such as
`lite-local.yaml` are intentionally out of scope for this issue.

