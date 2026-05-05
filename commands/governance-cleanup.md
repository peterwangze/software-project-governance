# governance-cleanup -- 声明式插件残留清理

> **推荐使用 `/governance`**——版本升级时自动触发清理（Scenario C）。本命令保留为手动快捷方式。

清理命令基于 canonical manifest (`skills/software-project-governance/core/manifest.json`) 的声明式 diff：
**REDUNDANT = ACTUAL - CANONICAL - EXCLUDE**。不再维护硬编码的冗余文件列表，
每次 manifest 更新后清理逻辑自动生效。

## 触发条件

- `/governance-cleanup` -- 执行清理
- 首次使用 `/governance` 时自动检测并提示（Scenario C 升级场景）
- CLAUDE.md bootstrap 自动升级序列中执行

## 核心原理

```
CANONICAL = expand_globs(manifest.root_entries + manifest.product + manifest.repo_only)
ACTUAL     = scan_directory(target_root)
EXCLUDE    = expand_globs(manifest.exclude_from_cleanup)
REDUNDANT  = ACTUAL - CANONICAL - EXCLUDE
```

canonical manifest 是**单一事实源**：声明"当前版本应该有哪些文件"。不在 manifest 中的文件 = 冗余。

## 执行流程

### Step 1: 检测（dry-run）

运行声明式清理脚本进行检测：

```bash
python skills/software-project-governance/infra/cleanup.py --dry-run
```

脚本自动完成：
- 加载 `manifest.json`（IF 不存在 -> CLEANUP-ERR-003，退出码 2）
- 展开 canonical 文件集（root_entries + product + repo_only 的 entries + glob_patterns）
- 扫描目标目录实际文件集
- 应用排除清单（`.git/`、`.governance/`、`node_modules/`、`__pycache__/`、`*.pyc`、`.env*`、`*.log`）
- 计算 REDUNDANT = ACTUAL - CANONICAL - EXCLUDE

如果冗余文件数为 0 -> CLEANUP-ERR-002（退出码 1），告知用户插件已是纯净版本。

### Step 2: 分类展示

脚本按 P0/P1/P2 三级分类展示冗余文件：

- **P0（必须移除）**: stub 残留（内容含 `plugin 发现 stub`）或文件所在目录不在 manifest 声明中（结构孤儿）
- **P1（建议移除）**: 文件不在 canonical 集中，但所在目录被 manifest 声明（已知目录中的额外文件）
- **P2（谨慎处理）**: 无法确定来源的文件

### Step 3: 用户确认

通过 AskUserQuestion 展示选项：

- (1) 一键清理全部（P0 + P1 + P2）
- (2) 仅清理 P0 必须移除的
- (3) 先看详情 -- 逐文件说明
- (4) 跳过 -- 保留所有文件（不推荐）

### Step 4: 执行清理

```bash
# 全部清理
python skills/software-project-governance/infra/cleanup.py --target <plugin_cache_dir>

# 仅清理 P0
python skills/software-project-governance/infra/cleanup.py --target <plugin_cache_dir> --categories P0

# 仅清理 P0 + P1
python skills/software-project-governance/infra/cleanup.py --target <plugin_cache_dir> --categories P0,P1
```

清理顺序：先删文件，后删空目录。`.git/` 和 `.governance/` 在任何情况下都不会被删除（硬编码保护 + manifest exclude 双保险）。

### Step 5: 输出报告

```
清理完成:
  Deleted {N} file(s)
  Removed {M} empty director(y/ies)
  Plugin installation is now clean.
```

## 参数

| 参数 | 类型 | 必需 | 默认值 | 描述 |
|------|------|------|---------|------|
| `--target` | 路径 | 否 | 当前工作目录 | 清理目标目录（默认：当前目录；用户机建议显式指定 plugin cache 路径） |
| `--dry-run` | 布尔 | 否 | false | 仅展示冗余文件，不执行删除 |
| `--json` | 布尔 | 否 | false | JSON 格式输出（供外部脚本消费） |
| `--manifest` | 路径 | 否 | `<target>/skills/software-project-governance/core/manifest.json` | 自定义 manifest 路径 |
| `--categories` | 字符串 | 否 | `P0,P1,P2` | 逗号分隔的清理类别（如 `P0` 或 `P0,P1`） |

## 错误码

| 代码 | 条件 | 退出码 | 动作 |
|------|------|--------|------|
| CLEANUP-ERR-001 | target 目录不存在 | 3 | 提示用户检查插件安装状态，或使用 `--target` 指定正确路径 |
| CLEANUP-ERR-002 | 无可清理文件 | 1 | 告知用户插件已是纯净版本，无需操作 |
| CLEANUP-ERR-003 | manifest.json 不存在或格式错误 | 2 | 提示：`skills/software-project-governance/core/manifest.json` 缺失。检查插件安装完整性或降级为旧版硬编码模式 |

## 安全保证

- **不触碰用户项目文件**：清理目标目录由 `--target` 显式指定，默认不操作用户项目根目录
- **不删除 `.governance/`**：始终在 exclude_from_cleanup 中，且有硬编码二次保护
- **不删除 `.git/`**：同上，双重保护
- **dry-run 先展示**：所有清理前必须通过 `--dry-run` 展示待删列表，用户确认后才执行
- **排除清单**：`node_modules/`、`__pycache__/`、`*.pyc`、`.env*`、`*.log` 等永远不被视为冗余
- **可跳过**：用户始终可以选择不清理

## 自校验

- [ ] manifest.json 已加载且版本匹配
- [ ] 冗余文件列表已按 P0/P1/P2 分类展示
- [ ] 排除清单中的文件未被标记为冗余
- [ ] 用户已确认清理范围（或 dry-run 模式仅查看）
- [ ] `.git/` 和 `.governance/` 未被触碰
- [ ] 用户项目文件未被触碰
- [ ] 清理后插件目录只包含 canonical 文件

## 设计演进

| 旧设计（v0.19.0 之前） | 新设计（v0.19.0+） |
|---|---|
| 硬编码 45 个冗余文件路径 | 从 manifest.json 自动计算 |
| "已知冗余" -- 维护者需记住上版本有什么 | "结构 diff" -- manifest 声明当前版本有什么，其余 = 冗余 |
| stub 内容检测是特例化逻辑 | cleanup.py 中作为 P0 分类辅助，不再需要手动维护 stub 列表 |
| 版本升级需手动追加清理条目 | 版本升级只需更新 manifest.json（移除旧路径、添加新路径） |
| 无参数 | 支持 `--dry-run`、`--json`、`--target`、`--manifest`、`--categories` |
| 2 个错误码 | 3 个错误码（新增 CLEANUP-ERR-003: manifest 缺失） |
