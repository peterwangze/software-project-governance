# Fix FEAT-037 contract wording (regex compliance)
$ErrorActionPreference = "Stop"
$p = "D:\AI\agent\claude\coding\project_management_workflow\.governance\execution-packets.json"
$j = [System.IO.File]::ReadAllText($p, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
$pk = ($j.packets.PSObject.Properties | Where-Object { $_.Name -eq "FEAT-037" }).Value
$pk.product_success_contract.success_metrics = @(
    "用户可见结果：次要入口注入体积 16011B→2699B（-83%），双入口会话固定注入成本接近减半——用户在会话开始时多出 ~13KB 上下文可用空间",
    "用户可见结果：次要平台宿主（Codex/opencode）的会话引导仍完整可用——薄指针保留 fail-closed 第一动作、先读计划表、自检清单与模式确认，用户在这些宿主的体验与去重前等价",
    "可运行验收：python -m pytest skills/software-project-governance/infra/tests/test_entry_projection.py -q 返回 32 用例全绿（含双 apply 幂等与单入口场景）"
)
$pk.quality_budget.dimensions.ux.validation = "体积指标：次要入口 bootstrap 段 2699B 对 3072B 阈值上限（-83%）；主入口完整版 19502B 零改写承载；活体验证=当前 AGENTS.md 已重新加载薄指针版"
$out = $j | ConvertTo-Json -Depth 12
[System.IO.File]::WriteAllText($p, $out, (New-Object System.Text.UTF8Encoding($false)))
Write-Output "FEAT-037 wording fixed"
