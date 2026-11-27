# 炫语言与 XCGUI 开发指南

用户只描述功能时，自行选择模块：优先复用工程已有模块，再比较功能、架构、依赖和示例。尊重用户指定的模块与平台；只有无法推断且影响结果的关键条件才询问。

## 本仓库的构建与测试方式

本资料由入口 `cli-anything-xcide` 技能按需读取，来源哈希见同目录 `SOURCE.json`。安装 CLI 后用其命令完成工程操作；无需 `mcp-cli` 或 XC-MCP-Next。

- 编译使用 `cli-anything-xcide --json --ide IDE目录 --project 工程路径 build --diagnostics`。检查退出码、`ok`、`compiler.compiled`、错误数和本轮新 PE。
- 程序运行用 `runtime run`；后台交互用 `runtime test`，目标程序须主动接入 CLI 随包的 `native/automation_bridge.h`，采用 GDI 才能截图。先用 `--help` 和安装包中的 `AI_CALLING.md` 查看参数及可运行示例。
- 后台运行必须保持前台不受影响，不使用 `SendInput`、`SetCursorPos`、`SetForegroundWindow` 或切换桌面来补救。参考中的前台鼠标/OCR 流程属于历史外部联调记录，不适用于本仓库的后台测试。
- 参考中的 MCP 命令、`J:` 盘资料、旧工程与旧哈希仅作来源记录；不存在时用当前 IDE 文件和 CLI 查询，不把它们当作必需依赖，也不据此启动 MCP 服务。
- 模块索引不随包分发。从本指南目录运行 `python scripts/xc_modules.py --root 'I:\xcide\data\XC-Module' rebuild`，再按需 `search` 或 `show`。可用 `--root` 或 `XC_MODULE_ROOT` 指定模块库；索引位置及完整示例见[模块检索](references/xc-modules.md)。

## 按需读取

以下路径相对于本指南。先定位任务，再读下表对应章节。修改前读[开发与验证规则](references/task-rules.md)的对应小节；只查询接口时不用加载验证规则。

| 任务 | 参考文件（均在 references/） | 专项规则 |
| --- | --- | --- |
| 功能选模块、查接口/依赖/示例、接入工程 | [模块检索](references/xc-modules.md)和[脚本](scripts/xc_modules.py) | §3（写代码时） |
| 语法、类型、容器、预处理、入口、基础模块、批量改名 | [炫语言语法](references/xuanlang-lang.md) §1–§5；改名 §2.4.1 | §3 |
| 布局 XML、layout.*、控件/窗壳、工具窗 | [布局 XML](references/interface-xml.md) §1–§6 | §1；工具窗再读 §2 |
| bkInfoM 状态/绘制/颜色、resource.res 注册 | [背景与资源](references/bkinfom-res.md) §1–§6 | §1 |
| WmUi 类名/主题/辅助函数/部署 | [WmUi 样式](references/wmui-styles.md) §2–§6、§8 | §2；部署 §4、验证 §5 |
| hum/humbox 未闻花名、导航/面板/模板 | [皮肤平台](references/skin-platforms.md) §1–§6；[humbox 原始参考](absorbed/xcgui-humbox/GUIDE.md) | §2 |
| XCGUI 句柄/事件/列表/拖放、系统 API、线程池 | [XCGUI 接口](references/xcgui-code.md) §2–§9 | §3、§5（涉及交互时） |
| module_ 注解、CX 类型、库/示例、易语言迁移、构建部署 | [模块封装](references/module-packaging.md) §4–§14 | §3；构建迁移再读 §4 |
| UI 渲染、radio/check、DPI、原生输入/OCR 联调 | [UI 验证](references/ui-verification.md) §1–§8；事件细节见 XCGUI 接口 §6.5–§6.7 | §5 |
| 参考未覆盖的源材料、皮肤包本体 | `task-rules.md` §6 | 按来源读取 |

## 共用约束

- 接口、别名、属性、ID、资源和版本行为以当前源码为准；保留既有命名与结构，不臆造。
- 模块根目录 `I:\xcide\data\XC-Module`；旧资料中的 `常规/网络/kyozy` 分类不代表当前路径。
- 布局/资源 UTF-8 无 BOM；模块 `.h/.cpp` UTF-8-BOM。PowerShell 路径用 `-LiteralPath`。
- 模块通过 `.xcproj` 的 `<modules>` 引用，`common.xh` 不包含模块头。同名模块按完整路径区分。
- 索引命中、F7 投递、旧 EXE 均不证明当前源码构建成功；实际验收按对应任务取证。
- 不读取 `sessions/`、`.codegraph/` 作为技能资料。

API 用 `scripts/xc_modules.py` 查询。不要整读 `api.jsonl`、`catalog.json`、完整模块目录或全部参考；未命中时再扩大检索。详细规则与源材料均保留在按需参考中。
