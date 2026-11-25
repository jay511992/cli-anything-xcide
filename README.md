# 炫彩 IDE CLI 与后台自动化

`cli-anything-xcide` 让 AI Agent 和脚本通过命令行创建、编辑、检查、编译和测试炫语言工程。基于 CLI-Anything 工作流，直接使用本机炫彩 IDE 与原生工程文件，无需 MCP 服务。

文档从 [文档总览](DOCS.md) 进入。下载仓库后可用浏览器打开 [DOCS.html](DOCS.html)，所有阅读版均为离线 HTML。完整操作步骤见 [AI 自动化调用手册](AI_CALLING.md)，已有问题和修复依据见 [后台自动化审查](AUTOMATION_REVIEW.md)。

## 可用能力

- 浏览本机工程模板、示例和模块依赖；创建或派生独立工程。
- 读写源码，维护工程配置、源码登记、断点、监视表达式和书签。
- 查询原生语法、控件、属性、事件、布局节点、命名资源与 UI ZIP。
- 用真实 IDE 在独立 Windows 后台桌面编译；`build --diagnostics` 返回编译输出和文件/行号诊断。
- 用 `runtime run` 捕获本次进程的标准输出、调试输出、异常和退出码。
- 用 `runtime test` 执行后台消息点击、文本/按键输入、断言与 GDI 截图，生成 JSON 测试报告。

构建和运行不切换前台桌面、不移动鼠标。交互测试要求被测 XCGUI 程序主动接入随包提供的 `automation_bridge.h`；截图当前支持 GDI。完整支持范围和限制见调用手册。

## 安装

需要 Windows 10/11、Python 3.10+ 和已安装的炫彩 IDE。IDE 默认位置为 `I:\xcide`，可用 `--ide` 或 `XC_IDE_ROOT` 指定。后台自动化需要 64 位 Python 与可用的 Windows 桌面会话；编译输出桥接还需要 Visual Studio C++ 工具和 Windows SDK。

在仓库根目录运行：

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e './xcide/agent-harness[test]'
& .\.venv\Scripts\cli-anything-xcide.exe --help
```

`test` 安装 pytest 和截图所需 Pillow。只使用工具时可将安装选项换成 `automation`。激活虚拟环境后可直接使用 `cli-anything-xcide`；也可以始终使用其完整路径。

```powershell
& .\.venv\Scripts\Activate.ps1
$env:PYTHONUTF8 = '1'
cli-anything-xcide --json --ide 'I:\xcide' project template list
cli-anything-xcide --json --ide 'I:\xcide' example list '按钮'
```

全局参数放在子命令之前。Agent 应同时检查退出码、stdout/stderr 和 JSON 中的 `ok`。带诊断构建只有在确认编译完成、零错误及本轮新产物验证通过后才成功；普通 `build` 的编译器错误数仍为未知。

## 让 Agent 编写一个 XC 程序

把 [技能文件](skills/cli-anything-xcide/SKILL.md) 和 [调用手册](AI_CALLING.md) 提供给 Agent，并给出工程目标目录、IDE 路径、功能要求及验收标准。例如：

> 在指定新目录创建 x64 调试版计数器。先查本机模板、模块依赖和事件签名，再写炫语言源码；接入 automation_bridge.h 并使用 GDI 渲染。用 build --diagnostics 后台编译，依据真实错误修复。编写 runtime test JSON 场景，验证中文输入、按钮点击、业务日志、截图和正常退出。全程不得抢占前台或移动鼠标。交付源码、构建 JSON、测试报告和截图。

可运行的起点是 [计数器源码](xcide/agent-harness/cli_anything/xcide/examples/automation_counter.xc) 和 [测试场景](xcide/agent-harness/cli_anything/xcide/examples/automation_counter.json)。手册包含创建工程、添加模块、复制适配器、构建和测试的完整命令。

## 文件组织

| 路径 | 内容 |
| --- | --- |
| `xcide/agent-harness/` | 可安装的 Python harness、测试、原生桥接、示例及辅助工具 |
| `skills/cli-anything-xcide/` | AI Agent 技能说明及离线阅读版 |
| `xcide/automation-evidence/` | 编译成功/失败、后台交互及截图的历史验收证据 |
| `AI_CALLING.md`、`DOCS.md` | AI 调用手册和文档导航 |
| `AI_MINING_REPORT*.md`、`AI_MINING_EVIDENCE_*.json` | 三批 20/20/50 轮探索记录和原始取证 |
| `AUTOMATION_REVIEW.md` | 后台自动化问题、修复与验证记录 |

历史报告中的测试数量对应当时版本；开发期测试记录见 [TEST.md](xcide/agent-harness/cli_anything/xcide/tests/TEST.md)，本次搬迁复测见 [独立仓库验收](STANDALONE_VALIDATION.md)。证据 JSON 保留原运行环境的路径与哈希，部分临时路径已失效；已复制的截图可直接查看。

## 验证与打包

激活上述虚拟环境后，在仓库根目录运行：

```powershell
$env:CLI_ANYTHING_FORCE_INSTALLED = '1'
python -X utf8 -B -m pytest xcide/agent-harness/cli_anything/xcide/tests -q --tb=short -p no:cacheprovider
python -m pip wheel ./xcide/agent-harness --no-deps -w ./dist
```

完整测试包含真实 IDE 构建、诊断和后台交互测试，要求上述本机依赖齐全；部分验收样本目前固定读取 `I:\xcide`。测试不会因为缺少真实后端而假装通过。

2026-11-25 独立目录复测为 **190 项通过、1 项失败**。失败发生在拒绝 D2D 截图后的后台进程清理；定向复测中 x64 通过、x86 出现同类超时。普通 GDI 交互测试通过，超时原因仍未确认。原开发目录中曾完成 191 项全通过的记录保留作历史依据，本次未通过反复重跑掩盖失败，也未为搬迁修改运行代码。详见验收报告。

Markdown 为文档源文件，修改后可使用渲染器更新对应 HTML：

```powershell
python xcide/agent-harness/tools/render_markdown.py AI_CALLING.md AI_CALLING.html
```

项目来源及依赖说明见 [NOTICE](NOTICE)，保留的 CLI-Anything Apache 2.0 许可证见 [LICENSE](LICENSE)。
