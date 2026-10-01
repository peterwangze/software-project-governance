# 回滚方案 — 0.44.0

**版本**: 0.44.0
**范围**: Composable Governance Packs release package

## 回滚触发条件

- `check-version-consistency` 或 `check-release --version 0.44.0 --require-changelog --runtime-adapters` 在本地或干净 checkout 中失败。
- 发布后发现 source SKILL、canonical manifest、Claude/Codex plugin manifests、target fixture/projection 或 hook @version 仍停留在 0.43.0 或互相漂移。
- Pack registry 缺失、未被 manifest 声明为 canonical product artifact、未被 git 跟踪，或引用不存在文件/未知检查。
- `governance-context` 或 `/governance`/status 被确认编造 unfinished work，或在 open risk / blocked fact 存在时错误允许 auto-continue。
- README、status、release docs 或 release readiness 被确认把 pack enabled / pack membership 声明为任务证据、独立审查、质量门禁、发布门禁、official approval、marketplace approval、universal/full runtime support 或 1.0.0 production-ready。
- 发布提交混入 0.45.0 governance benchmark、Codex Desktop marketplace-management E2E PASS、0.46.0 official submission 或 1.0.0 changes。

## 回滚步骤

1. 回滚 0.44.0 发布提交：

```bash
git revert <0.44.0-release-commit>
```

2. 如 tag 已发布且必须撤销：

```bash
git tag -d v0.44.0
git push origin :refs/tags/v0.44.0
```

3. 复跑门禁并确认回到 0.43.0 package baseline：

```bash
python skills/software-project-governance/infra/verify_workflow.py verify
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.43.0 --require-changelog --runtime-adapters
python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues
git diff --check
```

4. 如仅 pack registry 或 release docs 文案越界，可先回滚 0.44.0 release commit；不要局部删除 `governance-packs.json` 而保留 0.44.0 version declarations，否则后续 freshness 和 release gate 会出现事实源漂移。

## 数据边界

`.governance/` 是运行态记录，不随产品发布提交。本回滚只处理产品/release package 文件；历史 governance evidence 可保留，用于说明 0.44.0 的发布准备、验证与回滚事实。

## 风险边界

回滚 0.44.0 不关闭 RISK-036。该风险的关闭标准仍依赖官方提交包齐备、至少 2 个外部项目验证通过、主流入口矩阵公开且不夸大能力、Codex Desktop 插件市场管理真实 E2E PASS 或明确 blocked 且官方提交包保守声明、README/manifest 能清晰表达 delivery trust layer 差异化。
