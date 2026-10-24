# Rollback Plan — 0.99.0

- **版本**: 0.99.0 · **区间锚**: `7f161a6（v0.98.0 tag 终点）..HEAD（21 commits 载荷窗）` · **起草**: 2026-10-24（M-4 组装面）

## 1. 回滚触发条件

- M-2~M-7 任一门禁/审查发现未裁定 P0/P1 阻断且无 GO 终审路径；
- tag v0.99.0 误发（指向错误 commit / 发布后 24h 内发现阻断缺陷）；
- 下游 /plugin update 后 bootstrap 升级失败或会话不可用（FEAT-035 升级确认门异常）；
- **0.99 特有**：FIX-448 迁移后热表读入口异常（迁移行不可定位/消费者报错——恢复材料见 §4）。

## 2. 回滚序列（按发现时点）

### 2.1 tag 未打（M-7 前）——全链可逆

```
git revert <M-4 组装 commit>..HEAD        # 或逐 commit revert（21 commits 窗口）
# 版本面恢复 0.98.0：SKILL frontmatter/针脚/投影/entry sync 随 revert 恢复
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency   # 预期 PASS@0.98.0
```

载荷 commit（cad2f47〔FEAT-103〕/2ed8bb4 等 FEAT-102 五链/cc40646 等 FEAT-100 三链/7db915b 等 FEAT-101 两链/dcf5009/FIX-449~456 八票/f392a0b）如需回退：逐票 `git revert`（各票独立成 commit，D4 纯粹性保证可逆性）。

### 2.2 tag 已打未推送（M-7 中）

```
git tag -d v0.99.0                        # 本地删除重打（0.80.0 先例：未推送即删重建不算重指）
```

### 2.3 tag 已推送（M-7 后）

```
git revert <发布窗口 commits>             # 前滚式回滚（revert commit 而非 force-push）
git tag -d v0.99.0 && git push origin :refs/tags/v0.99.0   # 删除远端 tag（仅在无可接受前滚路径时）
```

### 2.4 下游用户回退

固定旧版本：/plugin update 前的安装（0.98.0）继续使用；CHANGELOG 0.99.0 段披露回退方式。

## 3. 数据兼容性声明

**治理数据**（.governance/ 不入发布——下游无数据迁移）：
- FEAT-093 权威账本 sidecar 与 task-row-update 状态机：0.99 无 schema 变更（FEAT-103/448 载荷零状态机改动）；
- FIX-448 D1 迁移只发生在**本仓库**治理热表（.governance/evidence-log.md，gitignored），不随插件分发——下游零影响。

## 4. FIX-448 迁移恢复（本仓库专用）

- 完整备份：`D:\AI\agent\claude\coding\acl-recovery-20261024-m2pre\`（evidence-log DDD37374 逐位校验一致 + archive 153 文件 + risk-log F6BE958B）；
- 迁移恢复材料：`.governance/migration-staging/evdt-20261024T000345Z-b600b5b7/`（before-evidence.md + manifest + segments——设计 §8.2/§8.3 回滚契约）；
- 恢复操作：以 staging before-evidence.md 替换热表 + 删除三 evdt-segment 段 + build-index 重建 → archive-integrity PASS 验证；
- **不可变历史**：迁移零改写（I1）——恢复操作亦不覆写 archive/ 既有文件（FIX-446 原语保证）。

## 5. 决策记录

- 范围四项裁决：DEC-368（承载=b/暂停=顺延 0.100/P2=FIX-448 先行/§11=D1 安全子集）；
- GO 终审披露面：CHANGELOG 0.99.0「发布边界」节（FIX-444/445 顺延、FIX-448 容量 BLOCKED、FEAT-103 NOT_RUN 5 条等）。

## 6. 保守边界声明

本回滚方案不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 先例口径延续）；回滚验证判据以本仓实测命令为准，非 Windows 未验证；下游真实环境回退效果以下游 /plugin update 实测为准（本方案验证范围=本仓库回滚序列可执行性，不含下游环境恢复保证）。
