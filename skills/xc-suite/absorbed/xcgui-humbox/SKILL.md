---
name: xcgui-humbox
description: 炫彩界面库(XCGUI/DirectUI)桌面皮肤包开发与维护指南，以未闻花名UI平台(humbox)皮肤为参考实现。涵盖 bkInfoM 样式宏语言、windowUI/layoutPanel 布局XML、resource.res 资源注册、列表项模板与面板注入架构。当用户要修改/新增炫彩界面布局、皮肤样式、bkInfoM、resource.res、窗口XML、列表模板，或提到 炫彩IDE/炫彩界面库/XCGUI/未闻花名/humbox/布局文件/皮肤包/DirectUI界面 时使用本技能——即使用户没有明说"皮肤"。
---

# XCGUI humbox 皮肤包开发

## 项目定位（先读这段）

当前项目是**炫彩界面库 (XCGUI) 的 Windows 桌面 DirectUI 皮肤包**（未闻花名UI平台），不是 Web 项目——没有 HTML/CSS/JS/构建系统。它由两类东西组成：

```
humbox/
├── 布局文件/   57 个 XML：17 窗口(windowUI) + 18 面板(layoutPanel) + 21 列表项模板
└── 资源文件/   resource.res（XML 资源清单）+ 230 图片 + font/ 6 字体
```

被 XCGUI 宿主程序（或炫彩IDE设计器）加载运行。**一切修改都是编辑这些 XML**。

## 参考文档索引（按需读取，不要一次全读）

| 文件 | 何时读 |
|---|---|
| `references/bkinfom-grammar.md` | **要写/改任何 `bkInfoM="..."` 属性之前（必读）**。bkInfoM 样式宏语言的完整语法、状态码表、颜色换算、真实实例逐段注释 |
| `references/layout-widgets.md` | 要写/改布局属性（`layout.*`）、控件（buttonUI/editUI/comboBoxUI…）、窗口属性、滚动条声明时 |
| `references/architecture.md` | 要新增窗口/页面/资源、理解面板注入机制（main_body 槽位、bindEle、@ID_* 切换）、命名约定时 |
| `references/file-map.md` | **做任何修改前先在此定位目标文件**。全部文件的分类地图 + 依赖关系图 + resource.res 注册内容速查 |

## 核心心智模型（30 秒版）

1. **三层引用**：布局 XML 里写 `@名称` → resource.res 注册表解析 → 实际文件在 资源文件/。图片/字体/符号ID/复用样式**未注册即静默失效**
2. **bkInfoM 是样式系统**：`{99:1.9.9;98:状态映射;绘制段0;绘制段1;...}`——段落按顺序编号，`98:` 的状态码决定每个交互态画哪些段
3. **面板注入**：main.xml 留 `name="main_body"` 空槽，宿主注入页面面板；页内切换用 单选按钮 `bindEle="@ID_X"` + 面板 `id="@ID_X"` 声明式联动
4. **数据绑定**：模板里 `{binding field=字段名}` 由宿主运行时填充

## 常见任务工作流

### 任务 1：新增图片/字体资源

1. 文件放入 `资源文件/`（SVG 用 `style="default" svgAlpha="255" svgRotateCenter="1"`；9宫格 PNG 用 `style="image9" rect9="l,t,r,b"`）
2. 在 `资源文件/resource.res` 的 `<type_image>`（或 `<type_font>`）照同类条目抄一行注册
3. 布局里以 `4(@名)`（bkInfoM 图片段）或 `image="@名"`（shapePicture）引用
4. 字体 token 命名：`字号 + b(粗) + _yh(雅黑)/_vv/_num(数字字体)`，如 `13b`、`13_yh`

### 任务 2：新建窗口

1. 新建 `布局文件/<名>.xml`，固定开头：`<?xml version="1.0" encoding="UTF-8"?>` + `<!--炫彩界面库-窗口布局文件-->` + `<head />`
2. 根元素 `<windowUI className="唯一名" ...>`（className 是宿主加载名；弹窗加 `windowType="modalWindow" center="true"`；样式细节读 layout-widgets.md 第 3 节）
3. 参照同类型现有窗口抄骨架（msg.xml=消息框、input.xml=输入框、sponsor.xml=带文案弹窗）
4. 窗口视觉基线：暗色圆角 + 8px 阴影（`shadowSize="8" shadowDepth="75"`），关闭按钮 `buttonType="close"` 三态换图

### 任务 3：给主窗口加导航页

1. 新建面板 `布局文件/<页名>.xml`（根 `<layoutPanel>`，首行注释 `<!--炫彩界面库-布局面板文件-->`）
2. main.xml 标题栏导航区（groupID="0" 的四个单选）加一个 `buttonType="radio" groupID="0"` 按钮，样式**照抄相邻导航按钮的 bkInfoM**，只改文字段
3. 面板由宿主注入 main_body——布局文件只声明，不加宿主代码
4. 页内二级导航：单选 `groupID="N"`(顺延新号) + `bindEle="@ID_新符号"`，resource.res type_id 注册新 ID（从 125 顺延），被控面板 `id="@ID_新符号"` + `showT="false"`

### 任务 4：改样式（bkInfoM）

1. **先读 references/bkinfom-grammar.md**——bkInfoM 无官方文档，语法全部从本项目反推，瞎写必错
2. 优先在 布局文件/ 全文搜索现成配方（如垂直渐变搜 `24(2,90.00`、圆角4搜 `9(4,4,4,4)`、卡片底搜 `22(654311423)`），复制改参数
3. 改颜色的唯一正确方式：有符号十进制 ↔ 无符号 ↔ `#AARRGGBB`，grammar.md 第 4 节有换算式和常用色速查表
4. 同一样式出现 3 处以上时注册为命名样式（resource.res type_bkInfo）再 `bkInfoM="@名"` 引用

### 任务 5：新增列表项模板

1. 按目标控件选根标签：listViewUI→`<xc_template_listView>`（含 listView_Group+listView_item）、listUI→`<xc_template_list>`（含 listHeader_item+list_item）、comboBoxUI→`<xc_template_listBox>`
2. 数据字段用 `{binding field=name1}` 形式
3. 抄最接近的现有模板改（资源卡片抄 res_item_temaplate_free.xml，下拉项抄 combobox_template.xml）

## 红线（违反必产生静默故障）

- **UTF-8 编码**：所有文件必须 UTF-8；新建文件照抄现有文件头三行
- **@名必须已注册**：写 `@xxx` 前确认 resource.res 有对应条目
- **@ID_ 编号唯一且不复用**：新 ID 从 125 顺延
- **段落索引联动**：bkInfoM 增删绘制段后必须同步改 `98:` 映射里的索引
- **name 不可随手改**：宿主代码按 name 找元素（main_body、_up_* 槽、`皮肤_..._编辑框` 等语义名）
- **对齐码宁抄勿编**：bkInfoM 里 `2(15)`、`2(48)` 等对齐码含义未完全确证，一律从现有段落抄
- **Test.xml 不是规范**：那是设计器草稿，正式风格以其他布局文件为准
- **已知悬空引用别扩散**：flow_ic1.svg、home_btn3_icon_01.svg 等不存在（详见 architecture.md 第 6 节）

## 修改前的标准动作

1. 在 `references/file-map.md` 定位目标文件
2. Read 目标文件及周边关联文件（上游容器/下游模板）
3. 涉及 bkInfoM → 先读 grammar.md；涉及布局属性 → 读 layout-widgets.md
4. 改动保持最小：抄现有配方改参数，不发明新模式
5. 完成后全文搜索被改的 @资源名/@ID/name，确认无遗漏引用
