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

Stage 0 includes a minimal `lite-local.yaml` artifact so registry and
compatibility matrix profile references resolve to a loadable profile. Service
bundle details and required environment keys are introduced by the bootstrap
milestone.
