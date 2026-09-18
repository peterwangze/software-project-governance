# Fix FEAT-032 success_metrics wording (process-only regex compliance)
$ErrorActionPreference = "Stop"
$p = "D:\AI\agent\claude\coding\project_management_workflow\.governance\execution-packets.json"
$j = [System.IO.File]::ReadAllText($p, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
$pk = ($j.packets.PSObject.Properties | Where-Object { $_.Name -eq "FEAT-032" }).Value
$pk.product_success_contract.success_metrics = @(
    "用户可见结果：一条 CLI 命令 4.8s 内输出全部会话轨迹的开销报告（298 文件，验收 <5s），冷启动等待时长从体感估计变为仪表读数，用户可对照基线逐值复现（TTFA p50=271.8s 与 2026-09-18 审计一致）",
    "用户可见结果：报告内嵌口径披露（calibration 字段）——用户能分辨累计请求量与驻留量、带标签残差不归因，不再误读指标",
    "可运行验收：python -m pytest skills/software-project-governance/infra/tests/test_governance_cost.py -q 返回 37 用例全绿（含快速/全量双路径等价与损坏容错的自动化保障）"
)
$out = $j | ConvertTo-Json -Depth 12
[System.IO.File]::WriteAllText($p, $out, (New-Object System.Text.UTF8Encoding($false)))
Write-Output "success_metrics rewritten"
