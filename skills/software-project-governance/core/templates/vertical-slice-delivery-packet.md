# Vertical Slice Delivery Packet 模板

该模板用于 P0/P1 用户可见任务。目标是把大批量交付压缩成最小可演示、可回滚、可验收的用户切片，避免流程记录完整但产品不可用。

## Contract

```yaml
vertical_slice:
  user_visible_slice: "最小用户可见行为或场景"
  demo_path: "可运行 demo、smoke test、URL、截图或命令"
  scope_guard: "本切片允许修改的文件和行为边界"
  rollback_plan: "验证失败时如何回滚、禁用或拆除该切片"
  status: "PASS"
  evidence: "最近一次 demo proof 或计划证据位置"
```

## 使用规则

- 自动生成的 `TO_BE_DEFINED` 只是草案；P0/P1 任务必须替换为具体内容。
- `user_visible_slice` 必须描述用户、客户、使用者或操作者可以观察到的行为，不允许只写内部技术层。
- `demo_path` 必须包含可运行命令、demo、smoke/E2E/test/check、URL、截图或浏览器验证信号。
- `scope_guard` 必须是窄边界，不能写全仓、整个项目、所有文件或无边界重构。
- `rollback_plan` 必须说明验证失败时如何恢复或禁用该切片。
- 进行中或关闭任务必须使用 `PASS`；待实施任务可以暂用 `NOT_RUN_YET`，但仍必须写清切片和演示计划。

## 门禁

运行：

```bash
python skills/software-project-governance/infra/verify_workflow.py check-vertical-slices --fail-on-issues
```

`check-governance` 会在 Check 18g 中自动执行同一检查。
