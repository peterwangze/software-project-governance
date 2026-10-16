# Rollback Plan — 0.98.0

- **版本**: 0.98.0 · **区间锚**: `dd5c2a2（v0.97.0 tag peel→9950076..3b1a847..〈M-6b transition 回填位〉）` · **起草**: 2026-10-15（M-4 组装面）

## 1. 回滚触发条件

- M-2~M-7 任一门禁/审查发现未裁定 P0/P1 阻断且无 GO 终审路径；
- tag v0.98.0 误发（指向错误 commit / 发布后 24h 内发现阻断缺陷）；
- 下游 /plugin update 后 bootstrap 升级失败或会话不可用（FEAT-035 升级确认门异常）。

## 2. 回滚序列（按发现时点）

### 2.1 tag 未打（M-7 前）——全链可逆

```
git revert <M-4 组装 commit>..3b1a847   # 或逐 commit revert（10 commits 窗口）
# 版本面恢复 0.97.0：SKILL frontmatter/针脚/投影/entry sync 随 revert 恢复
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency   # 预期 PASS@0.97.0
```

载荷七票 commit（42ddbca/099acbf/75cc7e5/bf6942d/291b4f9/d0bac6e/daac2b8）如需一并回退：逐票 `git revert`（各票独立成 commit，D4 纯粹性保证可逆性）。

### 2.2 tag 已打未推送（M-7 中）

```
git tag -d v0.98.0                        # 本地删除重打（0.80.0 先例：未推送即删重建不算重指）
```

### 2.3 tag 已推送（M-7 后）

```
git revert <发布窗口 commits>             # 前滚式回滚（revert commit 而非 force-push）
git tag -d v0.98.0 && git push origin :refs/tags/v0.98.0   # 删除远端 tag（仅在无可接受前滚路径时）
```

### 2.4 下游用户回退

固定旧版本：/plugin update 前的安装（0.97.0）继续使用；CHANGELOG 0.98.0 段「升级路径」披露回退方式。**无数据迁移**（见 §3）。

## 3. 数据兼容性声明

- **权威账本 sidecar（FEAT-093）**：ops 收据台账（`<表>.ops.jsonl`）为**追加式日志**——revert 产品代码不动已写台账（治理数据完整性）；plan-tracker 热表为投影可重建，revert 后旧写入器继续工作（渐进开关默认 off，live migrate 未启用——读切换为后续票）。
- **ENFORCEMENT-ACTION jsonl（FEAT-095）**：默认 off 不产生执法记录；on 期间记录为追加式审计日志，revert 不清除（异常不隐藏）。
- **`.governance/` 治理数据**：0.98.0 窗口新增行（EVD-1695~1708/DEC-353~358/REVIEW-REL-102-R0）为历史事实记录，**任何回滚不删除不回写**（FIX-446 归档不覆写保护语义一致）。
- **archguard 基线/契约快照（DEC-358③ regen）**：R1 anchor 28204/R5 107 keys——revert 版本面不自动回滚基线（棘轮 only-down 语义：低 anchor 仍满足；如需恢复 28160 走 sanctioned shrink 裁定，不得手改）。
- **FIX-444/445 暂停链保全件**（hooks/commit-msg+test_hooks.py 工作树未提交 + .governance/incidents/FIX-445-rowdump-*）：不在发布窗口内，任何 0.98.0 回滚不触碰（DEC-342/358① 保全原义）。

## 4. 验证判据（回滚后）

1. `check-version-consistency` → PASSED@0.97.0；
2. `check-governance --summary-only` → 回落 0.97.0 基线 WARN 面（18d-RB2 FIX-444/445 与 28s 为 pre-0.98 既有面）；
3. 全量 unit tests → 0F/0E（C4 修复为独立 commit c46ad2a，可选择保留——时钟敏感修复对 0.97.0 同样正确）；
4. 下游会话 bootstrap → 版本面 0.97.0 正常呈现（FEAT-035 确认门不再触发 0.98 升级）。

## 5. 不可回滚面（如实披露）

- 已推送 tag 的历史可见性（删除远端 tag 属破坏性——需用户裁定）；
- 追加式治理台账行（EVD/DEC/REVIEW/ENFORCEMENT-ACTION）——按设计保留；
- ledger 事件（release-ledger candidate→released 事件为追加式——transition 记录随 commit revert 回退，ledger 事件链保留并标注）。
