# FIX-452 CI 依赖最小单元代码审查 R0

- 日期：2026-10-16
- 结论：APPROVED_WITH_NOTES
- unresolved_blockers=0
- 审查基准 HEAD：`a00105717935079c54ec30ed6e6c790e8bd97290`
- 待审对象：`.github/workflows/ci.yml` 两行新增；诊断依据 `docs/diagnostics/ci-failure-0.99.0.md`。
- workflow 文件字节 SHA-256：`1b67db0b34c7ddc02d787f6bc7f22c0f77e7f58dc2cde40b56c261ec7b2b2971`
- workflow diff SHA-256：`4b8842d8b371629fda9877a4cd5c95a312fe1ac1b4c0bd5c58220fbb6777f1c4`

## 逐行审查与设计一致性

Python 3.11 setup 后新增命名步骤，执行 `python -m pip install zstandard==0.25.0`。独立将 HEAD workflow 与当前文件规范化换行后进行精确比较，确认差异严格等于这一次两行插入；原 integrity、manifest、unit tests、cross-references 四门及其先后顺序保持。没有 `continue-on-error`、条件跳过、阈值放宽或测试删除。

读取 HEAD 的 `governance_cost.py` 与 `test_governance_cost.py`：zstandard 已是 DSH zstd 读取的既有依赖，生产 `_get_zstd()` 仍为懒加载，缺失时抛 `GovernanceCostError` 明确 fail-closed。该修改补齐测试执行环境，不引入产品新功能，不改变 ArchGuard 的 stdlib-only 冷导入契约。

## 五维度

| 维度 | 结论及事实 |
| --- | --- |
| 正确性 | 通过：依赖安装在 Python setup 之后且在四门之前；精确版本与独立运行使用的 zstandard 0.25.0 一致。 |
| 安全性 | 通过：无敏感凭证、权限扩张或用户数据操作；安装失败使用 Actions 默认失败语义；既有缺依赖错误路径保持。 |
| 可维护性 | 通过：一个明确命名步骤与一个版本 pin，修改范围集中；未重复门禁逻辑。 |
| 性能 | 通过：仅每次 CI 增加一次依赖安装，不改变产品运行算法、导入方式或预算门。 |
| 测试覆盖 | 通过本单元：临时导出的纯 HEAD 源码独立运行 governance_cost 模块 59 tests 全绿，包含缺依赖拒收测试；完整流水线不在此次通过范围。 |

## AI 专项与真实验证

mock 残留、硬编码返回值、幻觉 API、未实现 TODO、过度实现五项检查完成，未发现新增问题。pip 是当前 Python 解释器的模块调用；固定版本可安装性有诊断文档的 CPython 3.11 Linux wheel 下载记录支撑。

独立验证实际执行：

1. `git diff --check -- .github/workflows/ci.yml`：exit 0。
2. 对 workflow 做精确两行插入比较：PASS，四门及顺序字节内容保持。
3. `git archive --format=zip HEAD` 解包至 `tempfile.TemporaryDirectory`，在临时目录运行当前解释器的 `-X utf8 -m unittest discover -s skills/software-project-governance/infra/tests -p test_governance_cost.py`：**Ran 59 tests in 0.129s / OK / exit 0**。本验证没有加载正在修改的工作树 `governance_cost.py`。
4. 实测解释器 Windows Python **3.14.3**，`zstandard.__version__ == '0.25.0'`。输出中的三条 ERROR 是预期负向测试的 stderr，最终测试状态 OK；缺 zstandard 不静默跳过或伪造成功的分支仍通过验证。

## 发现、限制与硬门槛

P0=0，P1=0，P2=0。P3-N1（环境备注）：诊断文档的 Linux A/B 与 cp311 wheel 记录经阅读核对，本 Reviewer 未重跑 Linux Python 3.11 安装，也未验证 GitHub 最新运行；本地 59 tests 不可表述为远端恢复、完整 FIX-452 验收或 0.99.0 发布完成。其他已登记失败族仍需独立修复和全门验证。

五维度、设计一致性、AI 五项及分级检查完成。允许提交本最小配置修复与事实诊断文档；不扩大为全票完成声明。未修改 CI、产品、治理记录或 index；本报告为唯一写入产物。
