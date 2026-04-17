# assembly 完整项目文档

> **文档状态**：Draft v1
> **版本**：v0.1.2
> **作者**：Codex
> **创建日期**：2026-04-15
> **最后更新**：2026-04-15
> **文档目的**：把 `assembly` 子项目从“几个启动脚本和 compose 文件”的零散理解收束为可立项、可拆分、可实现、可验收的正式项目，使其成为主项目中唯一负责系统级环境总装、模块注册表、启动/健康检查、集成兼容性验证和 Lite/Full 运行档位切换的系统装配模块。

---

## 变更记录

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v0.1 | 2026-04-15 | 初稿 | Codex |
| v0.1.1 | 2026-04-15 | 补充 `MODULE_REGISTRY` 初版要求、跨文档对照表和 Lite 常驻进程硬约束 | Codex |
| v0.1.2 | 2026-04-15 | 把 Lite 常驻进程硬约束前置到 `EnvironmentProfile` 对象定义 | Codex |

---

## 1. 一句话定义

`assembly` 是主项目中**唯一负责把各个独立模块以可启动、可配置、可健康检查、可运行最小集成验证、可按 Lite/Full 档位切换的方式总装成一个完整系统**的系统装配模块，它以“只拥有环境与集成，不拥有业务实现”“只消费模块公开入口，不反向侵入模块私有内部”“Full 扩展通过 profile 加法而不是重写现有模块边界”为不可协商约束。

这里的 `assembly` 指**系统总装**，不是 `main-core` 内部的 publish bundle 装配，也不是 `orchestrator` 的执行图装配。  
它不拥有业务 contract，不拥有 Dagster asset 逻辑，不拥有图谱算法或主系统判断。

---

## 2. 文档定位与核心问题

本文解决的问题不是“怎么写一个启动脚本”，而是：

1. **系统级启动入口唯一化问题**：如果 PostgreSQL、Neo4j、Dagster、各模块配置和最小运行校验没有唯一总装层，后续 12+N 子项目即使各自完成，也很难真正拼成一套可运行系统。
2. **模块兼容性与版本矩阵问题**：各模块独立开发后，必须有一个地方明确记录“哪些版本、哪些合同、哪些 profile 能一起工作”，否则集成期会长期靠口头约定。
3. **Lite/Full 档位切换问题**：Lite 单节点与 Full 扩展不是两套新架构，而是同一架构在不同 profile 下启用不同服务 bundle；如果这层不冻结，后面每次扩展都会重谈部署边界。
4. **集成验收与最小 e2e 问题**：模块级测试并不能证明整套系统可跑，必须有系统级 smoke test、contract compatibility test 和最小 cycle e2e test 的统一入口。
5. **装配层与编排层混线问题**：`assembly` 很容易越界成“另一个 orchestrator”或“另一个 main-core”，必须明确它只负责环境、入口、集成和验收，不负责执行图策略和业务判断。

---

## 3. 术语表

| 术语 | 定义 | 备注 |
|------|------|------|
| System Assembly | 系统总装 | 指整个项目的环境与模块集成，不是业务装配 |
| Environment Profile | 一组可命名的运行档位配置 | 如 `lite-local`、`full-dev` |
| Service Bundle | 某个 profile 下需要启用的一组基础服务 | 如 PostgreSQL、Neo4j、Dagster |
| Module Registry | 记录模块版本、合同版本、依赖、集成就绪度的注册表 | 人类可读 + 机器可读 |
| Compatibility Matrix | 描述哪些模块版本/合同版本可共同运行的矩阵 | 属于 assembly 真相层 |
| Bootstrap Plan | 一次系统启动前的装配计划 | 包括 profile、服务、依赖顺序 |
| Health Check | 对服务、模块入口和最小运行能力的健康探测 | 不等于业务验收 |
| Smoke Test | 验证基础服务和模块入口可用的快速测试 | 时间短、覆盖浅 |
| Contract Compatibility Test | 验证模块间公开接口和合同兼容性的测试 | 重点看边界而非业务正确性 |
| Minimal Cycle E2E | 在最小 Lite 环境里跑通一轮最小日频 cycle 的系统级测试 | 是 assembly 的最高级别验收 |
| Resolved Config Snapshot | 某次启动实际生效的配置快照 | 用于排障与回放 |
| Version Lock | 对依赖、模块版本、profile 兼容关系的冻结记录 | 不等于每个模块内部 lockfile |

**规则**：

- `assembly` 可以依赖全部模块，但只能通过它们的**公开入口、公开配置和公开健康探针**集成。
- `Environment Profile` 只表达环境与组件启用关系，不改写模块业务语义。
- `Module Registry` 是系统集成真相源之一，必须显式记录模块版本、合同版本和集成状态。
- Lite/Full 差异必须通过 profile 和 service bundle 表达，不能要求业务模块改写合同边界。
- `assembly` 不得复制 `contracts`、不得复制其他模块源码、不得把模块私有表结构当作自己的稳定接口。

---

## 4. 目标与非目标

### 4.1 项目目标

1. **提供统一系统启动入口**：为 Lite 单机和后续 Full 扩展提供一致的 bootstrap 命令、脚本或 compose 入口。
2. **提供环境 profile 体系**：把 Lite/Full、local/dev/integration 的差异显式收束为可版本化 profile，而不是散落在脚本和文档里。
3. **维护模块注册表与兼容矩阵**：记录每个模块的版本、依赖、合同版本、集成就绪度和所在运行档位。
4. **提供统一健康检查**：对 PostgreSQL、Neo4j、Dagster 以及模块公开入口执行最小健康探测。
5. **提供集成级 contract test**：验证模块之间的公开接口、合同版本和兼容性边界。
6. **提供最小系统级 e2e 验收**：在 Lite 模式跑通最小 daily cycle，证明不是“模块都写了但系统拼不起来”。
7. **冻结部署与扩展路径**：按照主文档附录 F 的 Lite/Full 资源路线，明确哪些服务是 Lite 必需、哪些是 Full 可选。
8. **沉淀系统级运维与排障材料**：输出 `.env.example`、profile 文档、启动说明、故障排查入口和版本锁定说明。

### 4.2 非目标

- **不拥有业务实现**：各模块的业务逻辑、schema、算法、策略仍归各模块自己，因为总装层不能成为业务逻辑的隐藏容器。
- **不拥有 Dagster 执行图**：`orchestrator` 负责 definitions、jobs、Gate policy 和 resource wiring，`assembly` 只负责把它作为一个系统入口启动起来。
- **不拥有主系统发布逻辑**：`main-core` 的 publish bundle 和 formal object 逻辑不归 `assembly`。
- **不定义共享合同**：Ex、formal object、错误码、phase 枚举等共享合同都归 `contracts`。
- **不替代模块内单元测试**：assembly 只做系统集成验证，不替代各模块自己的 unit/integration test。
- **不反向侵入模块私有内部**：如果一个模块没有公开入口，assembly 应推动它补公开接口，而不是直接 import 私有实现或直读私有目录。
- **不把 Full 组件提前变成 Lite 前置依赖**：Kafka/Flink、Feast、Milvus、Grafana/Superset、Temporal 等只能按 profile 条件启用。
- **不拥有业务来源和密钥语义**：assembly 负责密钥注入和配置装配，但新闻源 allowlist、provider policy、实体规则等语义仍归对应模块。

---

## 5. 与现有工具的关系定位

### 5.1 架构位置

```text
contracts + all module public entrypoints + environment profiles
  -> assembly
      ├── bootstrap commands
      ├── env/profile resolution
      ├── module registry
      ├── service bundle manifests
      ├── health checks
      ├── contract compatibility suite
      └── minimal cycle e2e suite
  -> developers / CI / local machine / integration env
      -> runnable whole-system instance
```

### 5.2 上游输入

| 来源 | 提供内容 | 说明 |
|------|----------|------|
| `contracts` | 合同版本、共享类型、公共枚举 | assembly 只消费，不重定义 |
| `data-platform` | 存储依赖、初始化脚本公开入口、smoke hooks | 只通过公开入口装配 |
| `entity-registry` | 初始化入口、health probe、最小配置面 | 不直读私有内部实现 |
| `reasoner-runtime` | provider 配置面、health probe、最小 client 检查 | 凭据注入归 assembly |
| `graph-engine` | Neo4j 相关最小健康探针、启动前置条件 | 图谱业务逻辑不归 assembly |
| `main-core` | 最小运行入口、publish 相关公开检查接口 | 业务链不归 assembly |
| `audit-eval` | dashboard / backtest / replay 公开入口 | 仅做系统集成 |
| `subsystem-sdk` / `subsystem-*` | 注册、fixtures、最小 smoke 入口 | 仅通过公开接口接入 |
| `orchestrator` | 系统日频入口、Dagster runtime 启动方式 | 执行图装配归 orchestrator |
| `feature-store` / `stream-layer` | Full 模式可选 service bundle 与公开入口 | 仅在相应 profile 下启用 |

### 5.3 下游输出

| 目标 | 输出内容 | 消费方式 |
|------|----------|----------|
| 开发者 / 自动化代理 | 一键启动、profile 说明、环境模板、模块注册表 | CLI / 脚本 / 文件 |
| CI / reviewer | contract compatibility report、smoke report、e2e report | 测试入口 + artifacts |
| 本地 / 集成环境 | PostgreSQL、Neo4j、Dagster 等服务的系统级启动与健康检查 | compose / shell / Python CLI |
| 运维 / 架构 owner | 兼容矩阵、依赖清单、扩展路径文档 | Markdown + machine-readable manifest |

### 5.4 核心边界

- **`assembly` 只拥有系统总装，不拥有业务实现与编排策略**
- **`orchestrator` 负责执行图与 Gate policy，`assembly` 只负责把 `orchestrator` 作为运行入口装起来**
- **Lite/Full 差异通过 environment profile + service bundle 表达，不通过重写模块合同表达**
- **`assembly` 只依赖模块公开入口，禁止 import 模块私有内部**
- **模块注册表和兼容矩阵归 `assembly`，业务 schema 和算法真相不归 `assembly`**

---

## 6. 设计哲学

### 6.1 设计原则

#### 原则 1：Public-entrypoint-only

总装层可以认识所有模块，但只能认识它们愿意公开给系统集成层的那部分。  
一旦 assembly 直接 import 私有 package、私有脚本或内部表结构，模块边界就会在集成期被彻底打穿。

#### 原则 2：Profiles, Not Forked Architectures

Lite 和 Full 不是两套项目。  
它们应该是同一系统在不同 profile 下启用不同 service bundle 的结果，而不是写两套互不兼容的启动方式。

#### 原则 3：Assemble Reality, Not Documentation

系统是否可运行，不能靠 README 宣称，必须靠 bootstrap、health check、smoke test 和最小 e2e 真跑出来。  
assembly 的价值在于把“文档上的架构”收口成“机器可以启动和验证的系统”。

#### 原则 4：Registry Before Trust

模块数量一多，最大的集成风险不是代码本身，而是“不知道当前哪几个版本能一起工作”。  
所以 module registry 和 compatibility matrix 必须是 assembly 的一等对象，而不是散落在 issue 和聊天记录里。

#### 原则 5：Optional Services Stay Optional

主文档已经冻结了 Lite 的最小组件约束。  
因此 Grafana、Superset、Feast、Milvus、Temporal、Kafka/Flink 等只能通过 profile 显式开启，绝不能悄悄成为 Lite 启动前提。

#### 原则 6：System Tests Should Respect Module Ownership

assembly 做的是系统级测试，不是绕开模块作者去重新实现模块逻辑。  
因此 contract test、smoke test 和 e2e 必须基于模块公开入口构建，而不是复制模块内部逻辑。

### 6.2 反模式清单

| 反模式 | 为什么危险 |
|--------|-----------|
| 把 assembly 写成“另一个 orchestrator” | 运行入口、执行图和部署边界会混线 |
| 在 assembly 里复制模块私有启动逻辑 | 模块一改内部实现，总装层立刻断裂 |
| 用两套完全不同的 Lite / Full 启动方式 | 后续扩展会变成重新架构，不是 profile 增量 |
| 缺少 module registry，只靠口头记录集成状态 | 多模块并行开发后无法判断兼容组合 |
| 直接把 Full 服务写进 Lite 默认启动 | 破坏 1-3 人团队可控的基础约束 |
| 系统级测试绕过模块公开接口 | 失去对真实集成面的验证意义 |
| 用 assembly 保存业务阈值或业务常量 | 总装层侵入业务域，后续维护失控 |

---

## 7. 用户与消费方

### 7.1 直接消费方

| 消费方 | 消费内容 | 用途 |
|--------|----------|------|
| 开发者 | 启动脚本、profile、模块注册表、健康检查 | 本地开发与联调 |
| 自动化代理 | 统一 bootstrap / smoke / e2e 入口 | 多模块自动化开发后的系统集成 |
| reviewer / CI | 兼容矩阵、contract suite、system smoke | 集成验收 |
| 运维 / 架构 owner | 依赖清单、扩展路径、部署说明 | 部署与排障 |

### 7.2 间接用户

| 角色 | 关注点 |
|------|--------|
| 各模块 owner | 自己模块接入系统时需要哪些公开入口和健康探针 |
| 主编 / PM | 12+N 模块是否真的能拼成完整项目 |
| 研究与审计人员 | 最小整链是否可重复启动和复现 |

---

## 8. 总体系统结构

### 8.1 系统启动主线

```text
choose environment profile
  -> resolve env + secrets + storage paths
  -> load module registry + compatibility matrix
  -> build bootstrap plan
  -> start required service bundles
  -> start orchestrator / module public entrypoints
  -> run health checks
  -> emit resolved config snapshot + startup report
```

### 8.2 集成验证主线

```text
assembled environment
  -> run smoke tests
  -> run contract compatibility tests
  -> run minimal cycle e2e
  -> collect artifacts + reports
  -> mark profile/module readiness
```

### 8.3 Full 扩展主线

```text
lite-local profile
  -> add optional bundles by profile
  -> grafana / superset / temporal / feast / kafka-flink / milvus
  -> verify compatibility matrix
  -> keep module public contracts unchanged
```

关键点不是“把服务堆起来”，而是**让扩展发生在 profile 层，而不是让模块本身重新定义自己**。

---

## 9. 领域对象设计

### 9.1 持久层对象

| 对象名 | 职责 | 归属 |
|--------|------|------|
| EnvironmentProfile | 描述一个可运行档位的组件启用、配置来源和资源要求 | YAML / TOML |
| ModuleRegistryEntry | 描述单个模块的版本、依赖、公开入口和集成状态 | `MODULE_REGISTRY.md` + machine-readable manifest |
| CompatibilityMatrix | 描述模块版本与合同版本的兼容组合 | YAML / JSON / Markdown |
| ServiceBundleManifest | 描述一个 profile 下要启动的服务清单、依赖顺序和健康探针 | YAML / compose fragments |
| IntegrationRunRecord | 记录一次 smoke / contract / e2e 运行结果 | 文件 artifact / CI artifact |
| ResolvedConfigSnapshot | 记录某次 bootstrap 实际生效的配置快照 | 本地 artifact |

### 9.2 运行时对象

| 对象名 | 职责 | 生命周期 |
|--------|------|----------|
| AssemblyContext | 一次系统总装运行的上下文 | 单次 bootstrap / test run |
| BootstrapPlan | 启动计划与顺序 | 单次启动期间 |
| ServiceHandle | 某个已启动服务或进程的句柄 | 进程生命周期 |
| HealthCheckResult | 单项健康检查结果 | 单次检查期间 |
| CompatibilityReport | 一次兼容性验证结果 | 单次验证期间 |
| E2ERunContext | 一次最小整链运行上下文 | 单次 e2e 期间 |

### 9.3 核心对象详细设计

#### EnvironmentProfile

**角色**：系统运行档位的正式定义对象，决定要启用哪些模块、服务 bundle、配置覆盖和资源前提。

| 字段 | 类型 | 含义 |
|------|------|------|
| `profile_id` | string | profile 名称，如 `lite-local` |
| `mode` | enum | `lite` / `full` |
| `enabled_modules` | string[] | 当前 profile 允许接入的模块列表 |
| `enabled_service_bundles` | string[] | 要启用的基础服务 bundle |
| `required_env_keys` | string[] | 必填环境变量键 |
| `optional_env_keys` | string[] | 可选环境变量键 |
| `storage_backends` | object | PG / Iceberg / local SSD / MinIO 等配置 |
| `resource_expectation` | object | CPU / 内存 / 磁盘基线 |
| `max_long_running_daemons` | integer | Lite profile 固定为 `4`，除显式启用可选 bundle 外不得增加 |
| `notes` | string | 运行说明 |

**硬约束**：

- `lite-local` / `lite-dev` / `lite-integration` 的常驻基础进程固定为 4 个：PostgreSQL、Neo4j、Dagster daemon、Dagster webserver
- MinIO、Grafana、Superset、Temporal、Feast、Kafka/Flink 等只能通过额外 service bundle 显式开启，不能悄悄长进 Lite profile

#### ModuleRegistryEntry

**角色**：模块级系统接入事实的统一登记对象，用于回答“这个模块现在是否可被总装、以什么版本、在哪个 profile 下、具备哪些公开入口”。

| 字段 | 类型 | 含义 |
|------|------|------|
| `module_id` | string | 模块稳定标识，如 `contracts`、`subsystem-news` |
| `module_version` | string | 模块版本 |
| `contract_version` | string | 当前适配的合同版本 |
| `owner` | string | 当前模块 owner |
| `upstream_modules` | string[] | 上游依赖模块 |
| `downstream_modules` | string[] | 下游消费模块 |
| `public_entrypoints` | object[] | 可供 assembly 调用的公开入口 |
| `depends_on` | string[] | 模块依赖 |
| `supported_profiles` | string[] | 支持的 profile |
| `integration_status` | enum | not-started / partial / ready / verified / blocked |
| `last_smoke_result` | string | 最近 smoke 结果 |
| `notes` | string | 边界说明和未决事项 |

#### ServiceBundleManifest

**角色**：把基础服务与模块运行前提组成可复用 bundle，避免不同 profile 手写零散脚本。

| 字段 | 类型 | 含义 |
|------|------|------|
| `bundle_name` | string | bundle 名称 |
| `services` | object[] | 服务列表，如 PostgreSQL、Neo4j、Dagster |
| `startup_order` | string[] | 启动顺序 |
| `health_checks` | object[] | 探针定义 |
| `required_profiles` | string[] | 适用 profile |
| `optional` | bool | 是否可选 bundle |
| `shutdown_order` | string[] | 停止顺序 |

#### CompatibilityMatrix

**角色**：描述“哪些模块版本 + 合同版本 + profile 组合已经验证通过”，防止集成只能靠聊天记录追踪。

| 字段 | 类型 | 含义 |
|------|------|------|
| `matrix_version` | string | 兼容矩阵版本 |
| `profile_id` | string | 适用 profile |
| `module_set` | object[] | 模块与版本组合 |
| `contract_version` | string | 对应合同版本 |
| `required_tests` | string[] | 必须通过的 smoke / contract / e2e 套件 |
| `status` | enum | draft / verified / deprecated |
| `verified_at` | datetime | 最后验证时间 |

#### IntegrationRunRecord

**角色**：记录系统级验证的事实结果，为回归、排障和 readiness 更新提供依据。

| 字段 | 类型 | 含义 |
|------|------|------|
| `run_id` | string | 运行 ID |
| `profile_id` | string | 所用 profile |
| `run_type` | enum | smoke / contract / e2e |
| `started_at` | datetime | 开始时间 |
| `finished_at` | datetime | 结束时间 |
| `status` | enum | success / failed / partial |
| `artifacts` | object[] | 日志、报告、配置快照 |
| `failing_modules` | string[] | 失败模块 |
| `summary` | string | 结果摘要 |

---

## 10. 数据模型设计

### 10.1 文件与配置分层

`assembly` 的真相层以**文件化配置和集成 artifact**为主，而不是业务数据库表。

| 分层 | 内容 | 说明 |
|------|------|------|
| Profiles Layer | `EnvironmentProfile` 文件 | 决定 Lite / Full / local / integration 差异 |
| Registry Layer | `MODULE_REGISTRY.md` + machine-readable registry | 记录模块接入事实 |
| Bundle Layer | service bundle manifest、compose fragment、启动脚本 | 记录启动编排事实 |
| Env Layer | `.env.example`、模板、resolved snapshot | 记录环境注入事实 |
| Test Artifact Layer | smoke / contract / e2e 结果 | 用于回归和 readiness 更新 |

### 10.2 与其他模块的边界

- `assembly` 不拥有 PostgreSQL / Iceberg / Neo4j 的业务 schema。
- `assembly` 可以调用初始化脚本公开入口，但不直接维护其他模块的内部迁移逻辑。
- `assembly` 不维护各模块的单元测试数据；只维护系统集成层面的 fixtures 和报告。
- `assembly` 可以缓存 `ResolvedConfigSnapshot`、集成日志和报告，但这些不是业务审计真相层。

### 10.3 推荐文件形态

- `profiles/*.yaml` 或 `profiles/*.toml`
- `.env.example` 与 profile 覆盖模板
- `MODULE_REGISTRY.md`
- `module-registry.yaml` 或 `module-registry.json`
- `bundles/*.yaml` / `compose/*.yaml`
- `reports/smoke/*`、`reports/contract/*`、`reports/e2e/*`

---

## 11. 核心计算/算法设计

### 11.1 Profile 解析与配置合并

assembly 的第一步不是启动服务，而是先把 profile 解析清楚：

1. 读取 `EnvironmentProfile`
2. 校验必填 env key
3. 解析默认值与 profile override
4. 生成 `ResolvedConfigSnapshot`
5. 校验当前 profile 允许启用的模块和 bundle

关键约束：

- profile 只决定环境和组件启用关系，不改业务合同语义
- 缺失关键 env 时必须 fail-fast
- profile 结果必须可落盘，以支持后续排障和复现

### 11.2 模块注册表装载与兼容检查

在真正 bootstrap 前，assembly 必须先确认当前模块集合是“可装的”：

1. 读取 `ModuleRegistryEntry`
2. 校验模块是否支持当前 profile
3. 对比 `contract_version`
4. 对比依赖模块是否存在且状态足够
5. 输出 `CompatibilityReport`

拒绝启动的典型条件：

- 必需模块未登记
- 合同版本不兼容
- 某模块只声明支持 Full profile，却被放进 Lite profile
- 依赖模块处于 blocked 状态

### 11.3 服务 bundle 启动顺序

主文档已经冻结了 Lite 模式的基础服务形态，因此 Lite profile 的典型顺序应是：

```text
filesystem paths / env ready
  -> PostgreSQL
  -> Neo4j
  -> Dagster daemon + webserver
  -> orchestrator entrypoint
  -> module public smoke probes
```

说明：

- DuckDB、dbt Core 属于嵌入式或 Python 包，不应被错误建模成独立 daemon
- Iceberg 是存储格式与 catalog 组合，不应被错误建模成独立服务进程
- 如果 profile 启用了 MinIO、Grafana、Superset、Kafka/Flink 等，则通过额外 service bundle 加入

### 11.4 健康检查收敛

启动不等于可用。  
assembly 必须显式等待系统收敛到“可接受的最小健康态”：

1. 基础服务存活
2. 端口和连接可达
3. `orchestrator` 最小入口可加载
4. 关键模块 smoke probe 返回成功
5. profile 中要求的可选服务若已启用，也必须通过各自探针

健康检查结果应分级：

- `healthy`
- `degraded`
- `blocked`

`degraded` 只允许出现在 profile 明确允许的可选组件上，核心 Lite 服务一旦失败应直接 `blocked`。

### 11.5 Contract Compatibility Test

assembly 不拥有业务合同，但拥有“系统级接口兼容是否仍成立”的验证责任。

该测试至少应覆盖：

- `contracts` 版本与模块声明是否一致
- `subsystem-sdk` 与 Layer B submit/receipt 语义是否兼容
- `orchestrator` 是否仍能加载各模块公开入口
- `main-core` / `graph-engine` / `audit-eval` 等公开接口是否仍在兼容矩阵允许范围内

重点验证的是**边界兼容性**，不是业务准确率。

### 11.6 Minimal Cycle E2E

Minimal Cycle E2E 是 assembly 的最高级别系统验收：

```text
bootstrap lite profile
  -> load minimal fixtures
  -> run orchestrator minimal daily cycle
  -> verify phase progression
  -> verify key artifacts exist
  -> collect logs / reports / config snapshot
```

最小 e2e 不要求跑全市场，也不要求外部付费源都在线，但必须能证明：

- 系统可以从启动进入最小日频执行
- 关键 phase 顺序没有断裂
- 关键模块公开入口能协同工作
- 最小 formal / audit / trace 路径成立

### 11.7 Version Lock 与兼容冻结

随着模块增多，assembly 需要显式沉淀版本锁定：

1. 记录模块版本
2. 记录合同版本
3. 记录 profile 兼容组合
4. 记录当前验证通过的测试套件版本

这里的 Version Lock 更偏**系统兼容层**，不是替代各模块内部依赖 lockfile。

### 11.8 Full 扩展的装配策略

当系统进入 Full 模式时，assembly 只做以下事情：

- 新增 profile
- 新增 service bundle
- 更新兼容矩阵
- 更新 smoke / e2e 路径

明确不做：

- 不在 assembly 中实现 `feature-store` 逻辑
- 不在 assembly 中实现 `stream-layer` 逻辑
- 不把 Full 可选组件硬写回 Lite 默认路径

---

## 12. 触发/驱动引擎设计

### 12.1 本地 bootstrap 触发

```text
developer / agent
  -> choose profile
  -> bootstrap
  -> healthcheck
```

这是最基础的触发方式，用于本地开发、联调和自动化代理集成。

### 12.2 CI 集成验证触发

```text
pull request / integration branch
  -> load profile
  -> run contract compatibility suite
  -> run smoke suite
  -> optional minimal cycle e2e
```

CI 的职责不是跑最重场景，而是尽早发现“模块拼不起来”的集成问题。

### 12.3 发布前验收触发

```text
release candidate
  -> verify compatibility matrix
  -> bootstrap target profile
  -> run required e2e suite
  -> freeze version lock
```

### 12.4 档位切换触发

当系统从 Lite 扩到 Full 某个阶段时，触发的不是“重做架构”，而是：

1. 创建或更新 Full profile
2. 加入新的 service bundle
3. 更新 registry 与 compatibility matrix
4. 增补对应 smoke/e2e

---

## 13. 输出产物设计

### 13.1 系统启动与环境产物

| 产物 | 说明 |
|------|------|
| bootstrap 入口 | 一键启动命令、脚本或 CLI |
| profile 文件 | Lite / Full / local / integration 配置 |
| `.env.example` | 环境变量模板 |
| resolved config snapshot | 本次实际生效配置快照 |

### 13.2 集成治理产物

| 产物 | 说明 |
|------|------|
| `MODULE_REGISTRY.md` | 模块注册表，人类可读 |
| machine-readable registry | 供脚本消费的注册表 |
| compatibility matrix | 模块/合同/profile 兼容矩阵 |
| version lock 说明 | 当前验证通过的系统级版本冻结 |

### 13.2.1 `MODULE_REGISTRY` 初版最低要求

`MODULE_REGISTRY` 是阶段 0 的第一份交付物。  
在任何模块进入 verified compatibility matrix 之前，必须先生成首版 registry。

首版 registry 至少覆盖当前已冻结的 **12 个固定长期模块 + 首批 N=2 子系统 = 14 个项目**：

- `contracts`
- `data-platform`
- `entity-registry`
- `reasoner-runtime`
- `graph-engine`
- `main-core`
- `audit-eval`
- `subsystem-sdk`
- `orchestrator`
- `assembly`
- `feature-store`
- `stream-layer`
- `subsystem-announcement`
- `subsystem-news`

首版规则：

- 未开工模块统一登记为 `integration_status = not-started`
- 首版 `contract_version` 可登记为 `v0.0.0`，待对应模块冻结后再升级
- `MODULE_REGISTRY.md` 与 machine-readable registry 必须共享同一语义字段，不允许两套真相

### 13.2.2 跨文档统一对照表

#### Evidently 三层分工表

| 层级 | 职责 | owner | 对当轮运行的影响 |
|------|------|-------|------------------|
| 第一层 | 预处理、统计基线、窗口整理 | `data-platform` | 无，属于前置数据准备 |
| 第二层 | 写 `feature_weight_multiplier` 等在线控制字段 | `main-core.l3_features` | 有，直接影响当轮运行 |
| 第三层 | 报告定义、阈值、结构性告警 | `audit-eval` | 无，只输出评估和告警资产 |

#### L6 analyzer 合同对照表

| 关注点 | source of truth | 稳定要求 |
|--------|-----------------|----------|
| `analyze(stock, context) -> alpha_result` 合同与结果字段 | `contracts` | 结果字段固定为 `score`、`direction`、`confidence`、`rationale`、`evidence_refs`、`analyzer_name`、`analyzer_version` |
| `analyzer_type` 默认值与业务路由 | `main-core` | P2 默认 `single_prompt_v1`，后续扩展不得改写合同字段 |
| 结构化执行、lineage、replay bundle | `reasoner-runtime` | 只提供运行时执行与回放资产，不重定义分析业务字段 |

#### 编号对照表

| 编号族 | 用途 | 示例 | 说明 |
|--------|------|------|------|
| `module_id` | registry 内唯一模块标识 | `graph-engine` | `assembly` 的唯一系统级真相键 |
| `M##` | 架构讨论中的长期模块别名 | `M05` | 仅作为文档别名存在，如需使用应映射到唯一 `module_id` |
| `N##` | 具体子系统别名 | `N01` | 用于首批或后续子系统排序，不替代 `module_id` |
| `P##` / `P#a#b` | 实施波次编号 | `P1a`、`P2c` | 只表示施工顺序，不表示 repo / 项目身份 |

### 13.3 验证产物

| 产物 | 说明 |
|------|------|
| smoke report | 基础健康与入口验证结果 |
| contract compatibility report | 边界兼容验证结果 |
| minimal cycle e2e report | 最小整链运行结果 |
| logs / artifacts index | 运行日志和报告索引 |

### 13.4 运维与排障产物

| 产物 | 说明 |
|------|------|
| startup guide | 启动说明 |
| troubleshooting guide | 常见故障与排查路径 |
| service dependency doc | 服务依赖图与顺序 |
| profile comparison doc | Lite / Full 差异说明 |

---

## 14. 系统模块拆分

| 模块 | 责任 |
|------|------|
| `assembly.profiles` | profile 定义、env 覆盖、资源要求 |
| `assembly.registry` | `MODULE_REGISTRY` 与 compatibility matrix |
| `assembly.bootstrap` | 系统启动、停止、依赖顺序 |
| `assembly.health` | 健康检查与收敛判定 |
| `assembly.compat` | contract compatibility suite |
| `assembly.tests.smoke` | 系统级 smoke test |
| `assembly.tests.e2e` | minimal cycle e2e |
| `assembly.docs` | 启动说明、排障文档、profile 文档 |

模块边界要求：

- `profiles` 只定义配置，不启动服务
- `bootstrap` 只做系统启动与停止，不写模块业务逻辑
- `compat` 只测边界兼容，不测业务正确率
- `tests.e2e` 只能通过模块公开入口跑整链

---

## 15. 存储与技术路线

### 15.1 配置与清单技术

- YAML / TOML 管理 profile、bundle、registry、compatibility matrix
- `.env` 模板管理环境变量
- Markdown 维护人类可读的 module registry 与运维说明

### 15.2 启动与脚本技术

- Python CLI 作为主入口
- Shell / Makefile 作为便捷包装层
- `docker compose` 或等价本地脚本作为服务 bundle 启动方式之一

### 15.3 测试技术

- `pytest` 或等价测试框架承载 smoke / contract / e2e
- 日志与报告落盘为文件 artifact
- 不引入额外“系统测试专属平台”作为首版依赖

### 15.4 与主文档部署架构的对应

- Lite profile 对齐主文档附录 F.1：单节点，核心服务为 PostgreSQL、Neo4j、Dagster
- Lite profile 的常驻基础进程固定为 4 个：PostgreSQL、Neo4j、Dagster daemon、Dagster webserver
- Full profile 对齐附录 F.2：在 Lite 基础上按需追加 Grafana、Superset、Temporal、Feast、Milvus、Kafka/Flink 等 bundle
- DuckDB、dbt Core、模块业务代码继续作为嵌入式或 worker 内逻辑，不提升为独立常驻 daemon

### 15.5 明确不引入的路线

- 不在 assembly 内自建第二套服务发现系统
- 不在 assembly 内维护业务数据库 schema
- 不在 assembly 内直接封装模块私有管理脚本为长期接口

---

## 16. API 与接口合同

### 16.1 对外接口

| 接口 | 输入 | 输出 | 约束 |
|------|------|------|------|
| `list_profiles()` | 无 | `EnvironmentProfile[]` | 返回已登记 profile |
| `render_profile(profile_id)` | profile 名称 | `ResolvedConfigSnapshot` | 缺关键 env 时 fail-fast |
| `bootstrap(profile_id)` | profile 名称 | `BootstrapResult` | 只通过公开入口启动系统 |
| `healthcheck(profile_id)` | profile 名称 | `HealthCheckResult[]` | 必须区分 healthy/degraded/blocked |
| `export_module_registry()` | 无或 profile 名称 | registry artifact | 输出人类可读 + machine-readable 版本 |
| `run_contract_suite(profile_id)` | profile 名称 | `CompatibilityReport` | 只验证公开边界 |
| `run_smoke(profile_id)` | profile 名称 | smoke report | 只做快速系统验证 |
| `run_min_cycle_e2e(profile_id)` | profile 名称 | e2e report | 通过模块公开入口跑整链 |

### 16.2 对模块公开入口的依赖接口

| 接口类型 | 目的 |
|----------|------|
| health probe | 统一判断模块最小可用性 |
| init/bootstrap hook | 模块需要的最小初始化 |
| smoke hook | 模块最小可运行检查 |
| version/contract declaration | 写入 registry 和 compatibility matrix |

### 16.3 接口硬约束

- assembly 不得依赖未登记的私有入口
- registry 缺 `contract_version` 的模块不得进入 verified compatibility matrix
- `MODULE_REGISTRY` 初版未建立前，不得声称存在 verified 的系统级兼容组合
- `run_min_cycle_e2e()` 不得绕过 `orchestrator`
- Lite profile 不得要求 Full 可选组件存在

---

## 18. 测试与验证策略

### 18.1 测试层级

1. **Profile 解析测试**：验证环境变量、覆盖关系和必填键校验
2. **Registry 一致性测试**：验证模块、依赖、合同版本、profile 声明是否一致
3. **Bootstrap 顺序测试**：验证服务 bundle 启动与停止顺序
4. **Health Check 测试**：验证健康探针与状态分级
5. **Contract Compatibility Test**：验证模块公开接口与合同版本兼容
6. **Smoke Test**：验证 Lite profile 的最小服务组合可用
7. **Minimal Cycle E2E**：验证最小日频整链可跑

### 18.2 重点测试样本

| 样本类型 | 验证内容 |
|----------|----------|
| Lite 本地 profile | 单节点最小系统能启动 |
| 缺 env 样本 | fail-fast 是否生效 |
| 版本不兼容样本 | registry / compatibility matrix 是否拦截 |
| 可选服务关闭样本 | Lite 不应被 Full 组件阻塞 |
| 模块私有入口误用样本 | assembly 是否错误依赖私有实现 |
| 最小 cycle fixture | 是否能完整跑通 e2e |

### 18.3 验证原则

- 系统级测试只验证 assembly 承诺的那层，不复制模块内部测试
- 任何 profile 变更都必须伴随 smoke 或 contract suite 更新
- compatibility matrix 进入 `verified` 前，必须有实际运行记录支撑

---

## 19. 关键评价指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| Lite bootstrap success rate | >= 95% | 参考开发机上的 Lite 启动成功率 |
| Required env completeness | 100% | 必填环境变量缺失必须被拦截 |
| Registry coverage | 100% | 已进入集成的模块都必须登记到 registry |
| Contract suite pass rate | 100% | verified 组合必须全部通过 |
| Minimal cycle e2e pass rate | >= 95% | 冻结 fixture 上的整链成功率 |
| Lite health convergence time | <= 10 分钟 | 从 bootstrap 到核心服务 healthy |
| Optional-service isolation | 100% | Full 可选组件故障不影响 Lite profile |

---

## 20. 项目交付物清单

| 交付物 | 内容 | 验收方式 |
|--------|------|----------|
| environment profiles | Lite / Full / local / integration 配置 | 配置评审 |
| bootstrap 入口 | CLI、脚本、compose 或等价入口 | 本地启动验证 |
| `MODULE_REGISTRY.md` | 模块注册表（Phase 0 首个交付物） | 文档审查 |
| compatibility matrix | 模块/合同/profile 兼容矩阵 | 集成评审 |
| health + smoke suite | 健康检查和基础验证套件 | 自动运行通过 |
| minimal cycle e2e suite | 最小整链验收 | e2e 报告通过 |
| startup / troubleshooting docs | 启动说明与故障排查文档 | 文档审查 |

---

## 21. 实施路线图

### 阶段 0：系统级入口冻结

- 冻结 module registry 字段
- 冻结 profile 结构
- 冻结各模块需要公开给 assembly 的最小入口
- 产出首版 `MODULE_REGISTRY`，覆盖 12 个固定长期模块和首批 `N=2` 子系统，初始未开工项统一标记 `not-started`

### 阶段 1：Lite profile 与 bootstrap

- 建立 `lite-local` profile
- 对齐主文档附录 F.1
- 跑通 PostgreSQL、Neo4j、Dagster 的基础启动

### 阶段 2：registry + health + smoke

- 落地 `MODULE_REGISTRY.md`
- 落地兼容矩阵
- 落地基础健康检查和 smoke suite

### 阶段 3：contract compatibility + minimal e2e

- 对接 `contracts` 版本检查
- 对接模块公开入口兼容性验证
- 建立最小 cycle e2e

### 阶段 4：Full 扩展 profile

- 新增 Grafana / Superset profile
- 新增 Temporal / feature-store / stream-layer 对应 bundle 槽位
- 不改变现有 Lite 合同边界

### 阶段 5：系统级发布与运维材料完善

- 完善版本锁定说明
- 完善 troubleshooting 文档
- 把 verified compatibility matrix 作为正式集成基线

---

## 22. 主要风险

| 风险 | 描述 | 应对 |
|------|------|------|
| 模块公开入口不稳定 | assembly 被迫依赖内部实现 | 先冻结公开入口，再允许接入 |
| profile 漂移 | 环境差异散落到脚本和文档 | profile 文件化、版本化 |
| Lite 被 Full 污染 | 可选组件反向成为基础依赖 | 严格分离 service bundle |
| registry 失真 | 模块状态与实际集成状态不一致 | 所有 verified 状态都要绑定运行记录 |
| e2e 过重 | 系统级验收过慢导致形同虚设 | 保持 minimal cycle 路线，控制 fixture 规模 |
| 总装越界 | assembly 慢慢吸收业务逻辑 | 坚持 public-entrypoint-only 和非目标约束 |

---

## 23. 验收标准

1. 能通过统一入口在参考开发机上启动 Lite profile，并让 PostgreSQL、Neo4j、Dagster 进入健康状态。
2. 能输出 `MODULE_REGISTRY.md` 和 machine-readable registry，覆盖当前 12 个固定长期模块和首批 `N=2` 子系统及其合同版本、集成状态。
3. 能通过 profile 与 compatibility matrix 显式拦截不兼容的模块组合或缺失环境变量。
4. 能运行 contract compatibility suite 与 smoke suite，并生成可追溯报告。
5. 能在 Lite profile 上跑通最小 daily cycle e2e，证明系统不是“模块齐全但无法拼装”。
6. 能通过 profile 方式预留 Full 组件接入，不要求改写现有模块公共合同。
7. assembly 实现中不复制业务 contract、不承载业务逻辑、不侵入模块私有内部。

---

## 24. 一句话结论

`assembly` 应被定义为一个**只拥有系统总装、环境 profile、兼容矩阵、健康检查和系统级验收入口，把 12+N 个独立模块真实拼成一套可启动、可验证、可扩展系统，但坚决不越界吞并业务实现或编排策略**的系统项目。

---

## 25. 自动化开发对接

### 25.1 自动化输入契约

| 项 | 规则 |
|----|------|
| `module_id` | `assembly` |
| 脚本先读章节 | `§1` `§4` `§5.2` `§5.4` `§9` `§13` `§14` `§16` `§18` `§21` `§23` |
| 默认 issue 粒度 | 一次只实现一个 profile / registry / bootstrap / health / compat / smoke / e2e 能力 |
| 默认写入范围 | 当前 repo 的 profile 文件、registry、启动脚本、健康检查、测试、文档和系统配置 |
| 内部命名基线 | 以 `§14` 的内部模块名和 `§9` 的对象名为准，`module_id` 是唯一系统级真相键 |
| 禁止越界 | 不侵入模块私有内部、不复制业务 contract、不长出新业务逻辑或新默认 daemon |
| 完成判定 | 同时满足 `§18`、`§21` 当前阶段退出条件和 `§23` 对应条目 |

### 25.2 推荐自动化任务顺序

1. 先产出首版 `MODULE_REGISTRY` 和 `EnvironmentProfile`
2. 再落 bootstrap、healthcheck、contract suite 和 smoke 主干
3. 再落 minimal cycle e2e 和 troubleshooting / startup 文档
4. 最后补 Full profile 槽位与可选 service bundle

补充规则：

- 单个 issue 默认只改一个总装能力，不把 registry、bootstrap、e2e 混成大 PR
- Lite profile 未稳定前，不进入 Full bundle、可选服务或扩展 dashboard 类 issue

### 25.3 Blocker 升级条件

- 需要依赖其他模块私有入口、私有脚本或未登记接口
- Lite profile 需要新增未冻结的长期 daemon 或默认开启 Full 组件
- `MODULE_REGISTRY` 初版尚未建立却要宣称 verified 兼容组合
- 无法给出 bootstrap / health / smoke / e2e 的最小可重复执行命令
