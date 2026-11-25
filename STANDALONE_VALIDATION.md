# 独立仓库整理与验收

验收日期：2026-11-25。目录：`E:\AIWork\Codex\cli-anything-xcide`。本次工作把原本分散的 XCIDE harness、技能文档、探索报告和自动化证据整理到独立仓库。

## 整理范围

- 保留 `xcide/agent-harness`、`skills/cli-anything-xcide` 的相对结构，已有命令、模块、测试和原生桥接内容与原目录一致。
- 汇集 AI 调用手册、三批探索报告、JSON 取证、审查记录、编译/运行证据和截图。
- 增加仓库首页、Git 忽略规则、来源说明及许可证副本；修正文档中的仓库目录写法和示例脚本的一条旧注释。
- `.gitattributes` 保留原始 BOM 和换行字节，避免 Git 转换导致既有证据哈希失效。
- 虚拟环境、构建目录、wheel、IDE 可执行文件、SDK、模块二进制和临时工程均不提交。

## 完成的检查

1. 独立虚拟环境安装成功；确认 Python 导入路径和 `cli-anything-xcide.exe` 均位于新目录。
2. 迁移的 Python 文件按 Python 3.10 语法完成 AST 检查；实际运行环境为 Windows、Python 3.14。
3. 7 个自动化核心源码与历史 `summary.json` 中的 SHA-256 一致，现有源码没有因整理改变。
4. wheel 构建成功；42 个包内文件逐字节匹配本仓库源码，LICENSE 和 NOTICE 均随 wheel 分发。
5. 离线 HTML 与 Markdown 的本地链接完成可达性检查，目标均位于本仓库。
6. Git 提交清单已排除虚拟环境、编译产物和凭证文件；常见密钥/令牌特征扫描未命中。

## 全量安装命令测试

使用新目录的独立环境与已安装命令，命令为：

```powershell
$env:CLI_ANYTHING_FORCE_INSTALLED = '1'
$env:PYTHONUTF8 = '1'
& .\.venv\Scripts\python.exe -X utf8 -B -m pytest xcide/agent-harness/cli_anything/xcide/tests -q --tb=short -p no:cacheprovider
```

结果：**190 passed, 1 failed in 105.43s**。失败用例为 `TestRuntimeAutomation.test_background_adapter_modes_and_input_state[x64]`。原始日志：[full-suite.txt](xcide/automation-evidence/standalone-validation/full-suite.txt)。

对 x64/x86 的同组用例做了一次定向复测，结果：**1 passed, 1 failed, 34 deselected in 12.36s**。这次 x64 通过，x86 在相同清理阶段超时。原始日志：[targeted-retry.txt](xcide/automation-evidence/standalone-validation/targeted-retry.txt)。

## 已知未解决问题

- 严重程度：中。
- 文件位置：`xcide/agent-harness/cli_anything/xcide/utils/win_debug.py`，`DebugProcess.close`；对应断言在 `tests/test_full_e2e.py` 的后台适配器模式测试。
- 问题描述：D2D 截图按设计被拒绝后，CLI 终止自己启动的进程并等待退出，清理阶段偶发超时，`cleanup_error` 非空。一次报告尚未收到进程退出事件；另一次已有终止退出码，但进程句柄的后续 1 秒等待仍超时。
- 触发条件：本机真实 XCGUI 程序使用 D2D，在截图步骤收到“不支持”的返回后走强制清理。两轮测试分别在 x64、x86 出现，不能认定由架构或目录位置导致。
- 影响范围：失败运行会保留主要错误并返回失败，同时附加清理错误；目前证据不足以保证这一路径在所有环境都能于既定期限内回收。检查时这两个已知进程均已退出，未发现持续遗留。正常 GDI 输入、点击和截图用例通过。
- 最小修复建议：补充终止请求、调试退出事件、进程句柄 signaled 状态的时间线，确认延迟发生位置后再调整有限等待或清理顺序；保留主错误及清理错误，不删除断言或无条件忽略超时。
- 不确定之处：是否涉及 D2D/图形驱动、输入法组件或系统调度尚未确认。输出中出现输入法组件日志，但没有证据证明它就是根因。

原始失败报告分别为 [x64](xcide/automation-evidence/standalone-validation/d2d-cleanup-x64.json) 和 [x86](xcide/automation-evidence/standalone-validation/d2d-cleanup-x86.json)。本次整理不改变运行逻辑；原开发目录中 191 项通过的历史结果与这里的复测结果分别保留。
