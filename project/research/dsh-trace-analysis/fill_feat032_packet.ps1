# FEAT-032 execution packet contract fill (real deliverables from Developer report)
# Coordinator write-back per M1.2 (governance record data)
$ErrorActionPreference = "Stop"
$p = "D:\AI\agent\claude\coding\project_management_workflow\.governance\execution-packets.json"
$raw = [System.IO.File]::ReadAllText($p, [System.Text.Encoding]::UTF8)
$j = $raw | ConvertFrom-Json
$pk = ($j.packets.PSObject.Properties | Where-Object { $_.Name -eq "FEAT-032" }).Value

$pk.product_success_contract = [PSCustomObject]@{
    user = "治理工作流维护者（本仓 Coordinator/Developer）与使用 /governance 的终端用户——前者需要可信的治理开销度量来验收切片 A 优化，后者的等待时间是本任务要照亮的问题本身"
    job_to_be_done = "当我要评估/验收治理工作流的执行开销（冷启动时长、token 消耗、治理占比）时，用一条确定性 CLI 命令在数秒内得到机读指标报告，而不是人工解析会话轨迹或依赖不可复现的估计"
    non_goals = @(
        "不优化治理开销本身——优化是切片 A 后续任务（FEAT-033/034/039），本任务只建立可观测"
        "不产生流程仪式性输出——报告数值必须可复现（同快照等价）且口径内嵌披露，不把过程记录包装成产品价值"
        "不修改 requirements/pyproject 强制依赖 zstandard——保持可选运行时依赖 + fail-closed 报错"
    )
    success_metrics = @(
        "用户可见结果：单命令 4.8s 内输出 298 文件全语料的 TTFA/token 分项/工具分布报告（验收 <5s），治理轮 TTFA p50=271.8s 逐值复现审计基线——治理开销从'体感'变为'仪表'"
        "可运行验证：python -m pytest skills/software-project-governance/infra/tests/test_governance_cost.py -q（37 用例全绿，含 fast≡full 全语料等价看护）"
        "可运行验证：python skills/software-project-governance/infra/verify_workflow.py governance-cost-report --sessions-root <dir> --format json（exit 0，schema governance-cost-report/1）"
    )
    competitive_baseline = "成熟团队的 APM/可观测性实践：度量先于优化（Measure first）——无度量基线的性能优化不可验收；对标 audit-148 时代人工 zstd 解析 ~分钟级且不可复现，本任务将其产品化为 <5s 机读命令"
    done_definition = @(
        "37 单测全绿 + 受冻结面套件全绿（registry 77/contract_matrix/archguard_ratchet）+ 全语料 fast≡full 等价 298/298——事实已记录于本 JSON 与 EVD"
        "独立 Code Reviewer 审查确认：TTFA 口径与审计 §4 校准一致（原始时间戳差值不加工）、无 mock 残留/硬编码/幻觉 API——review-FEAT-032-CODE-R0.md"
        "0.83.0 基线快照落盘 docs/research/governance-cost-baseline-0.83.0.{md,json}，后续切片 A 验收（p50≤25s 目标）有对照起点"
    )
}

$pk.acceptance_contract = [PSCustomObject]@{
    scenario = "维护者在仓库根运行 governance-cost-report 指向任意 DSH sessions 目录，数秒内得到 JSON/text 机读报告；报告数值与 AUDIT-154 人工审计逐值一致（TTFA p50=271.8s/max=428.0s 复现 §3.1）"
    command = 'python skills/software-project-governance/infra/verify_workflow.py governance-cost-report --sessions-root <sessions-dir> --format text'
    expected_output = "exit 0；文本摘要含 per-turn TTFA、token 分项（in/cache/out 累计）、工具时长分布、LLM vs 工具占比、calibration 口径披露；单命令 <5s（实测 4.8s @ 298 文件/210MB 压缩）"
    last_run = [PSCustomObject]@{
        status = "pass"
        exit_code = 0
        summary = "2026-09-18 开发会话实测：298 文件 4.8s exit 0；治理轮子集 TTFA p50=271.8s/max=428.0s 逐值复现 AUDIT-154 §3.1；全语料同快照 fast≡full 等价 298/298 零失配；基线落盘 docs/research/governance-cost-baseline-0.83.0.json"
    }
    demo_evidence = "docs/research/governance-cost-baseline-0.83.0.md（人读摘要）+ .json（schema governance-cost-report/1）；37 单测含合成 zstd fixture 全路径覆盖（test_governance_cost.py）"
}

$pk.quality_budget = [PSCustomObject]@{
    dimensions = [PSCustomObject]@{
        performance = [PSCustomObject]@{
            threshold = "单命令全语料报告 <5s（298 文件基线；验收契约值）"
            validation = "实测 python verify_workflow.py governance-cost-report 4.8s（Developer 申报 + 基线 JSON 时点元数据）；字节级快速扫描器静态审查无 O(n^2) 全量反序列化路径"
            status = "pass"
            evidence = "docs/research/governance-cost-baseline-0.83.0.json（生成耗时元数据）；review-FEAT-032-CODE-R0 静态复核"
            exception = ""
        }
        reliability = [PSCustomObject]@{
            threshold = "同快照 fast≡full 等价 0 失配；损坏行/缺依赖 fail-closed 不崩溃"
            validation = "python -m pytest tests/test_governance_cost.py -q：37 用例含等价/容错/缺省报错/紧凑序列化回归全绿"
            status = "pass"
            evidence = "test_governance_cost.py 37/37（2026-09-18 开发会话）；全语料 298/298 等价扫描 exit 0"
            exception = ""
        }
        security = [PSCustomObject]@{
            threshold = "对用户环境零写入零删除零移动（纯只读扫描）；无注入面（输出为本地报告）"
            validation = "代码审查：文件操作仅 open(rb) 读取 + docs/research 落盘（仓库内）；R4 上报表 11+ 次真实环境调用全部只读 exit 0"
            status = "pass"
            evidence = "Developer R4 逐条上报表（本会话 FEAT-032 完成报告）；review-FEAT-032-CODE-R0 只读路径核查"
            exception = ""
        }
        accessibility = [PSCustomObject]@{
            threshold = "CLI 无 GUI 面——适用性=参数自解释 + 缺省报错给出修复指引 + text/json 双格式"
            validation = "check：--sessions-root 缺省时报错提示显式传入（不硬编码用户路径）；--format text 人读摘要"
            status = "pass"
            evidence = "test_governance_cost.py sessions-root fail-closed 用例"
            exception = ""
        }
        ux = [PSCustomObject]@{
            threshold = "维护者 5s 内得到可读报告；数值可复现可对照（审计基线逐值一致）"
            validation = "TTFA p50=271.8s/max=428.0s 与 AUDIT-154 §3.1 逐值一致（无口径漂移）；text 摘要含 calibration 口径披露"
            status = "pass"
            evidence = "docs/research/governance-cost-baseline-0.83.0.md 对比 docs/requirements/governance-bootstrap-cost-audit-0.84.0.md §3.1"
            exception = ""
        }
        maintainability = [PSCustomObject]@{
            threshold = "单模块自包含、引擎仅 3 处接线（import/subparser/dispatch）、R4 印数不变（1301）、研究脚本 deprecated 指针化防双源"
            validation = "check-manifest-consistency PASS（canonical 730→733）；archguard-ratchet PASS（R1 锚 regen 24583→24603，合并态 24617）；FROZEN 计数同步 bump"
            status = "pass"
            evidence = "test_registry.py 77 全绿 + test_contract_matrix.py 全绿 + TOOLS.md TOOL-053 登记"
            exception = ""
        }
    }
}

$pk.status = "🔄 审查中"
$out = $j | ConvertTo-Json -Depth 12
[System.IO.File]::WriteAllText($p, $out, (New-Object System.Text.UTF8Encoding($false)))
Write-Output "FEAT-032 packet contracts filled (psc/acceptance/qb) + status=审查中"
