# xcgui-code — 句柄 / CXWindow / 事件 / 列表适配器 / 弹窗 / 拖放 / 系统API 前缀索引 / 线程池

> 来源：`xc-代码\炫彩界面库.mdc`（Part 1 §1–§7、§10–§13；附录 §1–§12）、`xc-代码\系统API(前缀分类法).mdc`（全文）、`xc-代码\线程池.mdc`（全文）。

> 类型名/枚举名/事件名/函数名逐字保留。布局 XML 侧的 CSS 属性与选择器见 `interface-xml.md` / `bkinfom-res.md`；本文件只保留代码侧调用入口。语言语法与基础模块见 `xuanlang-lang.md`。

## 1. 模块概览与核心文件

炫彩界面库（C 接口 `module_xcgui.h` + C++ 封装 `module_xcgui_class.h`），当前版本 4.0.0，更新时间 2026-03-15。定位为 Windows 平台下的原生 GUI 封装库，基于 Win32 与自研渲染内核，提供窗口、元素控件、布局、样式（CSS）、动画、数据适配器等完整 UI 能力。依赖模块 `module_base.h`。

- `module_xcgui.h`：C API 主头文件；含模块元信息注释（版本、日期、变更日志）、库链接指令（`//@lib`）、运行时 DLL 复制标记（`//@复制文件`）；引入 `xcgui_event.h` 以统一窗口和元素事件枚举与说明；定义 GUI 句柄类型、对象类型枚举、对象扩展类型枚举等基础类型

- `module_xcgui_class.h`：C++ 面向对象封装，在 C API 基础上提供 `CXWindow`、`CXButton` 等强类型类封装；所有类以 `CXBase` 为根类，通过 `GetHXCGUI()` 统一获取底层 `HXCGUI` 资源句柄

- `xcgui_event.h`：事件常量与说明，含窗口事件（`WM_*`、`XWM_*`）与元素事件（`XE_*`）的详细中文注释、原型说明、参数说明

- `md5.txt`：模块文件的 MD5 信息，通常用于版本或完整性校验

## 2. 句柄与基础类型

```text
通用句柄:
HXCGUI   炫彩资源总句柄（标识任意资源：窗口、元素、图片等）
HWINDOW  炫彩窗口句柄（与系统 HWND 区分）
HELE     元素（控件）句柄
HMENUX   炫彩菜单句柄
HDRAW    绘图/渲染句柄
HIMAGE   图片资源句柄
HFONTX   炫彩字体句柄
HBKM     背景内容管理器句柄
HTEMP    模板句柄（用于列表、列表树、列表视图等项模板机制）
HSVG     SVG 矢量图形句柄
```

颜色与辅助宏：`RGBA(r, g, b, a)` 为统一的 32 位 RGBA 颜色宏（高 8 位为 Alpha）；另有内部颜色宏（如 `COLORREF_MAKE2`、`COLORREF_SET_A` 等）用于在 `COLORREF` 与 RGBA 之间转换、设置透明度。

## 3. 对象类型体系（`XC_OBJECT_TYPE`）

对象类型用于区分资源的功能角色，典型用于运行时类型判断、调试与通用接口（如 `XObj_*`）上的分发。

- **窗口与容器**：`XC_WINDOW`（普通窗口）、`XC_MODALWINDOW`（模态窗口）、`XC_FRAMEWND`（带停靠/浮动窗格能力的框架窗口）、`XC_FLOATWND`（浮动窗口）、`XC_COMBOBOXWINDOW`（组合框下拉窗口）、`XC_POPUPMENUWINDOW` / `XC_POPUPMENUCHILDWINDOW`（菜单主窗口 / 菜单子窗口）

- **基础元素与常用控件**：`XC_ELE`、`XC_BUTTON`、`XC_COMBOBOX`、`XC_SCROLLBAR`、`XC_SCROLLVIEW`、`XC_LIST` / `XC_LISTBOX` / `XC_LISTVIEW` / `XC_TREE`、`XC_MENUBAR`、`XC_SLIDERBAR`、`XC_PROGRESSBAR`、`XC_TOOLBAR`、`XC_MONTHCAL`、`XC_DATETIME`、`XC_PROPERTYGRID`、`XC_EDIT` / `XC_EDITOR`、`XC_TABBAR`、`XC_TEXTLINK`、文件/文件夹选择编辑框、布局元素（`XC_ELE_LAYOUT` / `XC_LAYOUT_FRAME`）等

- **形状与绘图对象**：`XC_SHAPE` 及其子类型 `XC_SHAPE_TEXT` / `XC_SHAPE_PICTURE` / `XC_SHAPE_RECT` / `XC_SHAPE_ELLIPSE` / `XC_SHAPE_LINE` / `XC_SHAPE_GROUPBOX` / `XC_SHAPE_GIF` / `XC_SHAPE_TABLE`；绘图与图片 `XC_HDRAW`（绘图操作对象）、`XC_IMAGE_TEXTURE`（图片源/纹理）、`XC_IMAGE_FRAME`（图片帧/渲染属性封装）、`XC_SVG`（SVG 对象）

- **数据与布局**：适配器系列 `XC_ADAPTER` / `XC_ADAPTER_TABLE` / `XC_ADAPTER_TREE` / `XC_ADAPTER_LISTVIEW` / `XC_ADAPTER_MAP`；布局相关 `XC_LAYOUT_BOX` / `XC_LAYOUT_FRAME` 及若干内部布局类型；其它 `XC_BKINFOM`（背景管理器）、`XC_ANIMATION_SEQUENCE` / `XC_ANIMATION_GROUP` / `XC_ANIMATION_ITEM`（动画序列、组、项）

- **对象扩展类型（`XC_OBJECT_TYPE_EX`）**：按钮扩展类型 `button_type_default` / `button_type_radio` / `button_type_check` / `button_type_close` / `button_type_min` / `button_type_max` 等；布局扩展类型 `element_type_layout` 等，用于标记启用布局能力的元素

## 4. 事件系统（`xcgui_event.h`）

### 4.1 窗口事件（`WM_*` / `XWM_*`）

- 绘制与生命周期：`WM_PAINT`（窗口绘制事件，可拦截炫彩默认绘制进行自绘）、`WM_CLOSE` / `WM_DESTROY` / `WM_NCDESTROY`（即将关闭、即将销毁、非客户区销毁）

- 鼠标：`WM_LBUTTONDOWN` / `WM_LBUTTONUP` / `WM_LBUTTONDBLCLK`；`WM_RBUTTONDOWN` / `WM_RBUTTONUP` / `WM_RBUTTONDBLCLK`；`WM_MOUSEMOVE` / `WM_MOUSEHOVER` / `WM_MOUSELEAVE` / `WM_MOUSEWHEEL` / `WM_SETCURSOR`

- 键盘：`WM_KEYDOWN` / `WM_KEYUP` / `WM_CHAR`

- 尺寸与布局：`WM_SIZE` / `WM_EXITSIZEMOVE`（改变大小/退出改变大小或移动）

- 定时器与焦点：`WM_TIMER`（系统定时器）、`WM_SETFOCUS` / `WM_KILLFOCUS`（窗口获得/失去焦点）

- 其它：`WM_DROPFILES`（文件拖入，需启用 `XWnd_EnableDragFiles`）、`WM_OTHER`（未被炫彩预定义的其他 `WM_` 消息）、`XWM_WINDPROC`（窗口消息过程事件，可统一过滤所有消息）、`XWM_XC_TIMER`（炫彩自有定时器，区别于系统定时器），以及与托盘图标、菜单弹出与绘制、框架窗口浮动窗格、窗格显示等相关的 `XWM_*` 自定义消息

### 4.2 元素事件（`XE_*`）

- 通用与绘制：`XE_ELEPROCE`（元素事件过滤，统一拦截除 `XE_` 以外的所有事件）、`XE_PAINT` / `XE_PAINT_END` / `XE_PAINT_SCROLLVIEW`（元素绘制、绘制完成、滚动视图绘制）

- 鼠标：`XE_MOUSEMOVE` / `XE_MOUSESTAY` / `XE_MOUSEHOVER` / `XE_MOUSELEAVE`；`XE_MOUSEWHEEL`；`XE_LBUTTONDOWN` / `XE_LBUTTONUP` / `XE_LBUTTONDBCLICK`；`XE_RBUTTONDOWN` / `XE_RBUTTONUP`；鼠标捕获 `XE_SETCAPTURE` / `XE_KILLCAPTURE`；设置光标 `XE_SETCURSOR`

- 焦点与显示：`XE_SETFOCUS` / `XE_KILLFOCUS`；`XE_SIZE`（大小改变）；`XE_SHOW`（显示/隐藏）；字体变更 `XE_SETFONT`

- 键盘：`XE_KEYDOWN` / `XE_KEYUP` / `XE_CHAR`；系统键 `XE_SYSKEYDOWN` / `XE_SYSKEYUP`

- 列表/列表框/列表树/列表视图：

  - 模板生命周期 `XE_LISTBOX_TEMP_CREATE` / `XE_LISTBOX_TEMP_CREATE_END` / `XE_LISTBOX_TEMP_DESTROY`，`XE_LIST_TEMP_CREATE` / `XE_LIST_TEMP_CREATE_END` / `XE_LIST_TEMP_DESTROY`，`XE_TREE_TEMP_CREATE` / `XE_TREE_TEMP_CREATE_END` / `XE_TREE_TEMP_DESTROY`，`XE_LISTVIEW_TEMP_CREATE` / `XE_LISTVIEW_TEMP_CREATE_END` / `XE_LISTVIEW_TEMP_DESTROY`

  - 绘制 `XE_LISTBOX_DRAWITEM` / `XE_LIST_DRAWITEM` / `XE_TREE_DRAWITEM` / `XE_LISTVIEW_DRAWITEM`

  - 选择 `XE_LISTBOX_SELECT` / `XE_LIST_SELECT` / `XE_TREE_SELECT` / `XE_LISTVIEW_SELECT`

  - 展开/折叠 `XE_TREE_EXPAND` / `XE_LISTVIEW_EXPAND`

- 滚动与进度：`XE_SCROLLVIEW_SCROLL_H` / `XE_SCROLLVIEW_SCROLL_V`；`XE_SBAR_SCROLL`（滚动条滚动）；`XE_SLIDERBAR_CHANGE`（滑动条改变）；`XE_PROGRESSBAR_CHANGE`（进度条改变）

- 菜单：`XE_MENU_POPUP` / `XE_MENU_POPUP_WND` / `XE_MENU_SELECT` / `XE_MENU_EXIT`；菜单绘制 `XE_MENU_DRAW_BACKGROUND` / `XE_MENU_DRAWITEM`

- 编辑框与代码编辑器：`XE_EDIT_SET` / `XE_EDIT_CHANGED` / `XE_EDIT_POS_CHANGED` / `XE_EDIT_STYLE_CHANGED`；`XE_EDIT_ENTER_GET_TABALIGN`（回车 TAB 对齐）；`XE_EDITOR_MODIFY_ROWS`（多行编辑内容修改）

- 其它：`XE_BNCLICK` / `XE_BUTTON_CHECK`（按钮点击与选中）；`XE_TABBAR_SELECT` / `XE_TABBAR_DELETE`；`XE_MONTHCAL_CHANGE`；`XE_DATETIME_CHANGE` / `XE_DATETIME_POPUP_MONTHCAL` / `XE_DATETIME_EXIT_MONTHCAL`；属性网格 `XE_PGRID_VALUE_CHANGE` / `XE_PGRID_ITEM_SET` / `XE_PGRID_ITEM_SELECT` / `XE_PGRID_ITEM_ADJUST_COORDINATE` / `XE_PGRID_ITEM_DESTROY` / `XE_PGRID_ITEM_EXPAND`；文件拖入 `XE_DROPFILES`

## 5. C++ 封装类（`module_xcgui_class.h`）

- **`CXBase`**：所有 C++ 封装类的基类，定义虚函数 `GetHXCGUI()`；类型查询接口 `GetType()`（对象最终类型 `XC_OBJECT_TYPE`）、`GetTypeBase()`（基础类型，如 `XC_WINDOW` / `XC_ELE` / `XC_SHAPE` / `XC_ADAPTER`）、`GetTypeEx()` / `SetTypeEx()`（获取/设置扩展类型，如按钮类型）

- **`CXObjectUI`**：继承 `CXBase`，面向一切可视对象（窗口、元素）的公共操作

  - 样式与 CSS：`SetStyle` / `GetStyle`（设置/获取 `XC_OBJECT_STYLE`）；`EnableCSS` / `EnableCssEx`（启用/禁用 CSS 样式，含或不含内嵌子元素）；`SetCssName` / `GetCssName`（设置/获取 CSS 套用样式名称）

- **`CXWindow`**：继承 `CXObjectUI`，封装窗口全部操作（创建/事件/布局/重绘/交互/拖放/DPI/子对象访问等）

- 其余元素、控件、适配器等 C++ 类封装，通常遵循：持有句柄 + 提供一一对应成员函数 + 通过类型系统减少句柄传错

## 6. 使用建议与最佳实践（代码侧，含 CSS 主题加载）

- **统一事件模型**：窗口事件与元素事件均通过 `xcgui_event.h` 中的 `WM_*` / `XWM_*` / `XE_*` 统一描述

- **优先使用 C++ 封装**：C++ 工程优先用 `module_xcgui_class.h` 的封装类；仅在兼容/性能有特殊需求时使用 C API

- **样式与 CSS 一致化**：用 `EnableCSS` / `EnableCssEx` 与 `SetCssName` 统一主题管理

- **模板与适配器机制**：列表/树/列表视图等在 `XE_*_TEMP_CREATE(_END)` 做绑定与填充

- **DPI 与多显示器适配**：`SetDPI` / `GetDPI` 配合 CSS 与 `HSVG` 做高 DPI 适配

- **与基础模块协同**：文本/文件/时间/路径等交给 `module_base`，GUI 只负责渲染与交互

### 6.1 典型使用场景（思路级）

- 创建主窗口并启用布局：`Create(...)` → `EnableLayout(TRUE)` → 添加子控件 → 注册事件处理交互

- 列表/树/列表视图 + 模板展示业务数据：适配器准备 → 模板创建/绘制事件填充 → 状态驱动颜色/图标

- 复杂 IDE 场景：`XC_PROPERTYGRID` + `XC_EDITOR` + `XC_TABBAR` + 布局元素组合

- **@斗鱼55：拖文件导入列表（工程级闭环示例）**：`listUI` + `list.itemTemplate="List1.xml,8"`，列 `name1..name8`，拖放事件导入并填充

### 6.2 事件回调（推荐组织方式）

- **UI事件函数**：处理设计器控件事件（按钮点击、绘制、弹出列表、弹出月历等）

- **「事件类继承主窗口类」**：示例工程用 `类 列表框事件 继承 主窗口类` 复用主窗口的成员与句柄，写回调更方便（能直接访问 `_列表框1` 等对象）

- **拦截参数**：很多 UI 事件提供 `逻辑型* 是否拦截`，需要阻止默认行为时才改它

### 6.3 易错点

- **资源加载顺序**：先 Base（字体/共用色）再主题（Light/Dark），否则可能出现字体/颜色引用缺失

- **主题切换后要重绘**：切换 `.res/.css` 后调用 `重绘()`，否则部分控件不会立刻刷新

- **列表模板事件**：想操作模板内部子控件，必须等「模板创建完成事件」触发后再取对象/绑定事件

- **少用指针**：文本/内存优先用 `文本型`、`字节集`


### 6.4 CSS 样式文件加载与「加载样式文件失败」排查

> 来源：`炫彩界面库.mdc` §9.4–§9.6。

**执行顺序（源 §9.4 示例代码原形）**：主题资源按 Base → 主题 `.res` → 主题 `.css` 顺序加载，全部在 `显示(真)` **之前**。

```xc
正整型 资源大小
常量 空类型  *局_UIzip = RC资源查找文件从ID(IDR_UI_ZIP, &资源大小)
炫彩_加载资源文件内存ZIP(局_UIzip, 资源大小, "WmUi\\WmUi_Base.res")
炫彩_加载资源文件内存ZIP(局_UIzip, 资源大小, "WmUi\\Dark\\WmUi.res")
炫彩_加载样式文件从资源ZIP(IDR_UI_ZIP, "WmUi\\Dark\\WmUi.css")

显示(真)
```

- 已在控件绘制完成后再加载/切换主题时，额外调用 `重绘()` 确保立即刷新；`炫彩_启用自动重绘UI(真)` 可在改 UI 后自动触发。
- **成对切换**：Light ↔ Dark 不要只换 `.css` 或只换 `.res`，两者都换再 `重绘()`。
- 两种加载入口：`炫彩_加载样式文件("xxx.css")`（磁盘文件，路径**相对运行目录**）与 `炫彩_加载样式文件从资源ZIP(IDR_UI_ZIP, "WmUi\\Dark\\WmUi.css")`（内嵌 ZIP 资源）。
- 按需加载布局文件：`炫彩_加载布局文件("布局文件\\msg.xml", 父窗口句柄)`（适合弹窗/子窗口快速复用）。

**「加载样式文件失败：xxx.css(行号)」排查顺序**（源 §9.5，`斗鱼55` 实战）：

1. **编码**：CSS 建议 **UTF-8 无 BOM**；工程含中文路径/中文注释时更要统一编码，否则解析器可能直接报行号。
2. **不要用 `/* ... */` 块注释**：某些版本的解析器把块注释当语法错误，报错行号落在注释行或附近。**CSS 内不写注释**，备注写到 `.mdc` 或外部文档。
3. **只用示例工程出现过的属性**：`WmUi.css` 里稳定出现的只有 `bkInfoM`、`transparent`、`padding`、`border`、`textColor`、`caretColor`。写没见过的字段（如 `bkColor`、`borderColor`、`radius`）可能触发解析失败（取决于当前炫彩版本的 CSS 语法支持）。**结论：高质量皮肤（背景色/圆角/边框/渐变）优先走 `bkInfoM` + `resource.res` 的 `type_bkInfo`/`type_color`。**
4. **路径与工作目录**：`炫彩_加载样式文件("xxx.css")` 的路径是**相对运行目录**（不是相对工程目录）。CSS 放在工程子目录时要拼出子目录，例如 `炫彩_加载样式文件("斗鱼55\\douyu55.css")`。
5. **最小化复现**：先建一个只有 1 条规则的 css（例如只写 `transparent:true;`），确认能加载后再逐步加规则，快速定位是哪条规则/哪行失败。
### 6.5 句柄、事件签名与复选框状态（当前 XCGUI 实战）

**先区分三种对象**：`HWINDOW` 是 XCGUI 窗口句柄，`HWND` 是系统窗口句柄（用 `XWnd_GetHWND` 取得），`HELE` 是元素／按钮句柄。即使某 API 的形参写成通用 `HXCGUI`，也不要未经当前头文件和运行验证就假定 `HWINDOW` 能安全传入 `XWidget_IsShow`。本项目实测该混用会导致界面自检卡住；窗口可见性统一经系统 HWND 判断，元素／形状仍使用其对应 XCGUI API。

- 元素显示：`XWidget_Show(hEle, ...)`；窗口显示：`XWnd_Show(hWindow, ...)`；窗口可见：系统 `IsWindowVisible(hwnd)`。可封装只接受本进程窗口的辅助函数，先 `IsWindow`、`GetWindowThreadProcessId` 校验 PID，再查询可见性；辅助函数名保持英文、`//@别名` 写中文，模块源文件继续 UTF-8-BOM。
- `XWnd_CloseWindow` 发送 `WM_CLOSE`；`XWnd_DestroyWindow` 是立即销毁。两者不是同一条生命周期路径。需要验证关闭事件和重开时，走前者并注册 `XWnd_RegEventC1(..., WM_CLOSE, ...)`，回调清空对应缓存句柄；重新打开必须重建列表适配器、模板和事件绑定。
- 设置辅助窗 owner 时使用 `SetWindowLongPtrW(hwnd, GWLP_HWNDPARENT, owner)`，先校验两个 HWND 均属于当前进程且不同。关闭主窗顺序：停轮询定时器 → 停止工作线程／监听并释放状态 → 断开／恢复外部状态 → 销毁辅助窗和主窗 → `炫彩_退出()`；关闭回调与消息循环结束后的清理应能幂等执行。
- **C 与 C1 不是可互换别名**：当前 `module_xcgui.h` 明示 `XEle_RegEventC` 省略自身元素句柄，`XEle_RegEventC1` 包含自身句柄。以当前事件头文件原型补参数，不要一律给回调强加 `hEle`。例如 C1 点击为 `(HELE hEle, BOOL *pbHandled)`；C1 选中为 `(HELE hEle, BOOL bCheck, BOOL *pbHandled)`，均加 `UI事件`／匹配的调用约定。

```xc
函数 UI事件 整型 状态按钮_点击(元素句柄 来源句柄, 逻辑型 *是否拦截)
	如果 (是否拦截 != 空)
		*是否拦截 = 真
	运行状态_切换()       // 可能失败，必须读取真实结果
	按钮_置选中(来源句柄, 运行状态_实际已启用())
	返回 0
```

**`XE_BNCLICK` 回调返回后，check 按钮仍可能发生默认翻转。** 已实测：业务层正确拒绝了操作并置回未选中，默认行为又把复选框翻回去。若状态由业务／运行层持有，只对这些复选按钮设 `*是否拦截 = 真`，并在每条成功、失败、停止路径同步真实状态；不要全局拦截普通配置复选框，也不要只测布尔业务变量而漏查 `XBtn_IsCheck`。

### 6.6 用真实事件做界面回归，不以“绑定存在”代替“行为正确”

1. 启动时检查实际 `XWnd_SetTimer` 返回值；未创建轮询定时器就明确失败，不把“已初始化”写成固定真。
2. 用 `XEle_SendEvent(hEle, XE_BUTTON_CHECK, 真, 0)` 或 `XE_BNCLICK` 驱动实际注册路径；这不是物理键鼠输入。逐一断言页面互斥显示、尺寸大于零、适配器／模板存在、保存与取消结果、按钮状态和错误路径。
3. 页面和辅助窗均用实际可见性判断；分别测加载／显示、关闭事件清句柄、从真实动作路径重开。多个辅助窗的 owner 可核对，主窗关闭须验证进程退出及残留窗口为零。
4. 日志放在事件前、事件返回后和每组断言后，便于定位“注册失败、事件没进、事件中阻塞、断言失败”。保存每次唯一报告目录，记录通过、失败及 `not_run`；未测试项不能计为通过。
5. 定向测试仅枚举本次新启动进程的线程窗口，并只向该进程主 HWND 投递 `WM_CLOSE`；不要向用户桌面制造全局输入、枚举或读写无关进程。进程退出后无窗口不等于系统里无 hook，工作线程／hook 清理要由实际生命周期断言分别证明。

若“创建窗口成功”却没有 UI 消息循环，只同步触发控件事件和检查可见性不足以证明交互正确；正常窗口模式应由独立持有进程句柄的关闭测试覆盖真实消息循环。静态核对控件 `name`／动作 ID 很有用，但不能替代本节动态检查。

### 6.7 原生鼠标、延迟模板与公共文件对话框回归（2026-11-07 实战）

`XEle_SendEvent` 适合验证业务路由，真实鼠标适合验证命中、焦点、布局和消息循环；两者互补，不能互相冒充。一次大型原生 UI 回归中，以下流程解决了首击丢失、列表“有数据但未呈现”、文件路径不回填和模态时序误判。

1. **真实点击先做所有权与坐标守护**：
   - 仅驱动本次启动且持有进程对象的程序；点击前确认前台窗口属于该 PID。`GetForegroundWindow()` 在焦点切换瞬间可能返回空句柄，应短轮询重试，不能当成点击失败或直接把空值传给字符串／整数转换。
   - 等后台 `busy=0` 且窗口矩形连续两次稳定，再读取控件的实际 DPI 客户区矩形；经 `ClientToScreen` 换算后用 `WindowFromPoint` 核对屏幕落点仍属于目标 PID，再执行鼠标按下／抬起。窗口仍在布局动画或首次显示时直接点击，会出现偶发首击无效。
   - Python `ctypes` 必须声明 64 位 `HWND` 等参数的 `argtypes/restype`，避免句柄截断；文本读取使用 Unicode 缓冲区。不得为了自动化向其他进程窗口发送输入，也不按进程名全局清理。
2. **后台表、适配器和可见单元格分开断言**。适配器行／列数正确，只证明数据已进入控件模型；模板可能延迟创建，实际可见单元格仍暂时为零。分别记录适配器行列数、可见单元格样本和前后台文本一致性，并短轮询模板完成，不把首次可见样本为空直接当产品缺陷，也不把最终截图当作适配器正确的证据。筛选／排序后还要检查选中行的真实对象地址没有跟着视觉行号错位。
3. **模态文件对话框必须等“关闭 + 业务回填”**。`GetOpenFileNameW` 等模态调用返回前，应用通常尚未执行路径赋值和加载逻辑。测试顺序是：触发按钮 → 找到同 PID 的 `#32770` → 提交文件名 → 等对话框 `IsWindow/IsWindowVisible` 消失 → 等应用空闲 → 用“输入路径等于预期、目标表已加载、导出内容正确”等条件等待。仅调用一个无条件的 `wait()` 会立即读到旧的空路径，造成“对话框成功但未回填”的假判断；对话框关闭本身也不等于文件加载成功。
4. **新版 Windows 公共文件对话框不要只写内部 Edit**。当前实测对话框含 `ComboBoxEx32`、`ComboBox` 和 `Edit`，文件名状态可能仍保存在组合框；只 `SetWindowTextW` 内层编辑框，文字虽可读回，点“打开”却不提交。优先用真实键盘粘贴／UI Automation；若使用 Win32 测试助手，可在同 PID 守护下采用本次验证的组合：定位 `ComboBoxEx32` 下的文件名组合框 → 写组合框文本 → 对编辑框 `EM_SETSEL` 并发送 `WM_CHAR` 产生修改通知 → 对实际“打开”按钮 `BM_CLICK`。这是当前环境的测试助手经验，不是所有 Windows 版本的固定协议；最终仍以路径回读、对话框关闭和应用加载结果为准。按钮尽量用控件 ID／类与父子关系定位，不依赖可能乱码的中文标题。
5. **快捷键与元素／窗口双层事件避免重复路由**。同一动作同时绑定元素和窗口时，只保留一个执行入口，或在元素回调将 `pbHandled` 设为真；否则一次按键可能执行两次。回归应断言动作计数或业务结果只变化一次，而不只看回调“进过”。
6. **证据要足以复盘失败**。每一步保存状态 JSON、适配器计数／样本、实际窗口矩形和截图；异常时另存 traceback、前台窗口与同 PID 对话框子控件树。最后走正常关闭路径并记录真实退出码，恢复测试占用的剪贴板等状态。失败目录不删除，成功结果也不覆盖先前失败证据。

## 7. 列表适配器与弹窗 / 拖放

### 7.1 列表类控件：模板 + 适配器 + 生命周期事件

- **列表框（listBox）**：模板 `置项模板从资源ZIP(IDR_UI_ZIP, "列表框项模板.xml")`；适配器 `创建数据适配器()` 然后 `添加项文本(...)`；模板创建完成事件用于拿到模板内子控件句柄并注册事件，典型用法为 取模板对象 → 置文本 → `元素_注册事件CPP1(...)`

- **列表（list）**：模板 `置项模板从资源ZIP(...)`；列与行 `列表头创建数据适配器()` + `添加列文本(width, name, title)`，`添加行文本扩展(colName, text)` + `置项文本扩展(row, colName, text)`；模板创建完成事件常用于「编辑/删除按钮」的点击事件绑定

- **列表树（tree）**：模板 `置项模板从资源ZIP(...)`；数据 `创建数据适配器()` + `插入项文本(text, parentId?)`

- **列表视图（listView）**：模板 `置项模板从资源ZIP(..., "列表视图项模板.xml", 空, 空)`；分组与项 `组添加项文本(...)`、`项添加文本扩展(group, colName, text, ...)`、`项置图片扩展(...)`

### 7.2 代码补样式（何时用、怎么用）

- **滑动条滑块**：`取滑块()` 得到子对象句柄，直接 `可视对象_置CSS名称(...)` 套按钮样式即可

- **菜单条**：放在容器里只解决布局，按钮样式通常要代码补——`可视对象_启用CSS(句柄, 真)` + `可视对象_置CSS名称(...)`；弹出菜单可开启用户绘制 `启用用户绘制项/背景(真)`，并在事件回调中绘制背景/项

- **日期时间/月历卡片**：常见需要 `Wm_日期时间_置样式(...)`、`Wm_月历卡片_置样式(...)` 这类封装函数处理内部子对象样式

- 滑块/菜单/日期时间/月历等内部子对象：必要时用代码补 `CSS 名称` 或封装统一置样式函数

### 7.3 弹窗与通知

- `msg.xml` 复用 + 模态返回值（用户数据 → `模态窗口_结束`）；轻提示用窗口内通知；阻塞选择用模态框

- **「模态消息框」封装成静态类**（例子2 封装为 `静态 类 弹出消息框类`）：布局复用（弹窗布局独立成 `布局文件\msg.xml`）；创建方式 `炫彩_加载布局文件("布局文件\\msg.xml", 父窗口句柄)`；图标策略通过 `XRes_GetImage(picName)` 从资源取图，「资源加载的图标不用释放」（按示例写法）；按钮返回值给按钮写 `元素_置用户数据(hEle, 1)`，点击回调里 `模态窗口_结束(_hWnd, 元素_取用户数据(来源句柄))` 把选择结果带出去；自动关闭与交互 `模态窗口_启用自动关闭(_hWnd, 自动关闭)`

- **「窗口中弹出通知消息」（轻提示）**：例子2 的登录校验失败用 `通知消息_窗口中弹出扩展(_句柄, 位置标识_中心, "提示", "请输入账号", 资源_取图片("warning.png"), 通知消息外观_错误, 假)`；适合「不打断流程」的提示，需要阻塞用户时再用模态消息框

### 7.4 文件拖放导入（闭环范式）

允许拖放 → 绑定 `元素事件_文件拖入` → 限长 + 分隔符优先级 + 列数稳定。

**@斗鱼55：拖文件导入到 `listUI`（两窗口 + 拖放 + 文本解析）**，参考工程目录 `斗鱼55/`：

- 窗口与布局：启动窗口 `斗鱼55/main.xc` + `斗鱼55/main.xml`（点击按钮进入主界面：`按钮1` 点击事件中调用 `indx.运行()`，然后关闭自身）；主界面 `斗鱼55/index.xc` + `斗鱼55/index.xml`，`listUI` 使用项模板 `list.itemTemplate="List1.xml,8"`（8 列字段绑定），列表容器 `布局元素1` + 列表 `列表1`

- 列表列定义（代码侧）：在 `Cindex.运行()` 中先初始化列再显示窗口——`添加列文本(width, field, title)` 依次定义 `name1..name8`；模板绑定（XML 侧）`List1.xml` 通过 `{binding field=nameX}` 把列字段映射到 `shapeText`

- 拖放导入关键点：让列表控件接收拖放 `A文件拖放_允许(_列表1.取窗口句柄系统(), 真)`；绑定拖放事件 `[元素事件_文件拖入, 列表1_文件拖放, 1]`；读取路径 `A文件拖放_取拖放文件(hDropInfo, 0, 路径, 1000)`；刷新数据先 `_列表1.删除行全部()` 再导入

- 文本/CSV/TAB 解析策略（可直接复用）：限长读取最大 10MB（避免异常大文件导致内存占用过高）；按行拆分——读取为 `文本型A`，用 `文本分割A(内容, A"\n")` 并去掉 `\r`；分隔符优先级 `\t` → `,` → `|` → 空格；字段不足补空（不足的列保持空字符串）；字段超出合并到 Ret（name8），把多余字段用空格拼接到最后一列，保证表格列数稳定

- 该工程是「拖放文件 → 文本解析 → 列表列字段 → XML 模板绑定」的最小闭环范例，适合当成「数据导入页面」的模板

### 7.5 易错点

- 想操作模板内部子控件，必须等「模板创建完成事件」触发后再取对象/绑定事件

- 拖放导入前需先 `删除行全部()` 再导入，否则旧数据残留

## 8. 系统API 前缀分组索引

> 来源：`系统API(前缀分类法).mdc`（全文）。**本节只保留分组索引与「去哪里查签名」的指引，不补任何函数原型。** 源材料本身只有分组、无逐函数正文；所有签名请查 `module_windowsApi.h`。

模块头信息：`//@模块名称 系统API(前缀分类法)`、`//@版本 1.0`、`//@日期 2025-01-21`、`//@作者 XCGUI`、`//@模块备注 windows-API（前缀分类命名法封装）`、`//@依赖 module_base.h`。

**简介**：本模块把常用 Windows API 以「前缀分类命名法」重新命名，避免与其他模块/项目符号冲突。统一前缀 **`A`** 代表「系统API模块」；命名示例 `A线程_创建()`、`A目录_创建()`。Windows API 参考文档：<https://learn.microsoft.com/zh-cn/windows/win32/api/>。

**文档结构约定（如何从 `module_windowsApi.h` 读懂所有接口）**

- **分组**：使用 `//@分组{ ... }` 与 `//@分组}` 包住一段相关 API

- **别名**：每个 API/常量前都会有一行 `//@别名 ...`，其后的函数原型/宏定义即为「原始声明」

- **参数/返回/备注**：同一段中会紧邻 `//@参数`、`//@返回`、`//@备注` 对应 WinAPI 的中文说明

**分组索引（来自 `module_windowsApi.h`）**

路径、窗口、窗口消息、对话框、文件拖放、坐标、HOOK、文件管理、内存管理、资源管理、插入符-光标-图标、临界区、互斥对象、等待操作、信号量功能、事件对象、通信管道、线程、进程、外壳程序、GDI绘图、菜单、结构体、其他。

**快速定位技巧**

- **按分组跳转**：在 `module_windowsApi.h` 内搜索 `//@分组{ 线程`、`//@分组{ 窗口` 等

- **按别名搜索**：直接搜 `A线程_` / `A窗口_` / `A文件_` / `A路径_` 等前缀

- **按 WinAPI 名称反查**：搜 `CreateFile`、`CreateThread`、`SendMessage` 等原始 API 名称，可对照其上方的 `//@别名` 获取「前缀分类名」

**@斗鱼55 关联点（文件拖放）**：`斗鱼55/index.xc` 用「文件拖放」分组下的接口把文件拖入列表控件完成导入：`A文件拖放_允许(HWND, 真)`（让目标窗口句柄允许接收拖放）、`A文件拖放_取拖放文件(HDROP, index, outPath, cch)`（从拖放信息读取文件路径）。定位方式：在 `module_windowsApi.h` 搜索 `//@分组{ 文件拖放` 或直接搜 `A文件拖放_`。

**备注（源材料遗留说明）**：源材料注明：本 `.mdc` 先提供分组与使用规则索引，便于快速理解模块组织方式；若要「每个分组下：别名 → 原始声明/定义」的完整清单，可按分组分批抽取并写入多个 `.mdc`（例如 `系统API-窗口.mdc`、`系统API-线程.mdc` 等），避免单文件过大。**本文件不生成这些原型清单。**

## 9. 线程池

> 来源：`线程池.mdc`（全文）

模块头信息：`//@模块名称 线程池`、`//@基于文件 module_threadpool.h, threadpool.cpp`、`//@版本信息 头文件标注 v1.1 (2023-08-27)`、`//@依赖 module_base.h（以及 Windows API）`、`//@备注 示例见：示例\模块示例\xc-线程池`。

### 9.1 模块概述与文件结构

轻量的「任务线程池」，把耗时任务投递到后台线程并发执行，避免阻塞主线程/UI 线程。实现上使用 Windows 的 IOCP（完成端口）作为任务队列，工作线程阻塞在 `GetQueuedCompletionStatus()` 上等待任务到来；每个任务以 `std::function<void()>` 的形式入队，在工作线程中执行。

- `module_threadpool.h`：对外接口（`ThreadPoolPro` 类、状态枚举、任务投递模板等）

- `threadpool.cpp`：线程池实现（创建/销毁、线程循环、清空任务、状态处理、计数维护）

- `示例\模块示例\xc-线程池\main.xc`：XC语言示例（创建、投递任务、等待完成、销毁）

### 9.2 线程模型（核心机制）

- **任务队列**：`PostQueuedCompletionStatus()` 把任务指针投递到 IOCP

- **工作线程**：`ThreadPoolWorkerThread()` 循环调用 `GetQueuedCompletionStatus()` 获取任务并执行

- **暂停/继续**：暂停时工作线程在 `hResumeSemaphore` 上等待；继续时释放信号量唤醒

- **退出**：销毁时向 IOCP 投递特殊状态码 `10086` 让线程跳出循环，同时释放 `hExitSemaphore` 让 `IsNeedExit()` 可检测退出信号

> 注意：任务对象由 `new std::function<void()>` 创建，工作线程使用 `std::unique_ptr<std::function<void()>>` 接管，确保正常/异常路径都会释放内存。

### 9.3 状态枚举（`ThreadPoolState` / 线程池状态）

`ThreadPoolState_Closed`（已关闭）、`ThreadPoolState_Closing`（正在关闭）、`ThreadPoolState_Starting`（正在创建）、`ThreadPoolState_Normal`（正常工作，可投递任务）、`ThreadPoolState_Adjust`（正在调整容量）、`ThreadPoolState_Suspend`（暂停）、`ThreadPoolState_Clear`（正在清空任务）。多数对外操作会检查 `state`，只有在 `Normal`（或「>= Normal」）时才允许投递/调整。

### 9.4 对外类与 API（`ThreadPoolPro` / 线程池类）

**生命周期**

- **创建(线程数量)** `CreateThreadPool(int32_t Capacity = 0) -> BOOL`：`Capacity <= 0` 时默认使用 `CPU核心数 + 1`；会创建 `Capacity` 个工作线程并 detach；成功后状态变为 `ThreadPoolState_Normal`

- **销毁(是否强制销毁, 最长等待时间)** `DestroyThreadPool(BOOL ForceDestroy = TRUE, int32_t WaitTime = -1) -> BOOL`：`ForceDestroy=TRUE` 更快退出（会投递退出信号并清理队列任务）；`ForceDestroy=FALSE` 最多等待 `WaitTime` 毫秒（`-1` 表示不限时）让线程自然收尾，内部会间隔 `Sleep(50)` 并调用 `ProcessMessage()` 防止 UI 卡死；如果线程池处于暂停状态，会强制销毁（避免等待卡住）

> 建议：若希望「任务全部做完再退出」，在销毁前先等待队列/执行计数归零（见示例）。

**任务投递**（只有在线程池存在且状态 `>= ThreadPoolState_Normal` 时投递才会成功）

- **投递任务()** `PostTask(Fun&& fun, Args&&... args) -> BOOL`：支持任意可调用对象与参数（内部 `std::bind` 绑定后入队）。投递成功时队列计数 `QueueTask++`；工作线程取到任务后 `QueueTask--`，执行时 `WorkerTask++`，完成时 `ComplateTask++` 并 `WorkerTask--`。投递失败会回滚 `QueueTask--` 并释放任务对象，避免内存泄漏与计数异常

- **投递任务2(执行函数)** `PostTask2(Fun& fun) -> BOOL`：适用于「无参数任务函数」

**控制与维护**

- **暂停()** `SuspendThreadPool() -> BOOL`；**继续()** `ResumeThreadPool() -> BOOL`

- **清空任务()** `ClearTask() -> BOOL`：若线程池处于暂停，会直接启动清空线程并等待清空完成；若处于正常，将状态置为 `Clear`，工作线程收到任务时会丢弃任务对象并递减队列计数，直到队列清空后自动回到 `Normal`

- **调整线程池(新线程数)** `SetThreadPoolCapacity(int32_t nNewThreadNum) -> BOOL`：扩容时创建新线程并维护 `ThreadsCount` 计数；缩容时状态置为 `Adjust`，投递若干「空任务」触发部分线程自我终结，直到 `ThreadsCount == Capacity`

**查询接口（计数/状态）**

```text
GetProcessorsCount() -> int32_t            取CPU核心数()
GetThreadsCount() const -> int32_t         取现行线程数()
GetThreadsCapacity() const -> int32_t      取线程池容量()
GetWorkerTaskCount() const -> int32_t      取执行任务数()
GetQueueTaskCount() const -> int64_t       取队列任务数()
GetComplateTaskCount() const -> int64_t    取已完成任务数()
GetFreeThreadsCount() const -> int32_t     取空闲线程数()
GetThreadPoolState() const -> int32_t      取工作状态()
ThreadPoolIsFree() const -> BOOL           是否空闲()，条件 QueueTask == 0 && WorkerTask == 0
IsNeedExit(int32_t nMillseconds = 0) -> BOOL  是否需要退出(最大检查等待时间)，通过等待 hExitSemaphore 判断是否收到退出信号
```

### 9.5 XC 语言用法示例（来自示例工程）

典型流程：1) 创建线程池 → 2) 投递任务 → 3) 主线程等待所有任务完成（队列数与执行数都为 0） → 4) 优雅销毁线程池。

示例（节选思路，完整代码见 `示例\模块示例\xc-线程池\main.xc`）：全局声明线程池对象，保证生命周期足够长，避免局部变量提前析构触发销毁；用 `取队列任务数()` + `取执行任务数()` 等待任务完成后再退出。

### 9.6 易错点与最佳实践

- **线程池对象生命周期**：若在函数局部创建 `ThreadPoolPro`，函数结束会调用析构，从而触发 `DestroyThreadPool(FALSE, 2000)`；若仍有后台任务在跑，可能导致任务被清理/线程退出。建议把线程池对象放到更长生命周期（全局/成员变量）

- **任务函数异常**：工作线程执行任务时会捕获所有异常并吞掉，避免线程崩溃；因此建议在任务内部自行记录错误信息

- **UI 程序销毁**：若在 UI 线程调用「非强制销毁并等待」，内部会 `ProcessMessage()` 防止窗口假死，但仍建议在退出流程里明确等待条件与超时策略

- **清空任务的语义**：`ClearTask()` 会丢弃队列中尚未执行的任务（释放任务对象），不保证这些任务会执行

