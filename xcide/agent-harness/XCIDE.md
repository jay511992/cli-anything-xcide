# XCGUI／炫语言 IDE 无 MCP 命令行架构与操作说明

## 这个项目能做什么

`cli-anything-xcide` 是炫彩 IDE 的本地命令行助手。它直接读取本机安装的 IDE 模板、示例工程、`.xcproj` 工程 XML、源码和模块目录，支持检查、查找和派生项目，也可启动真实 IDE 编译；不需要安装或启动 MCP 插件。工具使用 Click 提供可脚本调用的子命令、JSON 输出、默认交互式 REPL 以及可持久化的工程会话。

炫语言工程使用 XML 格式的 `.xcproj` 文件。入口源码登记在 `<codeExpand>`，模块引用登记在 `<modules>`。IDE 自带空白窗口模板位于 `data/template/项目模板/炫语言/空白窗口程序/空白窗口程序/project`，包含 `template.xcproj`、`main.xc`、`common.xh`、`exe.rc` 和 `exe.ico`。

## 命令和能力对应关系

| 命令组 | 本地能力 | 副作用与边界 |
| --- | --- | --- |
| `project new/info/list/open/template/doctor` | 从 IDE 空白/官方/用户模板创建工程；检查工程配置、源码登记、模块引用和工程健康；递归查找 `.xcproj`；选择 CLI 会话工程。 | 模板 ID 来自本机安装目录；复制只会创建全新目录；`open` 是 CLI 选中工程，不控制 GUI 窗口。 |
| `project config list/set` | 查看和切换本机项目中已有的调试/发布配置以及 x86/x64 架构。 | 只更改准确 `.xcproj` 的活动设置；只允许选择 XML 里已存在的项，不构建或控制 GUI。 |
| `project sources list/add/remove` | 扫描工程中的 `.xc/.xcs` 文件，并维护 `<codeExpand>` 源码树登记。 | 添加需要真实工程内文件，移除仅取消登记且保留文件本身；不编译。 |
| `project breakpoints list/add/remove` | 查看工程断点并依据源码行数校验，增删工程 XML 中的断点项。 | 修改 `.xcproj` 断点数据，不修改源码，也不附加到调试器。 |
| `project debug list/watch-add/watch-remove/bookmark-add/bookmark-remove` | 读取或维护 `.xcproj` 的 watches、bookmarks 元数据。 | 监视表达式不求值、不运行程序；书签行通过磁盘源码核验。 |
| `example list/info/copy` | 搜索、检查并派生 IDE 随附的炫语言示例工程。 | 只读本机 `data/示例`；复制到新目录，重命名 `.xcproj`，排除构建产物，不修改原示例。 |
| `ui-template list/info/copy` | 搜索 IDE 原生 `template.config`，检查并复制布局模板或皮肤的资源目录。 | 不覆盖目标或改动安装目录；跳过生成物和符号链接。 |
| `theme list/info` | 解析安装的 `data/theme/*/xctheme.config`，显示字体、行距、皮肤路径、断点色与设计背景色。 | 只读主题 XML；不切换用户当前 IDE 全局主题。 |
| `editor read/write` | 从磁盘读写工程源码、头文件或安装目录中的文件；检测 UTF-8、UTF-16、GB18030、BOM 和 CRLF；写后回读验证。 | 默认只允许所选工程和 IDE 安装目录；其他本机路径需要 `--allow-outside-project`。 |
| `module list/search/dependencies` | 扫描 `data/XC-Module` 和 `data/XC-Module-dev`，解析名称、版本、作者、备注与 `//@依赖`，输出依赖优先级和诊断。 | 计划只读；同名、缺失和循环都会明确报告。 |
| `module add/remove` | 单独添加模块，或验证依赖闭包后一次性将模块引用写入 `.xcproj`；也可移除指定引用。 | `--with-dependencies` 遇到依赖缺失或同名歧义时会拒绝修改；成功后使用 XML 原子替换。 |
| `status` | 返回本地工程、IDE 安装位置和 CLI 会话信息。 | 不查询运行中 GUI 窗口。 |
| `build` / `build --diagnostics` | 独立后台桌面打开私有 IDE，定向 F7、核验新 PE；可选输出桥接读取真实错误和警告。 | 普通模式无插件、诊断未知；诊断模式仅在私有 IDE 编译/加载 DLL，不使用 MCP/网络。当前支持 AMD64 IDE v3。 |
| `runtime run/test` | 后台运行输出/异常/退出码捕获；XCGUI 消息分派、断言、完整 GDI 绘制截图。 | test 需程序显式接入 automation_bridge.h，不向任意程序注入；D2D 截图不支持。 |
| `preview capture/latest` | 根据磁盘工程信息和 EXE 产物发布、读取不可变 `preview-bundle/v1` 检查包。 | 不截图、不编译，也不读取 IDE 输出窗格。 |
| `interface list/check` | 发现 `main.xml`、其他炫彩布局 XML 与 `UI_ZIP.zip` 中的布局，并核验多根 XML、ZIP 条目及可验证的资源引用。 | 只读；无法可靠解析的主题资源提示为警告，不据此改写资源。 |
| `interface nodes/node` | 查询显式磁盘或 ZIP 布局的节点、层级、绑定、原生属性和子树。 | `showT` 不作运行时可见性推断；位置 ID 结合来源哈希使用。 |
| `resource list/show` | 读取任意命名 resources XML，递归展开 folder，定位资源和图片/字体文件。 | 分类名与资源名分别处理；命名空间引用保持未解析，不推断加载顺序。 |
| `archive list/read/export` | 检查 ZIP 目录、读取文本、原样导出单个成员。 | list 不验证 CRC；read/export 校验所选成员；export 只写显式新文件，拒绝安装目录。 |
| `session status/history/undo/redo` | 查看、撤销和重做 CLI 已选工程与 IDE 安装位置。 | 文件锁和修订号检查保护会话 JSON；不会撤销源码改动。 |

## 本地后端设计

- **后台执行：**`utils/win_debug.py` 用 Win32 CreateProcess 的 `lpDesktop` 创建进程，暂停启动后加入独立 Job 再恢复；结束时清理本次进程树。IDE 使用非调试模式，被测程序使用 Windows 调试事件模式。`utils/win_desktop.py` 只枚举私有桌面并验证 PID/EXE，无切换前台、移动鼠标或全局输入。窗口前后观测只是证据，不覆盖用户正在进行的操作。
- **编译诊断与原生交互：**`native/output_bridge.cpp` 根据官方插件 ABI 在 UI 线程读取 IDE 输出；`core/diagnostics.py` 同时核验完成、错误总数、原生失败和新产物。`native/automation_bridge.h` 供测试工程主动接入，用本轮 token 和桌面名限制启动，调用 `XC_SendMessage` 走控件消息路径；GDI 截图在 `XWM_PAINT_END` 复制真实绘制缓冲。

- **工程创建和检查：**复制 IDE 自带模板到暂存目录，更新 XML 工程名、配置、SDK、工具集和入口源码列表，再将新工程移动到唯一的新目标目录。
- **源码操作：**采用本地字节读取和原子写入，检测常见源码编码、BOM 及换行格式，读取和写入都检查 `.xcproj`、工程目录和 IDE 安装根目录之间的边界。
- **模块操作：**扫描模块目录和 UTF-8／GB18030 头部元数据，使用同目录临时文件和 `os.replace` 更新工程 XML。
- **调试元数据：**工程源文件登记、断点、watches 和 bookmarks 以本地真实 `<codeExpand>`、`<breakpoints>`、`<watches>`、`<bookmarks>` 结构读取；安全校验路径/行号，原子替换 `.xcproj`，不声称在线附加、求值表达式或控制 IDE 调试器。
- **界面素材与主题：**布局/皮肤以真实 `template.config` 中的嵌套 `common`/`template_object` 字段索引；主题以 `xctheme.config` 解析真实编辑器参数和安装内皮肤文件。两者都是原生文件系统能力，无需 MCP。
- **显式资源与归档：**`core/archive.py` 对 ZIP 做有界内存快照，保留原始成员名字并给出统一 ID；拒绝歧义或不安全成员，单成员读取核验 CRC。导出在目标目录暂存、fsync、回读后，以硬链接实现完整文件的无覆盖发布。`core/ui_data.py` 读取磁盘或 ZIP XML，返回位置 ID 和来源哈希，递归展开资源分类，保留未知字段与布局绑定。范围和体积限制详见调用手册；没有自动重打包或运行时求值。
- **真实构建：**炫彩 IDE 的编译器没有已知的独立命令行入口。Harness 将 IDE EXE、DLL 和数据依赖复制至临时目录，将模块与工具目录链接过去，复制 `data/config` 并仅在临时配置中设置目标工程，且令 `data/plug` 为空。它从副本进程 PID 枚举窗口，核验进程映像路径，然后只向该 PID 的窗口发送 F7。构建完成后只对该 IDE 进程发送 `WM_CLOSE`；不会结束其他同名进程或使用强制结束。扫描工程树时忽略 `obj`、虚拟环境、VCS 和工具依赖目录，并核对本轮 PE 时间戳与架构。
- **可信结果：**`ok=true` 表示已检测到唯一且与工程架构相符的新／更新 PE 文件。`compiler.compiled`、`compiler.skipped` 和 `compiler.errorCount` 会保持 `null`；JSON 明确说明 IDE 错误列表不可通过已知的本地接口读取。它不会把仅发送 F7 或旧 EXE 误报成零编译错误。
- **预览：**发布磁盘 `.xcproj`、模块引用、入口文件和 PE 元数据；所有内容来自本机工程文件，不伪装成 GUI 画面或 IDE 实时状态。

## 常见工作流

新增 `reference sources/search/show` 直接查询 `data/config` 中的 10 类原生参考数据：代码片段、语言帮助、控件名称、属性/独立帮助/事件、组合控件、编译选项和两种补全表。实现在 `core/references.py`；预定义源文件限制在所选安装目录内，解析失败返回可定位的错误，单文件上限 4 MiB。结果附来源 SHA-256，保留属性层级、候选值和回调占位符，不修改 IDE 配置。`reference sources` 逐项报告可用性；搜索与准确 ID 读取在请求源损坏时失败。

```powershell
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference search properties buttonType --scope 'elementUI/buttonUI'
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference show events 'elementUI/buttonUI/XE_BNCLICK'
```

第二批 20 轮的证据与待开发方向见 [新增挖掘报告](../../AI_MINING_REPORT_02.md)。可在 harness 目录重跑 `python tools/explore_round2.py --ide 'I:\xcide' --output '../../AI_MINING_EVIDENCE_02.json'`；脚本调用已安装 CLI，并只向指定位置写入证据文件。

第三批 50 轮包含资源、布局、ZIP、编译配置和模块声明交叉检查，详见 [50 轮深度挖掘报告](../../AI_MINING_REPORT_03.md)。重跑命令为 `python -X utf8 -B tools/explore_round3.py --ide 'I:\xcide' --output '../../AI_MINING_EVIDENCE_03.json'`。脚本记录直接读取的 249 个文件前后哈希，并通过安装命令导出一个成员到独立临时新文件；证据内记录产物路径和 SHA-256。新查询不改变旧工程检查和构建命令的语义。

指定 IDE 安装位置后创建和查看工程：

```powershell
cli-anything-xcide --ide 'I:\xcide' --json project new 'E:\work\xc' 'Counter'
cli-anything-xcide --json project info 'E:\work\xc\Counter\Counter.xcproj'
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' status
cli-anything-xcide --json --ide 'I:\xcide' project template list '暗黑UI'
cli-anything-xcide --json --ide 'I:\xcide' project new 'E:\work\xc' 'Dark Counter' --template '用户模板/暗黑UI/project/OP测试' --configuration '发布版' --platform x64
cli-anything-xcide --json --ide 'I:\xcide' example list '按钮'
cli-anything-xcide --json --ide 'I:\xcide' example info '炫彩界面库-示例/xc-Button-按钮/xc-demo.xcproj'
cli-anything-xcide --json --ide 'I:\xcide' example copy 'E:\work\xc' '按钮实验' --id '炫彩界面库-示例/xc-Button-按钮/xc-demo.xcproj'
cli-anything-xcide --json --ide 'I:\xcide' ui-template list --category 皮肤
cli-anything-xcide --json --ide 'I:\xcide' theme list '暗'
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' project config list
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' project config set --configuration 调试版 --platform x64
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' project sources list
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' project debug list
cli-anything-xcide --json --project 'E:\work\xc\Dark Counter\Dark Counter.xcproj' project doctor
cli-anything-xcide --json --project 'E:\work\xc\Dark Counter\Dark Counter.xcproj' interface list
cli-anything-xcide --json --project 'E:\work\xc\Dark Counter\Dark Counter.xcproj' interface check
```

模板目录命令读取安装目录中的标准空白、官方及用户 `.xcproj` 模板。`project new --template` 保留模板项目配置、模块和其他原生文件；只有显式指定的配置/架构会被覆盖。`project doctor` 汇总入口源码、模块、布局和 UI 归档问题；`interface list/check` 也会读取 UI ZIP 里的布局和 `resource.res`。所有新检查都是只读，不会修补或重写现有布局资源。

示例命令直接读取 IDE 安装中的 `data/示例`，使用 `.xcproj` 的准确相对路径作为示例 ID。复制时会保留工程设置、模块、源码、布局及资源，并跳过 Debug/Release/obj 等生成目录、二进制产物和符号链接。目标目录已存在时操作失败；原始示例始终保持不变。

本地读取、编辑和搜索模块：

```powershell
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' editor read 'E:\work\xc\Counter\main.xc'
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' module search XCGUI
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' module dependencies module_xcgui.h
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' module add --file module_xcgui.h --with-dependencies
```

读取 IDE 安装目录中的关键文本文件无需先选择工程：

```powershell
cli-anything-xcide --json --ide 'I:\xcide' editor read 'I:\xcide\data\config\config.config'
```

直接本地文件写入须提供一个含新文本的 UTF-8 文件：

```powershell
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' editor write 'E:\work\xc\Counter\main.xc' '.\main-new.txt'
```

本机 GUI 构建与产物检查：

```powershell
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' build
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' preview capture --recipe executable
```

`preview capture` 会在工程目录中生成检查包，可以直接查看其中的 JSON 清单和文件，不需要单独的预览服务。

构建会复制私有 IDE 到系统临时目录，并在独立后台桌面启动；可能需要数百 MB 空间。原生对话框会返回标题和文字，正常关闭超时后只终止本次 Job，保留主错误和关闭错误。普通模式保持空插件目录；诊断模式添加本轮编译的输出桥接。

## 限制与验证

- 本地工程操作可在没有正在运行 IDE 的情况下使用。
- 真正构建需要 Windows 登录会话、创建桌面权限、炫彩 IDE、MSVC 与匹配 Windows SDK；Windows 服务、锁屏及 RDP 断线场景未测。程序和编译在后台完成，前台鼠标与焦点不作为执行条件。
- 普通 F7 构建只核验新 PE；使用 `--diagnostics` 才获取真实输出和错误数。运行捕获只覆盖本次主进程的调试事件，退出时清理子进程；源码调试/变量求值、其他 DPI、D2D 后台截图仍不在已验证范围。
- 模块名称查找以头文件的 `module_` 文件名和 `//@` 元数据为准；修改 `<modules>` 后通常要让 IDE 重新加载工程。
- 所有文档、命令帮助、示例和 JSON 面向用户的说明均使用中文。
- 无 MCP CLI 功能清单、20 轮本地安装包挖掘以及验证记录见 [AI 挖掘报告](../../AI_MINING_REPORT.md)。
- 若不能预览 Markdown，当前说明和测试报告也有独立的离线 HTML 副本 `XCIDE.html`、`cli_anything/xcide/README.html` 和 `cli_anything/xcide/tests/TEST.html`。

完整测试计划及本轮测试结果记录在 [`tests/TEST.md`](cli_anything/xcide/tests/TEST.md)。

AI 代理的命令调用约定、返回 JSON 处理、无 MCP 工作流、配置切换和命令副作用详见 `cli_anything/xcide/AI_CALLING.md`，同一离线预览为 `cli_anything/xcide/AI_CALLING.html`；该手册 Markdown 也随 Python 包一起发布。
