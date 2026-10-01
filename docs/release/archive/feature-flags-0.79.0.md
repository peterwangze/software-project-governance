# Feature Flags - 0.79.0

**Version**: 0.79.0 (minor)
**Release**: 降噪第二波/规则判定能力批 + RISK-049 关闭三件套 + 治理数据归档迁移 + 0.80.0 重构线 P0 前置波
**Date**: 2026-09-10

## Feature Flag Inventory

This release has **no runtime feature flags** — 全部变更为确定性检查器/守卫/判定规则/门禁组件扩展与缺陷修复（0.78.0/0.78.1 无 flag 先例延续）：无 rollout 门控、无默认行为切换开关、无灰度放量面。

涉及「行为变化」的项均带**确定性旁路或降级路径**（见 Behavior 表），不需要 flag 化：G5 重复抑制带 `--force` 旁路且首次义务穿透缓存（fail-open）；post-commit Step 4b 为 advisory 非阻断（SKIP 降级显式）；release gate 新组件 skip 路径显式 [SKIP] 披露；判定面扩展均走放宽/fail-safe 方向（历史形状 FAIL→WARN、机器行白名单、保守漏降级修正——「ACTIVE/真实 nonzero 恒 FAIL」边界锁定）。

## Behavior

| Component | Default | Notes |
|-----------|---------|-------|
| governance-write-guard（FEAT-011） | enabled（手动/协议触发） | Coordinator 直写 `.governance` 后按 M1.2 MUST 复跑；只检不改，exit 0/1/SKIP；B 级检查器工件 + A 级协议触发（FIX-297——不宣示时点强制/C 级） |
| post-commit Step 4b write-guard 段（FEAT-017/FIX-302） | enabled（advisory 非阻断） | 三态：PASS 含耗时 / FAIL 面板前 3 条 + 复跑提示 / SKIP 降级；GNU timeout 语义探测；回滚 = 删 Step 4b（文档化） |
| task-priority-analysis 同会话缓存（FEAT-012 G5） | enabled | tpa-last-run.json 当日 + mtime 未变即复用（fail-open）；RECO 三条件抑制；`--force` 旁路；完成必推荐首次义务穿透缓存 |
| check-governance --summary-only 尾行（FEAT-012 G6） | enabled | 两态：构成 ≤cap5 =「已全量展示」/ 超出 = 追查预算指引行 |
| Check 28t claim→evidence 映射（FEAT-014） | enabled（advisory） | ADAPTER_CLAIM_REGISTRY 4 类 dsh 宣示 + README 等级标注（live-session/isolation/static 三级） |
| Check 28u preset 冒烟（FEAT-015） | enabled（advisory） | `launch.py --smoke`（installed + shipped 双面加载断言；真实 home 零写入——M7.7 隔离环境三选一取 (a)） |
| check-release dsh_upgrade_regression（FEAT-016） | enabled（execution gates 开启时实际运行并阻断 FAIL） | `--skip-execution-gates` / BR-4 released-history 显式 [SKIP] 披露；SPG_RELEASE_GATE_TIMEOUT 先例语义 |
| ArchGuard 棘轮 R1~R7（FEAT-019） | enabled（fatal 位） | R1 主文件行数锚 24,302 只降不升（FEAT-013 sanctioned regen 后 24,329）；R7 regen 幂等；负对照全覆盖 |
| 契约矩阵 harness（FEAT-020） | manual（`--regen`/`--check`/`--self-check`/`--golden`） | 快照四契约面（CLI 82 键〔80→81 FEAT-019→82 FEAT-013 sanctioned〕/ Check 70 段 / Result 形状 5 / guard 输出 pin）+ 27 特征测试 |
| 归档 explain（FIX-301） | manual（explain 参数贯穿 migrate 链） | 可审计解释输出：四类五数字 + 逐条保留原因 + 未知结构清单（P7 不强删） |
| Check 30 历史格式迁移 / 30c 机器行分类 / 终态 marker 集（FIX-291） | enabled | pre-FIX-174 文件式 review 记录按历史形状 WARN；REVIEW-/RECO- 合法机器行白名单/溯源分类；fail-safe 边界不放宽 |
| 18c~18i 执行包谓词（FIX-292） | enabled | `_is_incomplete_task_status` 委托 W-7/BC-7 终态链权威（只消费不改写） |
| Check 10 M5 扫描面（FIX-295）/ Check 36 R3（FIX-294） | enabled | docs/release + docs/reviews 记录类豁免 + [EXEMPT] 披露 / 归档语料可解析 ID 按 DEC-151 豁免（不可解析保留 WARN） |
| 派发锁 acquire API（FEAT-013） | enabled | 写入前路径存在性校验（exit 2 零写入）+ `--expected-new` 豁免审计化 + 当日 triage files 交叉核对 WARN；模板锁操作机器化禁手写 |

DSH upgrade path: `git -C <plugin_root> pull && python <plugin_root>/adapters/dsh/launch.py --sync`（bundle 安装则 `dsh plugin --profile web update` + 重启）。The persona version line (v0.79.0) reaches sessions only after sync/restart; a pulled-but-not-synced checkout still injects the old template. Do not claim session-level effects for unsynced installations.

## No-overclaim boundaries

This candidate does not create or prove `v0.79.0` and does not close RISK-036 or RISK-039. 0.79.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). RISK-049 已关闭（2026-09-09 用户裁决，DEC-185——口径限定：①dsh 用户面宣示〔DEC-179〕②isolation 加载面等级〔DEC-180〕；live/headless 会话面与非 dsh 适配器等级映射登记后续候选）。RISK-044 缓解中（DEC-177②——quick-scan 评估交付非实现，Slice-1/2/3 → 0.80.0）；RISK-046 根因修复已交付（FEAT-013）但维持打开至 2026-09-30 复评窗收口；RISK-047/048 维持观察。No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim is made. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.
