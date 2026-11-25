---
name: xc-suite
description: 炫语言与炫彩 XCGUI/DirectUI 开发：按功能选用 XC-Module、语法/API、布局资源、hum/humbox/WmUi、模块封装及 IDE 构建。涉及炫语言、炫彩、XCGUI 或本地模块调用时使用。
---

# 炫语言 / 炫彩

用户只描述功能时，自行选择模块：优先复用工程已有模块，再比较功能、架构、依赖和示例。尊重用户指定的模块与平台；只有无法推断且影响结果的关键条件才询问。

## 本仓库的构建与测试方式

此版本从用户的本机 `xc-suite` 整理而来，来源哈希见 `SOURCE.json`。本技能提供炫语言语法、模块和 UI 资料；安装 `cli-anything-xcide` 后用其命令完成工程操作。它不需要 `mcp-cli` 或 XC-MCP-Next。

- 编译使用 `cli-anything-xcide --json --ide IDE目录 --project 工程路径 build --diagnostics`。检查退出码、`ok`、`compiler.compiled`、错误数和本轮新 PE。
- 程序运行用 `runtime run`；后台交互用 `runtime test`，目标程序须主动接入 CLI 随包的 `native/automation_bridge.h`，采用 GDI 才能截图。先用 `--help` 和安装包中的 `AI_CALLING.md` 查看参数及可运行示例。
- 后台运行必须保持前台不受影响，不使用 `SendInput`、`SetCursorPos`、`SetForegroundWindow` 或切换桌面来补救。参考中的前台鼠标/OCR 流程属于历史外部联调记录，不适用于本仓库的后台测试。
- 参考中的 MCP 命令、`J:` 盘资料、旧工程与旧哈希仅作来源记录；不存在时用当前 IDE 文件和 CLI 查询，不把它们当作必需依赖，也不据此启动 MCP 服务。
- 模块索引不随仓库分发。在此技能目录运行 `python scripts/xc_modules.py --root 'I:\xcide\data\XC-Module' rebuild`，然后用 `stats`、`list`、`search`、`show` 等按需查询。重建只写技能目录中的三份索引；其他安装位置通过 `--root` 或 `XC_MODULE_ROOT` 指定。

## 按需读取

先定位任务，再读下表对应章节。长文先用 `rg -n '^#{1,4} ' 文件` 找标题，只读所需范围。修改前读 `references/task-rules.md` 的对应小节；只查询接口时不用加载验证规则。

| 任务 | 参考文件（均在 references/） | 专项规则 |
| --- | --- | --- |
| 功能选模块、查接口/依赖/示例、接入工程 | `xc-modules.md`；直接运行检索脚本 | §3（写代码时） |
| 语法、类型、容器、预处理、入口、基础模块、批量改名 | `xuanlang-lang.md` §1–§5；改名 §2.4.1 | §3 |
| 布局 XML、layout.*、控件/窗壳、工具窗 | `interface-xml.md` §1–§6 | §1；工具窗再读 §2 |
| bkInfoM 状态/绘制/颜色、resource.res 注册 | `bkinfom-res.md` §1–§6 | §1 |
| WmUi 类名/主题/辅助函数/部署 | `wmui-styles.md` §2–§6、§8 | §2；部署 §4、验证 §5 |
| hum/humbox 未闻花名、导航/面板/模板 | `skin-platforms.md` §1–§6 | §2 |
| XCGUI 句柄/事件/列表/拖放、系统API、线程池 | `xcgui-code.md` §2–§9 | §3、§5（涉及交互时） |
| module_ 注解、CX 类型、库/示例、易语言迁移、构建部署 | `module-packaging.md` §4–§14 | §3；构建迁移再读 §4 |
| UI 渲染、radio/check、DPI、原生输入/OCR 联调 | `ui-verification.md` §1–§8；事件细节 `xcgui-code.md` §6.5–§6.7 | §5 |
| 参考未覆盖的源材料、皮肤包本体 | `task-rules.md` §6 | 按来源读取 |

## 共用约束

- 接口、别名、属性、ID、资源和版本行为以当前源码为准；保留既有命名与结构，不臆造。
- 模块根目录 `I:\xcide\data\XC-Module`；旧资料中的 `常规/网络/kyozy` 分类不代表当前路径。
- 布局/资源 UTF-8 无 BOM；模块 `.h/.cpp` UTF-8-BOM。PowerShell 路径用 `-LiteralPath`。
- 模块通过 `.xcproj` 的 `<modules>` 引用，`common.xh` 不包含模块头。同名模块按完整路径区分。
- 索引命中、F7 投递、旧 EXE 均不证明当前源码构建成功；实际验收按对应任务取证。
- 不读取 `sessions/`、`.codegraph/` 作为技能资料。

API 用 `scripts/xc_modules.py` 查询。不要整读 `api.jsonl`、`catalog.json`、完整模块目录或全部参考；未命中时再扩大检索。详细规则与源材料均保留在按需参考中。
