# FIX-453 CI 修复子集 CODE R1

- 日期：2026-10-17
- 审查结论：APPROVED_WITH_NOTES
- unresolved_blockers=0
- 审查基准 HEAD：`f0910607beaf5480b2f1d80718c8b639c4c34eda`
- 前轮：`docs/reviews/review-FIX-453-MARKER-R0.md`。R0 只审 marker 单行，已在 `2fa4938` 提交；R0 无待修 finding。本轮重新审查下列 18 路径，不把 marker 结论扩大到本轮。
- 审批范围：仅本报告绑定的 CI 源码、测试隔离、机器快照与诊断文档，可形成该子集的独立提交。不是完整 FIX-453、完整 CI、FIX-450、FIX-449、FIX-454、DSH 0.2 原生接线或版本发布通过结论。

## 1. 对象绑定

范围来自 `.governance/dispatch-fix-453-continuation.json` 的 `action.write_paths`。以下是审查及独立验证结束时的当前文件字节 SHA-256：

| 路径 | SHA-256 |
| --- | --- |
| adapters/dsh/launch.py | 26b4323ba7a8f854379d60dae33b3fb8c24270ed07c6993d06414a025fd94007 |
| skills/software-project-governance/core/architecture-baseline.json | e301df70d90cd20220c59a6480fcf589b8640e396d8fe9f2cbcd1cff1f0294ad |
| skills/software-project-governance/infra/registry.py | 043c00fd0b84c3a1a1ae4b97b10dbcec3bdd7d2a531f8ce252ba9a4b905535b8 |
| skills/software-project-governance/infra/checks/version.py | 129a59906080442327a64d1d98f383fe292c62c1f3dfe66f4400d9256dea2f31 |
| skills/software-project-governance/infra/contract_matrix/generator.py | 4e3284163a353e73d834c206c8f0be41f09ec4768b2f5ef49daec07656275feb |
| skills/software-project-governance/infra/contract_matrix/snapshots.json | ab0e327fa66eae7c0ea0d66c008801454f8d4e1dac98da2c5ecedf82514f8193 |
| skills/software-project-governance/infra/tests/test_registry.py | 7a78c2da1434ed0ed679b1b44a7e9849197d028fee2964277b6fe855ab92bbb2 |
| skills/software-project-governance/infra/tests/test_archguard_ratchet.py | afa3765150beeae20f7d3837caae6567d96f1f035e4dfc85265feac00ac40fa6 |
| skills/software-project-governance/infra/tests/test_behavior_profile.py | cebff9842207ee905395ce39429646daaeafd8228e54d3a474ca3c3973280b47 |
| skills/software-project-governance/infra/tests/test_contract_matrix.py | 22d01ee1adaa9a5c8a256fe0851c30ab2a6b3a48924341ef954365d0b67a9915 |
| skills/software-project-governance/infra/tests/test_dsh_adapter.py | 3ecad49c23da4d49199988ebb09ff930aca10b5124c309c1c19b7b3632aa8225 |
| skills/software-project-governance/infra/tests/test_feat014_check28t_product_gate.py | e7106b01d4929a2b96241ae86a371fe021cd42694a40e4727257bad84115a8f2 |
| skills/software-project-governance/infra/tests/test_fix270_product_gates.py | 1df4438efe84dd64f7f5757aca30619cda0f2b75f27f1c086718c39cc193393f |
| skills/software-project-governance/infra/tests/test_gate_sequence_for_release.py | e28354f7d616a5d9a9168d4b1af69db47c482a178bcf22e84fed0a6e193a06c0 |
| skills/software-project-governance/infra/tests/test_review_record.py | 9c1a24b50f585871f5aa3ab5d62a8046964f912c085226cc53ee7c3e2f31a931 |
| skills/software-project-governance/infra/tests/test_review_machine_provenance.py | 042d3168c5481977fe3d92281b71c6bead7ccd8a349655500b67e5e78fc2b86f |
| skills/software-project-governance/infra/tests/test_projection_legacy_snapshots.py | f4ebc6b03144755e0adba87c60f8f1b294dc5140db792aebf85d1d3f7ff66cd9 |
| docs/diagnostics/ci-clean-checkout-repair.md | c0ca5f7ab83664129ba7ea40fb408df08da2938758a2af1259dd99c844f015c8 |

18 路径集合摘要：`38d9031ba600303378f8ff65f257d711cb10ee5c9522f52a492b20690ab865c6`，算法为按 dispatch 顺序拼接 `path + NUL + hex_sha256 + LF` 后再 SHA-256。17 个 tracked 路径的 `git diff -- <18 paths>` 摘要为 `92bb5d3f487fa003503d8778ae545f9a538a56cac1b2f18652b03df926596c7a`；新诊断文档尚 untracked，未计入 Git diff，但其完整字节已在上表绑定。

独立验证使用 producer 的仓内 clean clone：`.codex-sandbox/FIX-453/clean`，实际 HEAD 为 `2aae6ff1f1cf49e3566e25c5d55b7fe1afdb762f`。17 个 CI 源码/测试/快照文件与当前工作树 SHA-256 **逐一相等**；诊断文档后续追加，不影响代码对象。clean 根 `.governance` 实测不存在。clean SKILL SHA-256 为 `5ceb9b9c79c02c9ee223e4be8542edd0c903f7525a5a9f759472c2baf25d997b`；工作树 SKILL 正由 FIX-450 并行修改，本审不加载其在途版本来制造绿灯。

## 2. 逐项审查与设计一致性

1. **launch 兼容性**：`launch.py:1589` 将跨行 f-string 内条件表达式提取为 `witness_status`，PASS/FAIL 两分支打印文本独立比较均逐字相等。独立 AST 对比 HEAD 原代码有 `(1590,1591)` 跨行 FormattedValue，新代码没有。新增回归覆盖整份 launch 的表达式边界，不只钉这一行；这仍是结构防护，不能替代真实 3.11 运行。
2. **registry**：补回已存在于 engine 与 snapshot 的 `enforcement-check` → `verify_workflow.cmd_enforcement_check_engine`，没有新执行分支。实际 key 集合、callable、白名单、别名核验通过；107 key 与 209 冷导入记录是对既有事实的对齐，没有删除 fail-closed 检查。
3. **Result shape**：`generator.py:249` 的真实临时 initialized host 固定返回类型采样上下文；仅绑定宿主事实路径，仍调用原五个代表性检查，未替换检查返回值。clean 环境的 Result shape 与 snapshot 匹配，变更 CLI key、segment、Result 类型、guard 输出四种负向扰动仍被检出。新增 `unittest.mock.patch` 属标准库，工具生成器没有新增第三方运行依赖。
4. **机器快照**：architecture 的 R1 降至真实 28214，R2 位置对齐 triage 与 generator 的真实行号；48 sites / 37 entries 未增加。独立 R7 重新真实提取、双提取逐字相等、当前基线匹配、手改提取区与陈旧 anchor 拒收均通过。contract 的实际四 faces 零漂移记录经核对；没有抬容量、删除规则或新增 exemption。
5. **版本豁免**：`checks/version.py:389` 仅同一路径、同一 token `0.95.0`、同一 `_REASON_FIXTURE_ROW_TEXT` 的精确行锚 5862→5870；没有扩大匹配范围或新增豁免项，符合 DEC-213③ 的可追溯固定历史夹具例外。
6. **宿主隔离**：behavior、Check 28t、FIX-270、gate sequence 构造临时 plan/evidence/risk/decision 事实，再绑定原宿主入口；关键断言及真实检查未被换成固定 PASS。未初始化 CLI 反例仍验证初始化提示与无 project 面，legacy 行为回退没有改变安全语义。
7. **可信链**：`test_review_record.py:35` 的 helper 创建实际 Git commit、实际 report 字节及实际 ledger。禁用 fixture hooks/GPG，不操作用户仓库；新增正例实际验证 commit pin 与 `verify_review_trust == CLEAN`。已有仅检验 CLI 参数转发的 routing mock 仍在，但新增 persistence/trust 证据没有 mock Git 或生产信任读写器；两类证据没有混称。
8. **projection/legacy**：`isolated_projection_root` 从 Git tracked canonical 路径构造临时副本，并把历史模型明确标为 `SYNTHETIC`。重命名测试不再声称 synthetic copy 已 shipped。缺文件、收敛、缺理由、坏 registry、空 ledger、过期 anchor、缺 marker 等拒收均保留并独立通过。生产 `release.projection.check_legacy_snapshots` 与 `checks/projection.py` 未修改；真实发行副本存在性没有被合成模型证明。
9. **DSH smoke 与时间窗**：临时 `DSH_INSTALL_DIR=absent-install` 隔离可变安装插件集合，NOT_RUN 仍诚实披露；新增 schema FAIL 传播负例通过，缺 SDK 没有被当作完成真实会话验收。`os.utime(ns=...)` 控制夹具时间因子，原 adapter-own-face、窗外、坏时间、无窗口负例保持并通过，没有 sleep 或放宽窗口。
10. **条款测试**：intro 计数改由真实连续条目派生，同时保留第 10 条 goal 锚；实际旧 SKILL 的 11/10 不一致因此继续 FAIL，4KB 预算也没有被提高。诊断区分中间 74 PASS 与最终有失败的结果，没有将两处 FIX-450 残余吞掉。

上述与既有版本派生纪律、FEAT-094 可信链、宿主/插件事实分离、R1/R7 只降及再生契约一致。本子集无生产安全判据放宽。

## 3. 五维度及 AI 专项

| 维度 | 结论与证据 |
| --- | --- |
| 正确性 | 本子集通过：等价输出、真实 CLI 集、固定宿主类型采样与完整错误路径保留；独立 85 项测试及直接可信链探针通过。 |
| 安全性 | 通过：没有用户数据修改、权限扩张、真实安装或可信链绕过；schema/缺报告/语义冲突/篡改均仍拒收。 |
| 可维护性 | 通过：fixture helper 可复用，条款数量与版本来源派生，快照由原工具再生；没有无关重构。 |
| 性能 | 本子集通过：生产仅局部字符串中间值与现有声明补齐；测试拷贝 tracked tree 有实际 I/O 成本，未放宽生产性能预算。定向耗时真实记录，未宣称全 CI 加速。 |
| 测试覆盖 | 本子集通过：目标正负例、真实可信链、legacy 拒收、Result 差分与 R7 再生；完整 4870 suite、3.11、真实发行资产与 FIX-450 仍是独立验收面。 |

AI 五项完成：无新增伪造成功返回或未实现 TODO；API/handler 均真实可解析运行；没有把 mock oracle 当真实 SDK 证据；synthetic legacy 明示用途，未借 ignored 数据冒充 shipped；没有无关产品扩展。

## 4. 独立运行证据与 R4 命令记录

解释器：Windows CPython 3.14.3。测试在上述 clean clone 执行，TEMP/TMP/DSH_HOME 指向 `.codex-sandbox/FIX-453/review-r1/`，DSH_INSTALL_DIR 指向同范围不存在的安装目录。没有读取 SDK/session 内容、启动 DSH 或修改用户 HOME 应用配置；普通 Git 可能读取全局 Git 配置。真实 argv、cwd、UTC 起止、exit、写入路径及访问说明保存在下列 JSON；对应日志均 UTF-8：

| 记录（均位于 `.codex-sandbox/FIX-453/review-r1/`） | UTC 起止 | 实际结果 |
| --- | --- | --- |
| independent-safety-tests.json / .log | 00:07:42.866924 → 00:08:07.578991，2026-10-17 | 45 tests / OK / exit 0，测试耗时 24.331s |
| independent-contract-tests.json / .log | 00:08:22.513669 → 00:10:13.461436，2026-10-17 | 40 tests / OK / exit 0，测试耗时 110.358s |
| independent-trust-probe.json / .log | 00:09:28.465136 → 00:09:29.976921，2026-10-17 | 四项直接 API 探针断言通过 / exit 0 |

第一组覆盖完整 review persistence/scope/wiring/overwrite guard、Check30c CLI、behavior CLI 与 fail-closed、launch 结构防护、schema FAIL 传播、mtime 正反例及 decoy-home 拒收。第二组覆盖完整 legacy declaration/backport 拒收、Result shape 与差分负例、command registry、ArchGuard R7 四个再生/防篡改测试。合计 **85 tests / 0F / 0E**，未重复完整 suite。

直接可信链探针使用临时真实 Git 仓，得到 `CLEAN`；修改 report 字节后为 `CONFLICT`；缺 report 与 report 明示 NEEDS_CHANGE 却写 APPROVED 均被拒且未生成对应 review 文件。探针临时 commit 为 `1e303fc21192e3c88c215f037a5e7daaae76e1b3`，不代表产品提交。

证据 SHA-256：

| 证据 | JSON | log |
| --- | --- | --- |
| safety | 8f9cfdc82f10946b671391373f40eed8ffb695301af87ea25001932e6cceb56c | 58442ebb545abcffbfce01402c75f8a48ade0773646eedf3f9f26142b92c134d |
| contract | 8d4ad0f8ba2f029f6f217c14b36ae1a001bd83b63b9336f10ea188c0e35f76bf | 9473c5ce28727cd234823c32cf225174028c5cdd71bd21eaca6dab63996baa5b |
| trust | 16efd1a90c65621283c45e7d6e520322f8173879b8745a22b35e3c8e221c100a | 2e0ba8d262868d6a476520f565e8d7947656bd1d20d3ce78f0b8098300a462c3 |

## 5. 通过备注、残余与裁决

P0=0，P1=0，P2=0；P3 非阻塞范围备注三项：

- **R1-N1 / P3，3.11**：本机较新 parser 的 feature_version 连旧坏 f-string 也接受，结构 RED/GREEN 有独立事实但不等于 3.11 实跑。Coordinator 必须在提交后用 GitHub Python 3.11 完整四门验证；本批准不预测远端已绿。
- **R1-N2 / P3，外票失败**：核对 `.governance/ci-38923337599.log:10787/10789` 的原始 **4870 / 75F / 81E / 37S**，并核对 producer clean JSON 与日志的 **413 / 2F / 0E / 1S**、额外 schema 负例 1P、三静态门 exit0。两失败为 SKILL intro 11/10 和 9648B>4096B；本审未将它们豁免，必须由 FIX-450 在发布前修复并另审。FIX-449 的 R0-F1 同样不由此报告关闭。
- **R1-N3 / P3，发行资产**：synthetic legacy tests 验证声明和拒收契约，不证明 ignored 历史代码已打包发行。真实副本/回填政策需在正式发行验收中处理；不能使用本轮单元通过替代生产 projection/legacy gate。

五维度、设计一致性、AI 五项、分级和真实运行证据硬门槛完成；无本范围未解决阻塞，可以仅提交绑定的 18 路径子集。Reviewer 未 commit/stage、未写产品或治理记录，仅新增本报告和仓内授权 scratch 证据。暂停 hook/test_hooks 在审查中再次 SHA-256 对比均与原记录相同。
