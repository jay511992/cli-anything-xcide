# humbox 架构：文件角色、资源注册、面板注入与命名约定

本文解释 humbox（未闻花名UI平台皮肤包）的运行机制：XML 文件分几种角色、宿主程序如何组装它们、以及所有命名约定。理解这个架构才能正确新增页面/窗口/资源。

## 1. 项目总体结构

```
humbox/
├── Test.xml          设计器草稿（独立实验窗口，与正式布局无关联）
├── 布局文件/          全部 XML 布局（57 个文件）
│   ├── 18 个窗口布局（根 <windowUI>，首行注释：炫彩界面库-窗口布局文件）
│   ├── 18 个布局面板（根 <layoutPanel>，首行注释：炫彩界面库-布局面板文件）
│   ├── 14 个列表模板（根 <xc_template_list>）
│   ├── 6 个列表视模板（根 <xc_template_listView>，首行注释：炫彩界面库-列表视元素项模板文件）
│   └── 1 个列表框模板（根 <xc_template_listBox>，首行注释：炫彩界面库-列表框元素项模板文件）
└── 资源文件/          resource.res（资源清单，XML 格式但扩展名 .res）+ 230 个图片 + font/ 6 字体
```

每个 XML 文件的固定开头（**新建文件必须照抄**）：
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!--炫彩界面库-窗口布局文件-->   ← 按文件类型选：窗口布局/布局面板/列表元素项模板/列表视元素项模板/列表框元素项模板/资源文件
<head />
```
全部 UTF-8 无 BOM，简体中文内容。

## 2. resource.res —— 资源注册清单

`资源文件/resource.res` 是 XML（不是二进制），根元素 `<resources>`，六个子节。**所有图片、字体、符号 ID、可复用样式都必须先在这里注册**，布局文件再以 `@名称` 引用——未注册的名字运行时静默失效。

### 2.1 type_image — 图片注册

```xml
<image name="login_sd.png" value="login_sd.png" loadType="file" style="image9" rect9="30,28,30,32" />
<image name="close1.svg"   value="close1.svg"   loadType="file" style="default" svgAlpha="255" svgRotateCenter="1" />
<image name="mine_vip_bg.png" value="mine_vip_bg.png" loadType="file" style="fixedRatio" />
```

| 属性 | 说明 |
|---|---|
| `name` | 引用名（布局里 `@name`） |
| `value` | 资源文件/ 下实际文件名 |
| `loadType` | 项目恒 `file` |
| `style` | `default`=原样 / `image9`=九宫格拉伸 / `stretch`=整体拉伸 / `fixedRatio`=锁定宽高比 |
| `rect9` | 九宫格四边距 `l,t,r,b`（仅 image9） |
| `svgAlpha` | SVG 透明度（仅 SVG） |
| `svgRotateCenter` | SVG 旋转中心标记（项目恒 `1`） |
| `center` | 是否中心锚定（fixedRatio 时出现，`"false"`） |

**新增图片流程**：① 文件放进 `资源文件/` ② 在 type_image 加一行注册（照同类图抄属性）③ 布局里 `4(@名)` 或 `image="@名"` 引用。**删除图片时反向执行**，并全文搜索确认无引用。

### 2.2 type_id — 符号 ID

```xml
<item name="ID_皮肤_一键加载" value="110" />
<item name="ID_更新器交互_程序配置_配置详细" value="124" />
```
布局里写 `id="@ID_皮肤_一键加载"`。用途：跨文件的面板显示切换（见第 4 节）。**value 是裸数字，全表唯一（110–124 区间已占用），新增顺延编号，不要复用**。

### 2.3 type_font — 字体注册

```xml
<font name="13b"  size="13" fontFile="font\Semibold.ttf" />
<font name="13_yh" size="13" fontName="微软雅黑" />
<font name="13_vv" size="13" fontFile="font\HUMUINUM2.ttf" />
```
命名规则：`字号 + b(粗体/Semibold) + _后缀`。后缀含义：无后缀=Regular.ttf、`b`=Semibold.ttf、`_yh`=系统微软雅黑、`_vv`/`_num`=自定义数字展示字体(HUMUINUM.ttf/HUMUINUM2.ttf)。布局引用 `font="@13b"`。已注册 23 个（`9/9b/9_yh/9_num/10/10b/10_yh/10b_yh/11/11b/12/12_vv/12b/13/13_num/13_vv/13_yh/13b/15b/16b/18b/26b/8_yh`）。

### 2.4 type_bkInfo — 命名样式（等价 CSS class）

```xml
<item name="滚动条" type="22" bkInfoM="{...}" bkInfoM_nameT="" description="" />
```
布局里 `bkInfoM="@滚动条"` 引用。**新样式若会在 3 处以上复用（如滚动条、头像框），注册到这里再引用**，否则内联。

### 2.5 type_string / type_color / type_nameTable
项目里均为空占位节，保持存在即可。

## 3. 三种布局文件的角色

### 3.1 窗口布局（windowUI）— 独立弹出的窗口

每文件一个窗口，靠 `className` 供宿主加载。两类：
- **主窗口** main.xml（`className="humbox"`）：标题栏导航 + `name="main_body"` 的空槽（第 4 节）
- **功能弹窗**：login(登录)、msg(消息框,modalWindow)、VIP、mine(用户卡片)、preview(资源预览)、input(输入框)、settingWnd(设置)、sdk(SDK日志)、updater(更新器)、helpWnd(帮助菜单)、sponsor(赞助)、flowing(桌面悬浮球,42x40) 等，每个一个 className（见 file-map.md）

### 3.2 布局面板（layoutPanel）— 注入主窗口的页面

```xml
<layoutPanel heightT="580" showT="true" widthT="1024">
  <layoutEleUI layout.height="fill" layout.width="fill">页面内容</layoutEleUI>
</layoutPanel>
```
`widthT/heightT` 是设计器参考尺寸，实际随 `main_body` 槽位伸缩。主页面板（home/res/skin/Interaction）由宿主在用户点导航时注入 main_body；子面板（Vv/myinfo/avatar/progress/dropfile 等）由宿主按 `name` 查找并动态挂载。

### 3.3 列表模板 — 数据绑定的项外观

三种根标签对应三种列表控件：

```xml
<!-- 列表视模板（listViewUI 用，资源卡片）-->
<xc_template_listView>
  <listView_Group>分组头外观（字段 {binding field=name1}）</listView_Group>
  <listView_item>数据项外观（字段 {binding field=缩略图} 等）</listView_item>
</xc_template_listView>

<!-- 列表模板（listUI 用，排行榜/日志行）-->
<xc_template_list>
  <listHeader_item>表头列</listHeader_item>
  <list_item>数据行</list_item>
</xc_template_list>

<!-- 列表框模板（comboBoxUI 下拉项用）-->
<xc_template_listBox>
  <layoutEleUI><shapeText content="{binding field=name1}" /></layoutEleUI>
</xc_template_listBox>
```

**数据绑定语法**：任何属性值里写 `{binding field=字段名}`（如 `image="{binding field=缩略图}"`、`content="{binding field=name1}"`），运行时由宿主填真实数据。模板里还会写 `itemID="N"` 给项内元素编号。

## 4. 主窗口面板注入架构

main.xml 的骨架（简化）：

```xml
<windowUI className="humbox">
  <layoutEleUI name="main">                      ← 根容器
    <layoutEleUI ...>标题栏：LOGO + 4个导航单选按钮(groupID=0) + 用户/菜单/帮助 + min/max/close</layoutEleUI>
    <layoutEleUI name="main_body" layout.height=":1" layout.width="fill" />   ← 页面槽位（空）
  </layoutEleUI>
</windowUI>
```

**页面切换机制**（宿主运行时完成，布局文件只负责声明）：
1. 四个导航按钮 `首页/资源/皮肤/交互` 是 `buttonType="radio" groupID="0"`，各带快捷键 tooltip（快捷键[1]~[4]）
2. 宿主监听单选切换，把对应面板（home.xml/res.xml/skin.xml/Interaction.xml）注入 `main_body`
3. 页面内部的二级导航（如 skin.xml 的 自定义加载/一键加载）用 `groupID="3"` 单选 + `bindEle` 机制

**bindEle 显示切换**（布局内声明式切换，无需宿主代码）：
```xml
<buttonUI bindEle="@ID_皮肤_自定义加载" buttonType="radio" groupID="3" ... />   ← 导航单选
...
<layoutEleUI id="@ID_皮肤_自定义加载" showT="true">内容A</layoutEleUI>           ← 被控面板A
<layoutEleUI id="@ID_皮肤_一键加载"   showT="false">内容B</layoutEleUI>          ← 被控面板B
```
选中带 `bindEle="@ID_X"` 的按钮 → 显示 `id="@ID_X"` 的面板、隐藏同组其他。符号 ID 在 resource.res type_id 注册（第 2.2 节）。嵌套版本（Interaction.xml）：子面板自身又是新单选组的 bindEle 容器，形成 `@ID_更新器交互` → `@ID_更新器交互_程序配置` → `@ID_更新器交互_程序配置_配置详细` 三层。

## 5. 命名约定全集

### 5.1 元素 name（宿主代码按 name 查找元素，改错即断功能）

| 模式 | 示例 | 用途 |
|---|---|---|
| `{页面}_NN` | `home_01`..`home_12`、`myinfo_00`..`16`、`vv_01..03` | 设计器自动生成的结构名 |
| `{页}_{区块}_{控件}_{类型}` | `皮肤_自定义加载_对接程序_编辑框`、`皮肤_一键加载_算法类型_组合框`、`交互_更新器_确认生成更新器_按钮` | 代码驱动的功能元素（下划线层级点分语义） |
| `{页}_nav_{项}` | `皮肤_nav_自定义加载`、`皮肤_nav_一键加载` | 页内导航 |
| 槽位前缀 `_up_` | `_up_title`、`_up_time`、`_up_content`、`_up_update`、`_up_prog`、`_up_task_text`、`_up_task_prec` | layoutFrame.xml 的通用更新帧槽位（宿主填充） |
| `main` / `main_body` | — | 主窗口根容器与页面槽（**保留名**） |

### 5.2 资源文件名

- 图标多态三份：`_01`=正常、`_02`=悬停、`_03`=按下（如 `navbtn_icon_skin_01/02/03.svg`、`close1/2/3.svg`）
- 头像框：`头像框{1,2,3}_{尺寸}x{尺寸}_{状态序号}.{png|svg}`，尺寸 32/80/120/160
- 拼音/英文小写下划线命名为主

### 5.3 符号 ID（type_id）

`ID_{模块}_{功能}[_{子级}]`：模块∈{皮肤,更新器交互,验证交互,安装器交互}。层级用下划线延伸：`ID_更新器交互_程序配置_配置详细`。

### 5.4 groupID 分配

| groupID | 作用域 |
|---|---|
| 0 | 主窗口导航（首页/资源/皮肤/交互） |
| 2 | 资源页内导航 |
| 3 | 皮肤页内导航 |
| 4 | 交互页内导航 |

新增页面内导航顺延新号，不与现有冲突。

## 6. 已知问题清单（修改时留意）

1. `flow_ic1.svg`、`home_btn3_icon_01.svg`：布局中引用但**文件不存在**（悬空引用，运行时不显示）
2. resource.res 注册了 `pv_vip.jpg` 但实际文件是 `pv_vip.png`（jpg 条目失效）；`banner.jpg` 注册但未随包分发
3. `lgbg.png` 被 login.xml 的 bkInfoM 引用但**未在 resource.res 注册**（login 能显示说明宿主可能宽松解析，但按规范应补注册）
4. `11.png`、`22.png`、`en.ttf` 为未引用的孤儿文件（可清理，但先与用户确认）
5. Test.xml 是设计器草稿，其中元素与资源（Vv_* 资产）是实验性的——**不要把 Test.xml 当作规范参考**，正式风格以 布局文件/ 内其他文件为准

## 7. 视觉风格基线（未闻花名皮肤）

新增界面必须延续以下风格（从现有文件提炼）：
- 暗色玻璃质感：深色半透明窗口（transparentFlag shaped/shadow、9-patch login_sd.png 类边框）
- 主色：暗底 `#270F0F0F`~`#654311423` 半透明白/黑、强调黄绿 `#FFBBF327`（光标/链接悬停 `#FFc5f35f`）、VIP 金紫
- 圆角 2~12px（小件 2、卡片 6、弹窗 8）
- 文字层级：正文 `@10`/`@13` 常规灰白（`#B3FFFFFF`），强调 `@10b`/`@13b`，标题 `@15b`/`@18b`，选中纯白 `-1`
- 悬停态规律：文字变亮（`23(178)`→`23(200)`）、底色提亮 5~10%、cursor=IDC_HAND
- 按下态：再提亮或压暗一档 + 透明度微降
- 图标三态换图（_01/_02/_03），不使用单张图变色
