# 布局引擎与控件清单

XCGUI 的布局系统由 `layout.*` 命名空间属性驱动（等价于 flexbox），加上每个控件自己的功能属性。本文列出项目里实际用到的全部属性拼写——**属性名必须逐字符精确**，写错一个字母布局就静默失效。

## 1. 布局容器

### layoutEleUI — 弹性盒子（最常用容器）

```xml
<layoutEleUI expandT="true" layout.height="fill" layout.width="fill"
  layout.space="24" layout.spaceRow="20" padding="24,0,20,0"
  layout.alignH="left" layout.alignV="center" layout.alignBaseline="center"
  layout.overflowHide="true" layout.minSize="200,10" layout.float="true"
  layout.autoWrap="false" layout.wrap="true" mouseThrough="false"
  transparent="true" name="main" rect="0,0,0,0" showT="true" />
```

| 属性 | 取值 | 说明 |
|---|---|---|
| `layout.width` / `layout.height` | `fill` / `auto` / `:1` / `:5(占用剩余空间)` / `%30(百分比)` / 像素数 | 主尺寸。`:N` 是权重（flex 比例），`:5(占用剩余空间)` 与 `:2(占用剩余空间)` 即 5:2 分配；`%30(百分比)` 占父容器 30% |
| `layout.space` | 像素 | 水平排列时子元素间距 |
| `layout.spaceRow` | 像素 | 垂直排列时子元素间距 |
| `padding` | `l,t,r,b` | 内边距（四值逗号分隔） |
| `layout.alignH` | `left` / `center` / `right` | 子元素水平对齐 |
| `layout.alignV` | `top` / `center` / `bottom` | 子元素垂直对齐 |
| `layout.alignBaseline` | `auto` / `center` | 基线对齐 |
| `layout.float` | `true` / `false` | 浮动（脱离流式排布，配合 layout.margin 定位） |
| `layout.margin` | `l,t,r,b` | 外边距，可为负值（如 `layout.margin="-52,0,0,0"` 让元素向左突出） |
| `layout.minSize` | `w,h` 或单值 | 最小尺寸（单值时只约束宽） |
| `layout.overflowHide` | `true` | 溢出裁剪 |
| `layout.autoWrap` | `true` / `false` | 子元素换行开关 |
| `layout.wrap` | `true` | 允许自身换行 |
| `layout.horizon` | `true` / `false` | 排列方向（模板文件里常见） |
| `mouseThrough` | `true` / `false` | 鼠标穿透（装饰层用） |
| `expandT` | `true` | 设计时展开（照抄） |
| `enableCanvas` | `true` / `false` | 启用画布缓存（滚动容器优化） |
| `drawBorder` | `false` | 设计时边框（模板内照抄） |

### layoutFrameUI — 可滚动框架

```xml
<layoutFrameUI enableCanvas="true" name="home_01"
  layout.height=":1" layout.width="fill" layout.space="28" layout.spaceRow="24"
  layout.minSize="500,292" layout.autoWrap="false"
  scrollBarAuto="true" scrollBarShowH="true" scrollBarShowV="false"
  scrollView.scrollBarSize="4" transparent="true">
  <child>
    <scrollBarUI layout.height="64" scrollBar.sliderMinLength="120"
      scrollBar.sliderSpace="0" showButton="false" childType="scrollBarH" />
    <buttonUI bkInfoM="{sizeT:100,6;99:1.9.9;98:16(0)32(0)64(0);5:2(15)20(1)21(4)26(1)24(2,0.00,1694498815,0,100663295,100)9(2,2,2,2);}"
      layout.height="4" transparent="true" childType="scrollBarH.button" />
    <scrollBarUI scrollBar.sliderSpace="0" showButton="false" childType="scrollBarV" />
  </child>
  <!-- 内容子元素放这里 -->
</layoutFrameUI>
```

| 属性 | 说明 |
|---|---|
| `scrollBarShowH` / `scrollBarShowV` | 水平/垂直滚动条显示开关 |
| `scrollBarAuto` | 内容超出自动出滚动条 |
| `scrollView.scrollBarSize` | 滚动条宽度像素 |
| `<child>` 块 | 声明滚动条本体：`scrollBarUI childType="scrollBarH/scrollBarV"` + 滑块按钮 `buttonUI childType="scrollBarH.button/scrollBarV.button"`（滑块样式来自 bkInfoM，常引用命名样式 `bkInfoM="@滚动条"`） |
| `scrollBar.sliderMinLength` | 滑块最短长度 |
| `scrollBar.sliderSpace` | 滑块与轨道的间隙 |
| `showButton` | 是否显示两端箭头按钮（项目里恒 `false`） |

### editUI / richTextBoxUI 等的滚动条子声明

文本框也能带滚动条，写在 `<child>` 内（skin.xml 使用说明框实例）：
```xml
<editUI multiLine="true" edit.autoWrap="true" edit.readOnly="true"
  scrollBarAuto="true" scrollBarShowH="false" scrollView.scrollBarSize="6" ...>
  <child>
    <scrollBarUI scrollBar.sliderSpace="0" showButton="false" childType="scrollBarV" />
    <buttonUI bkInfoM="@滚动条" transparent="true" childType="scrollBarV.button" />
  </child>
</editUI>
```

## 2. 控件清单（实际用到的属性拼写）

### buttonUI

```xml
<buttonUI bkInfoM="..." buttonType="radio" check="true" groupID="0"
  bindEle="@ID_皮肤_一键加载" content="选择" font="@10b" textColor="#FDFFFFFF"
  cursor="IDC_HAND" toolTip="刷新皮肤列表" imageIcon="@res_sel_icon.svg"
  enable="false" layout.height="32" layout.width="32" transparent="true" />
```

| 属性 | 说明 |
|---|---|
| `buttonType` | `radio`（单选）/ `check`（复选）/ `min` / `max` / `close`（窗口标题按钮） |
| `check` | 初始选中 |
| `groupID` | 单选组号：0=主导航，2=资源页，3=皮肤页，4=交互页。**同组互斥** |
| `bindEle` | 绑定目标：`bindEle="@ID_皮肤_一键加载"` 使本按钮选中时显示该 ID 面板 |
| `imageIcon` | 图标（走资源注册名） |
| `cursor` | `IDC_HAND` / `IDC_ARROW` |
| `content` + `font` + `textColor` | 内容文字（也可用 bkInfoM 文字段绘制文字，二选一；项目内两种都大量存在） |
| `enable` | `false` 禁用（"敬请期待"卡片） |
| `textAlign` | `DT_LEFT,DT_VCENTER,DT_SINGLELINE`（DrawText 标志） |

### editUI — 文本输入框

```xml
<editUI contentTips="输入你的账号" contentTipsColor="#BBFFFFFF" caretColor="#FFBBF327"
  edit.password="true" multiLine="true" edit.autoWrap="true" edit.readOnly="true"
  enableFocus="false" font="@10b" textColor="#FFFFFFFF" border="12,0,12,0"
  layout.height="40" layout.width="fill" name="皮肤_自定义加载_对接程序_编辑框" />
```

| 属性 | 说明 |
|---|---|
| `contentTips` | 占位提示文字 |
| `contentTipsColor` | 占位色（`#BBFFFFFF`） |
| `caretColor` | 光标色（品牌黄绿 `#FFBBF327`） |
| `edit.password` | 密码模式 |
| `multiLine` | 多行 |
| `edit.autoWrap` | 自动换行 |
| `edit.readOnly` | 只读 |
| `enableFocus` | `false` 禁止聚焦（说明文本用） |
| `border` | `l,t,r,b` 文字与边框内距 |

### shapeText — 静态文本

```xml
<shapeText content="出现任何问题，请随时与我们联系反馈" font="@10"
  textColor="#FFE9EAEA" textAlign="DT_LEFT,DT_VCENTER,DT_SINGLELINE" />
```

### shapePicture — 图片

```xml
<shapePicture image="@LOGO.svg" layout.height="40" layout.width="40" />
```
`image` 走资源注册名；模板里可绑数据 `image="{binding field=缩略图}"`。

### textLinkUI — 文字链接

```xml
<textLinkUI content="《用户协议》" font="@10b" alpha="240"
  textColor="#FFFFFFFF" textColorStay="#FFc5f35f"
  underlineLeave="false" underlineStay="true" cursor="IDC_HAND" />
```
`textColorStay` = 悬停色（项目品牌绿 `#FFc5f35f`），`underlineStay` = 悬停显示下划线。

### comboBoxUI — 下拉框

```xml
<comboBoxUI comboBox.enableEdit="false" comboBox.drawButton="false"
  contentTips="请选择授权皮肤" border="140,0,56,0" font="@10b"
  name="皮肤_自定义加载_授权皮肤_组合框" />
```
下拉项外观由绑定模板（combobox_template.xml，`xc_template_listBox` 根）决定。

### progressBarUI、listViewUI、listUI + listHeaderUI

进度条与列表控件在 progress.xml / raking.xml / res.xml 中使用；列表项外观由模板文件控制（见 architecture.md 第 3 节）。

### elementUI — 通用元素

`<elementUI>` 是无语义占位元素，纯靠 bkInfoM 画样式（login.xml 的头像区、Test.xml 的实验卡片）。

## 3. 窗口属性（windowUI 根元素）

```xml
<windowUI center="true" className="humbox" content="未闻花名UI平台"
  rect="20,20,1168,670" dragWindow="true" dragBorder="true" overlayBorder="true"
  shadowColor="#FF000000" shadowSize="8" shadowDepth="75"
  transparentFlag="shadow" transparentAlpha="255" windowStyle="0" showT="true" />
```

| 属性 | 说明 |
|---|---|
| `className` | **宿主程序按此名查找加载窗口**，新增窗口必须注册且唯一（humbox、MdMsg、MdNotf、mineCard、vipAc…） |
| `content` | 窗口标题 |
| `rect` | `x,y,w,h` 设计器坐标（运行时由布局覆盖，但保留以兼容设计器） |
| `center` | 启动居中 |
| `windowType` | `modalWindow` = 模态（msg.xml、VIP.xml） |
| `topmost` | 置顶（updater.xml） |
| `dragWindow` | 整窗可拖动 |
| `dragBorder` | 边框可拖拽调整大小 |
| `overlayBorder` | 覆盖边框模式 |
| `transparentFlag` | `shaped` = 异形窗口（login.xml）；`shadow` = 阴影模式（main.xml） |
| `transparentAlpha` | 0–255 窗口透明度 |
| `shadowColor` / `shadowSize` / `shadowDepth` | 阴影颜色/扩散/浓度 |
| `enableLayout` | 启用布局引擎（login.xml 显式声明） |
| `windowStyle` | 数值样式标志（项目里恒 `0`；Test.xml 用过 `2031`） |
| `bkInfoM` | 窗口级背景样式（login.xml：9-patch 边框图 + 内层图） |

**模态弹窗模式**（msg.xml 500x320）：`windowType="modalWindow"` + 居中 + 自带关闭按钮。

## 4. 通用元素属性

| 属性 | 适用 | 说明 |
|---|---|---|
| `name` | 所有元素 | 查找名（宿主代码 getElement 按此找）——必须全局可定位，遵循命名规范 |
| `id` | 所有元素 | 数字 id（窗口内唯一）或 `@ID_符号名`（跨文件符号 ID） |
| `show` / `showT` | 所有元素 | 运行时显示 / 设计时显示（skin.xml 用 `show="false"` 隐藏"刷新"按钮，`showT="true"` 保留设计器可见性） |
| `transparent` | 所有元素 | 背景透明（几乎所有带 bkInfoM 的控件都要 `transparent="true"`，否则出现系统默认底色） |
| `toolTip` | 交互元素 | 悬停提示，格式常带快捷键 `[N]` |
| `font` | 有文字的元素 | `@字体名` 引用注册字体 |
| `textColor` | 有文字的元素 | `#AARRGGBB` |
| `alpha` | 有文字的元素 | 0–255 整体透明度 |
| `offsetXY` | 所有元素 | 偏移修正（复选框 `offsetXY="18"`） |
| `itemID` | 模板内元素 | 模板项内元素编号 |
| `layoutControl` | login.xml 密码眼睛按钮 | 关闭布局接管，用绝对 rect 定位（`layoutControl="false"` + rect） |

## 5. 常见布局模式速查

**表单行**（标签+输入框+按钮，skin.xml）：
```xml
<layoutEleUI layout.height="40" layout.space="12" layout.width="fill" padding="140,0,12,0">
  <editUI layout.width=":1" layout.height="fill" />
  <buttonUI layout.height="24" layout.width="24" toolTip="粘贴" />
  <buttonUI content="选择" layout.height="28" layout.width="40" />
</layoutEleUI>
```
标签文字由容器自身的 bkInfoM 文字段绘制（`7:2(11)3(16,0,120,0)30(5,对接程序*)...`），不是独立元素。

**左内容右说明双栏**（5:2 权重）：
```xml
<layoutEleUI layout.width=":5(占用剩余空间)" ...>表单</layoutEleUI>
<layoutEleUI layout.width=":2(占用剩余空间)" layout.minSize="340" ...>说明框</layoutEleUI>
```

**标题条带容器**（顶部标题栏 + 下方内容区）：
```xml
<layoutEleUI bkInfoM="{...;5:2(7)3(0,0,0,32)...标题底;7:...标题文字;5:2(15)3(0,32,0,0)...内容底;}"
  padding="12,46,12,12">子元素</layoutEleUI>
```

**浮动工具按钮**（标题栏右侧）：
```xml
<buttonUI layout.float="true" layout.height="32" layout.width="32"
  layout.margin="0,0,-4,0" ... />
```
