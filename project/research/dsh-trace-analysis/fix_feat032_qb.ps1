# Fix FEAT-032 quality_budget.security.validation signal wording
$ErrorActionPreference = "Stop"
$p = "D:\AI\agent\claude\coding\project_management_workflow\.governance\execution-packets.json"
$j = [System.IO.File]::ReadAllText($p, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
$pk = ($j.packets.PSObject.Properties | Where-Object { $_.Name -eq "FEAT-032" }).Value
$pk.quality_budget.dimensions.security.validation = "安全检查（静态扫描）：文件操作面仅 open(rb) 只读 + 仓库内 docs/research 落盘，无任何用户环境写入路径；R4 逐条上报表 11+ 次真实环境调用全部只读 exit 0"
$out = $j | ConvertTo-Json -Depth 12
[System.IO.File]::WriteAllText($p, $out, (New-Object System.Text.UTF8Encoding($false)))
Write-Output "security.validation rewritten"
