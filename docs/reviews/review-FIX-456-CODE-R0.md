# FIX-456 CODE R0 — DSH 本地契约前置拒收

- 日期：2026-10-19（Asia/Shanghai）；下列命令时间均为实际 UTC。
- 结论：APPROVED_WITH_NOTES
- unresolved_blockers=0
- HEAD：`3622889ba35c909c07951045761257b97c9b662c`
- 独立性：Reviewer 未生产本票代码；已读 `agents/code-reviewer.md`、`skills/code-review/SKILL.md`、`skills/tech-review/SKILL.md` 和 FIX-456 execution packet。仅新增本报告和获授权仓内 scratch；无产品/index/治理记录修改。
- 审批范围：三路径中本票的本地 API 声明形状检查、真实 probe renderer 前置、错误类型归一化、对应回归及诊断。不是完整 CI、真实宿主验收或版本发布裁决；FEAT-098 原审查不受影响。

## 对象绑定

| 对象 | SHA-256 |
| --- | --- |
| `skills/software-project-governance/infra/dsh_compat.py` | 9b7eb9d15ca79f909e27b4f3b9260553883e13bf35c827f1acbc37a1dc09d1d8 |
| `skills/software-project-governance/infra/tests/test_dsh_contract.py` | cc4d7665f06dd5e15c30599abe7d0f26460fe601c51d99f018d177af2b97c2a4 |
| `docs/diagnostics/dsh-contract-preflight.md` | f9bc4a07378614a09570ef35641a7f9ce086a9b737588178407a9f9ffe95348c |
| 三路径 `git diff --` 输出（新诊断文件未跟踪，另以上述文件 SHA 绑定） | d153ca393328bef85cdcc40557427f0710d86dddfe432be9ad64b1b289d1fe61 |
| 保持 immutable 的 `review-FEAT-098-CODE-R0.md` | 76138cc983c9c6a6f033288a9a967eb345845814176fe3350d17db3fe252d263 |

三产品 SHA 与 Producer 派发值一致；结束前再次核对，未变化。目标三路径 `git diff --check` exit 0。本审查不读取或改写 paused hook/test_hooks 的工作内容。

## 正确性与边界裁决

1. **坏契约先于环境缺口。** `dsh_compat.py:1901` 在原结构化异常边界内调用 `_render_probe_script()`，随后才处理 compositions、install、Node。缺失 exports、错误 map/entry/member 及无法提供必需 role 的声明均先形成 `ContractMalformed`；不再因为无 composition 或无 host 变成 `NOT_RUN`。
2. **只有一套 probe 语义。** `:1331` 的真实 renderer 同时服务前置检查和 `:1423` 的实际 probe；没有复制 schema、返回硬编码 verdict 或添加 js-yaml 特判。`oracle_api_symbols():469` 遍历所有包，拒绝非空 object/list/string 约束之外的 map、entry、exports、元素，并在元素错误中给出下标。Reviewer 另外插入 `synthetic-new-api` 的坏声明，确认任意新增包也被拒收。
3. **原分类不被放宽。** `:546` 的既有 mapper 保持 `ContractUnreadable -> NOT_RUN`，`ContractMalformed/ContractSchemaUnknown -> FAIL + issue`。缺文件与无效 UTF-8 走原 unreadable 策略；截断 JSON 与未知 schema FAIL。renderer 的缺 role、builtin group/boolean 与剩余 token 错误改为契约专用异常，直接调用者拿到明确异常，guard 拿到结构化结果，没有 traceback 降级成成功。
4. **健康环境缺口保留。** 独立 guard class 运行的健康契约/空 PATH 案例得到 `NOT_RUN`、issues=0、rows_checked=0，原因明确为 installed dsh unavailable。独立最小 fixture 的健康/no-composition 控制也保持 `NOT_RUN`。
5. **公共入口与权威保持。** 无 `main`、`run_cli`、lazy public exports 或发现策略接口变更。新增前置检查只读取已交付本地契约并渲染字符串，不解析 profile、不读取宿主、不运行 Node。flat/nested/pnpm/profile 权威、NODE_PATH 拒绝旁路、missing schema 与 schema failure 七项相关真实解析回归全部通过；零 schema 不报 PASS。
6. **CLI 有真实进程证据。** 对最小复制仓直接运行脚本，`--json --fail-on-issues` 下坏额外包 export 为 FAIL/exit 1，健康无宿主与缺契约为 NOT_RUN/exit 0。默认报告模式坏契约仍 FAIL/exit 0，这是 `:2243` 已声明的可选非零退出策略，非本票放宽。

所有通过结论限定于以上实际覆盖的声明形状、renderer 既有规则和环境分级，不宣称静态渲染能证明任意 JS 语义或真实 SDK 兼容。

## 独立实证

环境为 Windows CPython 3.14.3，复用已存在 QA venv，无安装依赖。没有重复 Producer 的 158 tests 或全仓 suite。

| Reviewer 验证 | 实际结果 |
| --- | --- |
| `TestGuardContractFailureVerdicts` 全 class 9 tests + `ResolutionContextTests` 代表性7 tests | **16 tests / OK / 5.481s / exit 0 / 无 skip** |
| direct oracle/renderer/guard：健康、missing、truncated、non-UTF8、empty apis、entry primitive、新增包 bad export、empty exports、missing exports、missing role | **10 案例全部断言通过**；每例独立进程 exit 0 |
| 三个 `--fail-on-issues` 真实 CLI 进程 | 坏 export FAIL/1；健康 NOT_RUN/0；missing NOT_RUN/0，全部符合断言 |
| 目标三文件 diff whitespace 检查 | exit 0 |

16 tests 的名单和完整输出在 `target-tests.log`。九项 guard class 包括 15 组 API shape mutation、missing/unreadable/truncated/schema unknown、健康对照、lazy public symbols、无契约 render_composition；15 subTests 没有重复计作15个 tests。七项解析回归为 flat hoisting、nested precedence、profile manifest 非权威、pnpm context、missing schema、NODE_PATH unrelated oracle、schema failure 非解析成功。

十个 direct 案例只复制未改动的 `dsh_contract.py` 与待审 `dsh_compat.py`，按例写入本地合成契约；调用真实 oracle、renderer 和 guard。将 discovery/install/which/probe runner 替换为会立即抛错的访问哨兵，**没有 mock renderer 或 verdict**。所有畸形例均未触达哨兵，rows_checked=0、install={}；健康 direct 例显式传空 compositions，因此只证明健康 renderer 可用且无 composition 时不探测 host。健康缺 host 的独立证据来自九项真实 class 和 CLI，而非把该空 compositions 控制冒充无 host 检测。

`synthetic-new-api` exports `[False]` 同时在 direct renderer 与 guard 报出 `host.apis[synthetic-new-api].exports[0]`；missing role 例的 oracle map 形状有效而 renderer 报错，覆盖只校验容器形状仍遗漏角色的风险。非 UTF-8 实测为 ContractUnreadable/NOT_RUN，不伪称该策略在本票变为 FAIL。

Producer 证据已读：原 `red-original.log` 为 1 failed、`NOT_RUN != FAIL`，修复后 `contract-module.log` 为 122 OK、`resolution-safety.log` 为36 OK，合计158个不同 tests；九项 guard 已在122内，不另加。诊断明确说明没有新 remote run。以上为 **Producer 留存运行**，不包装成 Reviewer 独立复跑158项。

探索 CLI 时，Reviewer 首次命令漏传 `--fail-on-issues` 却误断言应 exit 1，外层驱动因此断言失败（exit 1）；实际子进程 FAIL/exit 0 的输出和命令保留在 `cli-extra_bad_export.log`/审计中。核对既有参数说明后使用正确 flag 补验三例，未修改产品、测试阈值或删除原结果。

## 五维度、设计一致性与 AI 专项

| 维度 | 事实与结论 |
| --- | --- |
| 正确性 | 通过。结构校验覆盖所有 API 包；同一 renderer 前置进入既有 mapper。十个 direct 与实际 guard 对照支持坏契约优先、健康环境缺口保留。 |
| 安全性 | 通过本范围。前置检查无执行/宿主导入，新字符串诊断无 shell 拼接；probe 的 JSON 字符串替换规则未改。无新增密钥、权限旁路或真实 HOME 写入。零校验与坏 schema 回归继续拒收。 |
| 可维护性 | 通过。现有 guard/renderer/accessor 职责边界保持，仅集中加入声明形状约束及专用异常；没有第二套 schema、God module 新功能或包名特例。 |
| 性能 | 本地有界包/exports 遍历及字符串替换，无新增宿主探测、网络或循环 I/O。正常 probe 会再渲染一次同一字符串，属于本地固定模板工作；未声称有基准速度改善，未用宿主读取换取预检。 |
| 测试覆盖 | 本修复关键正负分支有真实测试；15组 mutation 与新增任意包 direct 例验证泛化。16 targeted 独立通过，158为 Producer 留存。未采集行覆盖率百分比，不把这些计数称为 strict 90% 或全量 CI 通过。 |

对照 execution packet 的用户目标：CLI 在未安装宿主时仍显示坏字段路径/FAIL；健康缺宿主 NOT_RUN；不安装运行真实宿主、不改解析权威，均有上述源码/实证支撑。错误数据不进入宿主执行，符合 P1-P7；变更保持单一修复，符合 D1-D4。

AI 五项逐项检查：**mock 残留**无（产品无新增 mock，测试只替换访问哨兵/合成依赖）；**硬编码成功**无（真实异常和报表产生判定）；**幻觉 API**无（复用已存在 renderer/accessor/mapper）；**未实现 TODO**无新增；**过度实现**无（未扩 SDK、profile、安装/发布功能）。

## 发现与残余

P0=0，P1=0，P2=0，P3=1；无未解决 BLOCKING finding。

**R0-N1 / P3 / 范围备注：** 本地 preflight 的通过不代表实际 DSH/SDK 执行成功；本次未运行真实 DSH、未读写用户插件/HOME、未执行全 suite、未重跑 GitHub Python 3.11，亦未关闭任何范围外 CI 失败。相关集成/发布义务由 Coordinator 独立验证，不在本报告中视为完成。无代码修改请求或需延期的阻塞发现。

## R4 命令、隔离与审计

所有实测子进程完整 argv/cwd、UTC 起止、实际 exit、环境和读写影响逐条保存在 `.codex-sandbox/FIX-456/review-r0/command-audit.json`；此为审计原件，下面按其 label 映射每条命令。未用日期推造旧运行时间。

- 执行器：仓内 `.governance/sandboxes/ci-integration-20261018/replay-venv/Scripts/python.exe -B -X utf8`，直接使用既存环境。
- 七变量：HOME/USERPROFILE/APPDATA/LOCALAPPDATA/DSH_HOME 均指向本仓 `.codex-sandbox/FIX-456/review-r0/home`，TEMP/TMP 指向同目录 `tmp`；禁写 bytecode、显式 UTF-8，删除 DSH_INSTALL_DIR/DSH_HARNESS_NODE_MODULES。
- targeted suite PATH 仅 QA Scripts、已部署 Node、Git、System32；Node 用于测试创建的合成 modules，无真实 DSH 启动/SDK 导入。direct/CLI 子进程 PATH 为空。
- R4 影响 I：只读仓库目标、既有依赖与本地合成模块；日志/临时复制仓/测试清理仅在本仓 scratch。影响 D：只读两个复制本地 Python 模块和选定合成契约，写日志于本仓 scratch。二者均无用户 HOME/真实 DSH/网络操作；这是命令隔离声明和可检查源码路径，不冒充系统级全文件访问监控。

| label（精确 argv 见审计同名记录） | 开始 UTC 2026-10-19 | 结束 UTC 2026-10-19 | exit | impact |
| --- | --- | --- | ---: | --- |
| target-tests：Python -c unittest suite，9+7选择如上 | 06:12:18.899847 | 06:12:24.580219 | 0 | I |
| direct-healthy：Python -c 真实 oracle/render/guard + fixtures/healthy | 06:13:20.554828 | 06:13:20.674994 | 0 | D |
| direct-missing：同直接调用 + fixtures/missing | 06:13:20.683751 | 06:13:20.779066 | 0 | D |
| direct-truncated：同直接调用 + fixtures/truncated | 06:13:20.784708 | 06:13:20.877626 | 0 | D |
| direct-non_utf8：同直接调用 + fixtures/non_utf8 | 06:13:20.882319 | 06:13:20.975730 | 0 | D |
| direct-empty_apis：同直接调用 + fixtures/empty_apis | 06:13:20.980101 | 06:13:21.074710 | 0 | D |
| direct-entry_primitive：同直接调用 + fixtures/entry_primitive | 06:13:21.079334 | 06:13:21.175187 | 0 | D |
| direct-extra_bad_export：同直接调用 + fixtures/extra_bad_export | 06:13:21.186823 | 06:13:21.282199 | 0 | D |
| direct-empty_exports：同直接调用 + fixtures/empty_exports | 06:13:21.287065 | 06:13:21.385663 | 0 | D |
| direct-missing_exports：同直接调用 + fixtures/missing_exports | 06:13:21.390396 | 06:13:21.485552 | 0 | D |
| direct-missing_role：同直接调用 + fixtures/missing_role | 06:13:21.490163 | 06:13:21.586471 | 0 | D |
| cli-extra_bad_export：复制脚本 --json --root fixtures/extra_bad_export | 06:15:16.077169 | 06:15:16.178630 | 0 | D |
| cli-failflag-extra_bad_export：复制脚本 --json --fail-on-issues --root fixtures/extra_bad_export | 06:16:44.478836 | 06:16:44.579333 | 1 | D，预期 FAIL |
| cli-failflag-healthy：复制脚本 --json --fail-on-issues --root fixtures/healthy | 06:16:44.583016 | 06:16:44.686047 | 0 | D，预期 NOT_RUN |
| cli-failflag-missing：复制脚本 --json --fail-on-issues --root fixtures/missing | 06:16:44.687434 | 06:16:44.781372 | 0 | D，预期 NOT_RUN |

| Reviewer 原始证据（scratch相对路径） | SHA-256 |
| --- | --- |
| command-audit.json | eb93ba43697140efa76cc875236680c1df928d89443db2f6a7411c73207aa916 |
| target-tests.log | 5f711734bd5f456eeeb51b4437d404daa5adf9ee34e997484544e57bf1edf3bc |
| direct-observations.json | 4b80f26424448fc3bc40383ce66bf9bac004c12f41a748ed8a25827a07000b97 |
| cli-extra_bad_export.log | 67b81247d33e579341748df1e949602d55c79d2c8552ad438e555358374a3917 |
| cli-failflag-extra_bad_export.log | e5d48c9178efb88ade8e43a524e28645b7f052087a90063263986b43f23bfb51 |
| cli-failflag-healthy.log | 2beb07194b2dec19ffd023e165f611f8378774845dab9f9244c0c29dca3a5b5e |
| cli-failflag-missing.log | 688f8e7d892282436ca6a0b960ad1ed67d47f19159360a40016554a1867969e6 |

五维度、分级、设计一致性、AI五项及真实运行结果已逐项记录。仅批准本报告所绑定的 FIX-456 修复范围，机录/锁释放/后续提交由 Coordinator 承接。
