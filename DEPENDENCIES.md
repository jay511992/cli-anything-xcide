# Agent 技能、MCP 插件与运行依赖

要在另一台机器上让 Agent 编写炫语言程序，建议一起携带本仓库的两套技能。MCP 插件不是当前 CLI 的运行依赖。

| 项目 | 用途 | 本仓库交付方式 |
| --- | --- | --- |
| `skills/cli-anything-xcide` | 告诉 Agent 如何调用 CLI、解析 JSON、编译和验收 | 已包含，pip wheel 另带兼容副本 |
| `skills/xc-suite` | 炫语言语法、模块、事件、布局、资源和皮肤知识 | 本轮补齐入口、参考、检索脚本和来源清单；随 Git 仓库交付 |
| `native/output_bridge.cpp` | 从本轮私有 IDE 读取真实编译输出 | 已随 CLI 源码和 wheel 包含，运行时在隔离副本编译加载 |
| `native/ide_bridge.cpp` | 持续后台 IDE 的编辑缓冲、符号、输出、弹窗及原生操作 | 已包含；配合 `ide start/call/stop`，本地文件 IPC，无 MCP 传输 |
| `native/automation_bridge.h` | 被测 XCGUI 程序主动接入的后台交互入口 | 已随 CLI 源码和 wheel 包含，Agent 按示例接入自己的程序 |
| XC-MCP-Next | 原生接口和工具迁移的参考源码 | `ide call` 已覆盖该版本的 30 个工具名及对应能力；不连接/加载原插件，不提供 MCP endpoint；差异见 [迁移说明](IDE_COMPAT.md) |
| `mcp-cli` 技能 | 调用本机配置的 MCP 服务 | 可选外部工具，不影响当前 CLI；不打包含其他服务端点和令牌的本机 `servers.json` |
| CLI-Anything 构建技能 | 开发 harness 时采用的方法和共享辅助代码 | 来源保留在 NOTICE；运行本工具不要求安装生成工具 |
| 炫彩 IDE、模块库、MSVC、Windows SDK | 原生格式、编译器、头文件与链接库 | 用户在目标机器安装，设置 `--ide`、`XC_IDE_ROOT` 或模块脚本的 `--root` |

## 在新机器上使用

1. 按 [仓库首页](README.md) 安装 CLI 与本机 IDE/编译环境。
2. 让 Agent 读取 [CLI 技能](skills/cli-anything-xcide/SKILL.md) 和 [XC 开发技能](skills/xc-suite/SKILL.md)。可直接读取仓库路径；如使用支持技能目录的代理，也可将这两个目录复制到该代理的技能目录，保留子目录结构。
3. 如需按原生别名或英文签名查模块，在仓库根目录运行下面的重建命令。索引反映目标机器的模块版本，不从旧报告推断当前 API。
4. 按 [调用手册](AI_CALLING.md) 创建工程、写源码、运行 `build --diagnostics`，再用 `runtime run/test` 验收。

```powershell
python skills/xc-suite/scripts/xc_modules.py --root 'I:\xcide\data\XC-Module' rebuild
python skills/xc-suite/scripts/xc_modules.py stats
python skills/xc-suite/scripts/xc_modules.py list 'JSON'
python skills/xc-suite/scripts/xc_modules.py search 'XBtn_Create' --limit 3
```

模块索引 `catalog.json`、`catalog.md`、`api.jsonl` 由本机生成并被 Git 忽略；可重新生成，不上传安装包内的大量声明副本。查询脚本只依赖 Python 标准库。

## 来源与边界

XC 技能来源快照见 [SOURCE.json](skills/xc-suite/SOURCE.json)。正文已做有限适配：去掉固定用户目录、说明索引重建、将默认构建方式指向当前 CLI，并明确历史前台输入流程不用于本仓库。参考中个别旧工程、`J:` 盘原始材料与皮肤包路径是历史来源；它们不随仓库提供，也不是正常创建/编译/后台测试的必需文件。接口仍以目标机器当前模块源码为准。

参考过的插件源码位于原机器 `I:\xcide\xc-plugin\XC-MCP-Next`，本次读取的提交为 `6581afba4fba5743844f702953adfe2f586a9f04`。这是可选外部工程的版本定位，不能据此宣称本 CLI 使用了 MCP 传输，或宣称插件本身具备“不影响前台”的保证。当前 Python 运行链没有 MCP 客户端或 HTTP 传输依赖，实际验收直接调用打包的桥接与本机 API。

在其他环境若明确要改为 MCP 工作流，应单独取得该插件源码及其许可、编译安装并配置本机端点；不要复制原机器的令牌、绝对路径或其他服务配置。当前提供的后台构建与测试无需这一步。
