# XCGUI IDE 本地命令行

`cli-anything-xcide` 是炫彩 IDE 与炫语言工程的本地命令行助手。它能浏览和派生 IDE 示例、使用工程模板创建 `.xcproj`、检查源码和界面资源、扫描本地模块库、维护工程模块引用、调用真实 IDE 构建，并发布本地检查预览。文件操作直接读写本机；实时能力使用本项目的原生桥接，不需要 MCP，也无需在正式 IDE 安装中加入插件。

真实构建使用 Windows 上已安装的炫彩 IDE 编译器。所有构建均在独立后台桌面启动临时 IDE 副本，向已核验的 XCGUI 主窗口发送 F7，并验证本轮新 EXE 及 PE 架构。普通 `build` 的插件目录为空，编译诊断返回 `null`；`build --diagnostics` 自动编译并加载仅供本轮使用的输出桥接，读取真实错误/警告和原始输出。正式 IDE 安装不加载新插件。IDE、编译器和运行测试都不会切换前台桌面或使用前台鼠标输入。

## 环境与安装

- Windows 10/11、Python 3.10 或更新版本。
- 已安装炫彩 IDE。默认搜索 `I:\xcide`；也可用 `--ide` 或 `XC_IDE_ROOT` 指定其他目录。
- 项目创建需要 IDE 的 `data/template`；模块查询需要 `data/XC-Module` 或 `data/XC-Module-dev`。
- 真实编译需要可用 Windows 桌面会话和炫彩 IDE 随附的 MSVC/Windows SDK。构建会临时复制 IDE 程序、DLL 和配置/模块元数据目录到系统临时目录，因此需要数百 MB 临时空间。

在 harness 目录安装：

```powershell
python -m pip install -e '.[test]'
cli-anything-xcide --help
```

面向 AI 代理的完整工作流、JSON 约定和命令示例见 [`AI_CALLING.md`](AI_CALLING.md)；无法预览 Markdown 时可直接打开同目录的离线 [`README.html`](README.html) 与 [`AI_CALLING.html`](AI_CALLING.html)。

若路径不在默认位置，设置 `XC_IDE_ROOT` 或为命令提供 `--ide`。全局参数（例如 `--json`、`--project` 和 `--dry-run`）必须写在子命令之前。

## 常用工作流

使用持久后台 IDE 和旧 `xc_*` 工具名：

```powershell
cli-anything-xcide --json ide tools
cli-anything-xcide --json --ide 'I:\xcide' --project 'E:\work\Demo\Demo.xcproj' ide start --directory 'E:\work\Demo-session'
cli-anything-xcide --json ide --instance 'E:\work\Demo-session' call xc_editor_get
cli-anything-xcide --json ide --instance 'E:\work\Demo-session' stop
```

30 项工具对应关系、参数、部分完成与版本边界见 [IDE_COMPAT.md](IDE_COMPAT.md)。实时会话需要 64 位 Python、AMD64 ABI v3 IDE 和 MSVC；使用独立 Windows 桌面，不能接管现有前台 IDE。

浏览 IDE 自带工程模板，并复制任一模板创建独立工程：

```powershell
cli-anything-xcide --json --ide 'I:\xcide' project template list
cli-anything-xcide --json --ide 'I:\xcide' project template list '暗黑UI'
cli-anything-xcide --json --ide 'I:\xcide' project new 'E:\work\xc' 'Dark Counter' --template '用户模板/暗黑UI/project/OP测试' --configuration '发布版' --platform x64
```

`project new` 省略 `--template` 时仍使用标准空白窗口模板；选用其他模板时保留其原有编译配置、架构、模块、源码和资源。仅指定 `--configuration`、`--platform` 时覆盖模板中已存在的选项。复制只写入一个全新的目标目录。

浏览、检查并派生 IDE 随附的真实示例工程：

```powershell
cli-anything-xcide --json --ide 'I:\xcide' example list '按钮'
cli-anything-xcide --json --ide 'I:\xcide' example info '炫彩界面库-示例/xc-Button-按钮/xc-demo.xcproj'
cli-anything-xcide --json --ide 'I:\xcide' example copy 'E:\work\xc' '按钮实验' --id '炫彩界面库-示例/xc-Button-按钮/xc-demo.xcproj'
cli-anything-xcide --json --project 'E:\work\xc\按钮实验\按钮实验.xcproj' project doctor
```

`example list` 返回准确相对 ID，`example info` 查看源码和资源文件清单；`example copy` 将所选工程复制到新目录，重命名 `.xcproj` 并保留模块、配置和资源。复制过程会跳过 Debug/Release/obj 目录、已生成二进制及符号链接，不会修改 IDE 自带示例或覆盖目标。

检查工程文件：

```powershell
cli-anything-xcide --json --ide 'I:\xcide' project new 'E:\work\xc' 'Counter'
cli-anything-xcide --json project info 'E:\work\xc\Counter\Counter.xcproj'
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' status
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' project doctor
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' interface list
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' interface check
```

`project doctor` 检查 `.xcproj` 登记的源码是否存在、模块引用能否在当前 IDE 模块库中唯一匹配，以及界面文件结构。`interface list/check` 识别磁盘中的 `main.xml`、`布局文件/*.xml` 和 `UI_ZIP.zip` 中的布局，校验炫彩多根布局 XML、ZIP 路径/CRC、resource.res 引用和图片/字体文件。资源歧义和未能确定的引用作为警告返回；命令不会修改布局或资源。

查看或切换 `.xcproj` 中实际存在的编译配置和架构：

```powershell
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' project config list
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' project config set --configuration 调试版 --platform x64
```

切换只更新工程活动配置字段，不启动 IDE 或自动编译。只提供其中一个选项时保留另一个当前值。

读取、编辑工程源码和查找本地已安装模块：

```powershell
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' editor read 'E:\work\xc\Counter\main.xc'
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' module search XCGUI
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' module dependencies module_xcgui.h
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' module add --file module_xcgui.h --with-dependencies
```

直接读取 IDE 安装目录中的关键文本文件时，不必先选择工程：

```powershell
cli-anything-xcide --json --ide 'I:\xcide' editor read 'I:\xcide\data\config\config.config'
```

`editor write` 需要已有文本文件作为输入。目标文件必须位于所选工程或所选 IDE 安装目录中；`--allow-outside-project` 可明确开放其他本机路径。对于已有文件，CLI 尽量保留 UTF-8／UTF-16／GB18030 编码、BOM 和 CRLF 格式；新建的炫语言源码使用 UTF-8 BOM 和 CRLF。写入后会从磁盘回读并核对字节。

登记额外源码、维护 `.xcproj` 中的断点/监视/书签，并浏览安装资源：

```powershell
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' project sources list
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' project sources add 'src/helper.xc'
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' project breakpoints add 'src/helper.xc' 12
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' project debug watch-add 'count'
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' project debug bookmark-add 'src/helper.xc' 12
cli-anything-xcide --json --ide 'I:\xcide' ui-template list '关闭按钮'
cli-anything-xcide --json --ide 'I:\xcide' theme list '黑色'
```

源码登记仅更新 `<codeExpand>`；取消登记会保留源码。断点/书签只保存于 `.xcproj` 元数据；变量监视也只登记表达式，不运行程序或求值。布局/皮肤素材可复制到新的输出目录；主题命令只读 `data/theme/*/xctheme.config`。

查询 IDE 自带代码片段、原生属性和事件声明：

```powershell
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference sources
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference search snippets '如果'
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference search properties buttonType --scope 'elementUI/buttonUI'
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference show events 'elementUI/buttonUI/XE_BNCLICK'
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference search functions XBtn_
```

`reference` 提供 10 类安装参考数据：`snippets`、`language`、`controls`、`properties`、`property-help`、`events`、`custom-objects`、`build-options`、`functions`、`completion-tokens`。使用 `search` 返回的准确 `id` 调用 `show`；通过 `--offset` 和 `--limit` 分页。每次返回来源路径及 SHA-256，控件属性和事件保留原始层级。`--scope` 只匹配该层，不自动合并父子层；声明占位符、编译器选项和补全行保持原生内容。补全表不能证明 API 当前可用，编译选项默认值也不等于项目的实际设置。查询不改安装文件；加全局 `--dry-run` 还会禁止保存 CLI 会话。

编译并检查新 EXE：

```powershell
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' build
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' preview capture --recipe executable
```

`preview capture` 会在工程目录中生成检查包，可以直接查看其中的 JSON 清单和文件，不需要单独的预览服务。

普通 `build.ok=true` 表示当前配置指定的 EXE 在本轮更新、超时前保持稳定，且 PE 架构正确；诊断字段为 `null`。带 `--diagnostics` 时，成功还要求原生编译完成、真实错误数为零且没有失败/跳过标记。`diagnostics` 返回错误位置和消息，`compiler_output` 保留原文。JSON 的 `expected_executable` 给出目标路径；未设置输出名称/目录时使用工程文件名及原生 Debug/Release 目录。DLL 工程或无法解析的输出变量会在启动 IDE 前被拒绝。`preview capture/latest` 仍仅发布工程/EXE 文件检查，不调用运行截图。

运行输出和后台界面验收：

```powershell
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' build --diagnostics
cli-anything-xcide --json runtime run --exe 'E:\work\xc\Tool\Debug64\Tool.exe' --arg=--self-test --output 'E:\work\xc\runs'
cli-anything-xcide --json runtime test 'E:\work\xc\Counter\scenario.json' --exe 'E:\work\xc\Counter\Debug64\Counter.exe' --output 'E:\work\xc\runs'
```

`runtime run` 捕获 OutputDebugString、stdout/stderr、异常与退出码。`runtime test` 要求程序接入随包提供的 `native/automation_bridge.h`，通过 XCGUI UI 线程分派后台消息并验证业务状态，不直接调用业务函数。GDI 截图读取完整绘制缓冲，D2D 截图不支持且会失败。示例源码、接入步骤、JSON 场景和可直接交给 Agent 的任务文本见 [AI_CALLING.md](AI_CALLING.md)。运行需要 Windows 64 位 Python，截图需要 `pip install cli-anything-xcide[automation]`；桥接编译需要 MSVC C++ 桌面工具及 Windows SDK。

直接查询 UI ZIP、命名资源表和布局节点：

```powershell
$zip = 'I:\xcide\data\template\项目模板\炫语言\用户模板\暗黑UI\project\UI_ZIP.zip'
cli-anything-xcide --json --dry-run --ide 'I:\xcide' archive list $zip
cli-anything-xcide --json --dry-run --ide 'I:\xcide' archive read $zip 'main.xml'
cli-anything-xcide --json --dry-run --ide 'I:\xcide' resource list $zip --member 'WmUi/Dark/WmUi.res' --kind type_bkInfo
cli-anything-xcide --json --dry-run --ide 'I:\xcide' interface nodes $zip --member 'main.xml' --tag buttonUI
```

`resource` 递归读取原生 `folder` 分类，返回资源位置 ID、分类元数据、原生属性和相对资产存在性；重复分类名不算作资源重名。`interface nodes/node` 返回父子层级、属性、绑定和子树 XML，支持 `xc_template_object`。从列表取准确 ID 后调用 `resource show` 或 `interface node`，并核对来源 SHA-256。分页使用 `next_offset`；`--limit` 默认 100，上限 2000。

`archive export FILE MEMBER OUTPUT` 将单个成员原样导出到显式新文件；先加全局 `--dry-run` 核验，再执行。父目录必须存在且支持硬链接；拒绝覆盖及安装目录目标。ZIP 目录查询不验证 CRC，读取和导出会校验选中成员。路径歧义、加密或超限成员会失败；资源资产的 `present` 仅是存在性，不能证明运行时可用。限制和 JSON 调用链详见 [AI_CALLING.md](AI_CALLING.md)。

## XC 开发资料

编写炫语言/XCGUI 代码时，Agent 从单个 `cli-anything-xcide` 合并技能中按需读取开发资料，无需另行启用 `xc-suite`。Git 仓库在 `skills/cli-anything-xcide/references/xc-suite/` 中保留完整手册和模块检索脚本；打包后的 skill 目录将其放在 `references/xc-suite/`。目标机器的模块声明索引从本地 IDE 模块树重建，不随包发布。

## 命令参考

| 命令 | 功能与数据来源 |
| --- | --- |
| `project new DIR NAME` | 从官方空白窗口模板创建独立 `.xcproj` 工程，设置名称、编译配置、目标架构和 `main.xc` 入口。 |
| `project info FILE` | 读取工程名称、编译配置、架构、SDK、工具集、模块引用和入口源码。 |
| `project list DIR [--recursive]` | 在本地目录中发现 `.xcproj`，跳过构建和工具目录。 |
| `project config list [--project FILE]` | 列出实际定义的配置、架构和活动设置。 |
| `project config set [--configuration NAME] [--platform x86\|x64]` | 原子切换工程活动配置与架构。 |
| `project sources list/add/remove [PATH]` | 查看 `.xc/.xcs` 文件及登记状态，或更新 `<codeExpand>`；添加需文件已经存在，移除不会删除文件。 |
| `project breakpoints list/add/remove [PATH LINE]` | 核验真实源码行并更新工程断点 XML。 |
| `project debug list/watch-add/watch-remove/bookmark-add/bookmark-remove` | 查看或维护本机工程的监视表达式与书签元数据。 |
| `project template list [QUERY]` | 搜索炫彩 IDE 中已安装的炫语言官方/用户工程模板并返回可复用 ID。 |
| `theme list [QUERY]`、`theme info ID` | 读取已安装的代码主题字体、行距、设计器背景、配色及可定位的皮肤文件。 |
| `reference sources` | 检查 10 类安装参考源的可用性、条目数和哈希；某源损坏会单独标记 `available=false`。 |
| `reference search KIND [QUERY] [--scope PATH] [--offset N] [--limit N]` | 搜索代码片段、语言、控件、属性/帮助/事件、组合控件、编译选项及补全表。 |
| `reference show KIND ID` | 用准确 ID 返回原生内容及来源；不写文件、不求值、不生成事件注册代码。 |
| `ui-template list [QUERY]`、`info ID`、`copy DIR NAME --id ID` | 检查或复制安装的布局模板和皮肤素材。 |
| `project new DIR NAME [--template ID] [--configuration NAME] [--platform x86\|x64]` | 根据空白模板或准确的本机模板 ID 创建独立工程。 |
| `example list [QUERY]` | 搜索本机 IDE 安装包中的示例 `.xcproj`，返回准确相对 ID。 |
| `example info ID` | 检查示例工程元数据，并列出可复用的源码和资源文件。 |
| `example copy DIR NAME --id ID` | 派生示例为新工程，跳过编译产物并更新工程名称。 |
| `project doctor [--project FILE]` | 检查工程源码登记、模块引用、布局 XML、资源及 `UI_ZIP.zip`。 |
| `project open FILE` | 选择 CLI 会话所用工程；不会控制 IDE GUI 窗口。 |
| `status` | 显示本地工程、IDE 安装路径和 CLI 会话信息。 |
| `editor read FILE` | 从磁盘读取文本、编码、BOM、CRLF 和 SHA-256。 |
| `editor write FILE INPUT [--no-bom] [--allow-outside-project]` | 原子写入本地文本并核对写后文件内容。 |
| `module list [--limit N] [--project-only]` | 扫描模块库或列出当前工程已有模块引用。 |
| `module search QUERY [--depends-on NAME]` | 按名称、文件、作者和备注搜索，或反查依赖模块。 |
| `module dependencies FILE` | 按依赖顺序解析一个已安装模块的递归模块依赖，报告同名歧义、缺失依赖和循环。 |
| `module add --file FILE [--with-dependencies] [--project FILE]` | 验证无歧义的依赖闭包并依赖优先地写入工程模块列表；不传开关时只添加指定模块。 |
| `module remove --file FILE [--project FILE]` | 从工程 `<modules>` 区块移除指定模块引用。 |
| `interface list/check [--project FILE]` | 列出布局并核验炫彩布局多根 XML、资源清单和 ZIP 布局包。 |
| `interface nodes FILE [QUERY]`、`interface node FILE ID` | 读取显式布局文件或 `--member` 指定的 ZIP 布局；按标签、属性和值过滤节点，返回父子层级和子树。 |
| `resource list FILE [QUERY]`、`resource show FILE ID` | 读取显式资源表或 ZIP 中的命名资源表；保留分类、原始字段和资产状态，支持 `--kind`。 |
| `archive list FILE [QUERY]`、`archive read FILE MEMBER` | 列出 ZIP 原始名字、规范化 ID 和路径问题，或读取选中文本并校验 CRC。 |
| `archive export FILE MEMBER OUTPUT` | 回读核验后将成员原始字节发布到新文件，不覆盖现有文件。 |
| `build [--project FILE] [--timeout SEC] [--diagnostics]` | 后台启动私有 IDE、定向 F7 并核验新 PE；可选真实编译输出桥接。 |
| `runtime run --exe FILE --output DIR` | 后台运行本次程序并捕获输出、异常和退出码。 |
| `runtime test SCENARIO --exe FILE --output DIR` | 后台 XCGUI 消息、状态断言和 GDI 绘制截图；需测试适配器。 |
| `preview recipes/capture/latest` | 读取本地工程或可执行文件状态，并发布／读取 `preview-bundle/v1`。 |
| `session status/history/undo/redo` | 查看、撤销和重做 CLI 的工程选择记录。 |

## CLI 能做什么与不能做什么

无需插件时可用的功能包括工程创建和检查、工程文件查找、示例浏览和派生、源码读写与登记、断点/监视/书签的工程元数据维护、布局模板/皮肤复制、主题检查、本地模块扫描和工程模块声明管理、真实 IDE GUI 构建、PE 架构检查、JSON 输出和文件预览。

CLI 不会报告用户已有 IDE 的活动选项卡或尚未保存的源码。`build --diagnostics` 只读取本次私有 IDE 输出，当前支持 AMD64 IDE v3 ABI。`runtime` 只调试本次创建的进程；不提供源码单步、调用栈或变量求值。后台测试覆盖消息分派，不覆盖硬件鼠标、Raw Input、IME 或任意第三方控件。超时回收限定于本次创建的 Job，原生 IDE 对话框记录在 `ide_dialogs`，关闭错误另行保留。

## REPL、会话与自动化

不带子命令运行 `cli-anything-xcide` 会进入中文交互终端。会话 JSON 默认位于当前用户的应用数据目录，也可通过 `--session-file` 指定。会话采用文件锁、原子替换和修订号检查；`undo/redo` 仅切换 CLI 所选工程。

AI 自动化调用手册随 Harness 提供；pip 包用户可通过 `importlib.resources.files("cli_anything.xcide").joinpath("AI_CALLING.md")` 读取打包文档。

所有命令支持全局 `--json`。自动化脚本应检查退出码，读取 stdout 中的成功 JSON 或 stderr 中的错误 JSON，并使用绝对工程路径。`--dry-run` 只打印计划，不写入文件、调用 GUI 或保存会话。

文件操作完成后，若会话修订号冲突或保存失败，操作结果保留，JSON 另外返回 `session_saved=false` 和 `session_warning`（`operation_completed=true`、`retry_operation=false`）；不要重试已经完成的文件操作。会话选择、撤销和重做本身保存失败时仍返回失败。工程配置、源码登记、模块和调试元数据更新使用同一工程文件锁，提交前会检查磁盘内容是否被外部程序改动；IDE 不遵守 CLI 文件锁，自动化期间仍应避免在 IDE 中同时保存同一工程。

## 验证

测试计划和实测结果见 [`tests/TEST.md`](tests/TEST.md)。覆盖普通无插件构建的兼容性、带输出桥接的成功/错误源码编译、x86/x64 调试事件、后台中文输入/按钮/按键、原生绘制截图、错误断言及进程回收。真实验收使用临时工程与后台 IDE，检查正式配置哈希不变。
