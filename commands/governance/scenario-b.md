# Scenario B: 半途接入

> 本文件不在默认注入面——命中 `scenario_hint == "B"` 后按路由层契约 Read。
> 完整执行规程：原 `## Scenario B: 半途接入` 节逐字搬移（零语义丢失）。

## Scenario B: 半途接入

**检测条件**：`.governance/` 不存在 AND 项目有文件/commit 历史

**流程**：

### Step B1: 探索项目

读取以下信号自动推断项目状态（不依赖用户知道阶段术语）：

| 信号 | 读取方式 | 用途 |
|------|---------|------|
| 技术栈 | 读取 `package.json`/`pyproject.toml`/`Cargo.toml`/`go.mod` 等 | 确定语言、框架、依赖数量 |
| 目录结构 | `ls -la` 顶级目录 + 关键子目录 | 确定项目组织方式 |
| Git 历史 | `git log --oneline -20`, `git tag -l`, `git rev-list --count HEAD` | 确定项目成熟度 |
| 测试基础设施 | 搜索 `test/`, `tests/`, `spec/`, `__tests__/`, `*_test.*`, `*.spec.*` | 确定测试覆盖 |
| CI/CD | 搜索 `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, `Dockerfile` | 确定自动化成熟度 |
| 发布历史 | `git tag -l`, `project/CHANGELOG.md`, `VERSION` 文件 | 确定发布阶段 |
| 文档 | 搜索 `README.md`, `docs/`, `ARCHITECTURE.md`, `CONTRIBUTING.md` | 确定文档成熟度 |
| 项目配置 | 读取 `README.md` 前 50 行——项目名称和一句话描述 | 确定项目目标 |

### Step B2: 推断当前阶段

根据信号矩阵推断（按优先级从上到下匹配）：

| 阶段推断 | 匹配信号 |
|---------|---------|
| **维护** (11) | git log 显示大量 "fix"/"bug"/"patch" commit + 有 release tag |
| **运营** (10) | 有 monitoring/observability 配置 + 有 Dockerfile/k8s + 有 release |
| **发布** (9) | 有 git tag + 有 CHANGELOG + 有 CI/CD |
| **CI/CD** (8) | 有 `.github/workflows/` 或等效 + CI 配置完整 |
| **测试** (7) | 有 test/ 目录 + 测试文件 > 10 + 有 CI |
| **开发** (6) | 有源代码文件 > 10 + 无测试 或 测试很少 |
| **架构设计** (5) | 有 `ARCHITECTURE.md` 或 `docs/architecture/` |
| **基础设施** (4) | 有 `Dockerfile` + `docker-compose.yml` + 环境配置脚本 |
| **技术选型** (3) | 只有依赖文件 + README，源代码 < 5 文件 |
| **调研** (2) | 有 `research/` 目录或调研文档 |
| **立项** (1) | 只有 README 和项目章程，无代码 |

多信号匹配 → 取最成熟的阶段。模糊 → 使用 lifecycle.md 的阶段判定 checklist。

### Step B3: 展示阶段推断

通过 AskUserQuestion 展示发现并让用户确认：

```
项目探索结果：
- 技术栈: {language} + {framework}
- Git: {N} commits, {M} tags
- 测试: {has_tests? 有/无}
- CI/CD: {has_ci? 有/无}

推断当前阶段: **{stage_name}** ({stage_number}/11)

原因: {evidence_summary}

是否准确？
(1) 准确——继续
(2) 调整为: [11 阶段选择]
```

### Step B4: 收集治理参数

单面板 AskUserQuestion（同 Scenario A Step 1）：
- profile: lightweight / standard / strict
- trigger_mode: always-on / on-demand / silent-track
- permission_mode: maximum-autonomy / default-confirm

(project_type 固定为 "existing", current_stage 已从 B3 确定)

### Step B5: 创建 .governance/ 并执行 onboarding

按 profile 差异化执行（参考 `core/onboarding.md`）：

**所有 profile**：
- 创建 4 个治理文件（plan-tracker/evidence-log/decision-log/risk-log）
- plan-tracker: 当前阶段 = B3 确认的阶段，前置 Gate = passed-on-entry
- decision-log: DEC-001 onboarding 声明

**standard + strict 额外**：
- 当前阶段 ≥ 1 条决策 + ≥ 1 条风险 + ≥ 1 条证据
- 前置阶段各 ≥ 1 条关键决策

**strict 额外**：
- 前置阶段各 ≥ 1 条决策 + ≥ 1 条风险
- 当前阶段 ≥ 2 条证据

### Step B6-B7: 注入 bootstrap + 安装 hooks

同 Scenario A Step 7-8。

### Step B8: 接入确认

输出面板：
- 阶段映射: {inferred_stage} — {gate_status}
- 已创建: plan-tracker(含 onboarding 声明) + evidence-log + decision-log + risk-log
- Bootstrap: 平台原生入口文件 已注入
- Hooks: pre-commit + commit-msg + post-commit 已安装
- 下一步: 当前阶段子工作流可供使用

**输出**：阶段映射面板 + 已创建文件清单 + onboarding 决策记录

接入完成后 **MUST 自动衔接 Scenario F**——展示治理面板 → 引导用户进入下一步。
