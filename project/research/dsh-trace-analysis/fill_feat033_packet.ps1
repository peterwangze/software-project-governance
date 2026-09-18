# Fill FEAT-033 execution packet contracts with delivered values
$ErrorActionPreference = "Stop"
$p = "D:\AI\agent\claude\coding\project_management_workflow\.governance\execution-packets.json"
$j = [System.IO.File]::ReadAllText($p, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
$pk = ($j.packets.PSObject.Properties | Where-Object { $_.Name -eq "FEAT-033" }).Value

$pk.product_success_contract = [PSCustomObject]@{
    user = "使用 /governance 或会话引导的终端用户与 Coordinator——前者等待冷启动（实测中位 ~4.5min），后者需要单次确定性数据源替代 19 步串行读文件"
    job_to_be_done = "当会话开始时，一条 CLI 命令在数百毫秒内输出全部引导所需热数据（入口信封/状态/Gate/候选/迁移标志/健康占位），LLM 不再逐文件读热数据多轮往返"
    non_goals = @(
        "不做协议重排——交互时序前置是 FEAT-034 的边界（本任务仅协议文档加指向）"
        "不执行任何迁移——migration 仅输出标志（执行面属 FEAT-035）"
        "不在 v1 伪装健康已检查——health 恒 deferred + pending_checks（快速健康接线属切片 B）"
    )
    success_metrics = @(
        "用户可见结果：单命令 358ms 输出全部聚合字段（真实仓库实测，验收 <3s），为 FEAT-034 交互前置提供确定性数据底座",
        "用户可见结果：输出投影 4937B（≤8KB 阈值）——会话引导的固定读取量从 ~110KB 文件面降到 5KB 以内",
        "可运行验收：python -m pytest skills/software-project-governance/infra/tests/test_bootstrap_aggregate.py -q 返回 26 用例全绿（含预算降级与只读幂等）"
    )
    competitive_baseline = "成熟 CLI 的 single-pane-of-glass 惯例：一次调用返回完整状态视图（如 kubectl get -o json / docker inspect），避免调用方多轮拼装——对照现状 31 次工具调用串行链（审计 §3.3）"
    done_definition = @(
        "幂等与只读证明：双跑 payload 除时间戳字段外相等 + fixture 树哈希不变 + .governance 零写入——已实跑记录",
        "独立 Code Reviewer 确认 health deferred 诚实语义、零反向依赖、协议接线未越 FEAT-034 边界——review-FEAT-033-CODE-R0.md",
        "契约面冻结：schema governance-bootstrap/1 + 87 keys 零漂移 + 冻结计数同步——FEAT-034 可依赖的稳定底座"
    )
}

$pk.acceptance_contract = [PSCustomObject]@{
    scenario = "Coordinator 或 /governance 引导路径运行聚合命令，数百毫秒得到机读 JSON；超预算时得到部分结果+deferred 明示，绝不猜测通过"
    command = 'python skills/software-project-governance/infra/verify_workflow.py governance-bootstrap --format json'
    expected_output = "exit 0；schema governance-bootstrap/1；含 resolve envelope 子集/状态投影/candidates（空时带 empty_reason）/migration 标志/health deferred/next_actions；4937B ≤8KB"
    last_run = [PSCustomObject]@{
        status = "pass"
        exit_code = 0
        summary = "2026-09-18 开发会话实测：真实仓库 358ms exit 0；双跑幂等（payload 除 generated_at/duration_ms 外相等）；--budget-ms 0 降级路径 deferred 非空可测；text 12 行 ≤40"
    }
    demo_evidence = "test_bootstrap_aggregate.py 26/26（字段完整性/预算降级/只读幂等 fixture 树哈希/migration 单测/体积断言）；9 个受冻结面套件全绿（registry 77/contract 27/archguard 38/quickscan 82/dsh_boundary 136/perf 19/tpa 147/cost 37/engine 857）"
}

$pk.quality_budget = [PSCustomObject]@{
    dimensions = [PSCustomObject]@{
        performance = [PSCustomObject]@{
            threshold = "真实仓库单命令 <3s（验收契约）"
            validation = "实测 358ms（开发会话实跑）；静态评估：单进程 import 复用零子进程、无全量扫描路径"
            status = "pass"
            evidence = "开发会话实跑输出 + review 静态复核"
            exception = ""
        }
        reliability = [PSCustomObject]@{
            threshold = "幂等（双跑相等）；预算降级 fail-safe（deferred 明示不猜测）"
            validation = "python -m pytest tests/test_bootstrap_aggregate.py -q：26 用例含幂等/降级/只读红线全绿"
            status = "pass"
            evidence = "fixture 树 sha256 前后一致 + payload 双跑相等（实跑）"
            exception = ""
        }
        security = [PSCustomObject]@{
            threshold = "只读红线：零治理写入/零子进程/零 git 操作"
            validation = "安全检查（静态扫描）：结构断言测试在位；代码面无 open(w)/subprocess/os.system"
            status = "pass"
            evidence = "test_bootstrap_aggregate 只读红线结构断言；.governance 零变更实测"
            exception = ""
        }
        accessibility = [PSCustomObject]@{
            threshold = "参数自解释 + 双格式（json 机读/text ≤40 行人读）+ 截断披露"
            validation = "check：_clip 80 字符带披露标记；--help 可用"
            status = "pass"
            evidence = "text 12 行实测输出"
            exception = ""
        }
        ux = [PSCustomObject]@{
            threshold = "投影体积 ≤8KB 阈值（对照现状 ~110KB 引导读取面）"
            validation = "体积指标：4937B 对 8192B 阈值（60% 余量）；text 12 行对 40 行上限"
            status = "pass"
            evidence = "实测输出字节数（开发会话）"
            exception = ""
        }
        maintainability = [PSCustomObject]@{
            threshold = "engine-free 模块（仅 2 个叶子 import）；契约面走文档化 regen（87 keys 零漂移）"
            validation = "archguard R1~R7 PASS（R2 47 sites 零新增反向边；R6 198=baseline）"
            status = "pass"
            evidence = "9 个受冻结面套件全绿 + cross-refs/manifest PASS"
            exception = ""
        }
    }
}

$pk.status = "🔄 审查中"
$out = $j | ConvertTo-Json -Depth 12
[System.IO.File]::WriteAllText($p, $out, (New-Object System.Text.UTF8Encoding($false)))
Write-Output "FEAT-033 packet contracts filled"
