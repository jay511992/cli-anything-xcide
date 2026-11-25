# 炫彩 IDE 本地命令行：20 轮功能挖掘报告

**范围：**本机 `I:\xcide` 安装包、`data/` 工程/示例/模块/模板/主题，以及无需 MCP 插件的 `cli-anything-xcide` CLI。  
**执行结果：**20 轮 CLI 命令全部完成；正式安装配置和已检查示例 `.xcproj` 的 SHA-256 在扫描前后保持一致；皮肤模板副本只写入临时目录，随后已清除。  
**完整测试：**加入主题读取命令后的已安装 CLI 全量回归为 73/73 通过。

> 命令和发现都使用本机已安装 CLI 或 XML/文件枚举取得。报告只覆盖静态磁盘数据；“IDE 内存在什么”不代表能通过无 MCP API 读取运行中 IDE 内存状态。

## 20 轮挖掘记录

| 轮次 | 检查对象 | 实测发现 | 能力/现存边界 |
| --- | --- | --- | --- |
| 01 | CLI 命令面 | 安装命令公开 `build/editor/example/interface/module/preview/project/repl/session/status/ui-template/theme`。 | CLI 工作流不需要 MCP；`--help` 使用 CLI 原生文本而非 JSON。 |
| 02 | IDE 安装定位 | 默认根目录能解析为 `I:\xcide`。 | 通过默认路径或 `--ide` / `XC_IDE_ROOT` 使用本机安装。 |
| 03 | 炫语言项目模板 | `data/template/项目模板/炫语言` 下发现 17 个 `.xcproj` 模板。 | `project template list` 已提供搜索、准确 ID 和新工程实例化。 |
| 04 | 示例全文检索 | `example list 按钮` 返回 3 个工程。 | `example list/info/copy` 已覆盖本地示例发现、资源清点和安全派生。 |
| 05 | 真实示例解析 | “第一个窗口程序/窗口程序.xcproj”列出 8 个可复用工程文件和 4 个模块。 | 项目元数据/源文件清点可从磁盘复现。 |
| 06 | 工程源码登记 | 上述示例有 1 个磁盘 `.xc/.xcs` 文件、1 个 `<codeExpand>` 登记项。 | `project sources list/add/remove` 查找和维护登记；取消登记不删除源码。 |
| 07 | 调试断点 | 示例记录 1 个 `main.xc:47` 断点，但当前源码只有 46 行。 | `project breakpoints list` 把它报告为 `valid=false` / warning；新写入断点先检验源码行范围。只读盘点不自动修复。 |
| 08 | watches/bookmarks | 示例工程 watches 与 bookmarks 均为 0；模块库其他示例可查到监视表达式。 | `project debug list/watch-add/watch-remove/bookmark-add/bookmark-remove` 读写工程持久化 XML；watch 仅保存、不执行、不求值。 |
| 09 | 模块库规模 | 本地标准模块扫描发现 281 个 `module_*.h/.xc`。 | `module list/search` 已覆盖本地元数据；列表可分页/限量。 |
| 10 | 重名模块安全 | 有 6 组重名文件，其中 `module_sunnynet.h` 有 3 份。 | 依赖解析按文件身份检查歧义，不随意选其中一个写入工程。 |
| 11 | 依赖关系 | 安装命令对 `module_xcgui.h` 解析成功，依赖顺序中有 2 个模块。 | `module dependencies` 只读计划；缺失、同名和循环诊断明确返回。 |
| 12 | 工程体检 | 真正样例的 `project doctor` 得到 `errorCount=0`、`warningCount=0`。 | 这是一份工程体检结果，不是编译诊断或构建成功证明。 |
| 13 | 界面文件发现 | 同一真实样例发现 1 个布局、1 个 UI ZIP。 | `interface list` 可定位磁盘 XML 和原生 UI ZIP。 |
| 14 | 布局/资源验证 | `interface check` 返回 `ok=true`、0 条资源警告；ZIP 有效。 | 检查遵守炫彩布局 XML 多根格式；结构检查不读取 GUI 渲染结果。 |
| 15 | 皮肤目录 | 在 `data/template` 找到 5 个皮肤模板和 2 个布局模板。 | 此轮新加 `ui-template list`，标准 `template.config` 提供准确相对 ID。 |
| 16 | 皮肤细节 | “关闭按钮”皮肤有 5 个可复制文件，配置内 `common/template_object` 字段为嵌套 XML。 | 此轮新加 `ui-template info`；递归提取 name/type/objectType/path，输出实际文件清单。 |
| 17 | 素材派生 | 安装命令将 5 个关闭按钮皮肤文件复制到唯一系统临时目录。 | 此轮新加安全 `ui-template copy`；拒绝覆盖、不回写模板库，并过滤生成目录/符号链接。临时副本已清理。 |
| 18 | 代码编辑器主题 | `data/theme` 有 5 个有效 `.xctheme.config` 主题。 | 本轮新挖掘主题源码配置的字体、行距、颜色和皮肤路径。 |
| 19 | 主题皮肤解析 | 暗色主题配置报告编辑器默认字体、4 字符 Tab，皮肤文件 `style1.css` 存在。 | 新加 `theme list/info` 只读解析设置，不改用户 IDE 全局配置。 |
| 20 | 安装关键配置读取 | `data/config/config.config` 可由 `editor read` 读为 UTF-8 文本（扫描时 1,755 bytes）。 | 安装根目录允许文本检查；`editor write` 会改盘，应严格保留备份。本次仅 read。 |

## 已覆盖的无 MCP 功能

### 使用本地工程模板和示例创建项目

从 IDE 官方/用户模板新建 `.xcproj`；检索 60 个本地示例工程并检查素材；把示例派生到新目录而不覆盖安装原件；搜索本机项目模板并创建独立副本。

### 检查和维护工程 XML

读取工程配置、架构、入口源码、模块和设置；找出未登记的 `.xc/.xcs` 并补齐 `<codeExpand>`；在既有配置中切换活动配置；安全地维护断点、watches 和书签；通过 `project doctor` 汇总源码、模块和界面异常。

### 处理界面素材和模块依赖

检查 XCGUI 多根布局 XML、`resource.res` 引用及 `UI_ZIP.zip`；搜索模块头文件和 `//@` 注解；仅在依赖唯一且闭包完整时成组添加。UI 模板可读取和复制，主题可检查但不会自动切换 IDE 全局主题。

### 编写、构建和检查产物

在限定的工程/IDE 根目录读取和写入本机文本；构建可启动空插件临时 IDE 副本、向已核验窗口发 F7 并校验新 PE。构建结果只说明新产物文件身份和目标架构：目前无法读 IDE 输出窗格，所以 `compiler.errorCount` 必须为 `null`。预览基于磁盘工程和 EXE 元数据，不伪装成界面截图。

## 发现数据概况

这些数量来自对本次已安装包目录的独立枚举；部分过滤规则（是否排除 Debug、非 `module_` 工程头、全盘主题备份）会影响统计口径。

- `data/示例`：60 个有效 `.xcproj`，含 59 个 x86、1 个 x64；60 个都选择“调试版”。
- 其中 22 个示例工程登记断点，共 25 项；抽查真实旧示例可见行号过期记录。示例 `<watches>` / `<bookmarks>` 当前为空；模块库里另有示例保存 watches。
- 示例目录含 58 个 `.xc`、1 个 `.xcs`；磁盘实际源码文件 59 个，工程 `codeExpand` 登记合计 5 项。60 个项目里有 55 个没有登记子项；其余项目可能登记多个文件，不能把未登记项目数直接等同于未登记源码文件数。
- `XC-Module` 与 `XC-Module-dev` 可命令扫描的 `module_*.h/.xc` 共 281 个；其中 6 组重名、最大 3 份。模块库其余文件数和非模块辅助源另属不同范围统计。
- 模板目录找到 17 个炫语言项目模板、5 个皮肤和 2 个布局模板；另有非 template.config 资产。直接盘点 438 个文件项，早前更宽松的模板树统计约 420 项，口径不同，不能互换。
- 已安装主题目录有 5 个 `xctheme.config`，均解析到已存在的 `style1.css`/`style2.css` 本地皮肤文件。
- 示例目录有 21 个 `.xml` 和 2 个 ZIP。一个项目模板 UI ZIP 共 2 项且内含 1 个 XML 布局，另一例 CSS ZIP 为 31 项、没有 XML 布局。ZIP CRC 均通过；XML 多根结构不可直接按标准单根 XML 解释为坏文件。
- `project doctor`/`interface check` 报告只针对抽查的一个可复现项目，不代表 60 个示例全部无错误。

## 后续可挖掘方向

| 候选 | 当前证据 | 实施边界 |
| --- | --- | --- |
| 安装主题的切换预演 | 主配置文件保存 `<theme name>`。 | 可以规划哪个设置会变；涉及修改用户全局配置之前必须设计备份/回滚。当前 CLI 只提供只读主题检查。 |
| `.xcproj` 编译配置输出目录/宏选项清单 | project XML 的 vc/setting 具有嵌套配置数据。 | 可增只读矩阵扫描和过滤；不要用模板外字段推断通用写行为。 |
| 示例索引数据库与格式诊断汇总 | 示例中存在无效断点、未登记源码和已生成二进制。 | 先逐项目只读统计并标明损坏；仅复制到隔离目录测试自动修复。 |
| 资源包成员报告/解包 | `UI_ZIP.zip` 真实包含布局/资源；CRC 可验证。 | 可安全列出与选定条目解包；拒绝路径穿越且不擅自部署。 |
| 皮肤、布局到工程的最小导入规划 | 皮肤 `template.config` 指明资源路径/objectType。 | 可先输出拷贝计划和登记/源码关联提示；不要宣称只复制素材就已经部署可运行 UI。 |
| GUI 日志能力 | build 能启动无插件 IDE，但错误窗格目前不可通过本地接口读取。 | 若未来确认文件日志路径/格式，可增加日志读取；当前继续报告 error count 未知。 |

## 验证过程记录

- 主题功能加入后重新运行已安装 CLI 全套测试：73/73 通过；详情见 `tests/TEST.md`。
- 20 轮使用已安装 `cli-anything-xcide.exe` 调用真实数据，全部返回预期输出。所有子进程清除了已有 `XC_MCP_*` 环境变量。
- 源码行 47 的旧断点是坏数据实测，保留且报告为 warning；此示例没有被写入。
- 在临时目录测试 UI 皮肤安全复制并清理；IDE 正式配置 `config.config` 和抽样断点工程 `.xcproj` 的扫描前后 SHA-256 均相同。
- 本报告列出的 “errorCount=0” 只属于 `project doctor` 静态工程体检结果。无 MCP 构建仍明确将编译器 `errorCount` 视为未知，不可由目标文件倒推为 0。
