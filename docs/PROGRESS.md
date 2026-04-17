# assembly 项目进度总览

> 本文件跟踪 `assembly` 系统总装模块的阶段状态与 Issue 清单。详情见 [TASK_BREAKDOWN.md](./TASK_BREAKDOWN.md)。
> module_id: `assembly`
> 首版覆盖范围：12 固定长期模块 + N=2 子系统 = 14 项

## 阶段总览

| 阶段 | 名称 | 状态 | Issues | 退出条件 |
|------|------|------|--------|----------|
| 阶段 0 | 系统级入口冻结 | not-started | ISSUE-001, ISSUE-002, ISSUE-003 | profile schema / 模块公开入口契约 / 首版 MODULE_REGISTRY 覆盖 14 项（未开工项 `not-started`） |
| 阶段 1 | Lite profile 与 bootstrap | not-started | ISSUE-004, ISSUE-005 | lite-local 下 PostgreSQL / Neo4j / Dagster daemon / Dagster webserver 4 常驻进程 healthy |
| 阶段 2 | registry + health + smoke | not-started | ISSUE-006, ISSUE-007 | registry 覆盖率 100%、smoke 自动可运行 |
| 阶段 3 | contract compatibility + minimal e2e | not-started | ISSUE-008, ISSUE-009 | contract suite pass 100%、minimal cycle e2e 可在冻结 fixture 上运行 |
| 阶段 4 | Full 扩展 profile 与可选 bundle 槽位 | not-started | ISSUE-010 | 不改变 Lite 合同边界 |
| 阶段 5 | 发布与运维材料完善 | not-started | ISSUE-011 | 文档可评审、版本锁定可追溯、verified matrix 成为集成基线 |

## Issue 清单

| Issue | 标题 | 阶段 | 优先级 | 状态 | 依赖 |
|-------|------|------|--------|------|------|
| ISSUE-001 | 冻结 EnvironmentProfile / ServiceBundle schema 与 profile 目录结构 | 阶段 0 | P0 | not-started | 无 |
| ISSUE-002 | 产出首版 MODULE_REGISTRY 与 machine-readable registry（14 模块 + 兼容矩阵骨架） | 阶段 0 | P0 | not-started | #ISSUE-001 |
| ISSUE-003 | 冻结模块公开入口契约（PublicEntrypoint 协议 + 阶段 0 文档） | 阶段 0 | P0 | not-started | #ISSUE-001, #ISSUE-002 |
| ISSUE-004 | 落地 lite-local profile 与 service bundle manifest（含 .env.example） | 阶段 1 | P0 | not-started | #ISSUE-001, #ISSUE-002 |
| ISSUE-005 | 实现 bootstrap CLI 与服务启动编排（`assembly` 命令行入口） | 阶段 1 | P0 | not-started | #ISSUE-004 |
| ISSUE-006 | 实现 registry / compatibility matrix 运行时装载与 `export_module_registry()` | 阶段 2 | P0 | not-started | #ISSUE-002, #ISSUE-005 |
| ISSUE-007 | 健康检查收敛器与系统级 smoke suite | 阶段 2 | P0 | not-started | #ISSUE-005, #ISSUE-006 |
| ISSUE-008 | Contract compatibility suite（`assembly.compat`） | 阶段 3 | P0 | not-started | #ISSUE-006, #ISSUE-007 |
| ISSUE-009 | Minimal cycle e2e（通过 orchestrator 公开入口跑最小日频链） | 阶段 3 | P0 | not-started | #ISSUE-008 |
| ISSUE-010 | Full profile 与可选 service bundle 槽位（full-dev + 6 个可选 bundle） | 阶段 4 | P1 | not-started | #ISSUE-009 |
| ISSUE-011 | Version lock / troubleshooting / startup / profile 对比文档与 release 工作流 | 阶段 5 | P1 | not-started | #ISSUE-010 |

## 关键评价指标基线

| 指标 | 目标值 | 当前 |
|------|--------|------|
| Lite bootstrap success rate | >= 95% | n/a |
| Required env completeness | 100% | n/a |
| Registry coverage | 100%（14 项） | n/a |
| Contract suite pass rate | 100% | n/a |
| Minimal cycle e2e pass rate | >= 95% | n/a |
| Lite health convergence time | <= 10 分钟 | n/a |
| Optional-service isolation | 100% | n/a |

## Blocker 升级条件（摘录 CLAUDE.md）

- 需要依赖其他模块私有入口、私有脚本或未登记接口
- Lite profile 需要新增未冻结的长期 daemon，或默认开启 Full 可选组件
- `MODULE_REGISTRY` 初版尚未建立却要声称 verified 兼容组合
- 无法给出 bootstrap / health / smoke / e2e 的最小可重复执行命令
