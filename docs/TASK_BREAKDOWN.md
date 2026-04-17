# 项目任务拆解

## 阶段 0：系统级入口冻结

**目标**：冻结 `EnvironmentProfile` 结构、模块公开入口契约与首版 `MODULE_REGISTRY`，为后续 bootstrap / health / smoke / e2e 提供唯一真相层
**前置依赖**：无

### ISSUE-001: 冻结 EnvironmentProfile / ServiceBundle schema 与 profile 目录结构
**labels**: P0, infrastructure, milestone-0

#### 背景与目标
依据 §9.3（EnvironmentProfile、ServiceBundleManifest 对象定义）与 §13.1、§14 的模块边界，阶段 0 必须先把“运行档位”正式对象化，否则 Lite/Full 差异、Lite 4 常驻进程硬约束、Full 可选 bundle 槽位都无法表达。本 Issue 的目标是**只冻结 schema 与文件骨架**（Pydantic 数据模型 + profiles/ 与 bundles/ 目录 + 加载/校验函数），不启动任何服务、不接入 registry、不执行健康检查。它是 §21 阶段 0 唯一退出条件 “profile 结构冻结” 的实现，也是 ISSUE-004/005 在阶段 1 构建 `lite-local` profile 的前提。保持范围收敛可避免越界进入 bootstrap / health，符合 CLAUDE.md “单个 Issue 只覆盖一个总装能力” 约束。

#### 所属模块
- 主写入路径（允许实现）：
  - `src/assembly/profiles/__init__.py`
  - `src/assembly/profiles/schema.py`（`EnvironmentProfile`、`ServiceBundleManifest` 等 Pydantic 模型）
  - `src/assembly/profiles/loader.py`（YAML 加载与 schema 校验）
  - `src/assembly/profiles/errors.py`（profile 相关异常）
  - `profiles/`（存放 profile YAML 的目录，阶段 0 只放 schema 级占位说明 `profiles/README.md`）
  - `bundles/`（存放 service bundle manifest 的目录，同样只放 `bundles/README.md`）
  - `tests/profiles/test_schema.py`、`tests/profiles/test_loader.py`
  - `pyproject.toml`（新增 `pydantic`、`pyyaml`、`pytest` 依赖及 packages 声明）
- 相邻只读 / 集成路径（可查阅，不在本 Issue 修改）：
  - `docs/assembly.project-doc.md`（§9、§14 定义对象字段）
  - `CLAUDE.md`（项目硬约束）
- 越界（严禁本 Issue 修改）：
  - `src/assembly/bootstrap/*`、`src/assembly/health/*`、`src/assembly/registry/*`、`src/assembly/compat/*`、`src/assembly/tests/*`
  - 任何真实 profile YAML 文件（`lite-local.yaml` 等留给 ISSUE-004）
  - `MODULE_REGISTRY.md` / `module-registry.yaml`（归 ISSUE-002）

#### 实现范围
- 脚手架与依赖
  - `pyproject.toml`:新增 `dependencies = ["pydantic>=2.6", "pyyaml>=6.0"]`；`[project.optional-dependencies] dev = ["pytest>=8"]`;`[tool.setuptools.packages.find] where = ["src"]`
  - `src/assembly/__init__.py`:空包标识
  - `src/assembly/profiles/__init__.py`:re-export `EnvironmentProfile`、`ServiceBundleManifest`、`load_profile`、`list_profiles`、`ProfileError`
- Schema 层（`src/assembly/profiles/schema.py`）
  - `class ProfileMode(str, Enum)`:取值 `lite` / `full`
  - `class ResourceExpectation(BaseModel)`:字段 `cpu_cores: float`、`memory_gb: float`、`disk_gb: float`（均带下界校验）
  - `class StorageBackend(BaseModel)`:字段 `kind: Literal['postgres','neo4j','local_fs','minio','iceberg']`、`connection: dict[str, str]`
  - `class ServiceSpec(BaseModel)`:字段 `name: str`、`image_or_cmd: str`、`health_probe: str`、`env: dict[str, str] = {}`
  - `class ServiceBundleManifest(BaseModel)`:字段 `bundle_name: str`、`services: list[ServiceSpec]`、`startup_order: list[str]`、`shutdown_order: list[str]`、`health_checks: list[str]`、`required_profiles: list[str]`、`optional: bool`;`@model_validator` 验证 `startup_order`/`shutdown_order` 与 `services.name` 一一对应
  - `class EnvironmentProfile(BaseModel)`:字段 `profile_id: str`(正则 `^[a-z0-9]+(-[a-z0-9]+)*$`)、`mode: ProfileMode`、`enabled_modules: list[str]`、`enabled_service_bundles: list[str]`、`required_env_keys: list[str]`、`optional_env_keys: list[str]`、`storage_backends: dict[str, StorageBackend]`、`resource_expectation: ResourceExpectation`、`max_long_running_daemons: int`(`ge=1`)、`notes: str = ""`
  - `@model_validator(mode='after') def enforce_lite_daemon_cap(self)`:当 `mode == lite` 时强制 `max_long_running_daemons == 4`,违反抛 `ProfileConstraintError`
- 加载层（`src/assembly/profiles/loader.py`）
  - `def load_profile(path: Path) -> EnvironmentProfile`:读 YAML → `EnvironmentProfile.model_validate()`;文件不存在抛 `ProfileNotFoundError`,schema 不合法抛 `ProfileSchemaError`
  - `def load_bundle(path: Path) -> ServiceBundleManifest`:同上
  - `def list_profiles(root: Path = Path("profiles")) -> list[EnvironmentProfile]`:列出目录下所有 `*.yaml`/`*.yml`（阶段 0 可返回空列表）
  - `def list_bundles(root: Path = Path("bundles")) -> list[ServiceBundleManifest]`
- 异常层（`src/assembly/profiles/errors.py`）
  - `class ProfileError(Exception)`、`class ProfileNotFoundError(ProfileError)`、`class ProfileSchemaError(ProfileError)`、`class ProfileConstraintError(ProfileError)`
- 目录占位
  - `profiles/README.md`:说明 YAML schema 字段映射到 `EnvironmentProfile`
  - `bundles/README.md`:同上映射到 `ServiceBundleManifest`
- 测试（`tests/profiles/`）
  - `test_schema.py`:≥10 条用例,覆盖 lite 常驻进程硬约束、profile_id 正则、service bundle startup_order 不一致、必填字段缺失
  - `test_loader.py`:≥5 条用例,覆盖成功加载、文件缺失、YAML 语法错误、schema 错误、空目录 list

#### 不在本次范围
- 不创建 `lite-local.yaml` / `full-dev.yaml` 等真实 profile 内容（归 ISSUE-004）
- 不实现任何服务启动、docker compose、健康探针调用（归 ISSUE-005/007）
- 不加载或关联 `MODULE_REGISTRY`、不做 profile↔module 交叉校验（归 ISSUE-002/006）
- 不引入 `.env` 渲染或 `ResolvedConfigSnapshot`（归 ISSUE-004/005）
- 若发现需要新增 Lite 常驻 daemon 或默认开启 Full 组件，必须按 CLAUDE.md Blocker 条款挂起升级，不得在本 Issue 扩展字段

#### 关键交付物
- Pydantic 模型 `EnvironmentProfile`（含 `enforce_lite_daemon_cap` 验证器）与 `ServiceBundleManifest`
- 加载函数签名：`load_profile(path: Path) -> EnvironmentProfile`、`load_bundle(path: Path) -> ServiceBundleManifest`、`list_profiles(root: Path) -> list[EnvironmentProfile]`、`list_bundles(root: Path) -> list[ServiceBundleManifest]`
- 异常类 `ProfileError` / `ProfileNotFoundError` / `ProfileSchemaError` / `ProfileConstraintError`
- 配置键：`profile_id`、`mode`、`max_long_running_daemons`、`enabled_service_bundles` 等完全对齐 §9.3
- `profiles/` 与 `bundles/` 目录结构（含 README 说明）
- `pyproject.toml` 新增依赖与 `src` layout 包发现
- 测试用例 ≥15 条，全部通过

#### 验收标准
**核心功能：**
- [ ] `EnvironmentProfile.model_validate()` 在 `mode=lite` 且 `max_long_running_daemons != 4` 时抛 `ProfileConstraintError`
- [ ] `profile_id` 不符合小写短横线正则时抛 `ProfileSchemaError`
- [ ] `ServiceBundleManifest` 的 `startup_order` 名称与 `services.name` 不一致时验证失败
- [ ] `load_profile()` / `load_bundle()` 支持 `.yaml` 与 `.yml` 后缀
**错误处理：**
- [ ] 文件不存在 → `ProfileNotFoundError`（非通用 `FileNotFoundError`）
- [ ] YAML 语法错误 → `ProfileSchemaError`，携带 YAML 行号信息
**集成：**
- [ ] `from assembly.profiles import EnvironmentProfile, ServiceBundleManifest, load_profile` 可导入
- [ ] `list_profiles(Path("profiles"))` 在空目录返回 `[]` 不抛错
**测试：**
- [ ] `tests/profiles/` 至少 15 条用例通过，覆盖 schema 校验、加载、异常分支
- [ ] `pytest -q` 整体通过，且所有新增文件均被 `src` 包发现

#### 验证命令
```bash
# 安装依赖
pip install -e ".[dev]"
# 针对本 Issue 的单元测试
pytest tests/profiles -v
# 集成导入检查
python -c "from assembly.profiles import EnvironmentProfile, ServiceBundleManifest, load_profile, list_profiles; print('ok')"
# 全量回归
pytest -q
```

#### 依赖
无前置依赖

---

### ISSUE-002: 产出首版 MODULE_REGISTRY 与 machine-readable registry（14 模块 + 兼容矩阵骨架）
**labels**: P0, infrastructure, milestone-0

#### 背景与目标
依据 §13.2、§13.2.1 以及 CLAUDE.md “`MODULE_REGISTRY` 初版覆盖范围”，在任何模块进入 verified compatibility matrix 前必须先交付首版 registry，覆盖 12 固定长期模块 + N=2 子系统共 14 项。本 Issue 要同时产出 human-readable `MODULE_REGISTRY.md` 与 machine-readable `module-registry.yaml`，并建立 Pydantic schema 与一致性校验（两者不得成为两套真相，§6.2 反模式）。它也冻结 `CompatibilityMatrix` schema 骨架，但阶段 0 不声明任何 `verified` 组合（CLAUDE.md 约束 6）。产出物是 ISSUE-006 注册表加载、ISSUE-008 contract 套件、ISSUE-009 e2e 的上游真相。

#### 所属模块
- 主写入路径：
  - `src/assembly/registry/__init__.py`
  - `src/assembly/registry/schema.py`（`ModuleRegistryEntry`、`CompatibilityMatrix`、`IntegrationStatus` 等）
  - `src/assembly/registry/validator.py`（md↔yaml 一致性校验器）
  - `MODULE_REGISTRY.md`（人类可读）
  - `module-registry.yaml`（机器可读）
  - `compatibility-matrix.yaml`（骨架，状态全部 `draft`）
  - `tests/registry/test_schema.py`、`tests/registry/test_consistency.py`
- 相邻只读：
  - `src/assembly/profiles/schema.py`（阶段 0 不需要交叉引用，仅确认 `profile_id` 正则一致）
- 越界：
  - 不修改 `src/assembly/profiles/*`
  - 不实现任何 CLI / bootstrap / health / smoke
  - 不导入任何其他模块的私有包（CLAUDE.md 约束 1）

#### 实现范围
- Schema 层（`src/assembly/registry/schema.py`）
  - `class IntegrationStatus(str, Enum)`:`not_started` / `partial` / `ready` / `verified` / `blocked`
  - `class PublicEntrypoint(BaseModel)`:字段 `name: str`、`kind: Literal['health_probe','init_hook','smoke_hook','version_declaration','cli']`、`reference: str`（`module.path:symbol` 形式）
  - `class ModuleRegistryEntry(BaseModel)`:字段完全对齐 §9.3（`module_id`、`module_version`、`contract_version`、`owner`、`upstream_modules`、`downstream_modules`、`public_entrypoints`、`depends_on`、`supported_profiles`、`integration_status`、`last_smoke_result`、`notes`）
  - `class CompatibilityMatrixEntry(BaseModel)`:字段 `matrix_version`、`profile_id`、`module_set: list[{module_id, module_version}]`、`contract_version`、`required_tests: list[str]`、`status: Literal['draft','verified','deprecated']`、`verified_at: datetime | None`
  - `@model_validator` 强制：当 `status == 'verified'` 时 `verified_at` 必须非空；阶段 0 所有矩阵条目 `status` 只能是 `draft`
- 一致性校验（`src/assembly/registry/validator.py`）
  - `def load_registry_yaml(path: Path) -> list[ModuleRegistryEntry]`
  - `def parse_registry_md(path: Path) -> list[dict]`：从 Markdown 表格提取每行字段
  - `def assert_md_yaml_consistent(md_path: Path, yaml_path: Path) -> None`：若字段不一致抛 `RegistryInconsistentError`（至少校验 `module_id` / `integration_status` / `contract_version` 三列）
  - `class RegistryError(Exception)`、`class RegistryInconsistentError(RegistryError)`
- 首版数据（必须覆盖 14 项）
  - `module-registry.yaml` 列出：`contracts`、`data-platform`、`entity-registry`、`reasoner-runtime`、`graph-engine`、`main-core`、`audit-eval`、`subsystem-sdk`、`orchestrator`、`assembly`、`feature-store`、`stream-layer`、`subsystem-announcement`、`subsystem-news`
  - 除 `assembly` 本身可登记 `module_version=0.1.0`、`integration_status=partial` 外，其余 13 项 `module_version=0.0.0`、`contract_version=v0.0.0`、`integration_status=not_started`、`public_entrypoints=[]`、`supported_profiles=["lite-local"]`
  - `MODULE_REGISTRY.md`：表头 = `module_id | module_version | contract_version | owner | integration_status | supported_profiles | notes`，14 行与 YAML 一一对应
  - `compatibility-matrix.yaml`：包含一个 `profile_id=lite-local` 的 `draft` 条目，`module_set` 全部为 14 项当前版本，`verified_at=null`
- 测试（`tests/registry/`）
  - `test_schema.py`:≥8 条，覆盖 enum 值、verified 需要 verified_at、别名 `M##`/`N##` 禁止作为 `module_id`（正则只允许 kebab-case）
  - `test_consistency.py`:≥4 条，覆盖 md↔yaml 一致、故意制造字段漂移后被 `RegistryInconsistentError` 拦截、14 项覆盖检查、`status != draft` 在阶段 0 被拒绝

#### 不在本次范围
- 不声明任何 `verified` 组合（CLAUDE.md 约束 6 + §16.3）
- 不在 registry 中记录真实的模块公开入口（各模块未开工，阶段 0 留空）
- 不实现 `export_module_registry()` CLI（归 ISSUE-005/006）
- 不执行任何对其他模块的 import 探测或健康探针调用（归 ISSUE-007）
- 如发现某模块确有公开入口要登记，也不得越界在本 Issue 补齐；应单独挂 Issue 由模块 owner 驱动

#### 关键交付物
- Pydantic 模型 `ModuleRegistryEntry`、`CompatibilityMatrixEntry`、`PublicEntrypoint`、`IntegrationStatus`
- 校验函数 `assert_md_yaml_consistent(md_path: Path, yaml_path: Path) -> None`、`load_registry_yaml(path: Path) -> list[ModuleRegistryEntry]`
- 异常 `RegistryError` / `RegistryInconsistentError`
- `MODULE_REGISTRY.md`（14 行表格 + 阶段 0 说明段）
- `module-registry.yaml`（14 条 entry，full schema）
- `compatibility-matrix.yaml`（1 条 `draft` 骨架）
- `src/assembly/registry/` 包 + `tests/registry/` ≥12 条通过

#### 验收标准
**核心功能：**
- [ ] `module-registry.yaml` 覆盖全部 14 个 `module_id`，未开工项全部 `integration_status=not_started`、`contract_version=v0.0.0`
- [ ] `MODULE_REGISTRY.md` 表格行数 = 14 + 表头
- [ ] `compatibility-matrix.yaml` 所有条目 `status=draft`
- [ ] Schema 拒绝使用 `M##` / `N##` / `P##` 形式作为 `module_id`
**错误处理：**
- [ ] 故意将 md 某行 `integration_status` 改为 `verified` 而 yaml 仍为 `not_started` → `RegistryInconsistentError`
- [ ] `status=verified` 但 `verified_at=null` → 校验失败
**集成：**
- [ ] `from assembly.registry import ModuleRegistryEntry, load_registry_yaml, assert_md_yaml_consistent` 可导入
- [ ] `assert_md_yaml_consistent("MODULE_REGISTRY.md", "module-registry.yaml")` 在首版数据上通过
**测试：**
- [ ] `tests/registry/` ≥12 条全部通过
- [ ] `pytest -q` 整体绿

#### 验证命令
```bash
# 单元测试
pytest tests/registry -v
# 一致性脚本（Python one-liner，沿用 validator API）
python -c "from pathlib import Path; from assembly.registry import assert_md_yaml_consistent; assert_md_yaml_consistent(Path('MODULE_REGISTRY.md'), Path('module-registry.yaml')); print('consistent')"
# 回归
pytest -q
```

#### 依赖
依赖 #ISSUE-001（复用 `profile_id` 正则约束与 Pydantic/PyYAML 依赖）

---

### ISSUE-003: 冻结模块公开入口契约（PublicEntrypoint 协议 + 阶段 0 文档）
**labels**: P0, infrastructure, integration, milestone-0

#### 背景与目标
依据 §16.2、§16.3、§25.1，`assembly` 只能通过模块的 **公开入口、公开配置、公开健康探针** 集成（CLAUDE.md 约束 1）。阶段 0 需要把“模块需要给 assembly 暴露什么”冻结为协议（Protocol / 数据契约）与文档，使 12+N 个模块的 owner 有统一对接模板，同时为 ISSUE-007 健康检查和 ISSUE-008 contract 套件提供可插拔入口。本 Issue 只冻结 **Python 协议 + 描述契约的 Pydantic 模型 + 文档**，不实现任何具体模块探针，也不执行探针（严禁越界执行）。这是 §21 阶段 0 “冻结各模块需要公开给 assembly 的最小入口” 的落地。

#### 所属模块
- 主写入路径：
  - `src/assembly/contracts/__init__.py`（注意此处 `contracts` 命名空间仅为 assembly 内部公开入口协议聚合，不得 import 上游 `contracts` 模块源）
  - `src/assembly/contracts/protocols.py`（`HealthProbe`、`SmokeHook`、`InitHook`、`VersionDeclaration` Protocol）
  - `src/assembly/contracts/models.py`（`HealthResult`、`SmokeResult`、`VersionInfo` 数据模型）
  - `docs/PUBLIC_ENTRYPOINTS.md`（模块 owner 对接指南）
  - `tests/contracts/test_protocols.py`、`tests/contracts/test_models.py`
- 相邻只读：
  - `src/assembly/registry/schema.py`（`PublicEntrypoint.kind` 枚举需与本 Issue 的 Protocol 一一对应；仅读取，不修改）
- 越界：
  - 不实现任何具体模块的探针（各模块 owner 负责）
  - 不执行 `HealthProbe.check()` / `SmokeHook.run()`（执行归 ISSUE-007）
  - 不 import 任何其他模块源码（`contracts` / `orchestrator` / `main-core` 均禁止 import）

#### 实现范围
- 数据模型（`src/assembly/contracts/models.py`）
  - `class HealthStatus(str, Enum)`:`healthy` / `degraded` / `blocked`
  - `class HealthResult(BaseModel)`:`module_id: str`、`probe_name: str`、`status: HealthStatus`、`latency_ms: float`、`message: str`、`details: dict[str, Any] = {}`
  - `class SmokeResult(BaseModel)`:`module_id: str`、`hook_name: str`、`passed: bool`、`duration_ms: float`、`failure_reason: str | None = None`
  - `class VersionInfo(BaseModel)`:`module_id: str`、`module_version: str`、`contract_version: str`、`compatible_contract_range: str`（SemVer range 语法）
- 协议（`src/assembly/contracts/protocols.py`，`typing.Protocol`）
  - `class HealthProbe(Protocol)`:`def check(self, *, timeout_sec: float) -> HealthResult`
  - `class SmokeHook(Protocol)`:`def run(self, *, profile_id: str) -> SmokeResult`
  - `class InitHook(Protocol)`:`def initialize(self, *, resolved_env: dict[str, str]) -> None`
  - `class VersionDeclaration(Protocol)`:`def declare(self) -> VersionInfo`
  - 每个 Protocol 使用 `@runtime_checkable` 装饰器
  - `class CliEntrypoint(Protocol)`:`def invoke(self, argv: list[str]) -> int`（阶段 0 仅占位，方便 ISSUE-005 引用）
- 枚举一致性校验
  - 在 `src/assembly/contracts/__init__.py` 暴露 `ENTRYPOINT_KIND_TO_PROTOCOL: dict[str, type]`，覆盖 `health_probe` / `smoke_hook` / `init_hook` / `version_declaration` / `cli`，与 `registry.schema.PublicEntrypoint.kind` 枚举严格一致（测试里交叉断言）
- 文档（`docs/PUBLIC_ENTRYPOINTS.md`）
  - 说明每个 Protocol 的职责、返回语义、超时约定、错误如何转化为 `blocked`
  - 给出模块 owner 登记模板：`module_id / kind / reference` 三列
  - 明确“assembly 不接受未登记的私有入口”与 Blocker 升级路径
- 测试（`tests/contracts/`）
  - `test_models.py`:≥6 条，覆盖 `HealthStatus` 枚举、SemVer range 基本校验、必填字段
  - `test_protocols.py`:≥6 条，使用 `@runtime_checkable` + dummy 实现验证 `isinstance(dummy, HealthProbe)`；验证 `ENTRYPOINT_KIND_TO_PROTOCOL` 与 `PublicEntrypoint.kind` 枚举集合相等

#### 不在本次范围
- 不实现任何模块的 `HealthProbe` / `SmokeHook`（各模块 owner + ISSUE-007 组合完成）
- 不写 `assembly.health` / `assembly.bootstrap` 的任何代码
- 不与实际 PostgreSQL / Neo4j / Dagster 通信
- 不在 `MODULE_REGISTRY.md` 中补充 `public_entrypoints`（由各模块 owner 后续 PR）
- 若发现某模块无公开入口，按 CLAUDE.md 挂 Blocker 升级，不得在本 Issue 代写

#### 关键交付物
- Protocol: `HealthProbe.check(*, timeout_sec: float) -> HealthResult`、`SmokeHook.run(*, profile_id: str) -> SmokeResult`、`InitHook.initialize(*, resolved_env: dict[str, str]) -> None`、`VersionDeclaration.declare() -> VersionInfo`、`CliEntrypoint.invoke(argv: list[str]) -> int`
- 数据模型 `HealthResult` / `SmokeResult` / `VersionInfo` / `HealthStatus`
- 映射 `ENTRYPOINT_KIND_TO_PROTOCOL: dict[str, type]`
- `docs/PUBLIC_ENTRYPOINTS.md`（阶段 0 owner 对接指南）
- `tests/contracts/` ≥12 条通过
- `src/assembly/contracts/__init__.py` 导出上述全部符号

#### 验收标准
**核心功能：**
- [ ] 所有 Protocol 带 `@runtime_checkable`，dummy 实现可被 `isinstance` 判定为协议成员
- [ ] `HealthStatus` 枚举值严格为 `healthy` / `degraded` / `blocked`
- [ ] `ENTRYPOINT_KIND_TO_PROTOCOL.keys()` == `PublicEntrypoint.kind` 允许值集合
**错误处理：**
- [ ] `VersionInfo.compatible_contract_range` 非 SemVer range → schema 校验失败
- [ ] `HealthResult.status=degraded` 允许但 `message` 为空时产生警告（通过测试断言）
**集成：**
- [ ] `from assembly.contracts import HealthProbe, SmokeHook, HealthResult, VersionInfo, ENTRYPOINT_KIND_TO_PROTOCOL` 可导入
- [ ] `assembly.contracts` 命名空间未从外部 `contracts` 模块 import 任何符号（grep 检查）
**测试：**
- [ ] `tests/contracts/` ≥12 条通过
- [ ] `pytest -q` 全绿，无对外部模块的网络/进程副作用

#### 验证命令
```bash
# 单元测试
pytest tests/contracts -v
# 导入 + 隔离检查
python -c "from assembly.contracts import HealthProbe, SmokeHook, ENTRYPOINT_KIND_TO_PROTOCOL; print(list(ENTRYPOINT_KIND_TO_PROTOCOL))"
# 与 registry 枚举交叉检查
python -c "from assembly.registry.schema import PublicEntrypoint; from assembly.contracts import ENTRYPOINT_KIND_TO_PROTOCOL; kinds = {f.annotation.__args__ if hasattr(f.annotation, '__args__') else None for f in PublicEntrypoint.model_fields.values()}; print('ok')"
# 回归
pytest -q
```

#### 依赖
依赖 #ISSUE-001（复用 Pydantic 依赖与包布局）, #ISSUE-002（与 `PublicEntrypoint.kind` 枚举保持一致）

---

## 阶段 1：Lite profile 与 bootstrap

**目标**：建立 `lite-local` profile 与 bootstrap CLI，对齐主文档附录 F.1，跑通 PostgreSQL / Neo4j / Dagster daemon / Dagster webserver 四个常驻进程
**前置依赖**：阶段 0 完成（ISSUE-001/002/003）

### ISSUE-004: 落地 lite-local profile 与 service bundle manifest（含 .env.example）
**labels**: P0, infrastructure, milestone-1
**摘要**:创建 `profiles/lite-local.yaml`、`bundles/postgres.yaml`、`bundles/neo4j.yaml`、`bundles/dagster.yaml` 及 `.env.example`,锁定 Lite 4 常驻进程硬约束,并提供 `ResolvedConfigSnapshot` 导出接口
**所属模块**:
- 主写入：`profiles/lite-local.yaml`、`bundles/{postgres,neo4j,dagster}.yaml`、`.env.example`、`src/assembly/profiles/resolver.py`、`tests/profiles/test_resolver.py`
- 只读集成：`src/assembly/profiles/schema.py`（ISSUE-001）、`MODULE_REGISTRY.md`（ISSUE-002 校验 `enabled_modules` 全部存在）
**写入边界**:
- 允许修改：上述主写入路径、`src/assembly/profiles/__init__.py`（新增 export）
- 禁止修改：`src/assembly/profiles/schema.py`（schema 已冻结）、`src/assembly/registry/*`、任何 bootstrap/health/compat/测试运行器代码
**实现顺序**:
1) 先写 `bundles/postgres.yaml`、`bundles/neo4j.yaml`、`bundles/dagster.yaml`（含 daemon 与 webserver 两个 service,凑够 Lite 4 常驻进程）
2) 再写 `profiles/lite-local.yaml`（`mode=lite`,`max_long_running_daemons=4`,`enabled_service_bundles=[postgres,neo4j,dagster]`,`required_env_keys` 含 PG/Neo4j/Dagster 的关键变量）
3) 写 `.env.example` 覆盖 `required_env_keys` 与 `optional_env_keys`
4) 实现 `assembly.profiles.resolver.resolve(profile: EnvironmentProfile, env: Mapping[str,str]) -> ResolvedConfigSnapshot`（缺失必填 env → fail-fast 抛 `ProfileEnvMissingError`）
5) 补充 `list_profiles()` 真实返回、`ResolvedConfigSnapshot` 落盘 API `snapshot.dump(path: Path) -> None`
6) 测试覆盖：4 常驻进程计数、缺 env 拦截、Full 可选 bundle 不得出现在 lite-local、snapshot 往返
**依赖**: #ISSUE-001（profile schema）, #ISSUE-002（registry 用于 `enabled_modules` 一致性断言）

---

### ISSUE-005: 实现 bootstrap CLI 与服务启动编排（`assembly` 命令行入口）
**labels**: P0, infrastructure, integration, milestone-1
**摘要**:实现 `assembly` CLI（`bootstrap` / `shutdown` / `list-profiles` / `render-profile` / `export-registry` 五个子命令）、`assembly.bootstrap.plan` 启动计划构建、基于 `docker compose` 或等价本地脚本启动 Lite 4 进程并收敛到最小可运行状态
**所属模块**:
- 主写入：`src/assembly/cli/__init__.py`、`src/assembly/cli/main.py`、`src/assembly/bootstrap/plan.py`、`src/assembly/bootstrap/runner.py`、`src/assembly/bootstrap/service_handle.py`、`compose/lite-local.yaml`、`Makefile`、`tests/bootstrap/test_plan.py`、`tests/bootstrap/test_runner.py`、`tests/cli/test_main.py`
- 只读集成：`profiles/lite-local.yaml`、`bundles/*.yaml`、`src/assembly/profiles/*`、`src/assembly/registry/*`
**写入边界**:
- 允许：`src/assembly/bootstrap/*`、`src/assembly/cli/*`、`compose/`、`Makefile`、`pyproject.toml`（新增 `click` 依赖与 `[project.scripts] assembly = "assembly.cli.main:entrypoint"`）
- 禁止：profile/registry/contract 任何 schema、健康检查包 `assembly.health`、contract/smoke/e2e 运行器
- 严禁 import 任何模块私有包，只能通过 `docker compose` 命令启动服务（公开入口约束）
**实现顺序**:
1) 起 CLI 骨架 `main.py`(Click) + 子命令注册 + 退出码规范
2) `bootstrap.plan.build_plan(profile: EnvironmentProfile) -> BootstrapPlan`（解析 bundle startup_order → 拓扑序列）
3) `bootstrap.runner.Runner.start(plan)` / `.stop(plan)`,通过 `compose/lite-local.yaml` 编排 PG/Neo4j/Dagster daemon + webserver
4) `ServiceHandle` 包装子进程/compose 服务,暴露 `poll()` / `terminate()`
5) CLI 串联 `render-profile` → 生成 ResolvedConfigSnapshot,`bootstrap` → 启动,`shutdown` → 反序停止,`list-profiles` / `export-registry` 调用阶段 0 API
6) 测试：plan 拓扑序正确、缺 docker 时友好错误、fake runner 下 4 服务 start/stop 顺序、CLI 退出码
**依赖**: #ISSUE-004（需要真实 lite-local 与 bundle YAML）

---

## 阶段 2：registry + health + smoke

**目标**：落地 `MODULE_REGISTRY` 加载、兼容矩阵装载、系统级健康检查与 smoke suite，实现 §16 对外接口 `healthcheck()` / `run_smoke()`
**前置依赖**：阶段 1 完成（ISSUE-004/005）

### ISSUE-006: 实现 registry / compatibility matrix 运行时装载与 `export_module_registry()`
**labels**: P0, infrastructure, milestone-2
**摘要**:实现 `assembly.registry` 运行时 API（`load_all()` / `resolve_for_profile(profile_id)` / `export_module_registry(out_dir)`）、registry↔profile 交叉校验、兼容矩阵装载，并接入 CLI `export-registry` 子命令
**所属模块**:
- 主写入：`src/assembly/registry/loader.py`、`src/assembly/registry/resolver.py`、`src/assembly/registry/exporter.py`、`tests/registry/test_loader.py`、`tests/registry/test_resolver.py`
- 只读集成：`MODULE_REGISTRY.md`、`module-registry.yaml`、`compatibility-matrix.yaml`、`profiles/*.yaml`、`src/assembly/cli/main.py`（仅接入子命令）
**写入边界**:
- 允许：新增 loader/resolver/exporter 模块及对应测试，CLI `main.py` 中 `export-registry` 子命令走向真实实现
- 禁止：修改 schema（ISSUE-002 已冻结）、修改首版 registry 数据、越权声明 verified 组合
**实现顺序**:
1) `loader.load_all(root: Path) -> Registry`（组合 md + yaml + matrix,内部调用 ISSUE-002 的 `assert_md_yaml_consistent`）
2) `resolver.resolve_for_profile(registry: Registry, profile_id: str) -> list[ModuleRegistryEntry]`（按 `supported_profiles` 过滤 + 按 `depends_on` 拓扑 + blocked 模块直接拒绝）
3) `exporter.export_module_registry(registry, out_dir)` 产出 `reports/registry/{registry.json, matrix.json}`
4) CLI 接入：`assembly export-registry --out reports/registry/`
5) 测试：14 模块完整加载、缺依赖拦截、blocked 状态拦截、verified 声明阶段 0 仍被拒绝
**依赖**: #ISSUE-002, #ISSUE-005

---

### ISSUE-007: 健康检查收敛器与系统级 smoke suite
**labels**: P0, infrastructure, testing, milestone-2
**摘要**:实现 `assembly.health.HealthcheckRunner`（对 Lite 4 进程与已登记 `HealthProbe` 统一收敛,分级 healthy/degraded/blocked）与 `assembly.tests.smoke`（PG 可连、Neo4j 可连、Dagster webserver /server_info 200、已登记 `SmokeHook` 全通）+ `assembly healthcheck` / `assembly smoke` CLI
**所属模块**:
- 主写入：`src/assembly/health/__init__.py`、`src/assembly/health/runner.py`、`src/assembly/health/probes_builtin.py`、`src/assembly/tests/smoke/__init__.py`、`src/assembly/tests/smoke/runner.py`、`tests/health/*`、`tests/smoke/*`
- 只读集成：`src/assembly/contracts/*`、`src/assembly/registry/*`、`src/assembly/profiles/*`、`src/assembly/bootstrap/*`
**写入边界**:
- 允许：health/smoke 包与对应测试、CLI 子命令接入
- 禁止：修改 contracts Protocol（ISSUE-003 已冻结）、修改 bundle yaml、下探模块私有包
- 未登记探针一律跳过并在报告里显示 `integration_status=not_started`,严禁在本 Issue 替模块 owner 写探针
**实现顺序**:
1) `probes_builtin`:PG/Neo4j/Dagster-daemon/Dagster-webserver 四个内建 `HealthProbe` 实现（仅通过官方连接协议/HTTP,不 import 任何模块私有代码）
2) `HealthcheckRunner.run(profile, registry, timeout_sec) -> list[HealthResult]`,按 CLAUDE.md 分级:核心 Lite 服务失败 → `blocked`;可选组件允许 `degraded`
3) Smoke `SmokeSuite.run(profile) -> IntegrationRunRecord`,汇总内建健康 + 已登记 `SmokeHook` 结果 → `reports/smoke/<run_id>.json`
4) CLI:`assembly healthcheck --profile lite-local`、`assembly smoke --profile lite-local`（退出码:0=全 healthy,1=degraded,2=blocked）
5) 测试:fake probe、超时、blocked 传播、报告落盘与 schema
**依赖**: #ISSUE-005, #ISSUE-006

---

## 阶段 3：contract compatibility + minimal cycle e2e

**目标**：落地 §11.5 contract 套件与 §11.6 minimal cycle e2e，使 verified compatibility matrix 首次可被真实运行支撑
**前置依赖**：阶段 2 完成（ISSUE-006/007）

### ISSUE-008: Contract compatibility suite（`assembly.compat`）
**labels**: P0, testing, integration, milestone-3
**摘要**:实现 `assembly.compat` 套件,验证 contracts 版本一致性、subsystem-sdk submit/receipt 边界、orchestrator 是否能加载模块公开入口、main-core/graph-engine/audit-eval 公开接口是否在兼容矩阵允许范围内;产出 `CompatibilityReport` 并驱动矩阵状态迁移
**所属模块**:
- 主写入：`src/assembly/compat/__init__.py`、`src/assembly/compat/runner.py`、`src/assembly/compat/checks/{contracts_version,sdk_boundary,orchestrator_loadability,public_api_boundary}.py`、`tests/compat/*`、`reports/contract/*`（生成目录）
- 只读集成：`src/assembly/contracts/*`、`src/assembly/registry/*`、`compatibility-matrix.yaml`
**写入边界**:
- 允许：compat 包与测试、CLI `assembly contract-suite` 子命令
- 禁止：直接复制 `contracts` 模块源（CLAUDE.md 约束 8）、绕过 `orchestrator` 执行业务链（约束 7 留给 ISSUE-009 e2e）、在 compat 内写业务判断
- 只测边界兼容,不测业务准确率
**实现顺序**:
1) `Check` Protocol + 四类检查点实现（全部通过模块登记的 `VersionDeclaration`/`SmokeHook` 间接验证,不 import 私有包）
2) `CompatRunner.run(profile) -> CompatibilityReport`
3) 矩阵状态机:全部 required_tests pass + `verified_at` 写入 → 可申请 `draft → verified`,但状态迁移须显式 CLI `--promote` 开关,避免误升级
4) CLI:`assembly contract-suite --profile lite-local [--promote]`,报告落 `reports/contract/<run_id>.json`
5) 测试:4 类检查点的正/反例、promote 在未全通过时被拒绝、未登记模块跳过且报告 `not_started`
**依赖**: #ISSUE-006, #ISSUE-007

---

### ISSUE-009: Minimal cycle e2e（通过 `orchestrator` 公开入口跑最小日频链）
**labels**: P0, testing, integration, milestone-3
**摘要**:实现 `run_min_cycle_e2e(profile_id)`,在 lite-local 上加载冻结 fixture → 通过 orchestrator 公开入口触发最小 daily cycle → 校验 phase 顺序与关键 artifact → 输出 e2e 报告;严格不得绕过 orchestrator
**所属模块**:
- 主写入：`src/assembly/tests/e2e/__init__.py`、`src/assembly/tests/e2e/runner.py`、`src/assembly/tests/e2e/fixtures/minimal_cycle/*`、`src/assembly/tests/e2e/assertions.py`、`tests/e2e/*`
- 只读集成：`src/assembly/bootstrap/*`、`src/assembly/health/*`、`src/assembly/contracts/*`、`src/assembly/registry/*`、orchestrator 公开 CLI / HTTP 入口（仅通过登记的 `CliEntrypoint` 或 HTTP）
**写入边界**:
- 允许：e2e 包 + fixture + 测试 + CLI `assembly e2e`
- 禁止：直接 import orchestrator/main-core/graph-engine 内部包、在 e2e 里写业务阈值、把 fixture 膨胀到跨模块业务数据
- 任何需要绕过 orchestrator 的路径立刻挂 Blocker(CLAUDE.md 约束 7)
**实现顺序**:
1) 冻结最小 fixture 目录结构（只含占位 JSON/yaml,不含真实市场数据）
2) `E2ERunner.run(profile_id) -> IntegrationRunRecord`:bootstrap(若未启动) → 通过 orchestrator 登记的 CLI 入口触发 daily cycle → 轮询 phase → 断言关键 artifact 路径存在
3) `assertions.py`:phase 顺序、关键 artifact 清单、失败路径诊断
4) CLI `assembly e2e --profile lite-local`,报告落 `reports/e2e/<run_id>.json`
5) 测试:fake orchestrator 下 phase 顺序断言、fixture 缺失告警、真实 orchestrator 未登记入口时 fail-fast 并建议 Blocker
**依赖**: #ISSUE-008

---

## 阶段 4：Full 扩展 profile 与可选 service bundle 槽位

**目标**：在不改变现有 Lite 合同边界的前提下，新增 Full profile 与 MinIO / Grafana / Superset / Temporal / Feast / Kafka-Flink 槽位
**前置依赖**：阶段 3 完成（ISSUE-008/009）

### ISSUE-010: Full profile 与可选 service bundle 槽位（`full-dev` + 6 个可选 bundle）
**labels**: P1, infrastructure, milestone-4
**摘要**:新增 `profiles/full-dev.yaml` 与 `bundles/{minio,grafana,superset,temporal,feast,kafka-flink}.yaml` 骨架,扩展 CLI 支持 `--extra-bundles`,更新兼容矩阵增加 full-dev draft 条目;确保 Lite profile 的 4 常驻进程硬约束不被触动
**所属模块**:
- 主写入：`profiles/full-dev.yaml`、`bundles/{minio,grafana,superset,temporal,feast,kafka-flink}.yaml`、`src/assembly/profiles/resolver.py`（扩展 `--extra-bundles` 合并）、`compatibility-matrix.yaml`、`MODULE_REGISTRY.md` 与 `module-registry.yaml`（为 feature-store/stream-layer 补 `supported_profiles` 追加 `full-dev`）、`tests/profiles/test_full_dev.py`
- 只读集成：`src/assembly/profiles/schema.py`、`src/assembly/bootstrap/*`、`src/assembly/health/probes_builtin.py`
**写入边界**:
- 允许：上述主写入路径、CLI 中 `bootstrap --profile full-dev --extra-bundles=grafana,superset` 支持
- 禁止：把任何可选 bundle 加入 `lite-local.yaml`、修改 Lite 4 常驻进程硬约束、为可选 bundle 写业务逻辑
- 可选 bundle 故障必须被健康检查识别为 `degraded`,不得传播为 `blocked`
**实现顺序**:
1) 先写 6 个可选 bundle YAML（全部 `optional=true`）
2) 写 `full-dev.yaml`（`mode=full`、`enabled_service_bundles` 只含核心 3 项,可选 bundle 通过 `--extra-bundles` 叠加,`max_long_running_daemons` 允许 > 4）
3) 更新 resolver:`--extra-bundles` 合并 + 冲突校验 + Lite 组合拒绝叠加可选
4) 更新 `compatibility-matrix.yaml` 增加 `profile_id=full-dev` draft 条目
5) 测试:Lite 不受污染、Full 可按需叠加、可选 bundle 故障 → degraded 不传播为 blocked
**依赖**: #ISSUE-009

---

## 阶段 5：发布与运维材料完善

**目标**：完善版本锁定、troubleshooting、profile 对比文档，把 verified compatibility matrix 作为正式集成基线
**前置依赖**：阶段 4 完成（ISSUE-010）

### ISSUE-011: Version lock / troubleshooting / startup / profile 对比文档与 release 工作流
**labels**: P1, infrastructure, milestone-5
**摘要**:产出 `docs/VERSION_LOCK.md`、`docs/TROUBLESHOOTING.md`、`docs/STARTUP_GUIDE.md`、`docs/PROFILE_COMPARISON.md`,并新增 `assembly release-freeze` CLI 将当前 verified compatibility matrix 冻结为版本锁文件,使 matrix 首次成为集成基线
**所属模块**:
- 主写入：`docs/VERSION_LOCK.md`、`docs/TROUBLESHOOTING.md`、`docs/STARTUP_GUIDE.md`、`docs/PROFILE_COMPARISON.md`、`src/assembly/cli/release.py`、`src/assembly/registry/freezer.py`、`version-lock/*.yaml`（冻结输出目录）、`tests/release/*`
- 只读集成：所有阶段 0-4 产物
**写入边界**:
- 允许：docs 目录新增文档、release 子命令与 freezer 模块、`version-lock/` 目录
- 禁止：修改 schema、修改 lite 常驻进程硬约束、修改既有 profile/bundle 数据、回写业务逻辑
**实现顺序**:
1) 先写 4 份文档框架（结构参考 §13.4,内容从 §11.7 / §21 抽取）
2) 实现 `registry.freezer.freeze(registry, matrix, out_path)` 把 verified 组合序列化为 `version-lock/<date>-<profile>.yaml`（含模块版本、contract 版本、必过测试套件版本）
3) CLI `assembly release-freeze --profile lite-local --out version-lock/`,未全 verified 时拒绝冻结
4) Troubleshooting 覆盖阶段 1-3 典型失败（缺 env、PG 连接失败、orchestrator 未启动、contract mismatch）
5) 测试:freeze 在全 verified 时成功、在 draft 存在时拒绝、文档内部链接可解析
**依赖**: #ISSUE-010

---
