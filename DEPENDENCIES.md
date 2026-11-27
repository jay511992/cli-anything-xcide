# Agent 技能、MCP 插件与运行依赖

Magpie 只需启用一个 `cli-anything-xcide` 技能。它包含 CLI 调用规则和按需加载的炫语言/XCGUI 开发参考，不再依赖单独安装或启用 `xc-suite`。MCP 插件不是当前 CLI 的运行依赖。

| 项目 | 用途 | 本仓库交付方式 |
| --- | --- | --- |
| `skills/cli-anything-xcide` | CLI 调用、编译验收和 XC 开发 | 整个技能目录可单独导入 Magpie；wheel 在 `cli_anything/xcide/skills/` 中包含同样的文件 |
| 技能内 `references/xc-suite/` | 炫语言语法、模块、事件、布局、皮肤及模块检索脚本 | 随 Git 仓库和 wheel 提供；只在开发时读取，无需注册第二个技能 |
| `native/output_bridge.cpp` | 从本轮私有 IDE 读取真实编译输出 | 已随 CLI 源码和 wheel 包含，运行时在隔离副本编译加载 |
| `native/ide_bridge.cpp` | 持续后台 IDE 的编辑缓冲、符号、输出、弹窗及原生操作 | 已包含；配合 `ide start/call/stop`，本地文件 IPC，无 MCP 传输 |
| `native/automation_bridge.h` | 被测 XCGUI 程序主动接入的后台交互入口 | 已随 CLI 源码和 wheel 包含，Agent 按示例接入自己的程序 |
| XC-MCP-Next | 原生接口和工具迁移的参考源码 | `ide call` 已覆盖该版本的 30 个工具名及对应能力；不连接/加载原插件，不提供 MCP endpoint；差异见 [迁移说明](IDE_COMPAT.md) |
| `mcp-cli` 技能 | 调用本机配置的 MCP 服务 | 可选外部工具，不影响当前 CLI；不打包含其他服务端点和令牌的本机 `servers.json` |
| CLI-Anything 构建技能 | 开发 harness 时采用的方法和共享辅助代码 | 来源保留在 NOTICE；运行本工具不要求安装生成工具 |
| 炫彩 IDE、模块库、MSVC、Windows SDK | 原生格式、编译器、头文件与链接库 | 用户在目标机器安装，设置 `--ide`、`XC_IDE_ROOT` 或模块脚本的 `--root` |

## 在新机器上使用

1. 按 [仓库首页](README.md) 安装 CLI 与本机 IDE/编译环境。
2. 在 Magpie 的 Library → Skills 中导入整个 `skills/cli-anything-xcide/`，分配给需要的 Agent。若只安装了 wheel，可执行 `python -c "import cli_anything.xcide as xc; from pathlib import Path; print(Path(xc.__file__).parent / 'skills')"` 找到同样的目录，把它整体复制为 `cli-anything-xcide/` 再导入。不要只复制顶层 `SKILL.md`。
3. 如需按原生别名或英文签名查模块，从仓库根目录运行下例。单独导入或从 wheel 安装时，将 `$xc` 指向技能目录内同一相对位置的脚本。
4. 按 [调用手册](AI_CALLING.md) 创建工程、写源码、运行 `build --diagnostics`，再用 `runtime run/test` 验收。

```powershell
$xc = 'skills/cli-anything-xcide/references/xc-suite/scripts/xc_modules.py'
python $xc --root 'I:\xcide\data\XC-Module' rebuild
python $xc search 'XBtn_Create' --limit 3
```

检索脚本只依赖 Python 标准库。三份生成索引默认写入 `%LOCALAPPDATA%\cli-anything-xcide\module-index`，也可用 `XC_MODULE_INDEX_DIR` 指定可写目录，不要求有 wheel 安装目录的写权限。

## 来源与边界

XC 开发资料来源快照见 [SOURCE.json](skills/cli-anything-xcide/references/xc-suite/SOURCE.json)。正文已做有限适配：去掉固定用户目录、说明索引重建、将默认构建方式指向当前 CLI，并明确历史前台输入流程不用于本仓库。参考中个别旧工程、`J:` 盘原始材料与皮肤包路径是历史来源；它们不随仓库提供，也不是正常创建/编译/后台测试的必需文件。接口仍以目标机器当前模块源码为准。

参考过的插件源码位于原机器 `I:\xcide\xc-plugin\XC-MCP-Next`，本次读取的提交为 `6581afba4fba5743844f702953adfe2f586a9f04`。这是可选外部工程的版本定位，不能据此宣称本 CLI 使用了 MCP 传输，或宣称插件本身具备“不影响前台”的保证。当前 Python 运行链没有 MCP 客户端或 HTTP 传输依赖，实际验收直接调用打包的桥接与本机 API。

在其他环境若明确要改为 MCP 工作流，应单独取得该插件源码及其许可、编译安装并配置本机端点；不要复制原机器的令牌、绝对路径或其他服务配置。当前提供的后台构建与测试无需这一步。
