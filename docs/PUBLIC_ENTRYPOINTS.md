# Public Entrypoints

Assembly integrates modules only through registered public entrypoints. Module
owners must expose public configuration, public health probes, and public hooks
that match the protocols in `assembly.contracts`. Assembly does not import
private module packages, private scripts, or internal implementation details.

## Protocols

### `HealthProbe`

Signature:

```python
def check(self, *, timeout_sec: float) -> HealthResult
```

Responsibility: report whether a module is usable from assembly's perspective.
The probe must return a `HealthResult` with `status` set to one of:

- `healthy`: the required public surface is available.
- `degraded`: an optional component is impaired but the profile can continue.
- `blocked`: a required component is unavailable or unsafe to use.

Timeout convention: the implementation must respect `timeout_sec` and return
before that budget expires. Later health runners may convert timeout exceptions
into `blocked` results for required components.

Error convention: module code may raise an exception for unrecoverable probe
failures. Assembly health execution will convert probe execution failures into
`blocked` unless the component is declared optional by the active profile.

### `SmokeHook`

Signature:

```python
def run(self, *, profile_id: str) -> SmokeResult
```

Responsibility: perform a fast public-boundary validation for one profile. The
hook must not validate private business logic. A failed hook returns
`passed=False` and a `failure_reason`.

### `InitHook`

Signature:

```python
def initialize(self, *, resolved_env: dict[str, str]) -> None
```

Responsibility: initialize module resources from the resolved public
environment. The hook receives only string environment values already resolved
by assembly. It must not read assembly-private state or require unregistered
private inputs.

### `VersionDeclaration`

Signature:

```python
def declare(self) -> VersionInfo
```

Responsibility: declare the module version, current contract version, and the
compatible contract version range. `compatible_contract_range` must use a basic
SemVer range expression such as `>=1.0.0 <2.0.0`.

### `CliEntrypoint`

Signature:

```python
def invoke(self, argv: list[str]) -> int
```

Responsibility: provide a stable public CLI surface for future bootstrap and
orchestration wiring. Phase 0 reserves this protocol only; assembly does not
invoke module CLIs in this issue.

## Registration Template

Module owners register public entrypoints with these fields:

| module_id | kind | reference |
| --- | --- | --- |
| `example-module` | `health_probe` | `example_module.public:health_probe` |
| `example-module` | `smoke_hook` | `example_module.public:smoke_hook` |
| `example-module` | `init_hook` | `example_module.public:init_hook` |
| `example-module` | `version_declaration` | `example_module.public:version_declaration` |
| `example-module` | `cli` | `example_module.public:cli` |

Allowed `kind` values are exactly:

- `health_probe`
- `smoke_hook`
- `init_hook`
- `version_declaration`
- `cli`

## Blocker Path

Assembly does not accept unregistered private entrypoints. If integration needs
a private import, private script, internal database table, or any surface not
declared in the module registry, stop implementation and raise a Blocker for
the module owner to expose a public entrypoint.

Until that public entrypoint is registered, assembly must not work around the
gap by copying module code or calling private implementation details.
