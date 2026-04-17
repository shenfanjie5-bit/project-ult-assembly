# Service Bundles

This directory stores YAML files that validate as `ServiceBundleManifest`.

Required schema fields:

- `bundle_name`
- `services`
- `startup_order`
- `health_checks`
- `required_profiles`
- `optional`
- `shutdown_order`

Each service entry uses:

- `name`
- `image_or_cmd`
- `health_probe`
- `env` (optional, defaults to an empty mapping)

Stage 0 freezes the schema and directory shape only. Real service bundle
manifests are intentionally out of scope for this issue.
