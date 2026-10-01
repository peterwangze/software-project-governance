# 回滚方案 — 0.44.1

**版本**: 0.44.1
**范围**: Patch release package for FIX-113, FIX-114, REL-021

## 回滚触发条件

- `check-version-consistency` 或 `check-release --version 0.44.1 --require-changelog --runtime-adapters --skip-execution-gates` 在本地或干净 checkout 中失败。
- 发布后发现 source SKILL、canonical manifest、Claude/Codex plugin manifests、marketplace metadata、target fixture/projection 或 hook @version 仍停留在 0.44.0 或互相漂移。
- `governance-packs.json` 的 workflow version 或 release validation command 与 0.44.1 release package 不一致。
- 0.44.1 release docs 或 CHANGELOG 声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success、Codex Desktop marketplace-management E2E PASS 或 1.0.0 production-ready。
- 发布提交混入 0.45.0 governance benchmark、Codex Desktop marketplace-management E2E PASS、0.46.0 official submission、1.0.0 changes，或任何不属于 FIX-113/FIX-114/REL-021 release package 的产品语义变更。

## 回滚步骤

1. 回滚 0.44.1 release package commit：

```bash
git revert <0.44.1-release-package-commit>
```

2. 如 tag 已发布且必须撤销：

```bash
git tag -d v0.44.1
git push origin :refs/tags/v0.44.1
```

3. 复跑门禁并确认回到 0.44.0 package baseline：

```bash
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.44.0 --require-changelog --runtime-adapters
python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -k ProjectionSync -v
git diff --check
```

4. 如果仅 release docs 文案越界，优先回滚 release package commit 并重新准备 conservative patch release docs；不要局部保留 0.44.1 version declarations，否则后续 freshness、projection sync 和 release gate 会出现事实源漂移。

## 数据边界

`.governance/` 是运行态记录，不随本 patch release package 修改。本回滚只处理产品/release package 文件；历史 governance evidence 可保留，用于说明 FIX-113、FIX-114 和 REL-021 的准备、验证与回滚事实。

## 风险边界

回滚 0.44.1 不关闭 RISK-036。该风险的关闭标准仍依赖官方提交包齐备、至少 2 个外部项目验证通过、主流入口矩阵公开且不夸大能力、Codex Desktop 插件市场管理真实 E2E PASS 或明确 blocked 且官方提交包保守声明、README/manifest 能清晰表达 delivery trust layer 差异化。
