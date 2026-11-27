# interface-xml — 布局 XML 骨架 / 标签 / layout.* / 控件 / 窗口属性 / 窗壳 / 工具窗令牌

> 来源：`xc-代码\界面md\00-xc-xml-schema.md` §1/§3–§20/§23–§25、`07-pitfalls-and-checklist.md` §1/§2/§6、`08-window-shell-transparency.md`、`09-tool-window-tokens.md`、`xcgui-humbox\references\layout-widgets.md` §1–§5。

> 本文件是**窗口与布局属性的唯一权威表**。平台差异（humbox / hum 导航、配色、页面结构）见 `skin-platforms.md`；bkInfoM 与 resource.res 见 `bkinfom-res.md`。

> 剔除：`xc-代码\sessions\`、`xc-代码\.codegraph\`（源 `xc-代码/skill.md` 第 35 行原文：「`sessions/` 与 `.codegraph/` 不是技能材料。」）；`Test.xml` 等设计器草稿。

## 1. 文件骨架与标签

**不是单根 XML**。`<head />` 与真正根节点**并列**；注释决定类型，必须写对：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!--炫彩界面库-窗口布局文件-->
<head />
<windowUI ...>
```

| 注释 | 根节点 | 用途 |
|------|--------|------|
| 窗口布局文件 | `windowUI` | 独立窗口（主窗、模态弹窗） |
| 布局面板文件 | `layoutPanel` | 嵌入父元素的面板 |
| 列表元素项模板文件 | `xc_template_list` | `listUI` 表头+行 |
| 列表框元素项模板文件 | `xc_template_listBox` | `listBoxUI` / 组合框下拉项 |
| 列表视元素项模板文件 | `xc_template_listView` | `listViewUI` 分组+格子 |
| 树元素项模板文件 | `xc_template_tree` | `treeUI` 行 |

`<head>` 里可有 `<bindJsFile value="" />`；本仓库工具窗一般写 `<head />`，不用 JS。新建文件必须照抄固定开头三行。全部 **UTF-8 无 BOM**，简体中文内容。

**标准 XML 单根校验会误判**：炫彩文件常见 `<head />` + `<windowUI>`，不要用「必须单根」判定整文件废掉——**以炫彩 IDE 为准**。改完先在 IDE 打开布局，能开再跑 exe。

**humbox `布局文件/` 共 57 个 XML** = **17 个正式窗口**（`windowUI`）+ **1 个设计器草稿 `Test.xml`**（1936×1226，非风格参考）+ **18 个面板**（`layoutPanel`）+ **21 个列表项模板**（6 `xc_template_listView` + 14 `xc_template_list` + 1 `xc_template_listBox`）。

> 源冲突注记：`architecture.md` 的「18 个窗口」把 `Test.xml` 计入了窗口；`file-map.md`/`skill.md` 的「57 = 17+18+21」是加法笔误（实为 56，漏 `Test.xml`）。**按上式为最终口径。**

**标签全集（源文件出现顺序枚举）**

- 窗口/容器：`windowUI` `layoutPanel` `layoutEleUI` `layoutFrameUI` `elementUI` `scrollViewUI`

- 控件：`buttonUI` `textLinkUI` `editUI` `richTextBoxUI` `comboBoxUI` `listUI` `listBoxUI` `listViewUI` `treeUI` `scrollBarUI` `listHeaderUI` `progressBarUI` `sliderBarUI` `tabBarUI` `toolBarUI` `menuBarUI` `monthCalUI` `dateTimeUI` `paneUI` `propertyGridUI`

- 形状：`shapeText` `shapePicture` `shapeGif` `shapeRect` `shapeEllipse` `shapeGroupBox` `shapeLine`

- 模板根：`xc_template_list` `xc_template_listBox` `xc_template_listView` `xc_template_tree`

- 模板内子节点：`listHeader_item`、`list_Item`（00 拼写）/ `list_item`（architecture 拼写）、`listView_Group`、`listView_item`

- 滚动子声明：`<child>` 内的 `scrollBarUI` / `buttonUI` / `listHeaderUI`

> ⚠ 两来源差异：00 §20 写 `<list_Item heightT="30" widthT="1200">`，architecture §3.3 写 `<list_item>`；大小写不一致，抄目标工程现成模板。

**设计器属性 vs 运行时属性**（只服务设计器，**不要当运行时逻辑用**）：

| 属性 | 含义 | 注意 |
|------|------|------|
| `rect="l,t,w,h"` | 设计器画布占位 | 真正尺寸看 `layout.*` |
| `showT` | 设计器里显隐 | `showT="false"` 设计器隐藏，**运行时仍加载** |
| `expandT` | 设计器树节点展开 | 与运行时无关 |
| `widthT` / `heightT` | 模板项设计器预览宽高 | 运行时看 `layout.width/height` |
| `bkInfoM_nameT` / `bkInfoM_state` | 背景备注 / 预览态 | 可删 |

运行时显隐用 `show`（XML 初值）或代码显示 API。页签切换**禁止**靠 `showT`。`layout.align="statr"`、`layout.alignBaseline="statr"` 是设计器拼写错误，**不要学**。

**谁是布局盒子**：只有 `windowUI`（必须 `enableLayout="true"`）、`layoutEleUI`、`layoutFrameUI`（可滚动布局盒子）能排布子项；`layoutPanel` 本身不是盒子，里面要再放 `layoutEleUI`。

**不是盒子**：`elementUI`、普通 `buttonUI`、`shapeText`。父不是盒子时，子元素的 `layout.width/height` **无效**（`shapeText` 的布局宽高仍有效）。不要把一排表单塞进 `elementUI` 还指望自动排。

`layoutControl="false"`：该对象不受父盒子控制，改走 `rect`/`left/top`（layout-widgets 实例：login.xml 密码眼睛按钮）。默认受控，不要乱关。

```xml
<layoutPanel heightT="800" widthT="1500">
  <layoutEleUI layout.height="fill" layout.width="fill" ...>
</layoutPanel>
```

`heightT`/`widthT` 仅设计器画布。运行时由父撑满，根子项必须 `fill`。

## 2. `layout.*` 属性全集

**默认水平**。上下排必须 `layout.horizon="false"`。（旧文档曾写「默认纵向」——**以本条为准**。）

| 属性 | 值 | 用法 |
|------|-----|------|
| `layout.horizon` | `true` 水平 / `false` 垂直 | 漏写就是横排，窗口一拉就乱；模板文件里常见 |
| `layout.alignH` | `left` `right` `center` `equidistant` | 水平方向对齐/均分 |
| `layout.alignV` | `top` `bottom` `center` `equidistant` | 垂直方向 |
| `layout.alignBaseline` | `auto` `center` `end`（勿写 `statr`） | 同一排里齐顶/居中/齐底 |
| `layout.space` | 像素 | **列距**（水平子项间距） |
| `layout.spaceRow` | 像素 | **行距**。垂直堆叠用它 |
| `layout.autoWrap` | bool | 超出则换行。换行后不支持子项 `layout.align` |
| `layout.overflowHide` | bool | 超出裁剪，不换行 |

> ⚠ 两来源差异：`layout.alignH`/`layout.alignV` —— 00 额外给 `equidistant`，layout-widgets 只给 `left/center/right`、`top/center/bottom`；`layout.alignBaseline` —— 00 给 `auto center end`，layout-widgets 只给 `auto / center`；`layout.autoWrap` —— 00 归入「盒子属性（写在父上）」，layout-widgets 描述为「子元素换行开关」未指明父/子；`layout.wrap` —— 00 归入「项自身」意为「强制该项换到下一行」，layout-widgets 归入 layoutEleUI 表意为「允许自身换行」。**00 更全，采用 00。**

**项尺寸（写在子上）** `layout.width` / `layout.height`：

| XML 值 | 含义 | 坑 |
|--------|------|-----|
| `fill` | 撑满父 | 同一方向多个 `fill` 会抢；用 `:n` 分权重 |
| `auto` | 按内容 | 标题列不要 `auto`，勾选/文字会不齐 |
| `180` | 固定像素 | 父 `fill`、子全固定/`auto` → 底部留空 |
| `:7` | 剩余空间权重 | `:` 后是**比例**不是像素。`:7` 与 `:4` = 7:4 |
| `%30` | 占父百分比 | 少用 |

括号里的中文是设计器备注，运行只看数字：`:5(占用剩余空间)` / `:2(占用剩余空间)` / `%30(百分比)`。

`layout.minSize="w,h"`：限制缩放类尺寸下限，对固定像素无效；单值只约束宽。

| 项自身属性 | 含义 | 坑 |
|------|------|-----|
| `layout.align` | 该项在交叉轴上独立对齐 | `autoWrap` 时无效 |
| `layout.wrap` | 强制该项换到下一行 | 不是「文字换行」 |
| `layout.float` | 反方向靠齐 | 标题栏关闭钮靠右常用；脱离流式排布，配合 `layout.margin` 定位 |
| `layout.swap` | 换向时交换宽高 | 一般不用 |
| `layout.margin` | 该项外围空隙，可为负 | 实例 `layout.margin="-52,0,0,0"` 让元素向左突出 |
| `layout.position` | 相对盒子贴边，可负 | |
| `layout.minSize` | `w,h` 最小尺寸 | |
| `layoutControl` | `false` 关闭布局接管 | 改走绝对 `rect` |

**四元组：padding / border / margin / position** —— 一律 **左,上,右,下**。1 个数=四边相同；2 个数常见为 `水平,垂直`。不要写 3 个。

| 属性 | 写在 | 含义 |
|------|------|------|
| `padding` | 盒子 | 内边距 |
| `border` | 盒子/窗口 | 边占位。窗口顶边可含标题栏；editUI 上是文字与边框内距 |
| `layout.margin` / `layout.position` | 项 | 该项外围空隙 / 相对盒子贴边（可负）；两者在「项自身属性」表已列，此处仅标作用域 |

`overlayBorder="true"` 后布局会盖住系统标题栏，必须自己做标题栏。本仓库工具窗（含 RCP）都这样。

**吃满高度：铁律** —— 父是 `fill`、要吃满窗口时，子项必须用 `:n`（或合理 `fill`）把剩余空间分完。**禁止**：上面列表 `height="180"`，下面设置 `auto`。

**列表必须再包一层**，不要把 `listUI` 和表单做成同一父的兄弟：

```xml
<layoutEleUI layout.horizon="false" layout.height="fill" layout.width="fill" layout.spaceRow="10">
  <layoutEleUI layout.height=":7" layout.width="fill">
    <listUI name="列表_主机" layout.height="fill" layout.width="fill" />
  </layoutEleUI>
  <layoutEleUI layout.height=":3" layout.width="fill" layout.horizon="false" layout.spaceRow="8">
    <!-- 固定高的操作行 / 状态行 -->
  </layoutEleUI>
</layoutEleUI>
```

加载 XML 后，代码**不要**用固定像素 `SetItemSize` 把 XML 里的 `:n` 盖掉。页签叠在同一父里：各页都 `fill`，同时只显示一页。

**首次布局坑**：面板若 `show="false"` 或 radio `bindEle` 在首次布局前隐藏，`:1`/`fill` 可能算成 **0×0**，事后 `显示(真)` 也不重算。做法：先全部可见 → `显示(真)` → 再切页；或启动后强制 `窗口_调整布局`。

```xml
<!-- layoutEleUI 完整属性拼写样例（属性名必须逐字符精确，写错一个字母布局就静默失效） -->
<layoutEleUI expandT="true" layout.height="fill" layout.width="fill"
  layout.space="24" layout.spaceRow="20" padding="24,0,20,0"
  layout.alignH="left" layout.alignV="center" layout.alignBaseline="center"
  layout.overflowHide="true" layout.minSize="200,10" layout.float="true"
  layout.autoWrap="false" layout.wrap="true" mouseThrough="false"
  transparent="true" name="main" rect="0,0,0,0" showT="true" />
<!-- 垂直页 / 水平工具栏标准写法 -->
<layoutEleUI layout.horizon="false" layout.spaceRow="10" layout.height="fill" layout.width="fill">
<layoutEleUI layout.alignV="center" layout.height="36" layout.space="8" layout.width="fill">
```

不要用「水平 + 每个子项 `layout.wrap="true"`」冒充垂直；本仓库工具窗一律 `horizon="false"` 做竖排。

**layoutFrameUI（可滚动框架）**：长文档用；内容高度靠子项累加，不要把所有子项都 `fill`。`enableCanvas` 在此类容器可为 `true`。

```xml
<layoutFrameUI enableCanvas="true" name="home_01"
  layout.height=":1" layout.width="fill" layout.space="28" layout.spaceRow="24"
  layout.minSize="500,292" layout.autoWrap="false"
  scrollBarAuto="true" scrollBarShowH="true" scrollBarShowV="false"
  scrollView.scrollBarSize="4" transparent="true">
  <child>
    <scrollBarUI layout.height="64" scrollBar.sliderMinLength="120" scrollBar.sliderSpace="0" showButton="false" childType="scrollBarH" />
    <buttonUI bkInfoM="{sizeT:100,6;99:1.9.9;98:16(0)32(0)64(0);5:2(15)20(1)21(4)26(1)24(2,0.00,1694498815,0,100663295,100)9(2,2,2,2);}"
      layout.height="4" transparent="true" childType="scrollBarH.button" />
    <scrollBarUI scrollBar.sliderSpace="0" showButton="false" childType="scrollBarV" />
  </child>
</layoutFrameUI>
```

## 3. 控件清单与专有属性

**通用元素属性（几乎所有 HELE）**

| 属性 | 含义 | 坑 |
|------|------|-----|
| `enable` / `show` | 启用 / 运行时初值显隐 | 叠页用代码切 |
| `alpha` | 0–255 | 整控件透明度 |
| `transparent` | 背景透明 | 自绘/CSS 背景时常 true；几乎所有带 bkInfoM 的控件都要 `transparent="true"`，否则出现系统默认底色 |
| `drawBorder` / `drawFocus` | 默认边框 / 焦点框 | 模板里边框一律 `false` |
| `enableCanvas` | 独立画布 | **默认开**；`layoutEleUI` **默认关**。模板里必须 `false` |
| `mouseThrough` | 鼠标穿透 | 自己不收、**子仍收**。模板根必须 `true`；标题栏不要开穿透 |
| `cursor` | `IDC_HAND` / `IDC_ARROW` | 可点按钮给手型 |
| `toolTip` | 悬停提示 | 格式常带快捷键 `[N]` |
| `css.name` / `css.enable` | 套 CSS | 手写 `font`/`textColor` 时可 `css.enable="false"` |
| `bkInfoM` | 背景资源编码 | 能用命名样式/`css.name` 就别贴长串（语法见 `bkinfom-res.md`） |
| `font` / `textColor` | `@yahei_9` / `#AARRGGBB` / `@资源` | |
| `offsetXY` | 偏移修正 | 复选框 `offsetXY="22,0"`（00/07）/ `offsetXY="18"`（layout-widgets），不同工程实例并存 |

`shapeText` **不是 HELE**，点不中、不能当按钮用。要点击，点外层 `layoutEleUI` / `buttonUI`。

**容器语义**：`layoutEleUI` = 90% 的容器，默认 `enableCanvas=false`，不要擅自打开；`elementUI` = 不是布局盒子，用途 1px 分割线、图标底、纯背景块（纯靠 bkInfoM 画样式）；`layoutFrameUI` = 带滚动的布局盒子。

**滚动子对象 `<child>`**

```xml
<listUI ...>
  <child>
    <scrollBarUI showButton="false" childType="scrollBarV" />
    <listHeaderUI transparent="true" childType="listHeader" />
  </child>
</listUI>
```

`childType` 只允许：`scrollBarV` `scrollBarH` `scrollBarV.button` `scrollBarH.button` `listHeader`。多数列表可省略 `<child>`。

`scrollBarUI` 属性：`scrollBar.sliderMinLength`（滑块最短长度）、`scrollBar.sliderSpace`（滑块与轨道间隙）、`showButton`（两端箭头按钮，项目里恒 `false`）。`scrollView.scrollBarSize` = 滚动条宽度像素。

editUI / richTextBoxUI 的滚动条子声明：

```xml
<editUI multiLine="true" edit.autoWrap="true" edit.readOnly="true"
  scrollBarAuto="true" scrollBarShowH="false" scrollView.scrollBarSize="6" ...>
  <child>
    <scrollBarUI scrollBar.sliderSpace="0" showButton="false" childType="scrollBarV" />
    <buttonUI bkInfoM="@滚动条" transparent="true" childType="scrollBarV.button" />   <!-- 同上文 listUI 的 child 写法 -->
  </child>
</editUI>
```

> ⚠ 两来源差异（非冲突）：编辑框滚动属性名 —— 00 §14 用 `scrollBarShowV` / `scrollBarAuto`，layout-widgets §1 用 `scrollBarAuto` / `scrollBarShowH` / `scrollView.scrollBarSize`；H/V 并存，逐字抄源。

**`buttonUI`**

```xml
<buttonUI bkInfoM="..." buttonType="radio" check="true" groupID="0"
  bindEle="@ID_皮肤_一键加载" content="选择" font="@10b" textColor="#FDFFFFFF"
  cursor="IDC_HAND" toolTip="刷新皮肤列表" imageIcon="@res_sel_icon.svg"
  enable="false" layout.height="32" layout.width="32" transparent="true" />
```

| 属性 | 值 | 说明 |
|------|-----|------|
| `content` | 文本；模板可 `{binding ...}` | |
| `textAlign` | `left,vcenter` 或 `DT_LEFT,DT_VCENTER`（`DT_SINGLELINE`） | DrawText 标志 |
| `buttonType` | 空 / `radio` / `check` / `min` / `max` / `close` | **功能** |
| `style` | 空 / `radio` / `check` / `min` / `max` / `close` / `icon` | **外观**。系统勾选常配 `style="check"` |
| `check` | 是否选中 | 默认页 `check="true"` |
| `groupID` | 单选分组 | **同组互斥**。0=主导航，2=资源页，3=皮肤页，4=交互页 |
| `bindEle` | 选中则显示绑定元素 | hum/humbox 导航常用；工具窗可改用代码切页（同组代码同步先全部 `置选中(假)`，最后只对目标 `置选中(真)`；不要在混排循环中先真后假） |
| `imageIcon` | `@资源.svg` | 图标（走资源注册名） |
| `offsetXY` | 文本偏移 | 自定义复选框文字让开勾选区：`offsetXY="22,0"` |

**复选框**：`buttonType="check"` + `transparent="true"` + `@复选框`（或等价 bkInfoM），**不要**只写 `style="check"` 吃系统灰底。

`textLinkUI`：协议链接用这个，不要用按钮假装。

```xml
<textLinkUI content="《用户协议》" font="@10b" alpha="240"
  textColor="#FFFFFFFF" textColorStay="#FFc5f35f"
  underlineLeave="false" underlineStay="true" cursor="IDC_HAND" />
<shapeText content="出现任何问题，请随时与我们联系反馈" font="@10"
  textColor="#FFE9EAEA" textAlign="DT_LEFT,DT_VCENTER,DT_SINGLELINE" />
<shapePicture image="@LOGO.svg" layout.height="40" layout.width="40" />
```

`textColorStay` = 悬停色（项目品牌绿 `#FFc5f35f`），`underlineStay` = 悬停显示下划线。`image` 走资源注册名；模板里可绑数据 `image="{binding field=缩略图}"`。

**`editUI`**

```xml
<editUI contentTips="输入你的账号" contentTipsColor="#BBFFFFFF" caretColor="#FFBBF327"
  edit.password="true" multiLine="true" edit.autoWrap="true" edit.readOnly="true"
  enableFocus="false" font="@10b" textColor="#FFFFFFFF" border="12,0,12,0"
  layout.height="40" layout.width="fill" name="皮肤_自定义加载_对接程序_编辑框" />
```

属性：`content`/`contentTips`/`contentTipsColor`（初值/占位）；`multiLine`/`edit.autoWrap`；`edit.readOnly`；`edit.password`；`scrollBarShowV`/`scrollBarShowH`/`scrollBarAuto`；`caretColor`（光标色，品牌黄绿 `#FFBBF327`）；`enableFocus="false"`（禁止聚焦，说明文本用）；`border`（`l,t,r,b` 文字与边框内距）。

**`comboBoxUI`**：`comboBox.enableEdit`（false=只能选）、`comboBox.itemTemplate`（项模板；留空常靠代码建适配器）、`comboBox.dropHeight`（下拉高度）、`comboBox.drawButton`（关掉内置按钮，自绘箭头时 `false`）。

```xml
<comboBoxUI comboBox.enableEdit="false" comboBox.drawButton="false"
  contentTips="请选择授权皮肤" border="140,0,56,0" font="@10b"
  name="皮肤_自定义加载_授权皮肤_组合框" />
```

下拉项外观由绑定模板（`combobox_template.xml`，`xc_template_listBox` 根）决定。**美化与坑见 `skin-platforms.md` 组合框一节**：触发器样式 ≠ 弹出层；启动前 `创建数据适配器()`；弹出回调禁止乱改弹窗坐标/圆角壳。

**列表家族**：`listUI` 报表 `list.itemTemplate` = `文件名,最大延伸列数`（如 `list_agent_item.xml,8`）；`list.rowHeight` / `list.headerHeight`；`list.multiSel`；`list.dragChangeColumnWidth`。

**列宽铁律**：`添加列文本(宽,…)` 的宽度必须与项模板里每列 `layout.width` **一致**，否则表头与单元格错位截断。

`listBoxUI` / `listViewUI` / `treeUI`：见官方属性表；树模板左侧固定宽放 `expandButton="true"` 的展开钮。

**其它控件（少用也要写对）**：`progressBarUI` `sliderBarUI` `tabBarUI` `toolBarUI` `menuBarUI` `monthCalUI` `dateTimeUI` `paneUI` `propertyGridUI` `scrollViewUI` —— 能用 `layoutFrameUI` 就别用裸 `scrollViewUI`。本仓库页签多用 **radio 分段按钮**，不用 `tabBarUI`。

| 形状节点 | 用途 | 关键属性 |
|------|------|----------|
| `shapeText` | 标签 | `content` `font` `textColor` `textAlign` `offsetXY`；模板里 `itemID` + binding |
| `shapePicture` | 图 | `image="@x.svg"`；模板可绑 `image="{binding field=缩略图}"` |
| `shapeGif` | GIF | `image` |
| `shapeRect` / `shapeEllipse` | 几何 | `fill` `fillColor` `roundAngle` … |
| `shapeGroupBox` | 分组框 | `content` `borderColor` |
| `shapeLine` | 线 | `pointX1/Y1/X2/Y2` `color` |

`textAlign`：水平 `DT_LEFT|CENTER|RIGHT`，垂直 `DT_TOP|VCENTER|BOTTOM`，常加 `DT_SINGLELINE` / `DT_END_ELLIPSIS`。也可写 `left,vcenter`（视工程解析器）。

**项模板** —— 根必须是对应 `xc_template_*`。模板内根布局：

```xml
<layoutEleUI drawBorder="false" enableCanvas="false" mouseThrough="true"
  layout.height="fill" layout.width="fill" layout.alignV="center">
  <shapeText itemID="0" content="{binding field=c0}"
    layout.height="fill" layout.width="fill" />
</layoutEleUI>
```

**三条死命令**：`enableCanvas="false"`、`mouseThrough="true"`、`drawBorder="false"`。

**绑定语法**：`{binding field=字段名 source=data bSync=false}`，也可简写 `{binding field=c0}`（本仓库列表常用 `c0`…`c7`）。任何属性值里都能写。模板里还会写 `itemID="N"` 给项内元素编号。

**`list` 模板结构**：

```xml
<xc_template_list>
  <listHeader_item heightT="30" widthT="1200">  <!-- 每列一个 layoutEleUI -->
  <list_Item heightT="30" widthT="1200">       <!-- 列数与表头一致 -->
</xc_template_list>
```

`itemID` 按列递增且头/行一致。

**模板背景绑定 BUG**：若背景绑了字段，最外层若不展示该字段，尺寸可能被算成 0×0；须先在外部建同类型元素绑同一字段。`GetTemplateObject(..., 0)` 常拿到布局不是文本，改颜色找里面的 `SHAPE_TEXT`。

**常见布局模式速查**

- 表单行：`<layoutEleUI layout.height="40" layout.space="12" layout.width="fill" padding="140,0,12,0">` + `<editUI layout.width=":1" layout.height="fill" />` + `<buttonUI layout.height="24" layout.width="24" toolTip="粘贴" />` + `<buttonUI content="选择" layout.height="28" layout.width="40" />`。标签文字由容器自身的 bkInfoM 文字段绘制，不是独立元素。

- 左内容右说明双栏（5:2 权重）：`layout.width=":5(占用剩余空间)"` 表单 + `layout.width=":2(占用剩余空间)" layout.minSize="340"` 说明框。

- 标题条带容器：`<layoutEleUI bkInfoM="{...;5:2(7)3(0,0,0,32)...标题底;7:...标题文字;5:2(15)3(0,32,0,0)...内容底;}" padding="12,46,12,12">`。

- 浮动工具按钮（标题栏右侧）：`<buttonUI layout.float="true" layout.height="32" layout.width="32" layout.margin="0,0,-4,0" ... />`。

## 4. 窗口属性与窗壳

```xml
<!-- 工具窗推荐 · 产品 hum 主窗示例 -->
<windowUI center="true" dragBorder="false" dragWindow="true" enableLayout="true"
  overlayBorder="true" padding="24,24,24,24" rect="20,20,1180,720"
  windowStyle="0" transparentFlag="shaped" transparentAlpha="255"
  bkInfoM="@面板_窗壳">
<!-- humbox 主窗 -->
<windowUI center="true" className="humbox" content="未闻花名UI平台"
  rect="20,20,1168,670" dragWindow="true" dragBorder="true" overlayBorder="true"
  shadowColor="#FF000000" shadowSize="8" shadowDepth="75"
  transparentFlag="shadow" transparentAlpha="255" windowStyle="0" showT="true" />
```

| 属性 | 约定 |
|------|------|
| `className` | **宿主程序按此名查找加载窗口**，新增窗口必须注册且唯一（humbox、MdMsg、MdNotf、mineCard、vipAc…） |
| `content` | 窗口标题文本 |
| `center` | 弹出时居中 |
| `windowType` | 省略=普通；`modalWindow` 模态 |
| `windowStyle` | 工具窗 **`0`**（自绘窗控）；项目里恒 `0`，Test.xml 用过 `2031` |
| `enableLayout` | **必须 true** |
| `overlayBorder` | 自定义标题时常 **true** |
| `dragBorder` | 主窗可 true；小模态常 false |
| `dragWindow` | **有列表时优先 false**（点列表会拖走整窗） |
| `transparentFlag` | 工具窗/多数模态 `shaped`；**humbox 主窗 `shadow`** |
| `transparentAlpha` | 0–255 窗口透明度 |
| `bkInfoM` | **`shaped` 必有窗口级不透明底**：工具窗 `@面板_窗壳`；hum 产品 `@wnd_bg.png`。子控件色不能代替 |
| `padding` | 工具窗常 `10,8,10,10`；hum 主窗常 `24,24,24,24` |
| `minSize` / `rect` | 最小 `w,h` / `x,y,w,h` 设计器坐标（运行时由布局覆盖，但保留以兼容设计器） |
| `topmost` | 置顶 |
| `shadowColor` / `shadowSize` / `shadowDepth` | 阴影颜色/扩散/浓度 |

标题栏用 `buttonType="min|close"` + SVG；完整抄法见 §6。

> ⚠ 两来源差异（非冲突）：`dragBorder` 00 说主窗可 true、小模态常 false，layout-widgets 的 humbox 主窗实例给 `true`，而 §6 工具窗开标签给 `false` —— 针对不同窗型，勿混抄。

**铁律（三档透明模式）**

| 透明模式 | 必须同时具备 | 否则 |
|----------|--------------|------|
| **`shaped`** | 窗口 `bkInfoM` 有不透明底：工具窗用 **`@面板_窗壳`（§6）**；产品用壳图 / 实心 `22` | 透桌面 |
| **`shadow`** | humbox **主窗**专用；勿与 shaped 混抄 | 气质全错 |
| 无 flag | 普通 HWND | 无圆角异形 |

子控件 `bkColor` **不能**代替窗口级底。二维码「中间一块白、四周透」= 无窗壳的典型症状。

**原理**：`shaped` 按绘制结果生成透明区；窗口自身几乎无不透明像素 → Alpha≈0。

**`shaped` 还会影响命中区域，不只是视觉透明。** 实测普通矩形、数据密集窗口在 `transparentFlag="shaped"` 下可能出现控件可见但鼠标点不中：逐像素区域把透明像素也排除在命中之外。若产品不需要异形窗，应使用无 `transparentFlag` 的普通窗口，自定义标题栏与边框仍可保留；不要为此改动 humbox 既定的 `shadow` 规则。排障时用 `WindowFromPoint` 核对目标 HWND，并做一次真实鼠标按下／抬起，不能只凭截图或控件 `visible=true` 判定可交互。

| 窗壳方案 | 何时用 |
|------|--------|
| **`@面板_窗壳`** | **新工具窗（§6）** — 白底圆角描边，不必拷 `wnd_bg.png` |
| `@wnd_bg.png` | 仅复刻 hum 产品主窗 |
| `shadow` | 仅复刻 humbox 主窗 |
| 全窗 `22(-1)23(255)` | 无令牌时的纯色兜底 |
| 现象 | 处理 |
|------|------|
| 透桌面 / 整窗透桌面 | 补窗口级不透明底（补 `@面板_窗壳`）；查资源是否加载 |
| 仅二维码一块白、四周透 | 同上（图自带白底掩盖了无壳） |
| XML 改了仍旧 / 仍透 | `ui_loadType=1`：更新 zip 并重编；或改 `0` 读旁路文件 |
| 壳变白板 / 圆角壳变「系统白板」 | 去掉多余代码 `添加背景填充` |
| 主窗 shaped 却该是 shadow | humbox 主窗改回 `shadow` |
| `windowStyle=2031` | 系统标题栏在浅色窗上易看不见 |

代码兜底（**仅壳未生效时**）：`启用绘制背景` + `添加背景填充(..., RGBA(...,255))`。

窗壳摘要对照：`shaped` 无窗口级不透明底 → **透桌面**；`shaped` + **`@面板_窗壳`** → 工具窗正解；`shaped` + `@wnd_bg.png` → 仅 hum **产品**主窗；humbox 主窗用 `shaped` → 错，应 **`shadow`**。

## 5. XML 合法性与布局实战坑

**先避这些坑**：① 窗壳 / 令牌 / 顶栏按 §6 ② **会禁用的按钮** 必须有 `98:…2(n)` 禁用层（见 `bkinfom-res.md`）③ SVG 进 `resource.res` 并部署到 exe 旁 `svg\` ④ 属性禁止写在自闭合 `/` 后面，IDE 解析失败 ⑤ **组合框**：触发器 ≠ 弹出层；启动即 `创建数据适配器()`；弹出回调禁止改弹窗坐标/圆角壳 ⑥ 列表 `添加列文本` 列宽 = 项模板列宽。

**XML 合法性（IDE「解析不了」）**

致命：属性写在 `/` 后面。错误 `<layoutEleUI ... bkInfoM="..." / layout.space="6">`；正确：

```xml
<layoutEleUI ... layout.space="6" bkInfoM="...">
  <layoutEleUI ... bkInfoM="..." />
</layoutEleUI>
```

脚本批量改父节点 `layout.space` 时，**禁止**拼到子节点自闭合标签尾部。

程序改 XML 注意：`content="添加 / 续期"` 里的 `/` 会让「匹配到下一个 `/`」的正则截断标签，应用 `[^>]*>` 匹配整标签。

控件 `name` 与代码绑定：`main.xc` / `index.xc` 里 `"按钮_xxx"` 必须与 XML `name` **逐字一致**；美化时只改 `bkInfoM` / `imageIcon` / 文案展示，**不要改绑定用 name**（除非同步改 xc）。

**布局实战坑**

- 顶栏状态文案 vs 窗控：长状态若用 `layout.width="auto"` 与最小化/关闭同排，会 **顶满并叠到关闭钮**。推荐：

```xml
<shapeText name="形状文本_刷新状态" layout.width=":1" textAlign="right,vcenter" ... />
<layoutEleUI layout.width="68" layout.height="28" layout.horizon="true">
  <buttonUI buttonType="min" ... />
  <buttonUI buttonType="close" ... />
</layoutEleUI>
```

窗控样式对齐 hum：leave 仅 SVG；hover 浅灰底；关闭 hover 粉（右侧圆角 `9(0,8,0,0)`）。

- 右侧面板内容过高 → 底部按钮「消失」：单独一行的「发送弹幕」会被裁到面板外（看起来像没做）。**经验**：工具侧栏优先 **并排压缩**，不要假设用户会把窗拉高；改完在默认主窗高度下目视底部一行。

- 多选框系统灰底：`style="check"` 默认带浅灰矩形底。要 `buttonType="check"` + `transparent="true"` + `@复选框`、`offsetXY="22,0"`。

- 分段 radio：未选态是 `272/288/320`，已选是 `128/144/160/192`。若误写成普通按钮的 `16/32/64`，选中后 **不会高亮**。

- 列表表头错位 / 单元格截断：`添加列文本(宽, …)` 与模板里每列 `layout.width` **必须一致**。

- 隐藏面板首次布局 0×0：先全部可见 → 窗口显示 → 再切页；或 `窗口_调整布局`。

**组合框（comboBox）美化与坑** —— 触发器好看 ≠ 下拉列表好看。两者是 **两套对象**：组合框本体 + 弹出窗内的列表框。

| 层 | 对象 | 怎么美化 |
|----|------|---------|
| 关闭态触发器 | `comboBoxUI` | XML：`bkInfoM="@组合框_圆角"`、`comboBox.drawButton="false"`、`border="10,0,22,0"`、箭头 SVG |
| 展开后的列表 | 弹出 `HWINDOW` + `listBox` | 代码：绑定 **`元素事件_组合框弹出列表`**，在回调里改列表背景 / 项高 / 滚动条 |

项模板用 `xc_template_listBox`（不是 `xc_template_list`）：

```xml
<!-- 布局文件/combobox_item.xml -->
<xc_template_listBox>
  <layoutEleUI heightT="32" ... padding="10,0,10,0">
    <shapeText content="{binding field=name1}" itemID="0" ... />
  </layoutEleUI>
</xc_template_listBox>
```

代码侧（在 `创建数据适配器()` **之前**）：

```text
组合框.置项模板文件("布局文件\\combobox_item.xml")
组合框.创建数据适配器()
组合框.添加项文本("...")
```

| 现象 | 原因 | 修法 |
|------|------|------|
| 调试输出 `XAdTable_GetCountRow() 输入句柄可能无效[0x0]` 后退出 | 「等数据回来再建适配器」，用户先点开 → 取项数踩空句柄 | **启动时就 `创建数据适配器()`**；无数据时放占位项 |
| 弹出回调里 `列表框_取项数量AD` 崩 | 弹出列表框同样依赖适配器 | 先 `组合框_取数据适配器(ele) != 空` 再取项数 |
| 列表底边左右 **黑三角**、像双层框叠在一起 | 弹出后再 `窗口_置坐标` 改高度，并给弹窗上圆角 `9(...)` 壳，与系统已算好的弹出尺寸打架 | **不要**在弹出回调里改弹窗矩形；弹窗背景用直角细边 |
| 列表特别高、只有系统滚动条 | 默认下拉高度过大 | `组合框_启用下拉列表高度固定大小(真)` + `置下拉列表高度(项数×项高+余量)`；项少时 `滚动视_显示垂直滚动条(假)` |
| 项与项「贴死」 | 行距 0 或项高过小 | `列表框_置项默认高度(h,h)` + 适当 `置行间距` |

弹出回调推荐只做这些：

```text
1. 按项数计算 dropH → 组合框_置下拉列表高度
2. 列表框_置项默认高度 / 置行间距
3. 元素_置背景(列表框) 做 leave / hover / select
4. 滚动视_显示垂直滚动条（项少则隐藏） 5. 窗口_置背景(弹窗) 白底 + 细边，不要圆角壳，不要置坐标
```

API 别名别写错（IDE 检查失败）：`列表框_置默认项高度` → **`列表框_置项默认高度`**（对应 `XListBox_SetItemHeightDefault`）；`窗口_取矩形` / `窗口_置矩形` → **`窗口_取坐标` / `窗口_置坐标`**；矩形字段 `.bottom` / `.top` → 炫语言 **`下边` / `上边` / `左边` / `右边`**。

资源与字体：组合框箭头 SVG 必须进 `resource.res` 并部署到运行目录 `svg\`；项模板里尽量少依赖命名字体，列表弹出上下文偶发解析不到时可用普通字号。

## 6. 工具窗令牌（主控端金标准）

**一句话**：`windowStyle=0` + `shaped` + `bkInfoM="@面板_窗壳"` + `resource.res` 令牌（字体/色/面板/四态按钮） + 粉方标品牌 SVG + 自定义 min/close。

**不要**：系统标题栏 · humbox 黄绿/顶栏 Tab · 白 `logo1` 贴浅底 · 白卡叠白底无描边 · 壳已生效后再代码 `添加背景填充`。

复刻 hum / humbox **产品**主窗 → 改读 `skin-platforms.md`，不要用本节令牌硬套产品壳。

```xml
<windowUI
  windowStyle="0" transparentFlag="shaped" transparentAlpha="255" dragWindow="true"
  dragBorder="false" overlayBorder="true" enableLayout="true" center="true"
  padding="10,8,10,10" bkInfoM="@面板_窗壳">
  <layoutEleUI name="布局_壳内" layout.width="fill" layout.height="fill"
    layout.horizon="false" layout.spaceRow="0" padding="1,1,1,1" bkInfoM="@面板_内容">
```

**`@面板_窗壳`（写入 `resource.res`）**

```text
{sizeT:80,80;99:1.9.9;98:1(0);
 5:2(15)20(1)21(3)26(1)22(-1)23(255)
   10(1)7(1)11(3)16(1)12(-1185048)13(255)
   40(1)9(12,12,12,12);}
```

样式必须在本工程 `resource.res` 真实存在并部署到 exe 旁。

**布局骨架**

- 顶栏（高 42）：水平 · padding `12,4,8,4` → `26×26` 粉方标 SVG（logo_rcp / logo_wg，浅底可见）→ 标题 `@yahei_12_b` `@文本_标题` → 副标 `@yahei_9` `@文本_弱` → `1×16` `@面板_分隔` → 工具钮（可选）→ `:1` → min / close（深色 SVG；关闭 hover 粉）。

- 内容：分区 `@面板_分组`（白 + **可见描边**）；二维码空态 `@面板_二维码`；大工具台常见 左扫码/表单 ~200–300 · 右列表/日志 `:1`；小扫码窗 左二维码卡 · 右 Cookie 卡即可。

- 大窗示意（可选）：`windowUI shaped @面板_窗壳` → `@面板_内容` → 顶栏 + 水平（左：品牌区 / 扫码·表单 / 主次按钮；右：分组卡 + 列表 + 日志）。

**对照样例**：主控端 `main.xml` — 1200×720，分段 radio、列表、生成页、日志。扫码登陆 = 760×520 `@面板_窗壳` → `@面板_内容` → 顶栏（logo_wg + WeGame + 扫码登陆 | min/close）+ 水平（左 `@面板_分组`：二维码槽 + 状态条 + 获取二维码；右 `@面板_分组`：Cookie + 编辑框）。

| 工程 | 备注 |
|------|------|
| 主控端 | 09 数据源；分段 `@按钮_分段`；子窗 desktop/files/hostinfo |
| 扫码登陆 | 09 小窗样例 |
| 斗鱼协议 | 左扫码；右栏活动挂机｜礼物扩展用分段 radio（状态位 272/128，勿写成 16/32/64） |
| 虎牙挂机 | 左扫码+Cookie；右配置/批量/列表/日志；保留原 `name` |

气质：**浅色壳 + 黑主按钮 + Pro 粉点缀**；禁止 humbox 黄绿顶栏。浅底勿用白 `logo1`；白卡须有描边。

resource.res 令牌全集（字体 / 颜色 / 面板 / 按钮 / 编辑框）见 `bkinfom-res.md` §6.7。

## 7. 禁止清单与自检

**禁止清单（写 XML 前过一遍）**

1. 垂直堆叠漏写 `layout.horizon="false"`（默认是**水平**）。

2. 列表与表单做兄弟，或列表没有外层 `layoutEleUI`。

3. 父 `fill`、子全是固定高/`auto`，放大后底部空一截。

4. 用 `rect` / `showT` / `expandT` 当运行时逻辑。

5. 抄 `statr`。

6. 有列表的窗口随意 `dragWindow="true"`。

7. 窗控只写一半功能/外观配置却期望系统行为。

8. 勾选控件只设外观 `style="check"`、未设功能 `buttonType="check"` 或透明背景，导致系统灰底；工具窗应用 `@复选框` 样式。

9. 把表单塞进 `elementUI` 还设 `layout.width`。

10. 模板里 `enableCanvas="true"` 或根布局不 `mouseThrough`。

11. 隐藏页去取列表文本；叠页数据放成员变量。

12. 改了 XML 不重新编译 / 不更新嵌入的 UI zip。

13. `name` 重复或该绑代码的控件没 `name`。

14. 手写超长 `bkInfoM`；能命名样式就命名样式。

15. 同组页签在循环中混写真/假会清掉目标选态；代码同步先全部 `置选中(假)`，最后只对目标 `置选中(真)`，再核对实际唯一高亮。

16. 给 `layoutEleUI` 乱开 `enableCanvas`。

17. `nameTable`、把 `bindEle` 当唯一切页方案却又不懂首次布局。

18. `layout.space` 与 `layout.spaceRow` 用反。

19. `添加列文本` 列宽与模板列宽不一致。

20. 属性写到自闭合 `/` 后面（IDE 直接解析失败）。

21. **`shaped` 无窗口级不透明底**（透桌面；工具窗见 §6，产品壳见 §4）。

22. 把 humbox 主窗 `shadow` 与 hum/工具窗 `shaped` 混抄。

**AI 读 XML 时的优先级**：① `windowUI`：**宽高、padding、transparentFlag、windowStyle、bkInfoM 是否有不透明底** ② 顶层 `layoutEleUI`：**权重、horizon、space/spaceRow、padding** ③ `name` / `content` / `toolTip` ④ 命名样式 / 圆角 / 图资源 ⑤ 忽略设计器垃圾 `rect` / `showT` 与超长色值精度。

**提交前自检清单**

- 壳：工具窗 `shaped` + `@面板_窗壳`；或 hum 产品 `@wnd_bg`；或 humbox 主窗 `shadow` ｜ 自定义 min/close，品牌标浅底可见 ｜ `bkInfoM="@面板_窗壳"` 且在本工程 `resource.res` ｜ 未误用 humbox `shadow` / 未空 shaped ｜ 未代码整窗实心填充盖壳 ｜ 分组/二维码有描边

- 样式：主 / 次 / 危险按钮圆角观感一致 ｜ 会禁用的按钮 `98` 含 `2(n)`，禁用仍圆角 ｜ 未混用 humbox 黄绿 / 顶栏结构 ｜ 侧栏默认高度下底部操作钮仍可见 ｜ 主钮用浅色图标

- 组合框：触发器已套 `@组合框_圆角`（或等价）+ 箭头 SVG ｜ 有 `combobox_item.xml`（`xc_template_listBox`）且已部署 ｜ **每个**可点击组合框启动时已 `创建数据适配器()` ｜ 已绑 `元素事件_组合框弹出列表`；回调 **未** `窗口_置坐标` / 未给弹窗加圆角壳 ｜ 项少时无系统大方块滚动条；API 用 `列表框_置项默认高度`

- SVG：`resource.res` 已登记全部用到的 svg（含 `combobox_x*.svg`）｜ `Release64\svg\`（或 exe 旁）文件齐全 ｜ 黑底用浅色图标、浅底用深色/粉色图标 ｜ `svg\` + `resource.res`（+ 模板）已同步到 Debug/Debug64

- XML / 绑定：IDE 能打开主布局（无 ` / attr` 类语法错误）｜ 所有 `name` 与 `.xc` 绑定一致 ｜ 列表 / 组合框 `itemTemplate` 文件名存在且已部署 ｜ 竖排容器已写 `layout.horizon="false"` + `layout.spaceRow` ｜ 吃满高度用了 `:n` / 外层包列表 ｜ 列宽一致 ｜ 项模板根 `enableCanvas="false"` + `mouseThrough="true"` + `drawBorder="false"` ｜ 复选框 `buttonType="check"` + `@复选框` ｜ 未用 `showT` / `rect` 当运行时显隐与尺寸 ｜ 同组切页先全部 `置选中(假)`、最后目标 `置选中(真)`并检查唯一高亮；首次布局注意隐藏面板 0×0

- 部署：同步 布局 XML、`resource.res`、`svg\`、列表与组合框模板 → 运行目录 ｜ 改了 `.xc` 必须重新编译；只拷 XML 不够

**标识属性**

| 属性 | 作用域 | 规则 |
|------|--------|------|
| `name` | 全局唯一 | 主通道。中文+下划线：`列表_主机`、`按钮_监听`。重复会抢句柄 |
| `id` | 窗口内 | `0` 忽略。可写数字或 `@ID_xxx` |
| `uid` | 全局 | 一般不用 |
| `itemID` | 仅项模板 | 模板实例化后才能取 |
| `nameTable` | 已废弃 | 不要写 |
| `properties` | 自定义 `名=值` | 不能与内置属性重名 |
| `userData` | 整型附加数据 | |

面板根不必强行 `name`；窗口/按钮/列表/编辑框凡是代码要找的必须有 `name`。炫语言工程在类的 `[绑定信息]` 里绑 `name`。`id` = 数字 id（窗口内唯一）或 `@ID_符号名`（跨文件符号 ID）；`show` = 运行时显示 / `showT` = 设计时显示。



