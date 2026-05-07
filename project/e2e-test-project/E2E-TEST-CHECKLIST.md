# E2E 命令验证清单 — AUDIT-087 Phase 3

## 测试环境

- **项目**: `project/e2e-test-project/`
- **状态**: 立项阶段，G1~G11 全部 pending，workflow 0.27.0
- **方式**: 在 e2e-test-project 中打开 Claude Code 会话，逐命令执行

## 测试前检查

- [ ] verify-e2e.sh 23/23 通过
- [ ] Python E2E 13/13 通过
- [ ] `.governance/` 4 个治理文件完整

---

## 命令 1: `/governance` — 统一治理入口

**预期路由**: Scenario D（session-snapshot.md 24h 内）或 Scenario F（无 snapshot）

**验证点**:
- [ ] 命令不报错（无 GOV-ERR-*）
- [ ] 正确展示项目状态（Stage 1 立项, G1 pending）
- [ ] 如果 snapshot 新鲜 → 展示恢复面板
- [ ] 如果无 snapshot → 展示 Scenario F 状态面板

---

## 命令 2: `/governance-gate G1` — Gate 检查

**预期**: 检查 G1（立项→调研），所有检查项 pending

**验证点**:
- [ ] 不返回 GATE-ERR-001（已初始化）
- [ ] 不返回 GATE-ERR-002（有效 gate_id）
- [ ] 读取 stage-gates.md 中 G1 定义
- [ ] 输出 G1 检查项列表及每项判定结果
- [ ] 整体结论清晰（passed / passed-with-conditions / failed）

---

## 命令 3: `/governance-review code` — 代码审查

**预期**: 触发 Code Reviewer agent 审查

**验证点**:
- [ ] 命令被识别（不报"未知命令"）
- [ ] 正确路由到 Code Reviewer agent
- [ ] Agent spawn 成功（如项目无代码，应合理降级而非崩溃）
- [ ] 审查报告写入 `.governance/review-*.md`

---

## 命令 4: `/governance-cleanup` — 清理

**预期**: 运行 cleanup.py --dry-run

**验证点**:
- [ ] 不返回 CLEANUP-ERR-003（manifest.json 存在）
- [ ] 展示冗余文件列表（或 CLEANUP-ERR-002 告知已纯净）
- [ ] dry-run 模式不实际删除文件
- [ ] P0/P1/P2 分级正确

---

## 命令 5: `/governance-status` — 状态展示

**预期**: 路由到 Scenario F，展示完整状态

**验证点**:
- [ ] 展示项目配置摘要（名称、profile、trigger_mode、permission_mode）
- [ ] 展示 Gate 状态表（G1~G11）
- [ ] 展示任务统计
- [ ] 展示活跃风险
- [ ] 展示插件版本新鲜度

---

## 命令 6: `/governance-verify` — 健康检查

**预期**: 路由到 Scenario E，执行诊断

**验证点**:
- [ ] 执行 Check 1~N（evidence completeness, risk staleness, gate consistency...）
- [ ] 每项检查输出 PASS/FAIL/INFO
- [ ] 汇总结果清晰
- [ ] 如发现异常 → 展示诊断面板 + 修复选项

---

## 边界测试（可选）

- [ ] `/governance-gate G99` → GATE-ERR-002（无效 gate_id）
- [ ] `/governance-review all` → 全阶段审查
- [ ] `/governance-cleanup`（第二次运行）→ CLEANUP-ERR-002（已纯净）
- [ ] 删除 `.governance/plan-tracker.md` 后运行 `/governance` → GOV-ERR-002 或异常恢复

## 测试结果

| 命令 | 结果 | 备注 |
|------|:--:|------|
| /governance | ⬜ | 路由模拟通过（Scenario F 降级——旧格式 snapshot 无 session_date） |
| /governance-gate G1 | ⬜ | G1 定义可读，检查项逻辑正确（4 项检查——目标可衡量/范围边界/干系人/不做什么） |
| /governance-review code | ⬜ | 需真实 Agent Team 交互 |
| /governance-cleanup | ✅ | FIX-042: --dry-run 返回 CLEANUP-ERR-002（已纯净，FIX-053 后不再误报用户文件） |
| /governance-status | ⬜ | 路由同 Scenario F |
| /governance-verify | ✅ | FIX-042: 9/9 核心检查 PASS（Check 1-9），Check 10 262 hits → FIX-054 修复后 0 误报 |

**静态验证进度**: 2/6 ✅ (cleanup + verify 命令行工具), 4/6 需真实会话
