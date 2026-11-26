# XCIDE CLI 本地模式测试计划与结果

本测试结果的浏览器版本为独立文件 `TEST.html`。

本测试计划覆盖无需 MCP 的本地工程、源码、模块库、调试元数据、布局/皮肤、主题、后台构建、运行调试和后台交互。真实编译使用临时工程与独立后台桌面中的私有 IDE；普通构建无插件，诊断构建只加载本轮输出桥接。验收不编辑、恢复或重写正式安装的配置，也不修改真实示例。

## 测试清单与计划

原生 IDE 会话与 XC-MCP-Next 兼容入口增量计划（已完成）：对照 30 个工具提供可发现的参数和行为映射，保持无需 MCP。新增后台持久 IDE 会话、令牌绑定/截止时间/串行 IPC、UI 线程原生查询、文件导入/编辑缓冲读取/符号导航/保存/编译投递/弹窗读取，以及本地函数索引和模块骨架创建。先测参数校验、路径限制、超时与过期请求、并发、版本门禁、dry-run、部分操作结果；再用已安装命令启动真实私有 IDE，串联查询、导入、符号/缓冲读取、输出与编译、正常停止和故障回收。确认正式 IDE 配置哈希不变、无前台输入、旧命令回归通过。工具投递不得冒充编译成功，未验证的 ABI/内存操作必须明确拒绝。完整支持与行为差异将在文档逐项记录。

2026-11-26 八项审查修复计划（已完成）：新增 34 项核心回归和 10 项安装命令用例，并扩展现有配置/后台按钮验收。覆盖含 CMD 特殊字符的真实目录联接、UI ZIP 压缩/成员/总解压大小与条目限制及 CRC、带单双引号的配置切换与回读、后台输入触发退出及错误退出码、退出后的 stdout/stderr 上限检查、磁盘与 ZIP 对象模板、损坏会话字段的 JSON 错误及文件保留、入口文件增删后的预览缓存失效。安装命令验收覆盖配置/会话/预览、真实原生对象模板，以及 x86/x64 后台退出按钮与超限输出。保留完整后台 IDE 构建和 GDI/D2D 回收验收；不修改正式安装或使用前台输入。

后台清理修复计划（独立仓库）：先记录真实 D2D 失败后的 `TerminateJobObject`、`EXIT_PROCESS_DEBUG_EVENT`、`ContinueDebugEvent` 与进程句柄等待时序。新增确定性回归，覆盖退出事件已到但句柄延迟超过 1 秒、终止/调试事件/最终等待共用有界截止时间、保留多个清理错误和等待 API 失败。真实 x64/x86 用例继续覆盖 GDI、D2D、无适配器；D2D 操作仍须失败，且回收后进程句柄必须已 signaled。新技能资料核对相对引用、索引重建及选定模块查询，不将 MCP 服务作为运行依赖。

自动化执行增量计划：`build --diagnostics` 在本轮私有 IDE 内加载本地输出桥接，测试真实成功编译、故意写错的炫语言源码、C++/链接错误及缺失桥接，不能把错误汇总为零当成编译成功。`runtime run/test` 仅调试本次创建的进程，覆盖 Unicode/ANSI 调试输出、首轮/未处理异常、退出码、超时回收、无输出程序、无效场景与 dry-run。按用户要求，运行与交互使用独立 Windows 桌面，不切换桌面、不调用前台输入 API；测试后台点击、中文输入、按键、状态日志、GDI 完整绘制缓冲截图和正常退出。核验 PID/EXE、测试适配器握手、失效窗口、越界坐标、缺失适配器、UTF-16 长度及前台窗口/鼠标观测。D2D 绘制截图不支持且应明确失败。新增测试不得改写正式 IDE 配置；桥接源码和可执行示例进入 wheel 并验证可迁移调用。

第三批 50 轮深度挖掘计划：围绕资源表、布局节点、ZIP 成员、项目配置/工具链和模块声明做 50 个有明确问题的原生数据探测，逐项保存来源与前后哈希。新增 `archive list/read/export`、`resource list/show`、`interface nodes/node`，预计增加约 30 项核心边界用例和 3 项安装命令工作流。覆盖 ZIP 原始成员名、路径/大小写冲突、符号链接、加密/损坏/超限成员、CRC、文本编码和二进制导出；资源类型、嵌套 folder 分类与重复分类名、资源重名、相对资产路径、WmUi 命名资源表；布局多根、节点定位、属性/绑定过滤、非标准模板根及深度限制。导出仅写临时新文件，不覆盖目标，不写正式安装；完整套件继续验证原有真实 GUI 构建。

第二批 20 轮挖掘的增量测试计划：新增只读 `reference sources/search/show`，验证安装包中的代码片段、语言帮助、控件名称、分层属性/选项、独立属性帮助、事件声明、组合控件、编译选项映射与函数/补全词。覆盖原生多根 XML、深层作用域、同名字段、分页、原文保留、补全空行与原始行号、缺失/损坏/超限配置及安装目录外链接；通过已安装命令串联“查片段 → 临时工程写入 → 回读”。记录数据来源 SHA-256；不改写正式安装、示例或全局配置。

本次代码审查修复的回归计划：验证同一工程的跨进程更新与外部修改冲突、目标产物身份及超时稳定性、UTF-16 LE/BE 的 BOM/CRLF 保留、模板源目录内复制拒绝、操作完成后的会话保存失败语义、跨工程预览隔离、长注释/UTF-16/生成目录布局检查、失效断点与书签删除，以及 HTML 链接随目录迁移和 wheel 打包后的可达性。测试只修改临时工程；真实构建仍使用无插件隔离 IDE。

- `test_core.py`：225 项本地单元用例（含参数化平台/错误边界用例）。
  - 原生 IDE 工具迁移新增 32 项：工具参数、Unicode 帧、路径、函数索引、模块生成/相对引用/模块库注册/回滚、BOM、dry-run、响应身份、部分完成和工作进程启动失败。
  - 本轮增加 34 项审查修复回归，覆盖上述八类问题及会话保存时并发损坏、输出上限与原错误同时发生等边界。
  - 保留此前 60 项工程、模块、编码、界面、主题、会话和构建测试。
  - 新增 25 项回归：跨进程工程更新与外部修改冲突、UTF-16 LE/BE、模板递归复制、失效断点/书签删除、提交后会话保存失败与 REPL、预览工程隔离、布局发现及生成目录选项、目标 EXE/超时核验、HTML 迁移。
  - 第二批功能挖掘新增 18 项：参考源与准确 ID、层级/分页、补全行号、独立帮助、重复名称和 JSON 键、12 种损坏格式、大小上限、UTF-16、缺失文件及越界链接。
  - 第三批新增 30 项：ZIP 原始成员名、10 类不安全路径、冲突/链接/加密/CRC/压缩错误、读取上限、无覆盖导出及竞争、嵌套资源分类、相对资产、未知/空资源节、布局节点身份、绑定、格式和深度。
  - 后台自动化新增 22 项：运行输出、异常、场景校验、原生输出桥接、诊断与后台构建错误边界；独立仓库再新增 4 项清理截止时间、进程句柄延迟和 API 错误回归。
- `test_full_e2e.py`：参数化后共 50 项。
  - 原生 IDE 迁移新增 4 项：工具目录与 dry-run、30 个工具的完整后台会话、空闲回收，以及真实 XCGUI 模态正文。会话用例同时核验过期请求、四个并发 CLI 调用和生成模块的实际编译。
  - 本轮增加 10 项：4 类损坏会话、源码增删缓存、真实对象模板，以及 x86/x64 各两个输出通道的超限；现有配置用例新增含引号名称，现有两个架构的交互用例新增退出按钮。
  - 通过 `_resolve_cli("cli-anything-xcide")` 验证已安装 CLI 的帮助、模板/示例、配置、工程检查、源码与模块工作流，以及新增加的源码登记、断点、调试元数据、皮肤模板复制和主题检索。
  - 其中 14 项通过已安装命令覆盖真实工程工作流，包括 UTF-16 写入后会话目录不可写和失效调试元数据清理；2 项在 Windows 运行真实 IDE 无插件隔离副本 F7，分别核验默认目录与自定义输出名称/目录的 AMD64 EXE，不将产物核验冒充 IDE 错误列表或零错误证明。
  - 另外 3 项验证 10 类真实参考数据的搜索/准确 ID/哈希、片段到临时工程的写入回读，以及缺失/损坏参考源的部分目录发现和 JSON 错误输出。
  - 第三批增加 3 项：真实 UI ZIP 文本读取/精确导出/拒绝覆盖、命名资源表/包内字体/QQ 音乐嵌套分类、磁盘与 ZIP 布局节点查询。
  - 后台自动化增加 14 项：x86/x64 运行输出、异常、超时、无输出、适配器模式，dry-run/无效场景，以及真实 XC 编译诊断与后台交互；本轮进一步检查模式测试的退出码和进程结束状态。

## 关键端到端场景

1. 从炫彩 IDE 官方模板创建新 `.xcproj`，查看配置/架构、源码登记、模块引用和项目健康状态。
2. 从真实示例目录读取准确工程 ID、检查源码与资源，并派生到新的临时目录；验证原例哈希未变化。
3. 对隔离工程以 Click 安装命令维护源码登记、真实断点行、监视表达式和书签；拒绝越界路径及超长行号，回读真实 XML 并确保源文件仍在。
4. 从嵌套的 `template.config` 发现并复制皮肤/布局素材，过滤生成目录；从真实 `xctheme.config` 读取编辑器主题，并验证未修改原主题 XML。
5. 扫描真实示例工程、界面布局、UI ZIP、模块依赖和 IDE 主题目录；检查目录、源工程及全局配置 SHA-256 均未变化。
6. 运行 `example copy --dry-run` 等只读计划，并验证目标目录和持久会话均无变化。
7. 在隔离 Windows 工程中启动无插件临时 IDE 副本并发送 F7，核验新 PE 文件架构、ID 和大小，确认临时副本已清除。
8. 列出真实 ZIP 成员后按准确 ID 读取/导出，比较字节 SHA-256；查询 WmUi 资源和布局节点，区分分类名、资源名与位置 ID，不改写来源。

## 最近完整测试结果

2026-11-26 原生 IDE 工具迁移后最终结果：**275 passed in 141.18s**，225 项核心测试、50 项安装/原生端到端测试，无失败或跳过。新增 32 项核心和 4 项端到端用例；Windows、Python 3.14、仓库 `.venv`、`CLI_ANYTHING_FORCE_INSTALLED=1`。完整日志位于本机忽略目录 `build/ide-migration/pytest.log`。生成模块也经过真实编译验收：关闭 IDE 后仍保留磁盘修改，重新加载工程，炫语言调用 `样例_初始化()`，诊断构建确认编译成功。

一次中间复测为 272 通过、1 失败：旧断言要求前后前台 HWND 相等，实际两个句柄属于其他应用而非本次 IDE。新增只读观测 `foreground_pid/input_desktop`，将断言改为前台进程不属于被测进程、输入桌面不等于私有桌面，保留原始 HWND/鼠标位置。未改变输入发送路径。该次日志保留为 `build/ide-migration/pytest-foreground-observation.log`；之后补充模块库注册边界和两个用例，再取得上述全量 275 通过。

覆盖内容：全部 30 个工具名的真实私有 IDE 调用、编辑缓冲/符号/导航/输出、F7 新 AMD64 产物、模块生成/引用维护/重新构建、正常停止与空闲回收、四个并发 CLI 调用、过期请求不执行、身份拒绝与参数/路径校验、部分导入结果、双文件发布回滚、UTF-16/BOM 和 dry-run。独立的真实 XCGUI ABI 测试宿主验证模态调用超时后读取直接绘制的弹窗正文，以及未验证宿主的解析计数拒绝；它不是另一个编译器验收。正式 IDE 配置前后 SHA-256 保持 `977e1d599024cb3a119cd1c6ebfa4cb64c0a5f87ce73e5c3b0600de234ed9d1c`。

工具投递结果不视作保存或编译完成；主套件仍保留旧 `build --diagnostics`、x86/x64 后台交互与 D2D 拒绝/回收测试。30 个接口的对应行为、精确版本限制与字段差异见同包 `IDE_COMPAT.md`。

## 上次完整测试结果（八项审查修复）

2026-11-26 八项审查修复后：**239 passed in 96.12s**，193 项核心测试、46 项安装命令测试，无失败或跳过。Windows、Python 3.14.8，`CLI_ANYTHING_FORCE_INSTALLED=1`，使用本仓库 `.venv` 和可编辑安装。执行方式与下方命令相同，完整日志保存在本机忽略目录 `build/review-fixes/pytest.log`。

修复前，36 项定向检查中 33 项失败、3 项已有行为通过，覆盖全部八类问题；修复后核心套件 193 项通过，定向真实安装验收 13 项通过，再完成全量 239 项。最终将损坏会话用例的调用改为已存在的 `session status`，相关 12 项复测通过。10 个修改的 Python 文件通过语法编译及 Python 3.10 AST 检查，`git diff --check` 通过。正式 IDE 配置前后 SHA-256 均为 `977E1D599024CB3A119CD1C6EBFA4CB64C0A5F87CE73E5C3B0600DE234ED9D1C`。

此次行为变化：界面体检现在拒绝超过单成员 8 MiB、归档文件或总解压大小 64 MiB、条目数 10000 的 UI ZIP；沿用归档读取的成员路径、歧义和 CRC 检查。有效 JSON 会话的错误字段类型返回结构化错误并保留文件，业务写入已完成后的会话损坏仍报告成功附带警告，避免错误重试；已有空撤销/重做快照继续兼容。输入后退出依然校验后续断言及预期退出码，最终输出超限返回失败。预览因缓存指纹增加入口文件列表，升级后的首次捕获会重新生成。命令参数和正常调用格式不变，未加入前台输入路径或修改原生桥接。

## 上次完整测试结果（后台清理修复）

2026-11-25 独立仓库清理修复后：**195 passed in 93.63s**，159 项核心测试、36 项安装命令端到端测试。Windows、Python 3.14.8；`CLI_ANYTHING_FORCE_INSTALLED=1`，PATH 优先使用独立仓库的 `.venv\Scripts`，导入与 CLI 均来自本仓库。执行命令：

```powershell
$env:PATH = (Join-Path (Get-Location).Path '.venv\Scripts') + ';' + $env:PATH
$env:CLI_ANYTHING_FORCE_INSTALLED = '1'
$env:PYTHONUTF8 = '1'
& .\.venv\Scripts\python.exe -X utf8 -B -m pytest xcide/agent-harness/cli_anything/xcide/tests -v --tb=short -p no:cacheprovider
```

4 项确定性清理回归在旧实现失败、修复后通过；真实定向测试 10 项通过，另做 x86/x64 各 12 次 D2D 预期失败回收检查，均确认进程已结束且无清理错误。该批真实最终等待最大 0.296064 秒，超过 1 秒的时序由确定性回归覆盖。D2D 截图继续明确失败，未改变成功标准或增加前台输入。原生底层退出延迟的具体组件来源仍不确定。完整日志附于文末，详细时序与取证在仓库根目录 `CLEANUP_FIX.md` 和 `xcide/automation-evidence/cleanup-fix/`。

## 历史后台自动化测试结果

运行环境：Windows，Python 3.14；`CLI_ANYTHING_FORCE_INSTALLED=1`，子进程使用 `C:\Program Files\Python314\Scripts\cli-anything-xcide.exe`。

```text
$ CLI_ANYTHING_FORCE_INSTALLED=1 python -X utf8 -B -m pytest cli_anything/xcide/tests -q --tb=short -p no:cacheprovider
........................................................................ [ 37%]
........................................................................ [ 75%]
...............................................                          [100%]
191 passed in 96.33s (0:01:36)
```

- 原开发目录后台自动化回归：191 项通过（155 项核心测试、36 项安装命令端到端用例）。新增诊断解析、UI 线程输出桥接、真实成功/失败源码编译；x86/x64 Unicode/ANSI/异常/退出/超时；后台消息交互、中文输入、退格、GDI 绘制截图、缺失适配器/D2D 截图失败、dry-run；F7 唯一主窗口、模态错误与清理失败保留。两项默认/自定义输出的旧构建验收继续通过。
- IDE 打开、编译、关闭及 runtime 运行均使用独立后台桌面；无 SendInput/SetCursorPos/SetForegroundWindow/SwitchDesktop 回退。本轮真实 XC 工程中，前台 HWND 在编译与运行前后一致；运行前后及四个输入动作前后，鼠标坐标均为 `[-624,733]`，前台 HWND 均为 `11931006`。这些是本轮观测，不将用户主动移动鼠标判为失败。
- 后台截图已实际查看，包含中文输入 `中文Automation`、点击后标题与按钮。使用 GDI 的 XWM_PAINT_END 完整缓冲，不使用桌面截图；x86/x64 原生 fixture 还比较编辑框区域前后像素。D2D 截图不支持且测试确认返回失败。
- 第三批 50 轮功能挖掘后的历史结果为 155 项（133 核心、22 端到端）；此前第二批为 122 项。以下轮次数据保留为历史取证，不与最新运行数混用。
- `tools/explore_round3.py` 完成 50 个具体问题的取证，直接读取的 249 个安装文件前后哈希一致，13 次安装命令检查返回预期结果；证据为 `AI_MINING_EVIDENCE_03.json`。31 轮需求已由新增 7 个命令覆盖，19 轮为观察结论，不将轮数当成新功能数。
- 新资源读取覆盖 38 张表的 1777 条资源记录（含 496 张图片），另返回 19 个分类；保留两处相对资产缺失。5 个 ZIP 共 42 个成员完成 CRC；42 个磁盘对应文件字节相同。上述样本验证不代表任意归档或运行加载都有效。
- `tools/explore_round2.py` 完成第二批 20 轮探测，读取的 64 个安装文件前后哈希一致，证据位于仓库根目录 `AI_MINING_EVIDENCE_02.json`；新增 10 类参考目录共 3829 条数据记录，不将记录数等同于 API 数量。
- 本轮真实构建前后，正式 IDE 配置 SHA-256 均为 `977E1D599024CB3A119CD1C6EBFA4CB64C0A5F87CE73E5C3B0600DE234ED9D1C`。
- 前期构建输出变量和布局标签边界回归保留通过。本批 28 个 Python 文件按 Python 3.10 语法规则完成 AST 检查；实际运行测试环境为 Python 3.14。
- 本批 wheel 从独立构建目录生成，33 个 Python/Markdown/HTML 文件与当前源码一致，没有遗留 xcide_backend；解压后的 4 个 HTML 页面、6 个本地文档链接均可迁移。7 个新增子命令在解压目录直接运行通过，资源返回 474 条背景样式，实际导出哈希一致。
- 12 份更新的离线 HTML 页面共 154 处链接/锚点检查通过；50 轮报告已用本机 Chrome 渲染并查看，中文、目录和正文显示正常。
- 已完成针对真实 `I:\xcide` 的 20 轮 CLI 安装命令挖掘，20/20 调用返回预期数据。IDE 正式配置和一个断点示例工程在扫描前后 SHA-256 均与原值一致；临时素材副本已经清理。
- 本地示例工程盘点发现 60 个示例项目，22 个登记有断点，共 25 条；至少一个示例行号高于源码行数。CLI 会将其列为 warning/`valid=false`，不私自修复示例。
- 安装主题目录包含 5 个主题，均可解析有效 `data/xml/style1.css` 或 `style2.css` 皮肤文件；布局/皮肤目录含 5 个皮肤模板和 2 个布局模板。

## 运行方式

```powershell
$env:CLI_ANYTHING_FORCE_INSTALLED = '1'
python -m pytest cli_anything/xcide/tests/test_core.py cli_anything/xcide/tests/test_full_e2e.py -q --tb=short
```

## 限制

构建需要 Windows 登录会话、创建桌面权限、炫彩 IDE、MSVC、Windows SDK 和临时空间。普通 build 的诊断仍未知；--diagnostics 仅支持实测 AMD64 IDE v3 ABI。runtime 可捕获当前主进程输出/异常，但不提供实时变量、调用栈或源级单步。后台 test 要求程序主动接入适配器，当前仅验证 x86/x64、96 DPI、GDI 截图和 XCGUI 消息路径；D2D 截图、其他 DPI、Raw Input/IME、锁屏/RDP 断线、服务会话未覆盖。旧示例失效行号仅诊断，不更改正式安装。

## 后台自动化最终复测明细

2026-11-25，保存最后版本的完整输出：

```text
============================= test session starts =============================
platform win32 -- Python 3.14.8, pytest-9.1.1, pluggy-1.7.0 -- C:\Program Files\Python314\python.exe
rootdir: E:\AIWork\Codex\CLI-Anything\xcide\agent-harness
plugins: anyio-4.15.1, platformdirs-4.13.5
collecting ... collected 191 items

cli_anything/xcide/tests/test_core.py::test_archive_roundtrip_normalizes_backslashes_without_losing_original PASSED [  0%]
cli_anything/xcide/tests/test_core.py::test_archive_unsafe_members_are_reported_and_not_exported[../escape] PASSED [  1%]
cli_anything/xcide/tests/test_core.py::test_archive_unsafe_members_are_reported_and_not_exported[/rooted] PASSED [  1%]
cli_anything/xcide/tests/test_core.py::test_archive_unsafe_members_are_reported_and_not_exported[C:/drive] PASSED [  2%]
cli_anything/xcide/tests/test_core.py::test_archive_unsafe_members_are_reported_and_not_exported[dir/../../escape] PASSED [  2%]
cli_anything/xcide/tests/test_core.py::test_archive_unsafe_members_are_reported_and_not_exported[a:stream] PASSED [  3%]
cli_anything/xcide/tests/test_core.py::test_archive_unsafe_members_are_reported_and_not_exported[CON.txt] PASSED [  3%]
cli_anything/xcide/tests/test_core.py::test_archive_unsafe_members_are_reported_and_not_exported[dir/name.] PASSED [  4%]
cli_anything/xcide/tests/test_core.py::test_archive_unsafe_members_are_reported_and_not_exported[dir/name ] PASSED [  4%]
cli_anything/xcide/tests/test_core.py::test_archive_unsafe_members_are_reported_and_not_exported[dir//name] PASSED [  5%]
cli_anything/xcide/tests/test_core.py::test_archive_unsafe_members_are_reported_and_not_exported[bad?.txt] PASSED [  5%]
cli_anything/xcide/tests/test_core.py::test_archive_member_integrity_and_ambiguity[case-collision] PASSED [  6%]
cli_anything/xcide/tests/test_core.py::test_archive_member_integrity_and_ambiguity[slash-collision] PASSED [  6%]
cli_anything/xcide/tests/test_core.py::test_archive_member_integrity_and_ambiguity[symlink] PASSED [  7%]
cli_anything/xcide/tests/test_core.py::test_archive_member_integrity_and_ambiguity[encrypted] PASSED [  7%]
cli_anything/xcide/tests/test_core.py::test_archive_member_integrity_and_ambiguity[bad-crc] PASSED [  8%]
cli_anything/xcide/tests/test_core.py::test_archive_member_integrity_and_ambiguity[compression] PASSED [  8%]
cli_anything/xcide/tests/test_core.py::test_archive_read_limits_and_atomic_export_collision PASSED [  9%]
cli_anything/xcide/tests/test_core.py::test_archive_export_refuses_installation_and_outside_input PASSED [  9%]
cli_anything/xcide/tests/test_core.py::test_resource_queries_preserve_unknown_sections_and_resolve_relative_assets[False] PASSED [ 10%]
cli_anything/xcide/tests/test_core.py::test_resource_queries_preserve_unknown_sections_and_resolve_relative_assets[True] PASSED [ 10%]
cli_anything/xcide/tests/test_core.py::test_resource_folders_are_recursive_categories_not_resource_names[False] PASSED [ 11%]
cli_anything/xcide/tests/test_core.py::test_resource_folders_are_recursive_categories_not_resource_names[True] PASSED [ 12%]
cli_anything/xcide/tests/test_core.py::test_layout_queries_preserve_identity_bindings_and_designer_fields[False] PASSED [ 12%]
cli_anything/xcide/tests/test_core.py::test_layout_queries_preserve_identity_bindings_and_designer_fields[True] PASSED [ 13%]
cli_anything/xcide/tests/test_core.py::test_layout_rejects_unknown_and_malformed_input[<head/><windowUI/><windowUI/>] PASSED [ 13%]
cli_anything/xcide/tests/test_core.py::test_layout_rejects_unknown_and_malformed_input[<heiyue/>] PASSED [ 14%]
cli_anything/xcide/tests/test_core.py::test_layout_rejects_unknown_and_malformed_input[<windowUI>] PASSED [ 14%]
cli_anything/xcide/tests/test_core.py::test_layout_rejects_unknown_and_malformed_input[<!DOCTYPE x [<!ENTITY a "b">]><windowUI/>] PASSED [ 15%]
cli_anything/xcide/tests/test_core.py::test_layout_object_root_and_depth_limits PASSED [ 15%]
cli_anything/xcide/tests/test_core.py::test_reference_sources_and_literal_content PASSED [ 16%]
cli_anything/xcide/tests/test_core.py::test_reference_completion_preserves_raw_line_numbers_and_duplicate_declarations PASSED [ 16%]
cli_anything/xcide/tests/test_core.py::test_reference_hierarchy_and_pagination_do_not_invent_inheritance PASSED [ 17%]
cli_anything/xcide/tests/test_core.py::test_reference_rejects_malformed_source_without_silently_dropping_items[snippets-{}] PASSED [ 17%]
cli_anything/xcide/tests/test_core.py::test_reference_rejects_malformed_source_without_silently_dropping_items[snippets-[{"name":"broken","comment":"","data":null}]] PASSED [ 18%]
cli_anything/xcide/tests/test_core.py::test_reference_rejects_malformed_source_without_silently_dropping_items[language-{"type":{},"other":"text"}] PASSED [ 18%]
cli_anything/xcide/tests/test_core.py::test_reference_rejects_malformed_source_without_silently_dropping_items[language-{"same":"one","same":"two"}] PASSED [ 19%]
cli_anything/xcide/tests/test_core.py::test_reference_rejects_malformed_source_without_silently_dropping_items[properties-{"elementUI":{"self":[["edit","true","id"]]}}] PASSED [ 19%]
cli_anything/xcide/tests/test_core.py::test_reference_rejects_malformed_source_without_silently_dropping_items[properties-{"elementUI":{"self":[["edit","true","id","ID","",["invalid"]]]}}] PASSED [ 20%]
cli_anything/xcide/tests/test_core.py::test_reference_rejects_malformed_source_without_silently_dropping_items[events-<wrong/>] PASSED [ 20%]
cli_anything/xcide/tests/test_core.py::test_reference_rejects_malformed_source_without_silently_dropping_items[events-<events><buttonUI><item event="CLICK"/></buttonUI></events>] PASSED [ 21%]
cli_anything/xcide/tests/test_core.py::test_reference_rejects_malformed_source_without_silently_dropping_items[events-<!DOCTYPE events [<!ENTITY e "hello">]><events/>] PASSED [ 21%]
cli_anything/xcide/tests/test_core.py::test_reference_rejects_malformed_source_without_silently_dropping_items[controls-<buttonUI name="one"/><buttonUI name="two"/>] PASSED [ 22%]
cli_anything/xcide/tests/test_core.py::test_reference_rejects_malformed_source_without_silently_dropping_items[custom-objects-<customObject><buttonUI/></customObject>] PASSED [ 23%]
cli_anything/xcide/tests/test_core.py::test_reference_rejects_malformed_source_without_silently_dropping_items[build-options-{"runtime": {"xml_label":"runtimeLibrary","uiType":"comboBox","flag":"cl","list":[]}}] PASSED [ 23%]
cli_anything/xcide/tests/test_core.py::test_reference_limits_missing_source_and_utf16 PASSED [ 24%]
cli_anything/xcide/tests/test_core.py::test_reference_ids_scope_and_bounds_are_validated PASSED [ 24%]
cli_anything/xcide/tests/test_core.py::test_reference_refuses_source_link_outside_installation PASSED [ 25%]
cli_anything/xcide/tests/test_core.py::test_new_project_preserves_native_modules_and_lists_existing_entrypoint PASSED [ 25%]
cli_anything/xcide/tests/test_core.py::test_project_uses_selected_platform_from_installed_template[x64] PASSED [ 26%]
cli_anything/xcide/tests/test_core.py::test_project_uses_selected_platform_from_installed_template[x86] PASSED [ 26%]
cli_anything/xcide/tests/test_core.py::test_project_configuration_tracks_installed_ide_toolset_and_sdk PASSED [ 27%]
cli_anything/xcide/tests/test_core.py::test_project_template_toolchain_defaults_survive_when_ide_config_is_unavailable PASSED [ 27%]
cli_anything/xcide/tests/test_core.py::test_invalid_windows_project_names_are_rejected[] PASSED [ 28%]
cli_anything/xcide/tests/test_core.py::test_invalid_windows_project_names_are_rejected[..] PASSED [ 28%]
cli_anything/xcide/tests/test_core.py::test_invalid_windows_project_names_are_rejected[a/b] PASSED [ 29%]
cli_anything/xcide/tests/test_core.py::test_invalid_windows_project_names_are_rejected[a\\b] PASSED [ 29%]
cli_anything/xcide/tests/test_core.py::test_invalid_windows_project_names_are_rejected[foo.] PASSED [ 30%]
cli_anything/xcide/tests/test_core.py::test_invalid_windows_project_names_are_rejected[CON] PASSED [ 30%]
cli_anything/xcide/tests/test_core.py::test_invalid_windows_project_names_are_rejected[com3] PASSED [ 31%]
cli_anything/xcide/tests/test_core.py::test_invalid_windows_project_names_are_rejected[bad:name] PASSED [ 31%]
cli_anything/xcide/tests/test_core.py::test_invalid_windows_project_names_are_rejected[ x ] PASSED [ 32%]
cli_anything/xcide/tests/test_core.py::test_project_creation_refuses_destination_and_does_not_replace_file PASSED [ 32%]
cli_anything/xcide/tests/test_core.py::test_project_xml_and_source_entry_errors_are_explicit PASSED [ 33%]
cli_anything/xcide/tests/test_core.py::test_activate_source_is_safe_idempotent_and_retains_modules PASSED [ 34%]
cli_anything/xcide/tests/test_core.py::test_project_discovery_skips_compiler_output PASSED [ 34%]
cli_anything/xcide/tests/test_core.py::test_project_configuration_inventory_and_atomic_switch_preserve_other_fields PASSED [ 35%]
cli_anything/xcide/tests/test_core.py::test_project_configuration_rejects_missing_platform_without_partial_update PASSED [ 35%]
cli_anything/xcide/tests/test_core.py::test_project_source_inventory_add_remove_and_path_safety PASSED [ 36%]
cli_anything/xcide/tests/test_core.py::test_project_breakpoint_crud_bounds_idempotency_and_diagnostics PASSED [ 36%]
cli_anything/xcide/tests/test_core.py::test_ui_template_catalog_metadata_filter_payload_and_copy PASSED [ 37%]
cli_anything/xcide/tests/test_core.py::test_ui_template_search_skips_malformed_metadata_and_bad_payload PASSED [ 37%]
cli_anything/xcide/tests/test_core.py::test_theme_catalog_extracts_native_editor_configuration_without_writing PASSED [ 38%]
cli_anything/xcide/tests/test_core.py::test_project_watch_and_bookmark_metadata_crud_preserves_native_shapes PASSED [ 38%]
cli_anything/xcide/tests/test_core.py::test_ide_template_catalog_finds_native_xuan_projects PASSED [ 39%]
cli_anything/xcide/tests/test_core.py::test_create_project_from_template_preserves_native_configuration_and_retargets_name PASSED [ 39%]
cli_anything/xcide/tests/test_core.py::test_create_project_from_template_can_override_existing_platform_and_config PASSED [ 40%]
cli_anything/xcide/tests/test_core.py::test_example_library_indexes_searches_and_describes_native_projects PASSED [ 40%]
cli_anything/xcide/tests/test_core.py::test_example_lookup_rejects_non_relative_or_non_project_ids[] PASSED [ 41%]
cli_anything/xcide/tests/test_core.py::test_example_lookup_rejects_non_relative_or_non_project_ids[../outside.xcproj] PASSED [ 41%]
cli_anything/xcide/tests/test_core.py::test_example_lookup_rejects_non_relative_or_non_project_ids[C:/outside.xcproj] PASSED [ 42%]
cli_anything/xcide/tests/test_core.py::test_example_lookup_rejects_non_relative_or_non_project_ids[sample.txt] PASSED [ 42%]
cli_anything/xcide/tests/test_core.py::test_example_copy_retargets_project_and_preserves_native_files_without_build_outputs PASSED [ 43%]
cli_anything/xcide/tests/test_core.py::test_example_copy_rejects_destinations_inside_the_installed_example_catalog PASSED [ 43%]
cli_anything/xcide/tests/test_core.py::test_example_list_reports_corrupt_native_projects PASSED [ 44%]
cli_anything/xcide/tests/test_core.py::test_layout_inspector_supports_xcgui_multi_root_and_resource_references PASSED [ 45%]
cli_anything/xcide/tests/test_core.py::test_layout_inspector_verifies_ui_zip_and_rejects_escaping_paths PASSED [ 45%]
cli_anything/xcide/tests/test_core.py::test_project_doctor_finds_missing_entries_modules_and_broken_layout PASSED [ 46%]
cli_anything/xcide/tests/test_core.py::test_session_initialization_undo_redo_audit_and_history PASSED [ 46%]
cli_anything/xcide/tests/test_core.py::test_session_invalid_content_and_concurrent_revision PASSED [ 47%]
cli_anything/xcide/tests/test_core.py::test_session_limit_and_malformed_history_are_bounded PASSED [ 47%]
cli_anything/xcide/tests/test_core.py::test_session_save_protects_json_from_simultaneous_readers PASSED [ 48%]
cli_anything/xcide/tests/test_core.py::test_local_path_rules_match_project_and_module_roots_and_reject_prefix_escapes PASSED [ 48%]
cli_anything/xcide/tests/test_core.py::test_local_editor_preserves_utf8_bom_crlf_and_round_trips PASSED [ 49%]
cli_anything/xcide/tests/test_core.py::test_local_editor_detects_gb18030_and_rejects_binary PASSED [ 49%]
cli_anything/xcide/tests/test_core.py::test_module_library_list_search_and_project_references PASSED [ 50%]
cli_anything/xcide/tests/test_core.py::test_module_dependency_plan_rejects_cycles_missing_and_ambiguous_edges PASSED [ 50%]
cli_anything/xcide/tests/test_core.py::test_cli_module_dependencies_and_add_with_dependency_plan PASSED [ 51%]
cli_anything/xcide/tests/test_core.py::test_native_pe_reader_accepts_x64_and_refuses_invalid_headers PASSED [ 51%]
cli_anything/xcide/tests/test_core.py::test_native_pe_reader_reports_other_machine_types[332-x86] PASSED [ 52%]
cli_anything/xcide/tests/test_core.py::test_native_pe_reader_reports_other_machine_types[43620-ARM64] PASSED [ 52%]
cli_anything/xcide/tests/test_core.py::test_build_backend_needs_only_the_native_ide PASSED [ 53%]
cli_anything/xcide/tests/test_core.py::test_build_artifact_discovery_includes_native_release64_output PASSED [ 53%]
cli_anything/xcide/tests/test_core.py::test_preview_read_only_latest_does_not_need_or_call_ide PASSED [ 54%]
cli_anything/xcide/tests/test_core.py::test_cli_json_errors_are_valid_and_return_nonzero PASSED [ 54%]
cli_anything/xcide/tests/test_core.py::test_cli_dry_run_cannot_save_session_or_touch_project PASSED [ 55%]
cli_anything/xcide/tests/test_core.py::test_cli_new_project_selects_session_and_persists_undo PASSED [ 56%]
cli_anything/xcide/tests/test_core.py::test_cli_example_copy_dry_run_has_no_filesystem_or_session_side_effects PASSED [ 56%]
cli_anything/xcide/tests/test_core.py::test_project_updates_serialize_across_processes[project.set_project_debug_item(target, 'watches', 'parallel_watch')] PASSED [ 57%]
cli_anything/xcide/tests/test_core.py::test_project_updates_serialize_across_processes[modules.remove_module(target, 'module_base.h')] PASSED [ 57%]
cli_anything/xcide/tests/test_core.py::test_project_update_refuses_external_change_before_commit PASSED [ 58%]
cli_anything/xcide/tests/test_core.py::test_editor_preserves_utf16_bom_and_crlf[utf-16-le-\xff\xfe] PASSED [ 58%]
cli_anything/xcide/tests/test_core.py::test_editor_preserves_utf16_bom_and_crlf[utf-16-be-\xfe\xff] PASSED [ 59%]
cli_anything/xcide/tests/test_core.py::test_template_copy_rejects_source_descendants_before_creating_directories PASSED [ 59%]
cli_anything/xcide/tests/test_core.py::test_remove_stale_breakpoint_and_bookmark[False] PASSED [ 60%]
cli_anything/xcide/tests/test_core.py::test_remove_stale_breakpoint_and_bookmark[True] PASSED [ 60%]
cli_anything/xcide/tests/test_core.py::test_cli_completed_write_reports_session_warning_without_retry[conflict] PASSED [ 61%]
cli_anything/xcide/tests/test_core.py::test_cli_completed_write_reports_session_warning_without_retry[disk] PASSED [ 61%]
cli_anything/xcide/tests/test_core.py::test_cli_session_only_save_failure_does_not_report_success PASSED [ 62%]
cli_anything/xcide/tests/test_core.py::test_repl_does_not_retry_failed_postcommit_session_save PASSED [ 62%]
cli_anything/xcide/tests/test_core.py::test_session_write_failure_keeps_revision_retryable PASSED [ 63%]
cli_anything/xcide/tests/test_core.py::test_preview_cache_and_latest_are_project_scoped[False] PASSED [ 63%]
cli_anything/xcide/tests/test_core.py::test_preview_cache_and_latest_are_project_scoped[True] PASSED [ 64%]
cli_anything/xcide/tests/test_core.py::test_interface_checks_long_comments_known_paths_and_utf16 PASSED [ 64%]
cli_anything/xcide/tests/test_core.py::test_interface_include_generated_applies_to_layouts_resources_and_zip PASSED [ 65%]
cli_anything/xcide/tests/test_core.py::test_build_requires_configured_stable_output[unrelated] PASSED [ 65%]
cli_anything/xcide/tests/test_core.py::test_build_requires_configured_stable_output[timeout] PASSED [ 66%]
cli_anything/xcide/tests/test_core.py::test_build_requires_configured_stable_output[same-size-write] PASSED [ 67%]
cli_anything/xcide/tests/test_core.py::test_build_requires_configured_stable_output[custom-output] PASSED [ 67%]
cli_anything/xcide/tests/test_core.py::test_build_requires_configured_stable_output[exited] PASSED [ 68%]
cli_anything/xcide/tests/test_core.py::test_build_rejects_unresolvable_output_before_launch[dll] PASSED [ 68%]
cli_anything/xcide/tests/test_core.py::test_build_rejects_unresolvable_output_before_launch[macro] PASSED [ 69%]
cli_anything/xcide/tests/test_core.py::test_rendered_html_links_survive_relocation PASSED [ 69%]
cli_anything/xcide/tests/test_core.py::test_native_compiler_diagnostics_require_positive_evidence PASSED [ 70%]
cli_anything/xcide/tests/test_core.py::test_native_compiler_errors_survive_zero_ide_summary PASSED [ 70%]
cli_anything/xcide/tests/test_core.py::test_native_compiler_xc_positions_and_missing_detail PASSED [ 71%]
cli_anything/xcide/tests/test_core.py::test_runtime_scenario_rejects_unsafe_steps[step0] PASSED [ 71%]
cli_anything/xcide/tests/test_core.py::test_runtime_scenario_rejects_unsafe_steps[step1] PASSED [ 72%]
cli_anything/xcide/tests/test_core.py::test_runtime_scenario_rejects_unsafe_steps[step2] PASSED [ 72%]
cli_anything/xcide/tests/test_core.py::test_runtime_scenario_rejects_unsafe_steps[step3] PASSED [ 73%]
cli_anything/xcide/tests/test_core.py::test_runtime_scenario_rejects_unsafe_steps[step4] PASSED [ 73%]
cli_anything/xcide/tests/test_core.py::test_runtime_scenario_rejects_unsafe_steps[step5] PASSED [ 74%]
cli_anything/xcide/tests/test_core.py::test_runtime_scenario_rejects_unsafe_steps[step6] PASSED [ 74%]
cli_anything/xcide/tests/test_core.py::test_runtime_scenario_rejects_unsafe_steps[step7] PASSED [ 75%]
cli_anything/xcide/tests/test_core.py::test_runtime_scenario_rejects_unsafe_steps[step8] PASSED [ 75%]
cli_anything/xcide/tests/test_core.py::test_runtime_scenario_rejects_unsafe_steps[step9] PASSED [ 76%]
cli_anything/xcide/tests/test_core.py::test_runtime_scenario_rejects_unsafe_steps[step10] PASSED [ 76%]
cli_anything/xcide/tests/test_core.py::test_runtime_scenario_rejects_unsafe_steps[step11] PASSED [ 77%]
cli_anything/xcide/tests/test_core.py::test_runtime_scenario_requires_assertions_and_exit PASSED [ 78%]
cli_anything/xcide/tests/test_core.py::test_runtime_invalid_scenario_has_no_side_effects PASSED [ 78%]
cli_anything/xcide/tests/test_core.py::test_runtime_background_input_bounds_identity_and_utf16 PASSED [ 79%]
cli_anything/xcide/tests/test_core.py::test_f7_targets_main_window_and_rejects_ambiguity PASSED [ 79%]
cli_anything/xcide/tests/test_core.py::test_background_build_preserves_dialog_and_cleanup_failure PASSED [ 80%]
cli_anything/xcide/tests/test_core.py::test_runtime_protocol_shape_and_no_foreground_fallback PASSED [ 80%]
cli_anything/xcide/tests/test_core.py::test_output_bridge_rejects_wrong_identity_and_overflow PASSED [ 81%]
cli_anything/xcide/tests/test_full_e2e.py::TestCLISubprocess::test_editor_commit_survives_session_save_failure_and_preserves_utf16 PASSED [ 81%]
cli_anything/xcide/tests/test_full_e2e.py::TestCLISubprocess::test_stale_debug_entries_can_be_removed_through_installed_commands PASSED [ 82%]
cli_anything/xcide/tests/test_full_e2e.py::TestCLISubprocess::test_installed_help PASSED [ 82%]
cli_anything/xcide/tests/test_full_e2e.py::TestCLISubprocess::test_installed_ui_archive_exports_exact_member_without_overwrite PASSED [ 83%]
cli_anything/xcide/tests/test_full_e2e.py::TestCLISubprocess::test_installed_named_resource_catalog_and_packed_fonts PASSED [ 83%]
cli_anything/xcide/tests/test_full_e2e.py::TestCLISubprocess::test_installed_layout_nodes_on_disk_and_in_archive PASSED [ 84%]
cli_anything/xcide/tests/test_full_e2e.py::TestCLISubprocess::test_installed_reference_catalogs_are_readonly_and_have_native_provenance PASSED [ 84%]
cli_anything/xcide/tests/test_full_e2e.py::TestCLISubprocess::test_installed_native_snippet_can_feed_editor_workflow PASSED [ 85%]
cli_anything/xcide/tests/test_full_e2e.py::TestCLISubprocess::test_installed_reference_errors_and_partial_catalog_discovery PASSED [ 85%]
cli_anything/xcide/tests/test_full_e2e.py::TestCLISubprocess::test_real_editor_themes_can_be_inspected_without_mcp PASSED [ 86%]
cli_anything/xcide/tests/test_full_e2e.py::TestCLISubprocess::test_create_inspect_and_reject_collision PASSED [ 86%]
cli_anything/xcide/tests/test_full_e2e.py::TestCLISubprocess::test_project_configuration_commands_switch_without_mcp PASSED [ 87%]
cli_anything/xcide/tests/test_full_e2e.py::TestCLISubprocess::test_project_sources_and_breakpoints_commands_without_mcp PASSED [ 87%]
cli_anything/xcide/tests/test_full_e2e.py::TestCLISubprocess::test_installed_ui_template_can_be_found_inspected_and_copied PASSED [ 88%]
cli_anything/xcide/tests/test_full_e2e.py::TestCLISubprocess::test_native_template_ui_and_project_doctor_commands_need_no_plugin PASSED [ 89%]
cli_anything/xcide/tests/test_full_e2e.py::TestCLISubprocess::test_local_example_library_can_inspect_and_derive_a_native_project PASSED [ 89%]
cli_anything/xcide/tests/test_full_e2e.py::TestCLISubprocess::test_project_listing_and_read_only_latest PASSED [ 90%]
cli_anything/xcide/tests/test_full_e2e.py::TestCLISubprocess::test_local_editor_and_module_commands_need_no_plugin PASSED [ 90%]
cli_anything/xcide/tests/test_full_e2e.py::TestCLISubprocess::test_dry_run_has_no_side_effects_or_ide_calls PASSED [ 91%]
cli_anything/xcide/tests/test_full_e2e.py::TestCLISubprocess::test_selected_session_round_trip_and_undo_redo PASSED [ 91%]
cli_anything/xcide/tests/test_full_e2e.py::TestRealIDEAcceptance::test_blank_window_template_compiles_to_fresh_amd64[False] PASSED [ 92%]
cli_anything/xcide/tests/test_full_e2e.py::TestRealIDEAcceptance::test_blank_window_template_compiles_to_fresh_amd64[True] PASSED [ 92%]
cli_anything/xcide/tests/test_full_e2e.py::TestRuntimeAutomation::test_debug_unicode_ansi_channels_and_expected_exit[x64] PASSED [ 93%]
cli_anything/xcide/tests/test_full_e2e.py::TestRuntimeAutomation::test_debug_exception_and_timeout_semantics[x64-handled] PASSED [ 93%]
cli_anything/xcide/tests/test_full_e2e.py::TestRuntimeAutomation::test_debug_exception_and_timeout_semantics[x64-crash] PASSED [ 94%]
cli_anything/xcide/tests/test_full_e2e.py::TestRuntimeAutomation::test_debug_exception_and_timeout_semantics[x64-sleep] PASSED [ 94%]
cli_anything/xcide/tests/test_full_e2e.py::TestRuntimeAutomation::test_debug_exception_and_timeout_semantics[x64-quiet] PASSED [ 95%]
cli_anything/xcide/tests/test_full_e2e.py::TestRuntimeAutomation::test_debug_unicode_ansi_channels_and_expected_exit[x86] PASSED [ 95%]
cli_anything/xcide/tests/test_full_e2e.py::TestRuntimeAutomation::test_debug_exception_and_timeout_semantics[x86-handled] PASSED [ 96%]
cli_anything/xcide/tests/test_full_e2e.py::TestRuntimeAutomation::test_debug_exception_and_timeout_semantics[x86-crash] PASSED [ 96%]
cli_anything/xcide/tests/test_full_e2e.py::TestRuntimeAutomation::test_debug_exception_and_timeout_semantics[x86-sleep] PASSED [ 97%]
cli_anything/xcide/tests/test_full_e2e.py::TestRuntimeAutomation::test_debug_exception_and_timeout_semantics[x86-quiet] PASSED [ 97%]
cli_anything/xcide/tests/test_full_e2e.py::TestRuntimeAutomation::test_runtime_dry_run_and_invalid_scenario_do_not_launch PASSED [ 98%]
cli_anything/xcide/tests/test_full_e2e.py::TestRuntimeAutomation::test_background_adapter_modes_and_input_state[x64] PASSED [ 98%]
cli_anything/xcide/tests/test_full_e2e.py::TestRuntimeAutomation::test_background_adapter_modes_and_input_state[x86] PASSED [ 99%]
cli_anything/xcide/tests/test_full_e2e.py::TestRuntimeAutomation::test_native_xc_diagnostics_and_background_workflow PASSED [100%]

======================= 191 passed in 86.94s (0:01:26) ========================
```

## 独立仓库清理修复完整输出（2026-11-25）

```text
============================= test session starts =============================
platform win32 -- Python 3.14.8, pytest-9.1.1, pluggy-1.7.0 -- E:\AIWork\Codex\cli-anything-xcide\.venv\Scripts\python.exe
rootdir: E:\AIWork\Codex\cli-anything-xcide\xcide\agent-harness
plugins: anyio-4.15.1, platformdirs-4.13.5
collecting ... collected 195 items

xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_archive_roundtrip_normalizes_backslashes_without_losing_original PASSED [  0%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_archive_unsafe_members_are_reported_and_not_exported[../escape] PASSED [  1%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_archive_unsafe_members_are_reported_and_not_exported[/rooted] PASSED [  1%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_archive_unsafe_members_are_reported_and_not_exported[C:/drive] PASSED [  2%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_archive_unsafe_members_are_reported_and_not_exported[dir/../../escape] PASSED [  2%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_archive_unsafe_members_are_reported_and_not_exported[a:stream] PASSED [  3%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_archive_unsafe_members_are_reported_and_not_exported[CON.txt] PASSED [  3%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_archive_unsafe_members_are_reported_and_not_exported[dir/name.] PASSED [  4%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_archive_unsafe_members_are_reported_and_not_exported[dir/name ] PASSED [  4%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_archive_unsafe_members_are_reported_and_not_exported[dir//name] PASSED [  5%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_archive_unsafe_members_are_reported_and_not_exported[bad?.txt] PASSED [  5%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_archive_member_integrity_and_ambiguity[case-collision] PASSED [  6%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_archive_member_integrity_and_ambiguity[slash-collision] PASSED [  6%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_archive_member_integrity_and_ambiguity[symlink] PASSED [  7%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_archive_member_integrity_and_ambiguity[encrypted] PASSED [  7%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_archive_member_integrity_and_ambiguity[bad-crc] PASSED [  8%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_archive_member_integrity_and_ambiguity[compression] PASSED [  8%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_archive_read_limits_and_atomic_export_collision PASSED [  9%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_archive_export_refuses_installation_and_outside_input PASSED [  9%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_resource_queries_preserve_unknown_sections_and_resolve_relative_assets[False] PASSED [ 10%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_resource_queries_preserve_unknown_sections_and_resolve_relative_assets[True] PASSED [ 10%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_resource_folders_are_recursive_categories_not_resource_names[False] PASSED [ 11%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_resource_folders_are_recursive_categories_not_resource_names[True] PASSED [ 11%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_layout_queries_preserve_identity_bindings_and_designer_fields[False] PASSED [ 12%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_layout_queries_preserve_identity_bindings_and_designer_fields[True] PASSED [ 12%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_layout_rejects_unknown_and_malformed_input[<head/><windowUI/><windowUI/>] PASSED [ 13%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_layout_rejects_unknown_and_malformed_input[<heiyue/>] PASSED [ 13%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_layout_rejects_unknown_and_malformed_input[<windowUI>] PASSED [ 14%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_layout_rejects_unknown_and_malformed_input[<!DOCTYPE x [<!ENTITY a "b">]><windowUI/>] PASSED [ 14%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_layout_object_root_and_depth_limits PASSED [ 15%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_reference_sources_and_literal_content PASSED [ 15%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_reference_completion_preserves_raw_line_numbers_and_duplicate_declarations PASSED [ 16%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_reference_hierarchy_and_pagination_do_not_invent_inheritance PASSED [ 16%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_reference_rejects_malformed_source_without_silently_dropping_items[snippets-{}] PASSED [ 17%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_reference_rejects_malformed_source_without_silently_dropping_items[snippets-[{"name":"broken","comment":"","data":null}]] PASSED [ 17%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_reference_rejects_malformed_source_without_silently_dropping_items[language-{"type":{},"other":"text"}] PASSED [ 18%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_reference_rejects_malformed_source_without_silently_dropping_items[language-{"same":"one","same":"two"}] PASSED [ 18%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_reference_rejects_malformed_source_without_silently_dropping_items[properties-{"elementUI":{"self":[["edit","true","id"]]}}] PASSED [ 19%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_reference_rejects_malformed_source_without_silently_dropping_items[properties-{"elementUI":{"self":[["edit","true","id","ID","",["invalid"]]]}}] PASSED [ 20%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_reference_rejects_malformed_source_without_silently_dropping_items[events-<wrong/>] PASSED [ 20%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_reference_rejects_malformed_source_without_silently_dropping_items[events-<events><buttonUI><item event="CLICK"/></buttonUI></events>] PASSED [ 21%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_reference_rejects_malformed_source_without_silently_dropping_items[events-<!DOCTYPE events [<!ENTITY e "hello">]><events/>] PASSED [ 21%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_reference_rejects_malformed_source_without_silently_dropping_items[controls-<buttonUI name="one"/><buttonUI name="two"/>] PASSED [ 22%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_reference_rejects_malformed_source_without_silently_dropping_items[custom-objects-<customObject><buttonUI/></customObject>] PASSED [ 22%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_reference_rejects_malformed_source_without_silently_dropping_items[build-options-{"runtime": {"xml_label":"runtimeLibrary","uiType":"comboBox","flag":"cl","list":[]}}] PASSED [ 23%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_reference_limits_missing_source_and_utf16 PASSED [ 23%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_reference_ids_scope_and_bounds_are_validated PASSED [ 24%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_reference_refuses_source_link_outside_installation PASSED [ 24%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_new_project_preserves_native_modules_and_lists_existing_entrypoint PASSED [ 25%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_project_uses_selected_platform_from_installed_template[x64] PASSED [ 25%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_project_uses_selected_platform_from_installed_template[x86] PASSED [ 26%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_project_configuration_tracks_installed_ide_toolset_and_sdk PASSED [ 26%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_project_template_toolchain_defaults_survive_when_ide_config_is_unavailable PASSED [ 27%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_invalid_windows_project_names_are_rejected[] PASSED [ 27%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_invalid_windows_project_names_are_rejected[..] PASSED [ 28%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_invalid_windows_project_names_are_rejected[a/b] PASSED [ 28%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_invalid_windows_project_names_are_rejected[a\\b] PASSED [ 29%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_invalid_windows_project_names_are_rejected[foo.] PASSED [ 29%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_invalid_windows_project_names_are_rejected[CON] PASSED [ 30%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_invalid_windows_project_names_are_rejected[com3] PASSED [ 30%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_invalid_windows_project_names_are_rejected[bad:name] PASSED [ 31%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_invalid_windows_project_names_are_rejected[ x ] PASSED [ 31%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_project_creation_refuses_destination_and_does_not_replace_file PASSED [ 32%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_project_xml_and_source_entry_errors_are_explicit PASSED [ 32%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_activate_source_is_safe_idempotent_and_retains_modules PASSED [ 33%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_project_discovery_skips_compiler_output PASSED [ 33%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_project_configuration_inventory_and_atomic_switch_preserve_other_fields PASSED [ 34%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_project_configuration_rejects_missing_platform_without_partial_update PASSED [ 34%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_project_source_inventory_add_remove_and_path_safety PASSED [ 35%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_project_breakpoint_crud_bounds_idempotency_and_diagnostics PASSED [ 35%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_ui_template_catalog_metadata_filter_payload_and_copy PASSED [ 36%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_ui_template_search_skips_malformed_metadata_and_bad_payload PASSED [ 36%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_theme_catalog_extracts_native_editor_configuration_without_writing PASSED [ 37%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_project_watch_and_bookmark_metadata_crud_preserves_native_shapes PASSED [ 37%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_ide_template_catalog_finds_native_xuan_projects PASSED [ 38%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_create_project_from_template_preserves_native_configuration_and_retargets_name PASSED [ 38%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_create_project_from_template_can_override_existing_platform_and_config PASSED [ 39%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_example_library_indexes_searches_and_describes_native_projects PASSED [ 40%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_example_lookup_rejects_non_relative_or_non_project_ids[] PASSED [ 40%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_example_lookup_rejects_non_relative_or_non_project_ids[../outside.xcproj] PASSED [ 41%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_example_lookup_rejects_non_relative_or_non_project_ids[C:/outside.xcproj] PASSED [ 41%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_example_lookup_rejects_non_relative_or_non_project_ids[sample.txt] PASSED [ 42%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_example_copy_retargets_project_and_preserves_native_files_without_build_outputs PASSED [ 42%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_example_copy_rejects_destinations_inside_the_installed_example_catalog PASSED [ 43%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_example_list_reports_corrupt_native_projects PASSED [ 43%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_layout_inspector_supports_xcgui_multi_root_and_resource_references PASSED [ 44%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_layout_inspector_verifies_ui_zip_and_rejects_escaping_paths PASSED [ 44%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_project_doctor_finds_missing_entries_modules_and_broken_layout PASSED [ 45%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_session_initialization_undo_redo_audit_and_history PASSED [ 45%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_session_invalid_content_and_concurrent_revision PASSED [ 46%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_session_limit_and_malformed_history_are_bounded PASSED [ 46%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_session_save_protects_json_from_simultaneous_readers PASSED [ 47%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_local_path_rules_match_project_and_module_roots_and_reject_prefix_escapes PASSED [ 47%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_local_editor_preserves_utf8_bom_crlf_and_round_trips PASSED [ 48%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_local_editor_detects_gb18030_and_rejects_binary PASSED [ 48%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_module_library_list_search_and_project_references PASSED [ 49%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_module_dependency_plan_rejects_cycles_missing_and_ambiguous_edges PASSED [ 49%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_cli_module_dependencies_and_add_with_dependency_plan PASSED [ 50%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_native_pe_reader_accepts_x64_and_refuses_invalid_headers PASSED [ 50%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_native_pe_reader_reports_other_machine_types[332-x86] PASSED [ 51%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_native_pe_reader_reports_other_machine_types[43620-ARM64] PASSED [ 51%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_build_backend_needs_only_the_native_ide PASSED [ 52%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_build_artifact_discovery_includes_native_release64_output PASSED [ 52%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_preview_read_only_latest_does_not_need_or_call_ide PASSED [ 53%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_cli_json_errors_are_valid_and_return_nonzero PASSED [ 53%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_cli_dry_run_cannot_save_session_or_touch_project PASSED [ 54%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_cli_new_project_selects_session_and_persists_undo PASSED [ 54%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_cli_example_copy_dry_run_has_no_filesystem_or_session_side_effects PASSED [ 55%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_project_updates_serialize_across_processes[project.set_project_debug_item(target, 'watches', 'parallel_watch')] PASSED [ 55%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_project_updates_serialize_across_processes[modules.remove_module(target, 'module_base.h')] PASSED [ 56%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_project_update_refuses_external_change_before_commit PASSED [ 56%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_editor_preserves_utf16_bom_and_crlf[utf-16-le-\xff\xfe] PASSED [ 57%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_editor_preserves_utf16_bom_and_crlf[utf-16-be-\xfe\xff] PASSED [ 57%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_template_copy_rejects_source_descendants_before_creating_directories PASSED [ 58%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_remove_stale_breakpoint_and_bookmark[False] PASSED [ 58%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_remove_stale_breakpoint_and_bookmark[True] PASSED [ 59%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_cli_completed_write_reports_session_warning_without_retry[conflict] PASSED [ 60%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_cli_completed_write_reports_session_warning_without_retry[disk] PASSED [ 60%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_cli_session_only_save_failure_does_not_report_success PASSED [ 61%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_repl_does_not_retry_failed_postcommit_session_save PASSED [ 61%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_session_write_failure_keeps_revision_retryable PASSED [ 62%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_preview_cache_and_latest_are_project_scoped[False] PASSED [ 62%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_preview_cache_and_latest_are_project_scoped[True] PASSED [ 63%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_interface_checks_long_comments_known_paths_and_utf16 PASSED [ 63%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_interface_include_generated_applies_to_layouts_resources_and_zip PASSED [ 64%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_build_requires_configured_stable_output[unrelated] PASSED [ 64%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_build_requires_configured_stable_output[timeout] PASSED [ 65%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_build_requires_configured_stable_output[same-size-write] PASSED [ 65%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_build_requires_configured_stable_output[custom-output] PASSED [ 66%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_build_requires_configured_stable_output[exited] PASSED [ 66%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_build_rejects_unresolvable_output_before_launch[dll] PASSED [ 67%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_build_rejects_unresolvable_output_before_launch[macro] PASSED [ 67%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_rendered_html_links_survive_relocation PASSED [ 68%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_native_compiler_diagnostics_require_positive_evidence PASSED [ 68%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_native_compiler_errors_survive_zero_ide_summary PASSED [ 69%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_native_compiler_xc_positions_and_missing_detail PASSED [ 69%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_runtime_scenario_rejects_unsafe_steps[step0] PASSED [ 70%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_runtime_scenario_rejects_unsafe_steps[step1] PASSED [ 70%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_runtime_scenario_rejects_unsafe_steps[step2] PASSED [ 71%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_runtime_scenario_rejects_unsafe_steps[step3] PASSED [ 71%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_runtime_scenario_rejects_unsafe_steps[step4] PASSED [ 72%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_runtime_scenario_rejects_unsafe_steps[step5] PASSED [ 72%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_runtime_scenario_rejects_unsafe_steps[step6] PASSED [ 73%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_runtime_scenario_rejects_unsafe_steps[step7] PASSED [ 73%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_runtime_scenario_rejects_unsafe_steps[step8] PASSED [ 74%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_runtime_scenario_rejects_unsafe_steps[step9] PASSED [ 74%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_runtime_scenario_rejects_unsafe_steps[step10] PASSED [ 75%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_runtime_scenario_rejects_unsafe_steps[step11] PASSED [ 75%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_runtime_scenario_requires_assertions_and_exit PASSED [ 76%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_runtime_invalid_scenario_has_no_side_effects PASSED [ 76%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_runtime_background_input_bounds_identity_and_utf16 PASSED [ 77%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_f7_targets_main_window_and_rejects_ambiguity PASSED [ 77%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_background_build_preserves_dialog_and_cleanup_failure PASSED [ 78%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_runtime_protocol_shape_and_no_foreground_fallback PASSED [ 78%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_output_bridge_rejects_wrong_identity_and_overflow PASSED [ 79%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_debug_cleanup_waits_for_event_and_process_signal[0.1-1.4] PASSED [ 80%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_debug_cleanup_waits_for_event_and_process_signal[5.2-0.2] PASSED [ 80%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_debug_cleanup_deadline_is_shared_and_errors_are_preserved PASSED [ 81%]
xcide\agent-harness\cli_anything\xcide\tests\test_core.py::test_owned_process_wait_preserves_api_failures PASSED [ 81%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestCLISubprocess::test_editor_commit_survives_session_save_failure_and_preserves_utf16 PASSED [ 82%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestCLISubprocess::test_stale_debug_entries_can_be_removed_through_installed_commands PASSED [ 82%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestCLISubprocess::test_installed_help PASSED [ 83%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestCLISubprocess::test_installed_ui_archive_exports_exact_member_without_overwrite PASSED [ 83%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestCLISubprocess::test_installed_named_resource_catalog_and_packed_fonts PASSED [ 84%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestCLISubprocess::test_installed_layout_nodes_on_disk_and_in_archive PASSED [ 84%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestCLISubprocess::test_installed_reference_catalogs_are_readonly_and_have_native_provenance PASSED [ 85%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestCLISubprocess::test_installed_native_snippet_can_feed_editor_workflow PASSED [ 85%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestCLISubprocess::test_installed_reference_errors_and_partial_catalog_discovery PASSED [ 86%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestCLISubprocess::test_real_editor_themes_can_be_inspected_without_mcp PASSED [ 86%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestCLISubprocess::test_create_inspect_and_reject_collision PASSED [ 87%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestCLISubprocess::test_project_configuration_commands_switch_without_mcp PASSED [ 87%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestCLISubprocess::test_project_sources_and_breakpoints_commands_without_mcp PASSED [ 88%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestCLISubprocess::test_installed_ui_template_can_be_found_inspected_and_copied PASSED [ 88%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestCLISubprocess::test_native_template_ui_and_project_doctor_commands_need_no_plugin PASSED [ 89%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestCLISubprocess::test_local_example_library_can_inspect_and_derive_a_native_project PASSED [ 89%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestCLISubprocess::test_project_listing_and_read_only_latest PASSED [ 90%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestCLISubprocess::test_local_editor_and_module_commands_need_no_plugin PASSED [ 90%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestCLISubprocess::test_dry_run_has_no_side_effects_or_ide_calls PASSED [ 91%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestCLISubprocess::test_selected_session_round_trip_and_undo_redo PASSED [ 91%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestRealIDEAcceptance::test_blank_window_template_compiles_to_fresh_amd64[False] PASSED [ 92%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestRealIDEAcceptance::test_blank_window_template_compiles_to_fresh_amd64[True] PASSED [ 92%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestRuntimeAutomation::test_debug_unicode_ansi_channels_and_expected_exit[x64] PASSED [ 93%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestRuntimeAutomation::test_debug_exception_and_timeout_semantics[x64-handled] PASSED [ 93%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestRuntimeAutomation::test_debug_exception_and_timeout_semantics[x64-crash] PASSED [ 94%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestRuntimeAutomation::test_debug_exception_and_timeout_semantics[x64-sleep] PASSED [ 94%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestRuntimeAutomation::test_debug_exception_and_timeout_semantics[x64-quiet] PASSED [ 95%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestRuntimeAutomation::test_debug_unicode_ansi_channels_and_expected_exit[x86] PASSED [ 95%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestRuntimeAutomation::test_debug_exception_and_timeout_semantics[x86-handled] PASSED [ 96%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestRuntimeAutomation::test_debug_exception_and_timeout_semantics[x86-crash] PASSED [ 96%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestRuntimeAutomation::test_debug_exception_and_timeout_semantics[x86-sleep] PASSED [ 97%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestRuntimeAutomation::test_debug_exception_and_timeout_semantics[x86-quiet] PASSED [ 97%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestRuntimeAutomation::test_runtime_dry_run_and_invalid_scenario_do_not_launch PASSED [ 98%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestRuntimeAutomation::test_background_adapter_modes_and_input_state[x64] PASSED [ 98%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestRuntimeAutomation::test_background_adapter_modes_and_input_state[x86] PASSED [ 99%]
xcide\agent-harness\cli_anything\xcide\tests\test_full_e2e.py::TestRuntimeAutomation::test_native_xc_diagnostics_and_background_workflow PASSED [100%]

======================= 195 passed in 93.63s (0:01:33) ========================
```
