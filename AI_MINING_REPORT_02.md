# 炫彩 IDE CLI：第二批 20 轮功能挖掘

本批针对 `I:\xcide` 完成 20 轮具体探测，补上 10 类原生参考数据的自动化查询。新增命令为 `reference sources`、`reference search` 和 `reference show`；其他 10 轮记录了可继续开发的方向及尚未确认的语义，没有将它们算作已实现功能。

全部探测的来源、命令、数据摘要和前后哈希见 [机器可读证据](AI_MINING_EVIDENCE_02.json)。探测读取的 64 个安装文件 SHA-256 前后一致。调用手册见 [AI_CALLING.md](AI_CALLING.md) 或 [HTML 阅读版](AI_CALLING.html)；本报告也有 [HTML 阅读版](AI_MINING_REPORT_02.html)。

## 本轮新增的可用能力

`reference` 提供按词搜索、准确 ID 读取和分页，保留来源文件及 SHA-256。数据来自本机安装版本；不需要 MCP、不启动 IDE，不改写安装配置。使用全局 `--dry-run` 还会禁止保存 CLI 会话。

| 目录 KIND | 本机条目数 | AI 可直接使用的结果 |
| --- | --- | --- |
| `snippets` | 29 | 条件、循环、类、函数等原生片段，含换行和占位内容。 |
| `language` | 57 | 类型、关键字和编译指令的本地帮助。 |
| `controls` | 32 | XML 控件标签与中文名称。 |
| `properties` | 300 | 50 个作用域中的属性行，26 行带候选值；共有 218 个不同属性名。 |
| `property-help` | 113 | 独立属性说明，包括没有对应属性行的 4 条帮助。 |
| `events` | 128 | 20 个原生作用域中的事件名称、回调声明模板和说明。 |
| `custom-objects` | 14 | 带子控件的组合片段及其属性、节点数。 |
| `build-options` | 15 | 编译器 UI 标签、XML 字段、候选参数和原生默认配置。 |
| `functions` | 1375 | IDE 函数自动补全原始行及行号。 |
| `completion-tokens` | 1766 | 非空常量/补全词行；原始文件为 1778 行，空行不作为条目。 |

这些数量是当前安装的数据记录数，包含属性、帮助和补全词，不代表新增了同等数量的运行时 API。

```powershell
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference sources
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference search snippets '如果'
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference search properties buttonType --scope 'elementUI/buttonUI'
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference show events 'elementUI/buttonUI/XE_BNCLICK'
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference show build-options runtimeLibrary
cli-anything-xcide --json --dry-run --ide 'I:\xcide' reference search functions XBtn_
```

## 20 轮探测与结论

以下路径均相对于 `I:\xcide`。前 10 轮经已安装命令验证；后 10 轮是原生文件检查，结果和未实现部分分别列明。

| 轮次 | 来源与探测内容 | 实测发现 | 交付或限制 |
| --- | --- | --- | --- |
| 01 | `data/config/codeSnippet.json`：片段格式、名称和代码。 | 29 条，名称可能是中文或英文别名；代码含制表符和占位符。 | 已实现 `snippets` 查询，保留原文，重复名称仍可用准确 ID 区分。 |
| 02 | `data/config/help.json`：类型、语言关键字和指令。 | 57 条，例如整型范围、循环、`#头文件`。 | 已实现 `language` 查询。 |
| 03 | `data/config/sys/objectName.config`：控件名称。 | XML 声明后为 32 个并列根节点，不能按单根 XML 读取。 | 已实现 `controls`，用受控包装解析原生片段。 |
| 04 | `data/config/sys/propertyList.json`：属性及候选值。 | 300 行、50 个层级；`buttonType` 原生值含 `radio/check/max/min/close`。 | 已实现 `properties`，保存 `scope/group/flags/choices`，不推断属性默认值。 |
| 05 | 同一文件 `help`：独立帮助覆盖。 | 113 条；`drawBk`、`tempExtend.start`、`tempExtend.count`、`itemID` 没有对应属性行。 | 已实现 `property-help`，避免只能从属性行间接查帮助而遗漏这些条目。 |
| 06 | `data/config/sys/events.xml`：事件与层级。 | 128 条，按钮点击声明带 `$[UI对象名称]`；部分子层无直接声明。 | 已实现 `events`；返回原始模板和层级，未验证的继承规则不自动合并。 |
| 07 | `data/config/customObject.config`：组合控件。 | 14 个顶层对象，包含布局组框、搜索编辑框、开关按钮等。 | 已实现 `custom-objects`；返回序列化片段，需调用方处理资源和 ID/name 冲突。 |
| 08 | `data/config/sys/vc-set.json`：编译选项映射。 | 15 类；含 `/MDd`、`/MD`、`/std:c++20` 等参数和不同配置默认值。 | 已实现 `build-options`；只展示安装定义，不修改项目设置。 |
| 09 | `data/config/sys/autoMatch_function.txt`：函数补全。 | 1375 个非空声明行。 | 已实现 `functions`，保留行号和原始空白；不保证当前模块可调用。 |
| 10 | `data/config/sys/autoMatch_const.txt`：常量/补全词。 | 1766 个非空行，混有 `for(...)` 等代码词条。 | 已实现 `completion-tokens`，不伪造常量值或把全部条目标为常量。 |
| 11 | `customPropertyName_ch.xml` 与 `customPropertyName_en.xml`。 | 中文表 117 条，英文表 118 条；仅中文 22 个键，仅英文 23 个键，存在旧式坐标/边距分量写法。 | 暂未实现别名合并。两表并非一一对应，不能自动替换当前属性名；以原生属性表为查询依据。 |
| 12 | `data/config/favoriteColor.config`：收藏配色。 | 4 个组，共 23 条纯色、16 条渐变记录。 | 已确认可扩展只读调色板查询；本轮保留原始记录，未写全局收藏或转换渐变。 |
| 13 | `data/config/customColor.config`：自定义颜色。 | 7 个带符号整数颜色和 7 个空渐变槽。 | 颜色位序/兼容行为未经运行验证，不将数值猜测为 RGBA。 |
| 14 | `data/config/sys/vc.config`：SDK、工具集、目录存在性。 | 2 个 SDK、3 个工具集；60 条非空目录记录中 4 条指向不存在的同一目录 `data/VC/XC-Module`。 | 可扩展工具链体检；这些记录不等于当前活动配置，未断言构建失败或自动修补。 |
| 15 | `data/xml/item_template/*.xml`：IDE 自用列表项模板。 | 41 个文件：21 列表框、12 树、5 列表、3 列表视图模板；全部含数据绑定表达式。 | 可研究模板复用；当前缺少绑定数据模型证明，未作为完整可运行窗口复制。 |
| 16 | 4 个 `layout_projectSetting_*.xml` 页面。 | 可见包含目录、库目录、继承值、排除列表、附加库和模块定义文件等控件。 | 确认未覆盖的设置入口；仅控件名称不足以确定 `.xcproj` 保存和继承规则，未增加写命令。 |
| 17 | `例子/炫彩界面AI项目/资源文件/resource.res`。 | 20 图片、7 字体、16 颜色、25 背景样式；此样本无同名条目。 | 可做资源导入计划；跨资源表冲突、文件复制和布局引用更新尚需事务设计，本轮未改资源。 |
| 18 | 同项目 `UI_ZIP.zip`：成员目录。 | 24 个成员，3 布局 XML、1 资源表；样本无加密成员或重名成员。 | 确认成员浏览/提取方向；未执行提取，不能据此保证其他归档安全。 |
| 19 | `module_sub_cxxastar.h`：模块 API 声明位置。 | 当前包装头无 `//@别名`，却含 `//@解析头文件` 并转向 `CXXCore-master/include/cxxastardevice.h`。 | 完整 API 索引需要处理转发、include 范围和宏条件，不能把包装头扫描空结果当成无 API。 |
| 20 | `data/tool` 与 `DbgView使用说明.txt`：原生工具。 | 7 个 EXE，说明文件仅给出 DebugView 官方文档 URL。 | 未执行 GUI 工具；仍缺少实测无界面调用协议，未包装成调试自动化接口。 |

## 自动化语义与错误处理

- `reference sources` 逐项给出 `available`、`count`、`error`。成功完成盘点不代表每个源均可用。
- `search` 以文本子串匹配，使用 `--limit/--offset` 翻页，返回 `next_offset`。准确 ID 只对当前源有效；源哈希变化后应重新搜索。
- `--scope` 为准确的原生层级；基础元素和按钮的条目分别查。空子层不代表控件没有能力。
- 参数合法但无匹配时返回成功的空列表；源文件缺失、超出 4 MiB、格式错误、重复 ID、非法作用域或未知 ID 返回错误。
- 拒绝读取安装目录外的源链接和含 DTD/实体声明的 XML。JSON 同名键会明确报错，避免悄悄丢失条目。
- 片段不自动替换占位符；组合控件 XML 会经过序列化，不承诺与源文件逐字相同；补全函数和编译选项需结合实际工程核验。

## 验证与复跑

在本仓库的 `xcide/agent-harness` 目录运行：

```powershell
python -X utf8 -B tools/explore_round2.py --ide 'I:\xcide' --output '../../AI_MINING_EVIDENCE_02.json'
$env:CLI_ANYTHING_FORCE_INSTALLED = '1'
python -X utf8 -B -m pytest cli_anything/xcide/tests -q --tb=short -p no:cacheprovider
```

本轮完整套件：**122 项通过**，包含 103 项核心测试和 19 项安装命令测试。新增 18 项核心边界用例与 3 项安装命令工作流；安装用例逐一搜索/读取 10 类目录，并把真实代码片段写入临时工程后回读比对。原有默认与自定义输出路径的 2 项真实 GUI 构建验收继续通过。裸片段仅做文件工作流验证，没有把含占位符的片段当成编译成功样例。

20 轮证据脚本检查 64 个安装文件，前后哈希一致；正式配置 SHA-256 仍为 `977E1D599024CB3A119CD1C6EBFA4CB64C0A5F87CE73E5C3B0600DE234ED9D1C`。没有启动额外子代理，也没有修改正式 IDE 配置、源码示例或资源表。

本轮生产代码集中在新增 `core/references.py` 及 CLI 命令注册。其余改动为相关测试、AI 调用文档、技能文件、离线 HTML、复跑工具和证据报告。已有命令参数与写入行为保持兼容。
