---
name: cli-anything-xcide
description: 无需 MCP 的 XCGUI 与炫语言 IDE 本地命令行工具，可查找和派生工程、读写源码、维护工程调试元数据、检查布局皮肤与主题、搜索模块并启动真实 IDE 构建。
---

# 炫彩 IDE 本地命令行

`cli-anything-xcide` 直接读写炫彩 IDE 安装目录和 `.xcproj` 文件，不需要 MCP。可创建、检查和派生工程，维护源码/调试元数据，搜索模块、检查界面素材，并在独立后台桌面编译和测试程序。可选编译输出桥接只安装在本次私有 IDE，不修改正式安装。

编写炫语言业务代码时，可一并读取仓库的 `skills/xc-suite/SKILL.md`，按需查语法、模块、事件和布局资料。它随 Git 仓库单独提供，模块索引在目标机器重建；CLI wheel 自带本调用技能及两种原生桥接，不要求安装 XC-MCP-Next 或 `mcp-cli`。

## 环境和安装

- Windows 10/11，Python 3.10 或更新版本。
- 炫彩 IDE，默认路径 `I:\xcide`；可使用 `--ide PATH` 或环境变量 `XC_IDE_ROOT` 指定其他位置。
- 在 `xcide/agent-harness` 目录运行 `python -m pip install -e '.[test]'`。
- 运行 `cli-anything-xcide --help` 查看命令。全局选项 `--json`、`--ide`、`--project` 和 `--dry-run` 必须放在子命令之前。

## 常用工作流

列出并派生真实安装包里的示例：

```powershell
cli-anything-xcide --json --ide 'I:\xcide' example list '按钮'
cli-anything-xcide --json --ide 'I:\xcide' example info '炫彩界面库-示例/xc-Button-按钮/xc-demo.xcproj'
cli-anything-xcide --json --ide 'I:\xcide' example copy 'E:\work\xc' 'ButtonStudy' --id '炫彩界面库-示例/xc-Button-按钮/xc-demo.xcproj'
```

查看工程源码并维护工程调试元数据：

```powershell
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' project sources list
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' project sources add 'src/helper.xc'
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' project breakpoints add 'src/helper.xc' 12
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' project debug watch-add 'count'
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' project debug bookmark-add 'src/helper.xc' 12
```

`sources add/remove` 仅变更 `.xcproj` 的 `<codeExpand>`，不会复制或删除源码。断点和书签会校验真实源码路径和行号。监视表达式仅保存供 IDE 使用，不运行或求值表达式，也不连接 IDE 调试器。

发现本机布局/皮肤素材和代码主题：

```powershell
cli-anything-xcide --json --ide 'I:\xcide' ui-template list '关闭按钮'
cli-anything-xcide --json --ide 'I:\xcide' ui-template info '皮肤/template-关闭按钮'
cli-anything-xcide --json --ide 'I:\xcide' ui-template copy 'E:\work\xc' '关闭按钮素材' --id '皮肤/template-关闭按钮'
cli-anything-xcide --json --ide 'I:\xcide' theme list '黑色'
```

先从 `list` 获取准确 ID，再用于 `info` 或 `copy`。素材复制拒绝覆盖目标并忽略生成目录和符号链接。主题命令只读取 `data/theme/*/xctheme.config`，不会切换 IDE 全局主题。

检查模块依赖、界面资源，再构建新工程：

```powershell
cli-anything-xcide --json --ide 'I:\xcide' module search XCGUI
cli-anything-xcide --json --ide 'I:\xcide' module dependencies module_xcgui.h
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' project doctor
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' interface check
cli-anything-xcide --json --project 'E:\work\xc\Counter\Counter.xcproj' build
```

## 命令组

- `reference sources/search/show`：只读查询原生代码片段、语言帮助、控件名称、属性/帮助/事件、组合控件、编译选项和函数/常量补全表。
- `project`：新建、查看、查找和体检原生 `.xcproj`。
- `project template list`：查找炫语言工程模板。
- `project config list/set`：列出或切换项目中真实定义的配置与架构。
- `project sources list/add/remove`：查询或维护 `<codeExpand>` 源码登记。
- `project breakpoints list/add/remove`：读取和维护工程断点记录。
- `project debug list/watch-add/watch-remove/bookmark-add/bookmark-remove`：维护 watches 和书签工程元数据。
- `example list/info/copy`：浏览和安全派生 IDE 示例工程。
- `ui-template list/info/copy`：检索、查看和复制布局/皮肤素材。
- `theme list/info`：只读检查编辑器字体、行距、颜色和皮肤文件。
- `editor read/write`：直接读取或更新本地源码文本，保留常见编码、BOM 和换行。
- `module list/search/dependencies/add/remove`：搜索本地模块，规划依赖并管理工程引用。
- `interface list/check`：发现布局文件、resource.res 和 UI ZIP，并检查格式。
- `interface nodes/node FILE`：定位磁盘或 ZIP 内的布局节点、原生属性、绑定和子树，支持 `--member`、标签及属性过滤。
- `resource list/show FILE`：查询命名资源表、递归分类、资源属性和相对资产；用源哈希与位置 ID 定位。
- `archive list/read/export FILE`：列出 ZIP 成员、读取文本或将单个成员原样导出到新文件。
- `build`：在后台私有 IDE 副本中发送定向 F7，并核验新 PE 架构。
- `build --diagnostics`：在私有 IDE 自动编译/加载输出桥接，读取真实错误、警告、行号和原始输出；需要 MSVC，当前支持 AMD64 IDE v3。
- `runtime run --exe FILE --output DIR`：后台捕获本次主进程的 OutputDebugString、stdout/stderr、异常和退出码。
- `runtime test SCENARIO --exe FILE --output DIR`：后台 XCGUI 消息、业务断言、GDI 完整绘制截图与退出验证；需目标程序接入适配器。
- `preview recipes/capture/latest`：基于磁盘工程与 EXE 文件发布或读取检查包。
- `session status/history/undo/redo`：管理 CLI 工程选择历史。

## 自动化约定和边界

生成炫语言代码或布局前，先查询本机原生定义：

```powershell
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference sources
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference search snippets '如果'
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference search properties buttonType --scope 'elementUI/buttonUI'
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference show events 'elementUI/buttonUI/XE_BNCLICK'
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference search functions XBtn_
```

参考目录 KIND 为 `snippets/language/controls/properties/property-help/events/custom-objects/build-options/functions/completion-tokens`。从 `search.items[].id` 取得准确 ID 后再 `show KIND ID`；分页使用 `next_offset`，并比较源文件 `source.sha256`。`--scope` 只匹配原生直接层级，需分别查询父层信息。事件占位符、组合控件片段和补全词必须由调用方结合实际工程验证；编译选项说明不代表工程实际设置。加 `--dry-run` 可禁止查询时保存安装选择会话。

1. 每次子进程调用带 `--json`；检查退出码。构建/运行失败报告也可能在 stdout，读取 stdout 或 stderr JSON 并保留两者原文。
2. 使用绝对路径，并在修改前读取当前对象、检查命令帮助及操作边界。
3. 支持 `--dry-run` 的修改先检查计划。dry-run 不保证 IDE 或目标格式本身有效。
4. CLI 读取磁盘内容，不知道 GUI 中尚未保存的编辑内容、活动标签或运行时变量。
5. 普通构建的 `compiler.errorCount/compiled/skipped` 为 `null`；`--diagnostics` 成功要求编译完成、零错误和新 PE 同时成立。失败应按 `diagnostics` 文件/行号修复，再构建，不复用旧 EXE。
6. `project open` 只选择 CLI 会话默认工程，不会在 GUI 中打开工程。

编译和运行都使用独立 Windows 桌面，不切换前台、不移动鼠标、不发送全局输入。`runtime test` 要求在被测项目中包含打包的 `native/automation_bridge.h`，在窗口 UI 线程、消息循环前调用 `xc_cli_test::install(HWINDOW)`；没有本次 token 和匹配桌面时不会安装。消息通过 `XC_SendMessage` 走控件命中/事件处理，不直接调用业务函数。示例 `examples/automation_counter.xc` 和 `.json` 可复制到新项目；默认缓存 include 路径为 `../../../automation_bridge.h`，头文件放工程根目录。

截图要求 GDI（`炫彩_初始化(假)`）和 Pillow，读取 `XWM_PAINT_END` 完整绘制缓冲；D2D 截图或缺少适配器明确失败，不回退前台。场景至少包含日志/标题断言且以 close/wait_exit 结束；输入后的断言默认仅匹配新输出。不要将投递成功、非黑帧等同于业务成功。已测 x86/x64、96 DPI，未覆盖硬件输入、IME、Raw Input、任意第三方控件或源级调试。

每次运行生成唯一 report.json；超时/失败回收本次 Job 进程树，其他 IDE/用户进程不受影响。`ide_dialogs/cleanup_error/terminated` 保留后台 IDE 模态错误及关闭结果，不自动确认弹窗。窗口/光标观测是证据，不自动恢复用户鼠标。

需要检查 UI 包时，先列成员，再对准确成员查询资源或布局：

```powershell
$zip = 'I:\xcide\data\template\项目模板\炫语言\用户模板\暗黑UI\project\UI_ZIP.zip'
cli-anything-xcide --json --dry-run --ide 'I:\xcide' archive list $zip
cli-anything-xcide --json --dry-run --ide 'I:\xcide' resource list $zip --member 'WmUi/Dark/WmUi.res' --kind type_bkInfo
cli-anything-xcide --json --dry-run --ide 'I:\xcide' interface nodes $zip --member 'main.xml' --tag buttonUI
```

从 `items[].id` 取准确 ID，分别交给 `resource show FILE ID` 或 `interface node FILE ID`；ZIP 输入保持同一 `--member`。位置 ID 依赖文件内容；比较 `source.sha256` 和 ZIP 的 `source.archive.sha256`，源变化须重新查询。列表默认 100 项，按 `next_offset` 翻页。资源 folder 分类单独返回，不算资源名称；资产存在不保证运行时可用。绑定、`show/showT` 和尺寸表达式只展示不求值。

`archive list` 不验证 CRC，`read/export` 才校验选中成员。导出用 `archive export FILE MEMBER OUTPUT`，输出父目录必须存在且支持硬链接，只能创建新文件，拒绝安装目录或覆盖。`--dry-run` 校验源但不写入输出/会话。归档上限 64 MiB/10,000 项，单成员 8 MiB，XML 4 MiB；拒绝路径冲突、链接、加密、坏 XML 或 DTD。需要原始字节时使用 export，节点 `xml` 是重新序列化结果。

完整 JSON 工作流见 `AI_CALLING.md`；前两批各 20 轮本机安装包发现见工作区的 `AI_MINING_REPORT.md`、`AI_MINING_REPORT_02.md`，第三批 50 轮及来源证据见 `AI_MINING_REPORT_03.md`。Markdown 预览不可用时可打开同目录离线 `SKILL.html`。
