# Rollback Plan — 0.90.0

- **日期**: 2026-09-27 · **回滚分类**: 可逆发布（无数据迁移/schema 变更——迁移工具协议戳 0.65.0 未动，DEC-257）

## 发布前回滚（任一门禁 FAIL）

fail-closed 阻断——修复后重跑门禁，不跳门（release-checklist 纪律）。候选态发现问题的回滚 = 丢弃候选 commit（`git reset`）或修复追加，无外部影响。

## 发布后回滚（tag 已推）

1. **插件面（消费者）**: 用户侧 `/plugin update` 回退到 0.89.0（marketplace 历史版本可得）；本版无破坏性行为变更（B-12/B-13 未激活、迁移 apply/rollback 语义与退出码不变——FEAT-070/071 向后兼容钉），回退无数据兼容风险
2. **仓库面（维护者）**: tag 误推 → 删 remote tag 重打；**历史 tag 变更必须有独立 DEC**（release-checklist 纪律，缺 DEC 不创建/不改 tag）
3. **发布后缺陷**: hotfix 0.90.1 路径——**不重写已发布 tag**

## 迁移工具面（如已在外部宿主使用 0.90.0 迁移功能）

- `--rollback` 旗标：迁移恢复路径（restored_from 留痕；FIX-398 后含孤儿清扫与自愈，回滚语义不变）
- 自愈重入（E-4）：中断态重入 apply 自动补偿——如需放弃迁移：`--rollback`（数据面=恢复迁移前快照，纯减法补偿不触碰用户数据，P7 已审）
- unit 清单（manifest）：宿主域数据（gitignored）——如需重置：删除 manifest 文件后经 `--record-unit-*` 链路重建（28 次调用可复演，EVD-1199）

## 数据兼容性

无 schema 变更；`.governance/` 治理记录格式无破坏性变更（新增 manifest 文件为增量）；bootstrap 升级路径（0.89→0.90）经宿主标记同步验证（check-version-consistency PASS）。

## 回滚影响评估

回滚唯一影响面=放弃本版新判据面（RB-2 可观测/自愈/影子）——均为增量能力，无依赖方；RISK-036 边界与官方审批状态不受回滚影响（本版未声明任何官方审批）。
