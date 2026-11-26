# 炫彩 IDE CLI：AI 自动化调用手册

本手册供 Codex、其他 AI 代理和脚本调用 `cli-anything-xcide`。CLI 读取和更新 Windows 本地文件，实时能力通过本项目原生桥接执行，不使用 MCP。`build --diagnostics` 和 `ide start` 自动在各自隔离 IDE 副本中编译并加载所需桥接，无需向正式 IDE 安装插件。

独立 Git 仓库同时提供 `skills/cli-anything-xcide`（调用规则）和 `skills/xc-suite`（炫语言、模块及 UI 开发资料）。写业务程序时建议一并读取；XC 模块索引按当前安装重建。wheel 包含 CLI 技能及原生桥接，XC 开发资料随仓库单独提供。XC-MCP-Next 与 `mcp-cli` 为可选外部工具，当前编译、读错误及后台测试不依赖它们；迁移方法见仓库根目录 `DEPENDENCIES.md`。

文档的离线预览版是 [AI_CALLING.html](AI_CALLING.html)。前两批各 20 轮安装包功能挖掘见工作区根目录的 `AI_MINING_REPORT.md`、`AI_MINING_REPORT_02.md`；第三批 50 轮见 `AI_MINING_REPORT_03.md`。均有同名 HTML 阅读版，不依赖网络或脚本。

## 安装和调用原则

在 harness 目录安装：

```powershell
python -m pip install -e '.[test]'
cli-anything-xcide --help
```

IDE 默认位置为 `I:\xcide`。其他位置通过 `--ide PATH` 或 `XC_IDE_ROOT` 指定。所有全局选项都必须放在命令之前：

```powershell
cli-anything-xcide --json --ide 'I:\xcide' example list '按钮'
cli-anything-xcide --json --project 'E:\work\Demo\Demo.xcproj' project config list
```

自动化调用建议：

1. 每次子进程调用都带 `--json`，并检查进程退出码。成功 JSON 写入 stdout；CLI 处理的错误 JSON 写入 stderr 并返回非零码。操作系统或 Python 启动错误也可能产生 traceback，应同时保留 stderr。
2. 路径使用绝对路径并加引号。不要假定相对路径基于仓库、脚本或 IDE 安装目录。
3. 新建、复制和配置修改前，先运行对应的 `info`、`list` 或 `doctor` 检查对象。支持 `--dry-run` 的修改命令可先确认操作计划。
4. 解析 JSON 字段前检查 `ok`；报告数量时读取结果里的实际字段。需要编译诊断时使用 `build --diagnostics`；普通 `build` 的 `compiler.errorCount` 仍为 `null`，代表未知。
5. 一条命令调用一次子进程。可以按 JSON 中返回的 `project_file`、示例 `id` 或模块 `file` 拼接下一条命令。

`--help` 即使带 `--json` 仍是纯文本。Windows 下若以 UTF-8 捕获中文帮助，给子进程环境设置 `PYTHONUTF8=1`（PowerShell：`$env:PYTHONUTF8='1'`）；父 Python 的 `-X utf8` 不会自动传给独立 CLI 进程。正常 `--json` 结果使用 ASCII 转义，不依赖中文控制台编码。

若文件操作已经完成，但会话保存失败，JSON 会保留操作结果并包含 `session_saved=false`、`session_warning.operation_completed=true` 和 `session_warning.retry_operation=false`。此时不要重试文件操作；重新读取会话，并在后续命令中显式传入 `--project`。会话专用操作的保存失败仍返回非零码。同一工程的结构化 XML 更新由 CLI 文件锁串行化，提交前检测外部修改；IDE 不遵守该锁，应避免同时保存同一工程。

Windows Python 子进程示例：

```python
import json
import subprocess

result = subprocess.run(
    ["cli-anything-xcide", "--json", "--ide", r"I:\xcide",
     "example", "list", "按钮"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    check=False,
)
if result.returncode:
    raise RuntimeError(result.stderr)
data = json.loads(result.stdout)
if not data["ok"]:
    raise RuntimeError(data)
example_ids = [item["id"] for item in data["examples"] if item["valid"]]
```

## 自动化工作流

### 持久 IDE 与旧 MCP 工具名

已将所参考 XC-MCP-Next 版本注册的 30 个工具名接到 `ide call`。`ide tools` 输出 schema 和行为备注；完整逐项说明见 [原生 IDE 与 MCP 迁移](IDE_COMPAT.md)。启动会话需要 64 位 Python、AMD64 ABI v3 IDE、MSVC 与 Windows SDK。

```powershell
cli-anything-xcide --json ide tools
cli-anything-xcide --json --ide 'I:\xcide' --project 'E:\work\Demo\Demo.xcproj' ide start --directory 'E:\work\Demo-session'
cli-anything-xcide --json ide --instance 'E:\work\Demo-session' call xc_get_project
cli-anything-xcide --json ide --instance 'E:\work\Demo-session' call xc_get_output
cli-anything-xcide --json ide --instance 'E:\work\Demo-session' call xc_get_dialogs
cli-anything-xcide --json ide --instance 'E:\work\Demo-session' stop
```

会话目录须全新；省略时从返回 JSON 的 `directory` 获取。默认空闲 1800 秒自动关闭。使用 `--args-file` 传 UTF-8 JSON 参数，`--dry-run` 只返回计划。只控制本 CLI 创建的后台 IDE，不接管用户的前台实例。

Agent 必须区分：`xc_editor_get` 读实际缓冲，`xc_read_file` 读磁盘；`xc_editor_set` 写磁盘并返回 `reload_required`。`xc_build`/`xc_menu_cmd` 和 `xc_save_all` 保留旧工具的投递语义，不能据此宣布编译成功或全部保存。完整验收继续使用 `build --diagnostics` 与 `runtime test`。

`ide call` 业务失败可在 stdout 返回 `ok=false` 并以 1 退出；参数与传输错误在 stderr，两者均应保留。超时后已开始操作可能继续完成；已创建文件会有 `created=true` 等部分结果，先回读核实，禁止整批盲重试。`xc_server` 管理本地会话，不启动 MCP endpoint。

### 先查原生定义，再生成代码或布局

`reference` 不需要工程；读取所选 IDE 安装目录的已保存文件。先用 `sources` 检查可用目录，再搜索和读取准确条目：

```powershell
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference sources
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference search snippets '如果'
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference show language '整型'
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference search controls '按钮'
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference search properties buttonType --scope 'elementUI/buttonUI'
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference show property-help itemID
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference show events 'elementUI/buttonUI/XE_BNCLICK'
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference search custom-objects '搜索编辑框'
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference show build-options runtimeLibrary
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference search functions XBtn_
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference search completion-tokens XC_WINDOW
```

| KIND | 主要返回字段 | 使用边界 |
| --- | --- | --- |
| `snippets` | `name`、`comment`、`code` | `code` 保留换行、制表符与“占位”等原生内容。需要调用方填入实际语句。 |
| `language` | `name`、`text` | 本机炫语言类型、关键字和指令帮助。 |
| `controls` | `tag`、`name` | 原生控件标签及中文名称。 |
| `properties` | `scope`、`attribute`、`choices`、`help`、`editor_type`、`flags` | `choices` 是 `[值, 显示名]`；`flags` 是 IDE 属性编辑器标识，不是属性默认值。 |
| `property-help` | `name`、`text` | 独立帮助条目，例如未列在属性行中的 `itemID`。 |
| `events` | `scope`、`class_name`、`declaration`、`remark` | 保留 `$[UI对象名称]` 模板变量，未替换对象名或生成事件注册代码。 |
| `custom-objects` | `tag`、`attributes`、`node_count`、`xml` | 序列化的组合控件片段，非完整窗口文件；复制前处理资源引用和 ID/name 冲突。 |
| `build-options` | `definition.xml_label/uiType/flag/list/default/default_debug`（可选字段按源文件） | 安装 UI 选项映射，不能据此断言项目启用了某选项。 |
| `functions` | `text`、`line_number` | 函数自动补全原始行，API 可用性仍需模块/头文件和构建验证。 |
| `completion-tokens` | `text`、`line_number` | 混有常量名称和代码词条；无数值，也不保证全是常量。 |

`search` 返回 `items`、`count`、匹配总量 `total`、`offset`、`truncated` 和 `next_offset`。`limit` 为 1–2000，默认 50；`next_offset=null` 表示本次查询没有下一页。翻页时保持 KIND、QUERY、scope 一致，并比较 `source.sha256`；源文件变化应重新搜索。返回顺序保持原生文件顺序。未匹配到条目是成功的空列表；无效 scope、损坏源或不存在的准确 ID 返回非零退出码及错误 JSON。

`sources.ok=true` 代表目录检查完成；必须逐项检查 `sources[].available`。缺少某参考文件不会阻塞其他目录的查询。查询限制为预定义的安装文件，每文件最大 4 MiB，拒绝越过安装目录的链接以及含 DTD/实体声明的 XML。

`properties` 和 `events` 的 `scopes` 列出原生层级路径。`--scope elementUI/buttonUI` 只返回按钮节点直接定义的条目；需要基础元素信息时另查 `--scope elementUI`。空作用域可能表示未直接声明条目，不表示控件没有能力。保留原始大小写和名字，不把这套目录结构当作已验证的运行时继承规则。

`show` 的 ID 必须来自 `search.items[].id`，它是逻辑标识，不是文件路径。片段、组合控件及补全条目的数字 ID 与源文件顺序有关，不能跨安装版本硬编码。结构化 JSON/XML 条目附带 `pointer`，补全条目附带原始 `line_number`；所有结果附带 `source.path/relative_path/size/sha256`。

下面的脚本只读取片段；后续可以把 `code` 写入 UTF-8 临时输入文件，再调用已有 `editor write` 写入选定工程。裸片段可能包含占位符，不能直接作为完整工程的编译验收依据。

```python
import json
import subprocess

base = ["cli-anything-xcide", "--json", "--dry-run", "--ide", r"I:\xcide"]
result = subprocess.run(base + ["reference", "search", "snippets", "如果"],
                        capture_output=True, text=True, encoding="utf-8", check=True)
page = json.loads(result.stdout)
snippet = next(item for item in page["items"] if item["name"] == "如果")
result = subprocess.run(base + ["reference", "show", "snippets", snippet["id"]],
                        capture_output=True, text=True, encoding="utf-8", check=True)
selected = json.loads(result.stdout)
if selected["source"]["sha256"] != page["source"]["sha256"]:
    raise RuntimeError("参考源已变化，请重新搜索")
code = selected["item"]["code"]
```

查询不会改写参考源；未传 `--dry-run` 时，显式 `--ide` 仍可能保存 CLI 会话中的安装选择。上面的只读示例通过 `--dry-run` 禁止会话保存。

### 找到并派生 IDE 示例

先按功能关键字查询，再用返回的准确 `.xcproj` 相对 ID 查看资源，最后复制到一个新目录：

```powershell
cli-anything-xcide --json --ide 'I:\xcide' example list '按钮'
cli-anything-xcide --json --ide 'I:\xcide' example info '炫彩界面库-示例/xc-Button-按钮/xc-demo.xcproj'
cli-anything-xcide --json --ide 'I:\xcide' example copy 'E:\work\炫彩' 'ButtonStudy' --id '炫彩界面库-示例/xc-Button-按钮/xc-demo.xcproj'
```

`example list` 的 `examples[].id` 可直接传给 `info` 和 `copy --id`。派生会更新项目 XML 名称和文件名，保留原工程配置、模块、源码与资源，跳过 Debug/Release/obj、可执行文件和符号链接。它拒绝覆盖目标目录，也拒绝在原始示例目录内生成副本。

### 新建工程并切换配置

可以从空白窗口工程或本机安装的其他工程模板创建项目：

```powershell
cli-anything-xcide --json --ide 'I:\xcide' project new 'E:\work\炫彩' 'Counter'
cli-anything-xcide --json --project 'E:\work\炫彩\Counter\Counter.xcproj' project config list
cli-anything-xcide --json --project 'E:\work\炫彩\Counter\Counter.xcproj' project config set --configuration 调试版 --platform x64
```

在调用 `config set` 前查看 `project config list` 的 `configurations`。只传 `--configuration` 或 `--platform` 时，另一个值保持当前值。无效配置或缺少的架构会报错且不改文件。`config set` 只更改 `.xcproj` 中活动设置，不启动 IDE、不编译。

自选模板时先列出准确 ID：

```powershell
cli-anything-xcide --json --ide 'I:\xcide' project template list '暗黑UI'
cli-anything-xcide --json --ide 'I:\xcide' project new 'E:\work\炫彩' 'Dark Counter' --template '用户模板/暗黑UI/project/OP测试'
```

### 读取工程源码、维护断点与书签

以下命令直接读取或写入本地 `.xcproj` 元数据，不需要已打开的 IDE GUI：

```powershell
cli-anything-xcide --json --project 'E:\work\炫彩\Counter\Counter.xcproj' project sources list
cli-anything-xcide --json --project 'E:\work\炫彩\Counter\Counter.xcproj' project sources add 'src/helper.xc'
cli-anything-xcide --json --project 'E:\work\炫彩\Counter\Counter.xcproj' project breakpoints add 'src/helper.xc' 12
cli-anything-xcide --json --project 'E:\work\炫彩\Counter\Counter.xcproj' project debug watch-add 'count'
cli-anything-xcide --json --project 'E:\work\炫彩\Counter\Counter.xcproj' project debug bookmark-add 'src/helper.xc' 12
cli-anything-xcide --json --project 'E:\work\炫彩\Counter\Counter.xcproj' project debug list
```

`project sources list` 显示磁盘 `.xc/.xcs` 和 `<codeExpand>` 登记状态；`add` 要求文件已存在且在工程目录内，`remove` 只取消项目树登记，绝不删除源码。断点和书签使用工程内实际存在的源码路径及行号，并拒绝越界；删除书签/断点不写入源码。`watch-add` 仅把单行表达式放入 `.xcproj` 的 `<watches>` 作为 IDE 工程设置，不执行工程、不附加调试器，也不会求值。

### 检索并复制 IDE 界面素材

```powershell
cli-anything-xcide --json --ide 'I:\xcide' ui-template list --category 皮肤
cli-anything-xcide --json --ide 'I:\xcide' ui-template list '关闭按钮'
cli-anything-xcide --json --ide 'I:\xcide' ui-template info '皮肤/template-关闭按钮'
cli-anything-xcide --json --ide 'I:\xcide' ui-template copy 'E:\work\炫彩' '关闭按钮素材' --id '皮肤/template-关闭按钮'
cli-anything-xcide --json --ide 'I:\xcide' theme list '黑色'
cli-anything-xcide --json --ide 'I:\xcide' theme info '黑色默认主题(暗+蓝+黄)/xctheme'
```

先从 `list` 取出准确相对 ID，再交给 `info` 或 `copy`。UI 素材复制会拒绝覆盖已存在目标并跳过 Debug/obj 等生成目录和符号链接；`theme` 只读取真实 `xctheme.config`，不切换正式 IDE 当前主题或写全局设置。

### 检查工程并构建

```powershell
cli-anything-xcide --json project info 'E:\work\炫彩\Counter\Counter.xcproj'
cli-anything-xcide --json --ide 'I:\xcide' --project 'E:\work\炫彩\Counter\Counter.xcproj' project doctor
cli-anything-xcide --json --project 'E:\work\炫彩\Counter\Counter.xcproj' interface check
cli-anything-xcide --json --project 'E:\work\炫彩\Counter\Counter.xcproj' build
```

`project doctor` 会检查登记源码、模块库引用和界面文件；存在错误时以非零码结束，诊断位于 stdout 的 JSON。警告不会被升级成错误。普通 `build.ok=true` 表示本轮目标 PE 更新、稳定且架构正确；需要真实诊断请使用下面的 `--diagnostics` 工作流。

### 让 Agent 编写、修复并验收一个炫语言程序

给 Agent 的任务可以这样写：

> 在指定的新目录创建炫语言 x64 调试版计数器，使用本机模块和原生 API。先查询模板、模块依赖及相关事件签名，再写源码。接入随包提供的 automation_bridge.h，在窗口 UI 线程安装测试入口，采用 GDI 渲染以支持后台截图。用 `build --diagnostics` 后台编译，按 `diagnostics` 的文件/行号修复；每次修改都重新构建。为编辑框输入和按钮点击编写 JSON 场景，用 `runtime test` 在独立后台桌面执行；核对业务日志、截图及正常退出。整个流程不得切换前台、移动鼠标或回退到前台输入。交付源码、构建 JSON、测试 report.json 和截图。失败时保留真实错误，不用旧 EXE 代替。

仓库和 wheel 都带有已验收的计数器源码与场景，可作为最小起点。Windows 64 位 Python、交互桌面及本机炫彩 IDE 是前提；输出桥接还需要 Visual Studio 的 C++ 桌面工具和 Windows SDK，截图需要 Pillow：

```powershell
python -m pip install -e '.[automation]'
$sample = python -c 'from importlib.resources import files; print(files("cli_anything.xcide").joinpath("examples"))'
$adapter = python -c 'from importlib.resources import files; print(files("cli_anything.xcide").joinpath("native/automation_bridge.h"))'
$new = cli-anything-xcide --json --ide 'I:\xcide' project new 'E:\work\xc' 'Counter' --configuration '调试版' --platform x64 | ConvertFrom-Json
$project = $new.project_file
cli-anything-xcide --json --ide 'I:\xcide' --project $project module add --file module_xcgui_class.h --with-dependencies
cli-anything-xcide --json --project $project editor write (Join-Path $new.directory 'main.xc') (Join-Path $sample 'automation_counter.xc')
Copy-Item -LiteralPath $adapter -Destination (Join-Path $new.directory 'automation_bridge.h')
cli-anything-xcide --json --ide 'I:\xcide' --project $project build --diagnostics --timeout 120
```

获取最后一条命令的 stdout JSON 后，只在退出码为 0、`ok=true`、`compiler.compiled=true`、`compiler.errorCount=0` 时使用其 `exe.path`。`build_result=compiled` 同时要求本轮预期 EXE 的时间、稳定性及架构核验通过。原生解析/检查错误包括 `file/line/column/end_column/message`；C++/链接诊断还有 `code`。`compiler_output` 保留输出窗格原文。C++ 失败时 IDE 汇总可能仍写“错误(0)”，CLI 会结合失败标记和原生诊断拒绝通过。缺少完成/零错误证据、桥接不可用或输出超限时不会降级成成功。

桥接仅支持当前已实测的 AMD64 IDE v3 插件 ABI，通过 UI 线程定时读取输出控件；首次构建前等待工程解析完成，不清空输出、不加载正式安装的插件、不开网络端口。构建会生成/更新工程产物，IDE 也可能规范化目标 `.xcproj` 元数据；请操作自己的工程副本。普通 `build` 保留原有空插件目录行为。

所有 `build`（含不带 diagnostics 的旧用法）在独立 Windows 桌面中启动隔离 IDE，编译器子进程继承该后台桌面。CLI 不切换桌面、不抢焦点、不移动光标，F7 只发给已核验 PID 的唯一 XCGUI 主窗口；输入法辅助窗口不会被当成 IDE 主窗口。`automation.desktop/foreground_input/observations` 记录执行方式及前后观测。用户同时移动鼠标或切换窗口会反映到观测中，观测差异本身不归因于 CLI。

`ide_dialogs` 保留发现的原生模态框标题/文字，`cleanup_error` 保留关闭错误；不会自动按确认按钮。关闭超时会回收本次 Job 中的私有 IDE 及其子进程，标记 `terminated=true/ok=false`，保留诊断而不让关闭异常覆盖主错误。工具不会结束用户已打开的 IDE。

### 捕获程序调试输出与异常

```powershell
cli-anything-xcide --json runtime run --exe 'E:\work\xc\Tool\Debug64\Tool.exe' --arg=--self-test --output 'E:\work\xc\runs' --timeout 30
```

`runtime run` 在独立后台桌面启动给定 EXE，不要求测试适配器，默认工作目录为 EXE 所在目录，可用 `--cwd` 覆盖。重复 `--arg` 传递独立参数，带选项前缀的值可写 `--arg=--self-test`。命令等待退出，`--expected-exit-code` 默认 0。仅调试本次创建的主进程，不附加到已有进程，也不占用 IDE 的调试会话。x86/x64 程序可由 64 位 Python 运行。

结果包含 `pid/exe.sha256/debug_output/debug_events/exceptions/exit_code/terminated`。调试字符串区分 Unicode/ANSI，按 Windows 事件的字节长度解码；stdout、stderr 是独立的原始二进制文件，不能混为调试输出。已被程序处理的首轮异常记录为 `first_chance=true`，通常不导致测试失败；未处理异常和非预期退出码导致 `ok=false`。不提供源级单步、断点求值、调用栈或变量监视。调试版的“调试输出”通常使用 OutputDebugString；发布版可能删除该调用，无输出不等于运行失败。

每次在 `--output` 下创建唯一 `run-*` 目录，保存 `report.json`、`stdout.bin`、`stderr.bin` 及场景截图。程序自有文件仍按指定 `--cwd` 写入。超时或场景失败会终止本次创建的进程树并写明 `terminated=true`；其他进程不受影响。主进程正常退出后也清理其残留子进程；子进程的调试事件不在当前捕获范围。CLI 不是代码沙箱，只运行你准备测试的程序。

运行结束后的清理单独使用约 10 秒的共同预算处理调试退出事件并等待进程句柄结束；正常结束会立即返回。调用方应在 `--timeout` 之外留出清理和写报告时间。`cleanup_error` 非空仍表示失败，可能包含多个清理原因，不会因收到退出事件而省略句柄结束核验。

### 后台按钮点击、输入及运行断言

`runtime test` 要求被测程序显式接入随包的 `native/automation_bridge.h`，不向任意 EXE 注入 DLL。示例源码已包含接入：在嵌入 C++ 中包含头文件，窗口创建后、消息循环前调用 `xc_cli_test::install(主窗口.m_hWindow)`。默认 `Debug64/obj/cache` 编译缓存使用示例中的 `../../../automation_bridge.h`；更改原生输出/缓存目录时应按实际缓存目录调整 include 或使用准确绝对路径。

适配器仅在运行环境含本次 token、目录且桌面名匹配时安装；普通启动没有测试入口，不开启网络端口。一次安装一个窗口。CLI 通过带 token 的 `WM_COPYDATA` 请求，让窗口自己的 UI 线程调用 `XC_SendMessage` 分派鼠标/字符/键盘消息，经过 XCGUI 的控件命中和事件处理；不直接调用业务回调。它验证原生消息路径，不能替代硬件鼠标、Raw Input、全局热键或 IME 候选交互的覆盖。

将构建 JSON 的 `exe.path` 传给测试命令：

```powershell
cli-anything-xcide --json runtime test (Join-Path $sample 'automation_counter.json') --exe 'E:\work\xc\Counter\Debug64\Counter.exe' --output 'E:\work\xc\runs' --timeout 30
```

JSON 场景使用 `version:1`、`steps` 数组和可选 `expected_exit_code:0`。每步可有 `timeout`（默认 5 秒，最多 120 秒）；总超时优先。最多 200 步，必须至少有一个状态断言，并以 `close` 或 `wait_exit` 结束。未知字段、无效坐标、越界文件名及超限输入会在启动前拒绝。全局 `--dry-run` 会校验场景并返回计划，不启动程序、不创建报告和会话。

| action | 参数 | 验证内容 |
| --- | --- | --- |
| `wait_window` | `title_contains` 可选 | 仅从本次 PID 的后台桌面选择唯一窗口，验证适配器握手。 |
| `click` | 整数 `x/y` | 后台窗口当前客户区物理像素，通过 XCGUI 分派移动/按下/抬起消息。 |
| `text` | `text` | 向 XCGUI 焦点元素发送 Unicode 字符，先用 click 定位编辑框；最多 4096 个 UTF-16 码元。 |
| `key` | `key` | ENTER/TAB/ESC/SPACE/BACKSPACE/DELETE/LEFT/UP/RIGHT/DOWN/HOME/END。 |
| `wait` | `seconds`（0–30） | 持续处理调试事件并等待。 |
| `assert_debug` | `contains`，可选 `after_action` | 默认只检查最近一次输入之后的新输出；设 false 可检查整个运行记录。 |
| `assert_title` | `contains` | 检查 Win32 窗口标题；自绘标签/标题未必同步到该文本。 |
| `screenshot` | 英文数字 `name`（支持 `-`、`_`） | 在 XCGUI 完整绘制后读取 GDI 缓冲，保存客户区 BMP/PNG，记录 DPI/尺寸/哈希，空白或黑帧失败。 |
| `close` | 无 | 向已核验窗口请求正常关闭并等待退出。 |
| `wait_exit` | 无 | 等待程序自行退出。 |

示例会输入 `中文Automation`，点击“增加计数”，断言真实输出 `COUNT=, 1` 和 `TEXT=, 中文Automation`；基础模块的多参数调试输出会插入逗号和空格。所有动作核验 PID、EXE 路径，坐标校验当前客户区边界。前台窗口和鼠标可继续供用户使用，后台测试不会调用全局输入或焦点切换 API。无适配器、窗口失效、协议拒绝或超时都返回失败，不回退前台操作。报告中的前后鼠标坐标只是观测，用户移动鼠标不会被自动恢复或覆盖。

后台截图当前只支持 `炫彩_初始化(假)` 的 GDI 渲染；D2D 请求截图会明确失败，CLI 不更改程序的渲染配置。截图来自原生 `XWM_PAINT_END` 的完整绘制缓冲，不截取用户桌面，不模拟绘制控件。非黑帧只证明有画面，业务状态仍须由日志/标题断言和截图共同审核。没有 OCR、UIA 名称定位或视觉语义断言；静态布局节点不能直接等同于运行坐标。已验收本机 x86/x64、96 DPI；其他 DPI、DirectUI 框架或应用版本应另行验证。

调试输出最多记录约 2 Mi 字符/10,000 事件，异常最多 10,000 条；超过上限会失败，避免截断后误判。stdout/stderr 各按 16 MiB 轮询上限控制，快速写入可能短暂超过该值。总超时主要覆盖启动后的运行与场景；MSVC 桥接编译、IDE 启动就绪和关闭有独立超时。

自动化失败时可能已有完整 stdout JSON（`build/project doctor/runtime` 的失败报告），不能只读 stderr：

```python
process = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", check=False)
data = json.loads(process.stdout or process.stderr)
if process.returncode or not data.get("ok"):
    # 保存原始 stdout/stderr 和 data；读取 diagnostics 或 report，修复后重新构建。
    raise RuntimeError(data)
```

### 解析和添加模块依赖

```powershell
cli-anything-xcide --json --ide 'I:\xcide' module search XCGUI
cli-anything-xcide --json --ide 'I:\xcide' module dependencies module_xcgui.h
cli-anything-xcide --json --ide 'I:\xcide' --project 'E:\work\炫彩\Counter\Counter.xcproj' module add --file module_xcgui.h --with-dependencies
cli-anything-xcide --json --project 'E:\work\炫彩\Counter\Counter.xcproj' module list --project-only
```

依赖命令使用 `//@依赖` 头部元数据。`dependencies` 是只读计划；依赖缺失或同名歧义时返回失败。`add --with-dependencies` 只在所有模块引用可以唯一解析时一次性原子更新工程 XML。循环依赖会返回诊断，访问集合保证解析终止；外部头文件不加入 IDE 模块列表。没有 `--with-dependencies` 时，`add` 仍仅增加所选模块。更改 `<modules>` 后通常需要重新加载 GUI 工程，命令不会替用户操作当前 IDE 窗口。

### 读取或更新源码文件

```powershell
cli-anything-xcide --json --project 'E:\work\炫彩\Counter\Counter.xcproj' editor read 'E:\work\炫彩\Counter\main.xc'
cli-anything-xcide --json --project 'E:\work\炫彩\Counter\Counter.xcproj' editor write 'E:\work\炫彩\Counter\main.xc' 'E:\work\new-main.xc'
```

`editor write` 的输入参数是包含完整新文本的现有文件，CLI 会尝试保留目标文件编码、BOM 和换行并回读验证。目标必须在所选工程或 `--ide` 安装目录下；其他位置需明确传 `--allow-outside-project`。CLI 直接改磁盘，因此自动化代理应在写入前读取原文，并保留可恢复的副本或版本控制状态。`--dry-run` 会报告计划，但不会验证输入内容或写文件。

### 检查炫彩界面资源

```powershell
cli-anything-xcide --json --project 'E:\work\炫彩\Counter\Counter.xcproj' interface list
cli-anything-xcide --json --project 'E:\work\炫彩\Counter\Counter.xcproj' interface check
```

检查包括多根布局 XML、`resource.res` 图片/字体文件、`UI_ZIP.zip` 的完整性、条目路径和布局结构。不能从项目文件确定的主题或资源引用会作为 warning 返回；检查命令只读，不自动修复布局。

### 读取 UI ZIP 并导出单个原始文件

以下三组查询支持显式磁盘文件或 ZIP 成员；不必先选工程，但输入文件必须位于所选 `--project` 工程目录或 `--ide` 安装目录中。请使用绝对磁盘路径。只读查询加全局 `--dry-run` 会正常返回数据，同时禁止保存 CLI 会话。

```powershell
$zip = 'I:\xcide\data\template\项目模板\炫语言\用户模板\暗黑UI\project\UI_ZIP.zip'
cli-anything-xcide --json --dry-run --ide 'I:\xcide' archive list $zip
cli-anything-xcide --json --dry-run --ide 'I:\xcide' archive read $zip 'main.xml'
cli-anything-xcide --json --dry-run --ide 'I:\xcide' archive read $zip 'WmUi/Dark/WmUi.css'
```

从 `archive list.items[].id` 取得准确成员 ID。它使用 `/` 分隔符，`original_name` 保留原始目录名字（本机 ZIP 中常用反斜杠）。必须原样传回 ID，不从模糊查询结果中自动取第一个。大小写或分隔符归一化后冲突的成员会被标为 `ambiguous-name`，不能读取或导出。

`list` 的 `ok=true` 只代表目录读取完成。检查 `problem_count`、`items[].problems` 和 `readable`；`readable` 仅表示没有发现目录级阻碍，未验证压缩流、CRC 或当前 Python 是否支持该压缩方法。目录返回 `crc_verified=false`。`read` 和 `export` 完整读取所选成员并核验 CRC，失败时返回非零码。`read` 返回 `content/encoding/bom/crlf`，二进制控制字符或无法解码的内容会被拒绝。

导出需要一个已存在的父目录及尚不存在的目标文件；先检查计划，再移除全局 `--dry-run` 执行：

```powershell
cli-anything-xcide --json --dry-run --ide 'I:\xcide' archive export $zip 'main.xml' 'E:\work\exported-main.xml'
cli-anything-xcide --json --ide 'I:\xcide' archive export $zip 'main.xml' 'E:\work\exported-main.xml'
```

导出保留原始字节，可用于 XML、CSS、字体等成员。先写同目录暂存文件、回读核验，再通过硬链接发布到新文件；目标文件系统需支持硬链接（本机 NTFS 已验证）。已有目标、并发创建的同名目标和正式 IDE 安装目录目标均拒绝写入。`--dry-run` 也读取并校验源成员，但不会创建输出。成功结果含 `created=true`、`verified=true`、`sha256`；暂存名清理失败会附 `cleanup_warning`，不应据此重试已完成的导出。CLI 不做整包解压，也不根据成员路径自动创建目录。

### 查询命名资源表和嵌套分类

资源表不只叫 `resource.res`；暗黑模板中的 `WmUi.res` 和 `WmUi_Base.res` 也可显式查询：

```powershell
cli-anything-xcide --json --dry-run --ide 'I:\xcide' resource list $zip --member 'WmUi/Dark/WmUi.res' --kind type_bkInfo --limit 10
cli-anything-xcide --json --dry-run --ide 'I:\xcide' resource list $zip --member 'WmUi/WmUi_Base.res' --kind type_font
cli-anything-xcide --json --dry-run --ide 'I:\xcide' resource list 'I:\xcide\data\示例\炫彩界面库-高级示例\xc-QQ音乐\resource.res' --kind type_image
```

`items` 返回资源记录：`id/kind/tag/name/attributes/xml/assets/parent/folder_ids`。`folder` 分类会递归展开，分类元数据另放在 `folders`；分类名不会被算作已注册资源名称。`sections[].count` 是该节的直接子节点数，`resource_count` 和 `folder_count` 分别是递归资源数与分类数。空节和未知资源类型均保留；`--kind` 必须是源文件中实际存在的节名。

`duplicate_names` 表示同一张表中重复出现的资源名字，可能跨类型；它不证明加载冲突。不同表的同名资源也不能合并，例如 Dark/Light 的同名背景可能有不同属性。准确 ID 是原生子节点位置，如 `0/1/2`；与源哈希一起使用，不跨文件或版本硬编码。由 `list.items[].id` 取得 ID 后调用 `resource show FILE ID [--member MEMBER]`。

`assets` 只解析图片的文件 `value` 和字体的 `fontFile`。磁盘相对路径基于资源表目录，ZIP 相对路径基于该成员的虚拟目录，嵌套分类不改变这个基准。`fontName`、旧版字体 `value` 不被当作物理文件。`status=present` 仅说明资产文件或无目录级问题的归档成员存在，不代表图片可解码、字体可安装或资产成员 CRC 已验证。缺失返回 `exists=false`；带命名空间的 `@...`、宏、限定路径或越界引用返回 `exists=null` 及原因，不借用磁盘同名文件来补齐 ZIP。查询 `ok=true` 不等同于所有资产完备。

### 定位布局节点、原生属性和绑定

```powershell
$layoutZip = 'I:\xcide\例子\炫彩界面AI项目\UI_ZIP.zip'
cli-anything-xcide --json --dry-run --ide 'I:\xcide' interface nodes $layoutZip --member '布局文件/main.xml' --tag buttonUI
cli-anything-xcide --json --dry-run --ide 'I:\xcide' interface nodes $layoutZip --member '布局文件/main.xml' --attribute list.itemTemplate
cli-anything-xcide --json --dry-run --ide 'I:\xcide' interface nodes 'I:\xcide\data\xml\item_template\ActionView_ListBox_Item.xml' --attribute content
```

`nodes` 返回父子位置 `id/parent/depth`、`tag/name/attributes/child_count/text` 和含 `{binding...}` 的 `bindings`；`heads` 保留 `<head>` 内的类绑定。`--tag`、`--attribute` 和 `--value` 区分大小写，`--value` 必须与 `--attribute` 一起使用。可用 `--attribute name --value '准确名称'` 过滤，但可能有多项；按返回的准确位置 ID 调用 `interface node FILE ID [--member MEMBER]` 取得 `item` 和子树 `xml`。根节点 ID 为 `0`。

XML 子树会重新序列化；若需要原始文件字节，请用 `archive export`。节点查询支持 `windowUI`、`layoutPanel`、五种 `xc_template_*` 根（list、listBox、listView、tree、object）；`heiyue` 是独立格式，当前返回不支持错误。`showT`、`show`、`id`、`uid`、`itemID` 分别保留；布局宽高可能是 `fill/auto/:1/%...`，CLI 不计算实际像素、运行时可见性或绑定值。原有 `interface list/check` 仍按工程进行整体检查，支持范围以其结果为准。

### 新查询的分页、来源和错误处理

`archive list`、`resource list` 和 `interface nodes` 均支持可选 QUERY（记录内容不区分大小写的子串搜索）、`--limit 1..2000`（默认 100）和 `--offset`。下一页使用 `next_offset`；保持所有过滤参数一致，`next_offset=null` 表示没有下一页。未匹配是成功的空列表，无效 ID、未知资源节、坏 XML 或不可读 ZIP 成员返回非零码与 stderr JSON。`--help` 以及 Click 参数用法错误仍可能是纯文本。

磁盘来源返回 `source.path/bytes/sha256`；ZIP 成员返回 `source.archive.path/bytes/sha256` 和成员自身的 `source.member/bytes/sha256/crc_verified`。先列表后读取、翻页或跨命令比较时，应核对源哈希；归档结果还应比较归档哈希。发生变化就重新获取列表和 ID。调用示例：

```python
import json
import subprocess

base = ['cli-anything-xcide', '--json', '--dry-run', '--ide', r'I:\xcide']
bundle = r'I:\xcide\例子\炫彩界面AI项目\UI_ZIP.zip'
def call(*args):
    process = subprocess.run(base + list(args), capture_output=True,
                             text=True, encoding='utf-8', check=True)
    data = json.loads(process.stdout)
    if not data['ok']:
        raise RuntimeError(data)
    return data

page = call('interface', 'nodes', bundle, '--member', '布局文件/main.xml', '--tag', 'buttonUI')
for entry in page['items']:
    item = call('interface', 'node', bundle, entry['id'], '--member', '布局文件/main.xml')
    if item['source'] != page['source']:
        raise RuntimeError('来源已变化，请重新查询')
    # 按业务需要使用 item['item'] 和 item['xml']；此示例不写入工程。
```

读取上限为 ZIP 文件 64 MiB、10,000 个成员、单成员解压 8 MiB；XML 文件或成员 4 MiB、20,000 个节点、深度 128。XML 不接受 DTD/实体声明。路径穿越、大小写/分隔符冲突、Windows 保留文件名、符号链接及加密成员会被标记并禁止读取/导出。这些限制只应用于本轮新增显式查询命令，不代表旧工程检查器与它们共享全部策略。

### 浏览、创建和定位项目

```powershell
cli-anything-xcide --json --ide 'I:\xcide' project list 'E:\work\炫彩' --recursive
cli-anything-xcide --json --ide 'I:\xcide' project new 'E:\work\炫彩' 'ConsoleTool'
cli-anything-xcide --json project open 'E:\work\炫彩\ConsoleTool\ConsoleTool.xcproj'
cli-anything-xcide --json --project 'E:\work\炫彩\ConsoleTool\ConsoleTool.xcproj' status
```

`project open` 只选择持久化 CLI 会话中的默认工程，并不会在 GUI 中打开窗口。会话提供 `session status/history/undo/redo` 管理工程选择记录；撤销不会恢复源码或 XML 文件。

## 命令速查

| 命令 | 主要用途 | 文件修改 |
| --- | --- | --- |
| `status`、`session status/history` | 查看 CLI 会话、当前工程和安装路径。 | 否 |
| `project info FILE`、`project list DIR [--recursive]` | 检查、发现原生工程。 | 否 |
| `project new DIR NAME [--template ID]` | 从真实 IDE 模板创建工程。 | 新建目标目录 |
| `project template list [QUERY]` | 查询工程模板 ID。 | 否 |
| `project config list/set` | 查看或切换已定义的编译配置和架构。 | `set` 更新 `.xcproj` |
| `project sources list/add/remove` | 检查 `.xc/.xcs` 与工程 `<codeExpand>` 登记；添加/移除仅变更工程 XML。 | `add/remove` 更新 `.xcproj`，不删除源码 |
| `project breakpoints list/add/remove` | 按真实源码验证和更新工程断点元数据。 | 更新 `.xcproj`，不连接调试器 |
| `project debug list/watch-add/watch-remove/bookmark-add/bookmark-remove` | 读写监视式和源码书签工程记录。 | 更新 `.xcproj`；监视只保存，不求值 |
| `ui-template list/info/copy`、`theme list/info` | 检查/复制安装的布局皮肤素材，读取主题配置。 | 只读或只新建显式目标 |
| `reference sources/search/show` | 查询 10 类原生参考目录、准确 ID、来源哈希和分页。 | 不改安装文件；`--dry-run` 还禁止保存 CLI 会话 |
| `project doctor`、`interface list/check` | 验证工程与界面资源。 | 否 |
| `archive list/read/export FILE [MEMBER] [OUTPUT]` | 查询 ZIP、读取文本成员、按原始字节导出单个成员。 | `export` 仅创建显式新文件；禁止安装目录目标 |
| `resource list/show FILE [QUERY或ID] [--member MEMBER]` | 查询命名资源表、嵌套分类、原生属性及相对资产。 | 不修改源文件 |
| `interface nodes/node FILE [QUERY或ID] [--member MEMBER]` | 定位布局节点、父子层级和绑定，返回子树 XML。 | 不修改源文件 |
| `example list/info/copy` | 查询或派生 IDE 示例工程。 | `copy` 新建目标目录 |
| `editor read/write` | 读取或更新本机文本源码。 | `write` 更新一个目标文件 |
| `module list/search/dependencies` | 搜索模块，解析模块依赖关系。 | 否 |
| `module add/remove` | 修改工程的模块引用。 | 更新 `.xcproj` |
| `build` | 在插件目录为空的临时 IDE 副本中发送 F7 并核验 PE。 | 生成/更新工程构建产物 |
| `build --diagnostics` | 私有输出桥接读取编译结果、错误行号、警告及原始输出。 | 在临时 IDE 中编译/加载本地 DLL；生成工程产物 |
| `runtime run/test` | 捕获运行输出、异常、退出码；后台消息交互、断言与 GDI 截图。 | 在独立后台桌面启动/回收本次进程树，生成报告 |
| `preview recipes/capture/latest` | 发布或读取本地工程/EXE 检查包。 | `capture` 在本机生成预览包 |

所有命令的具体参数以 `cli-anything-xcide <命令> --help` 为准。可对支持 dry-run 的创建、复制、写入、配置和模块修改命令加全局 `--dry-run`，但 dry-run 只确认操作计划，不保证目标文件格式或 IDE 后端工作正常。

## AI 自动化边界

工程查询读取磁盘状态，不能得知已有 IDE 的活动选项卡或未保存缓冲区；`project open` 不等同于 GUI 打开工程。`build --diagnostics` 只读取本次隔离 IDE 输出，`runtime` 只测试本次启动的程序。模块引用和配置切换修改后，当前已打开的 IDE 窗口可能仍保留旧设置。

真实构建需要 Windows 登录会话、本机炫彩 IDE、配套编译工具与临时磁盘空间；运行和构建都需要创建私有桌面的权限。没有验证 Windows 服务会话、锁屏/RDP 断线、权限等级不同的外部窗口或高 DPI。独立桌面隔离窗口和输入，不是对被测程序文件/网络行为的安全沙箱。

`build` 按当前配置的输出名称/路径确定 `expected_executable`，只接受该 EXE 在本轮更新、超时前保持稳定且架构正确的结果。默认输出为工程文件名和原生 Debug/Release（x64 带 64 后缀）目录。DLL 工程或无法解析的输出变量会在启动 IDE 前报错；超时或未完成稳定性核验返回 `ok=false`，不能当作编译成功。
