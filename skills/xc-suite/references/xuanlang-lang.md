# xuanlang-lang — 炫语言语法 / 类型 / 容器 / 入口 / 预处理 / 基础模块

> 来源：`xc-代码\炫语言手册总结.mdc`（§1–§24）、`xc-代码\基础模块.mdc`（§1–§7）。

> 类型名/函数名/宏名/前缀名逐字保留；示例代码保持源材料的可编译形态，未改写任何签名。

> **范围边界**：`炫彩界面库.mdc` 中属于界面/皮肤侧的 CSS 属性与选择器内容（`css.name`、`bkInfoM`、`buttonUI`/`editUI`、`transparent`/`padding`/`border`/`textColor`/`caretColor`、`bkColor`/`borderColor`/`radius`、`type_bkInfo`/`type_color`、`.res`/`.css` 资源链）不在此展开，见 `bkinfom-res.md` / `interface-xml.md`；本文件只保留其在代码侧的调用入口（`EnableCSS`/`EnableCssEx`/`SetCssName`、`可视对象_启用CSS`/`可视对象_置CSS名称`）。XCGUI 代码侧与线程池见 `xcgui-code.md`。

## 1. 语言语法与类型

### 1.1 数据类型对照（炫语言 / C++ / 易语言 / 火山PC）

| 炫语言 | C++ 对应 | 大小 |
| --- | --- | --- |
| 字节型(无符号) | `BYTE` | 1 |
| 字符型A(有符号) | `char` | 1 |
| 字符型 | `wchar_t` | 2 |
| 短整型 / 正短整型 | `short` | 2 |
| 整型 / 正整型 | `int` | 4 |
| 长整型 / 正长整型 | `int64` | 8 |
| 变整型 | `vint(int32,int64)` | 4/8 |
| 浮点型 | `float` | 4 |
| 双浮点型 | `double` | 8 |
| 逻辑型 | `BOOL` | 4 |
| 逻辑型c | `bool` | 1 |
| 文本型 | `wstring` | — |
| 文本型A / 单文本型 | `string` | — |
| 字节集 | 二进制/内存容器 | — |
| 指针 `*` | 指针 | 4/8（随平台） |

字面量：**字符**用单引号 `'a'` / `A'a'`；**文本**用双引号 `"abc"` / `A"abc"`。类型别名宏：`单文本型->文本型A`、`单字符型->字符型A`。

### 1.2 系统关键字对照（炫语言中文/英文 ↔ C++）

- 流程/控制：`如果/否则`(`if/else`)、`循环`(`while`)、`变量循环`(`for`)、`分支判断`(`switch`)、`跳出`(`break`)、`到循环尾`(`continue`)

- 结构/面向对象：`结构体`(`struct`)、`类`(`class`)、`公开/私有/保护`(`public/private/protected`)、`继承`(`inherit`)、`虚函数`(`virtual`)、`重写`(`override`)

- 函数：`函数`(`def`)、`返回`(`return`)、`WINAPI`(`__stdcall`)

- 内存：`new` / `delete`

- 预处理/声明：`#头文件` / `#库文件` / `#宏定义` / `#外部类型` / `#外部变量` / `#函数类型`

- 特殊常量：`空`(`NULL`)、`本类`(`this`)、`真/假`(`TRUE/FALSE`)、`逻辑真/逻辑假`(`true/false`)

- 入口：`入口函数`(`main`)、`入口函数_窗口`(`WinMain`)

### 1.3 运算符

算术 `+ - * / %`；赋值 `= += -=`；比较 `== != < > <= >=`；逻辑 `&& || !`；位运算 `& | ^ << >>`；自增自减 `++ --`；取地址与指针 `&变量`（取地址）、`*p`（解引用，修改指向内容）、`对象指针->成员`。

**条件表达式兼容（当前工具链实测）**：遇到 `条件 ? 值1 : 值2` 在“解析遇到错误”处失败，不要继续堆 C/C++ 表达式或反复猜类型；改为明确的 `如果／否则`。这是一项版本兼容经验，不据此宣称所有版本都禁用该语法。即便某些位置支持，也应优先使用当前工程已有且实际编译通过的写法：

```xc
文本型 状态 = "未连接"
如果 (已连接)
	状态 = "已连接"
否则
	状态 = "未连接"
```

普通取文本、布尔同步、数值格式化都可能触发同类问题；按 IDE 报告的文件／行号最小修复，再以真实构建确认，不能只修 C++ 缓存文件。

### 1.4 流程控制

- `如果(条件)` → `否则(条件)` → `否则`

- `循环(条件)`：条件真继续执行

- `循环判断首/尾`(do-while)：先执行再判断

- `变量循环(初始化; 条件; 递增)`(for)

- `变量循环扩展`(for_ex)：支持起始/目标/递增，并可忽略某些参数

- `计次循环`(for_count)：指定循环次数

- `列表循环`(for_list)：静态数组/动态数组遍历；字典遍历用 `迭代器 迭代器项; 字典`，通过 `迭代器项.键/.值` 访问

- `分支判断`(switch)：需要手动 `跳出`；`分支判断跳出` 自动跳出分支

- `跳出`(break) / `到循环尾`(continue)

- **字符串前缀匹配不是动作分类**：`名称.find("主程序__页签_") == 0` 才表示名称以此前缀开头；不要写成整个 `名称.find("页签") != -1` 后把所有动作 100–106 当页签。普通辅助窗口按钮可以恰好使用相同动作号，错误分流会把“返回工作台”误判成普通页签。动态页签名也允许存在，故不能只穷举固定名称。

### 1.5 字符串前缀（A / R / U）

- **A**：多字节字符串（`char`）；否则为宽字符串（`wchar_t`）

- **R**：原始字符串，不转义（路径推荐）：`R"(D:\Client\xx.pdf)"`、`AR"(D:\Client\xx.pdf)"`；不用 R 时路径要写双斜杠 `"D:\\Client\\xx.pdf"`

- **U**：UTF-8 字符串，如 `U"我是UTF8字符串"`

### 1.6 折行与换行

- 一行多语句用分号 `;`；子集块同行用冒号 `:`（如 `如果 条件 : 语句; 语句`）

- 多段字符串拼接 `"123""456"`（文档注明后续可能不支持）

- **折行符 `\`**：必须在行末，后面不能有任何内容（含空格）；折行内容需与作用域对齐（TAB 缩进）

- **逗号换行 `,`**：用于连续定义变量、函数定义参数列表、函数调用参数列表

### 1.7 易错点

- **少用裸指针**：指针使用不当容易内存泄漏、越界/野指针、崩溃。优先用对象封装——文本用字符串封装类（优先 `文本型 字符串="123"`，少用 `字符型*`）；字节集用内存/二进制封装类，尽量避免直接指针内存操作。

- **函数「传指针接收返回值」改为「传引用」**：不推荐 `结构_矩形* 对象` + `对象->成员=...`；推荐 `结构_矩形& 对象` + `对象.成员=...`

- **类型互相引用冲突（A 引 B，B 引 A）**：编译识别失败时的常用思路——把成员变量改成指针成员（减少完整类型依赖）；把类型定义拆到单独文件（集中声明）；调整代码顺序（先声明/后使用）

- **`new`/`delete` 与 `malloc`/`free` 语义不同**：`new` 分配对象并调用 `构造()`，返回对象指针（数组 `new 整型[100]`）；`delete` 释放 `new` 的对象并触发 `析构()`；`内存分配()` ↔ `malloc()`、`内存释放()` ↔ `free()`，不调用构造函数，需要对象生命周期则优先 `new`。手册示例里包含 `delete 数组1`（注意：在 C++ 里数组需要 `delete[]`；这里以炫语言/封装规则为准，按手册用法执行）

- **源码编码与缩进按工程约定统一**：`.xc`／`.xh` 使用 UTF-8 BOM，语句块使用 Tab 缩进；旁路布局 XML 与 `resource.res` 使用 UTF-8 无 BOM。批量格式化、编辑器自动转空格或整文件重写后必须检查前三字节与实际缩进，不能仅凭 IDE 能打开就认定编码正确。
- **以真实编译器标准为准**：若当前 IDE 强制 C++14，就不要因嵌入代码在本机其他编译器可过而使用 `std::filesystem`、结构化绑定等 C++17 特性，也不要假定炫语言支持函数重载。将实际标准写回 `.xcproj` 构建选项，避免文档、磁盘工程与 IDE 缓存各说一套。
- **避免类型名被成员名遮蔽**：成员字段与其类型同名时，后续再写该类型可能解析成成员而非类型并引发难以理解的编译错误。让类型名表达结构含义，例如把统计类型命名为 `XxxSummary`／`XxxHistogram`，与成员 `XxxCount` 区分；不要靠调整调用处偶然通过来掩盖命名冲突。

## 2. 容器与类

### 2.1 数据容器

- **数组（静态数组）**：定义时固定类型与大小，不可变更，如 `整型 数组[10]={0}`

- **动态数组（std::vector）**：`动态数组<类型> 变量`；添加/删除/插入 `添加(...)`、`取大小()`；遍历 `列表循环(整型 i=0; 数组A) ...`

- **字典（std::map）**：`字典<键,值> 变量`；通过 `[键]` 取值；`查找()` 得到迭代器；与 `空值()` 比较判断是否找到；遍历 `列表循环(迭代器 迭代器项; 字典A) ...`

- **字节集（内存/二进制容器）**：对内存的安全包装，便于添加不同类型、取文本指针、切片、按偏移读取等；常见操作 `置数据/取地址/置大小/取文本指针/添加整型/添加文本/取整型/取文本指针扩展`

### 2.2 函数（function/def）

- 定义 `函数 返回值 函数名(参数...)`；无返回值可省略返回类型；`...` 表示 IDE 不检查参数（任意参数/不定参）

- 调用约定 `WINAPI` 等同 `__stdcall`

- 函数别名：在函数末尾加 `: 别名xxx`

- **对象参数自动引用**：炫语言定义的函数，当参数是类/结构体且非指针/非引用时，IDE 可能自动加 `&`（减少拷贝）；若担心被改动可加 `常量(const)` 语义；若不希望自动引用使用 **[禁引用]**

### 2.3 `#函数类型`（函数地址/函数指针）

用于「只知道函数地址也能调用」的场景（动态调用 DLL、函数变量等）。需要声明返回类型、调用约定、参数类型/数量。

- 示例形态：`#函数类型  整型 (*函数指针_)(整型, 整型)`

- 将函数地址赋值给变量，再用 `函数指针_(...)` 调用

- 也可 `编译C` 声明为 `extern "C"` 风格

### 2.4 类与结构体

- `构造()` / `析构()` 无返回值；实例化触发构造；出作用域触发析构；成员访问控制 `公开/私有/保护`

- 继承与虚函数：子类继承父类后可使用父类成员；**虚函数**通过基类指针调用时优先调用子类覆盖版本；析构也可设为虚函数，以保证通过基类指针释放时调用到子类析构；重写要求返回值/函数名/参数类型数量一致

- 定义「数据结构」时建议用 `结构体`，语义更清晰

#### 2.4.1 标识符命名空间与批量改名（改名前必读）

- **类型名、函数名、全局变量共用一个命名空间**：`结构体 合成内存区域` 与函数 `合成内存区域` 不能并存，编译期直接判为重复定义。中文命名时同音近义很容易撞名，实测一轮结构体改名有 9 个候选名与既有函数冲突（`合成内存区域` `合成写入` `统计汇总` `界面快照上下文` `OCR配置` `视觉命令` `视觉点` `视觉矩形` `视觉文本`），必须逐个避让后重编。
- **不支持重载**：同名只能有一个签名；需要多个版本时用 `xxx` / `xxx2` / `xxxEx` 等后缀，中文名同理（如 `初始化` / `初始化合成` / `离线初始化`）。
- **改名要先查重再动手**：把「目标名」与「仓库里已有的全部标识符（类型/函数/全局变量）」比对，冲突就换名；只查旧名是否还存在是不够的。
- **按名字的所有声明文件同批改**：同名方法可能被多个结构体/多个文件各自声明（如 `try_read` 在三个内存类型上）；只改其中一处，非 owner 文件里的 `x.名字(...)` 会被错误替换到另一个类型上，编译通过但语义错位。稳妥做法是「该名字的全部声明文件同批处理」，否则跳过。
- **结构体改名会连带生成 C++ 头**：`app/include/host_forward.h` 这类前向声明头（常被 `common.xh` 预编译头包含）必须同步改成新名，并按 `.h` 编码规则保存为 **UTF-8-BOM**；实测 MSVC 接受中文标识符（`struct 桌面状态;` 正常编译）。
- **成员遮蔽自由函数**：成员函数与同名的自由函数并存时，成员优先。把 `Vision_begin_queue` 这类自由函数改成 `开始排队`，而某个结构体又恰好有 `开始排队` 成员，成员体内的调用会变成自调用（离线回归不触发，实机才炸）。给底层自由函数加技术前缀（`视觉…` / `地图仓库…` / `进程…`）比抢短名安全。

批量替换工具实现要点（踩过的坑）：

- 每行先切成 `{代码, 字符串, 注释}` 三段，只对代码段做整词替换（`(?<![A-Za-z0-9_\u4e00-\u9fff])名字(?![A-Za-z0-9_\u4e00-\u9fff])`），避免改到 `"…"` 里的 JSON 键、日志文案和 `gOcrConfig` 这类含子串的变量名。
- **切到字符串起始引号时必须清空代码缓冲**，否则代码段会进缓冲区第二遍，写回后变成 `如果 (argument == 如果 (argument == "--data" …)`。实测一次污染 56 个文件 3540 行；修复靠「反向改名让两份副本一致 → 折半还原 → 再正向改名」。
- 改名脚本要**幂等**（重复执行不叠加）并**先 dry-run**：输出「改名条目数 / 替换处数 / 零命中名单」，零命中通常意味着名字拼错或该名字其实属于别的声明。
- 一次只改一个子系统（core / runtime / ui / vision 分批评），每批立刻 `build.ps1`（`错误(0)`）+ `test-integration.ps1`（`cases=4368 failed=0`），失败就只回滚这一批。

### 2.5 内置函数（IDE 特殊功能）

- `取成员地址偏移(类名::成员变量名)`

- `取类型大小(类型)`，或对变量/成员取大小

- `调用函数()` / `调用函数扩展()`：动态调用函数地址；`调用函数()` 目标函数返回整型、调用约定 `__cdecl`，`调用函数扩展()` 可指定返回类型

- stdcall 版本：`调用函数stdcall()` / `调用函数扩展stdcall()`，目标调用约定 `__stdcall`（`WINAPI`）

### 2.6 内置宏、占位与调试输出

- 内置宏示例：`TRUE/FALSE`、`__FILE__/__LINE__`

- 平台/配置：`_WIN64`、`_DEBUG`、`NDEBUG`

- 模块链接偏好：`XCL_MODULE_USE_DLL`、`XCL_MODULE_USE_LIB`

- 工具集：`XCL_VS2015`、`XCL_VS2019`

- 类型别名宏：`单文本型->文本型A`、`单字符型->字符型A`

- 事件：`EVENT`、`EVENT_DEF`

- 调试定位内置宏：`#当前文件`、`#当前行号`、`#当前函数`、`#当前类`

- **占位**：`占位` / `[占位]` 代表一行空代码占位，类似 C++ 的 `{}`，用于避免「空函数体/空分支体」引发语法错误

- **调试输出**：`调试输出("...")` 为宽字符（Unicode / `wchar_t*`）；`调试输出A(A"...")` 为多字节（`char*`），字符串前加 `A`

## 3. 预处理 / common.xh / 嵌入 C++

- **`#头文件` / `#库文件`**：`<...>` 系统头文件（不解析内容）；`"..."` 普通头文件（解析内容），支持子目录 `"include\xcgui.h"`；可用隐藏命令隐藏不需解析的代码以提高解析速度（见 `module-packaging.md`）。

- **条件编译**：`#宏定义 宏名 值`；`#if 宏名` → `#else` → `#endif`

- **`#外部变量` / `#外部类型` / `#外部宏`**：声明外部已有符号便于 IDE 识别；支持中文别名（`:`）

- **common.xh（外部函数/类型声明）**：当函数/类型存在于外部库或嵌入代码中，需要在 `common.xh` 里声明让 IDE 识别。外部函数可用 `...` 表示不检查参数；外部类可只声明类型名，或写完整成员以支持成员访问

  - 落地做法：`common.xh` 集中写 `#外部类型 / 外部函数`、结构体声明等，减少每个 `.xc` 重复声明

  - 外部类型示例 `#外部类型 DWORD / DWORDLONG / SM_CXSCREEN / SM_CYSCREEN`；结构体声明示例 `MEMORYSTATUSEX`；外部函数示例 `GlobalMemoryStatusEx`、`GetSystemMetrics`、`GetSystemTimes`

  - 目的：减少每个源文件重复声明，且能作为「预编译头」提升修改时的编译速度

- **嵌入 C++**：`#嵌入代码 ... #嵌入代码结束` 嵌入 C++ 片段，与函数对齐时通常作用域为函数内（缩进一级）；访问嵌入代码变量需先 `#外部变量` 声明，再在炫语言代码里读写

- **与 C++ 源文件混合**：头文件声明函数，cpp 实现并包含预编译头（示例里包含 `common__.h`）

- ⚠ **`common.xh` 不能 `#include` 模块头** —— 见 `module-packaging.md` §10「示例工程 common.xh / xcproj 约定」。

## 4. `.xc` 入口与工程结构

### 4.1 程序入口

- **控制台入口**：常见流程 置中文编码 → 输出 → 暂停 → 返回

- **窗口入口（纯代码）**：`炫彩_初始化()` → `窗口_创建(...)` → `按钮_创建(...)` → 注册事件 `元素_注册事件C(..., XE_BNCLICK, 回调)` → `窗口_显示扩展(...)` → `炫彩_运行()` → `炫彩_退出()`

- **IDE 生成 UI 代码要点**：类继承 `窗口类`；通过 **[绑定信息]** 维护 UI 变量与事件；`_布局文件="main.xml"` 关联布局文件，便于加载/跳转/绑定；`运行()` 是 IDE 特殊处理的启动函数，负责加载布局与绑定

### 4.2 界面运行函数与资源加载

- `运行()`：界面类启动函数（IDE 做特殊处理）；`_布局文件` 为成员变量，关联 UI 布局文件

- `运行(...)` 支持可选参数（顺序不敏感），典型项：**禁用加载布局**、**名称前缀**、**父句柄 / 父句柄HWND / 附加HWND**

### 4.3 RC 资源文件（exe.rc）与资源查找

默认 RC `exe.rc`；UI 打包资源 `IDR_UI_ZIP`（与「UI 从资源」项目属性有关）；常见资源含版本信息、程序图标、文件、图标、光标、位图、字符串等。典型接口（按资源名或纯数字 ID）：`RC资源查找文件()` / `RC资源查找文件从ID()`；`RC资源查找文件到字节集()` / `...从ID()`；`RC资源查找文件到文本()` / `到文本A()`（及从ID）；`RC资源查找图标()` / `查找光标()` / `查找位图()` / `查找字符串()`。

### 4.4 推荐目录结构（适合中型项目）

- `源文件\main.xc`：初始化/资源/运行/循环

- `源文件\login.xc`、`源文件\index.xc`：窗口/页面拆分

- `布局文件\main.xml`、`布局文件\msg.xml`：布局复用（简单例子可直接放工程根目录，如 `main.xml`）

- `WmUi\WmUi_Base.res`、`WmUi\Light\*`、`WmUi\Dark\*`：Base→主题资源链

- `common.xh`：外部声明集中化

- 列表类控件项模板建议拆成独立 xml（如 `列表框项模板.xml`、`列表项模板.xml`、`列表树项模板.xml`、`列表视图项模板.xml`）

### 4.5 最小运行顺序（强烈建议固定）

`炫彩_初始化(真)` →（可选）自动重绘/非客户区 → Base→主题资源 → 窗口类 `运行()` 初始化 → `炫彩_运行()` / `炫彩_退出()`。

- 入口函数 `入口函数_窗口()` 只做「初始化 + 运行窗口 + 消息循环」

- 可选特性 `炫彩_启用自动重绘UI(真)`（修改 UI 后自动触发 `重绘()`）、（可选）`炫彩_启用窗口系统非客户区(真)`

- 加载资源通过 `#加载资源文件`（由项目属性决定从文件/从内存加载）

- 窗口类的 `运行()` 是「窗口创建完成后」做 UI 初始化的地方；用户初始化写这里

### 4.6 IDE 绑定信息（不要手改的区域）

`[绑定信息]` 段由 IDE 生成：变量绑定 + 事件绑定，尽量在设计器里改。包含 **UI 变量绑定** `[类型, 变量, "name"]` 与 **事件绑定** `[元素事件_xxx, 回调函数, 1]`。除非清楚 IDE 的生成逻辑，尽量不要手改。

- **解析与编译分层排错**：IDE 报“解析遇到错误”是 `.xc` 前端问题，不是 MSVC 链接器问题；先按源文件行号修复。生成目录中的 `main__.cpp` 等可用于核对事件签名和实际语义，但属于编译缓存，不作为源码修改落点。资源加载、布局绑定、列表模板加载和动作路由各自检查返回值，不因一个页面能显示就推定所有引用都成功。

### 4.7 调用已安装的官方/扩展模块

本机完整模块位于 `I:\xcide\data\XC-Module`。涉及 JSON/XML、压缩、HTTP/Socket、浏览器、数据库、线程池、绘图、多媒体、OCR、加密、脚本、办公或综合模块时，先读 [本地模块调用](xc-modules.md)，用 `scripts/xc_modules.py` 查选定包的完整入口、原始别名/签名、依赖与真实 `.xc` 调用示例；全部模块包见 `xc-modules/catalog.md`。

选定入口后通过 `*.xcproj` 的 `<modules><item path="module_xxx.h" /></modules>` 引用，纯炫语言模块引用其真实 `.xc` 入口。按已有工程合并条目，不替换整个模块列表；不要把模块头写进 `common.xh`。同名入口及架构条件须按源码确认，索引收录不表示已经编译验收。

## 5. 基础模块（CXText / CXBytes / CXFile / 日志）

> 来源：`基础模块.mdc`（§1–§7 全文归并）

定位：Windows 平台下的 C++ 通用基础功能库，为上层模块提供字符串、字节数组、文件/目录、时间日期、环境变量、注册表、资源、对话框等常用封装。同时支持宽字符 `CXText` 与窄字符 `CXTextA`，提供 `CXBytes` 二进制缓冲区类，深度封装 Win32 API，并提供统一的「任意类型转字符串」接口 `xcl_mkStr / xcl_mkStrA / xcl_mkStr2` 及调试日志接口 `xcl_log`。

### 5.1 目录结构

- `module_base.h` / `module_base.cpp`：基础类型与工具函数主实现，含 `CXBytes` / `CXText` / `CXTextA`、`CXFile`、时间日期封装 `CDateTimeTM` 及一系列 `xcl_*time*` 函数、文本处理/编码转换/Base64/URL 编解码、环境与进程、文件与目录、剪贴板、资源、注册表等

- `xc_mkStr.h` / `xc_mkStr.cpp`：宽字符日志与格式化字符串模板与实现（`CXText` 版本）

- `xc_mkStrA.h` / `xc_mkStrA.cpp`：窄字符日志与格式化字符串模板与实现（`CXTextA` 版本）

- `md5.txt`：版本或完整性校验信息（MD5 记录）

- `doc` 目录（对封装的类/函数与依赖的系统/CRT API 做文字说明或用法示例）：`xcl_urlEncodeUtf8.txt` / `xcl_urlEncodeA.txt` / `xcl_urlEncode.txt`、`xcl_setSrand.txt` / `xcl_getTimeTM.txt`、`vector_class.txt` / `queue_class.txt` / `queueEx_class.txt` / `map_class.txt` / `map_find.txt`、`file_class.txt` / `file_seekPos.txt` / `FILETIME.txt`、`bytes_class.txt`、`fputs.txt` / `LoadLibrary.txt` / `FindFirstFile.txt` / `GetSystemTime.txt` / `QueryPerformanceFrequency.txt`、`sin.txt` / `cos.txt` / `tan.txt` / `asin.txt` / `acos.txt` / `atan.txt` / `atan2.txt`

### 5.2 `CXBytes`（字节数组类）

管理任意二进制缓冲区（分配、扩容、插入、追加、替换）；支持从 `CXText` / `CXTextA` / C 字符串 / 整型 / `initializer_list` / `std::vector<BYTE>` 等构造。

```text
add* 系列（把 int/__int64/float/double/wchar_t/BYTE 以原始字节写入缓冲）
addHex | toHex / toHexA / toHexBytes / toHexBytesA
getLeft / getRight / getMid
getInt / getInt64 / getUInt / getUInt64 / getShort / getUShort / getFloat / getDouble / getWchar / getByte
findBytes（在当前字节数组内查找子字节序列）
```

### 5.3 `CXText` / `CXTextA` 与 `text_*` 工具函数

- **`CXText`（宽字符）**：封装 `std::wstring`；支持从 `std::string` / `CXTextA` / `CXBytes` / C 字符串 / 数字类型构造与赋值；提供 `substr` / `replaceSub`

- **`CXTextA`（窄字符）**：封装 `std::string`；支持从 `std::wstring` / `CXText` / `CXBytes` / C 字符串 / 数字类型构造与赋值

- **文本工具函数（前缀 `text_`）**：`text_*` 绝大多数都有窄字符 `A` 版本，即 `text_xxx` 与 `text_xxxA` 成对存在（例如 `text_split` / `text_splitA`、`text_split2` / `text_split2A`、`text_getRandChar` / `text_getRandCharA`、`text_getRandNumber` / `text_getRandNumberA`、`text_getReText` / `text_getReTextA`）。下列均含对应 `A` 版本（除已标注）：

```text
截取: text_getLeft / text_getRight / text_getSub / text_getSub2 / text_getSub3
查找: text_getSubPos / text_getSubPosRight
分割: text_split / text_split2 / text_splitChar / text_splitChar2 / text_splitRow / text_splitRow2
裁剪: text_trim / text_trimLeft / text_trimRight / text_trim2 / text_trimRight2
删空行: text_trimEmptyRow / text_trimEmptyRowA
大小写: text_upper / text_lower / text_upper2 / text_lower2
随机/重复: text_getRandChar / text_getRandNumber / text_getReText
```

### 5.4 文件与路径：`CXFile` 与 `xcl_*file*`

`CXFile` 封装 `FILE*`：

```text
打开: open / openRead / openWrite / openEx
位置与长度: getLength / getCurPos / seekBegin / seekEnd / seekPos
读写: readData / readDataRow / readDataBytes / readTextA / readChar / readWChar /
      writeData / writeText / writeTextA / writeText2 / writeText2A
状态: isEnd / isEof
```

快捷函数与目录路径：`xcl_writeFile` / `xcl_readFile` / `xcl_readFileTextA`；创建目录 `xcl_createFolder` / `xcl_createFolderA` / 递归创建 `xcl_createFolder2`；判断存在 `xcl_isFolderExist` / `xcl_isFileExist` / `xcl_isFileExist2` / `xcl_isPathExist`；拷贝与删除 `xcl_copyFile` / 递归删除目录 `xcl_deleteFolder`。

### 5.5 时间日期：`CDateTimeTM` 与 `xcl_*time*`

- `CDateTimeTM` 封装 `struct tm`：`getYear` / `getMonth` / `getDay` / `getHour` / `getMinute` / `getSecond` / `getDayOfWeek`

- 当前时间与格式化：`xcl_getTimeTM` / `xcl_getTimeToText` / `xcl_getDate` / `xcl_formatTimeTM` / `xcl_formatTime`

- 转换：`xcl_getDayInMonth`；`xcl_timeToTM` / `xcl_timeToLocalTM`；`xcl_timeToSystemTime` / `xcl_systemTimeToTime`；`xcl_timeToFileTime` / `xcl_fileTimeToTime`

- 文本 <-> 数值：`xcl_wtof` 与一系列 `xcl_textToInt/Uint/Int64/Uint64/Float/Double`

### 5.6 编码、进制与二进制文本

- 二进制转文本 `xcl_dataToBinTextA` / `xcl_dataToBinText`（按 bit 输出、可配置对齐与是否补零）；底层十六进制格式化 `_dataToHexStrA` / `_dataToHexStrW`

- 进制转换 `xcl_hexTextToInt` / `xcl_hexTextToInt64`、`xcl_binTextToInt` / `xcl_binTextToInt64`、`xcl_intToHexText` / `xcl_int64ToHexText`、`xcl_intToBinText` / `xcl_int64ToBinText`

- 字符编码 宽/窄 `W2A` / `A2W`（含 `CXText` / `CXTextA` 重载）；UTF-8 与 Unicode `W2U` / `U2W`；本地多字节之间 `A2U` / `U2A`

- Base64 `xcl_base64EncodeA` / `xcl_base64DecodeA`

- URL 编解码 内核 `xcl_urlEncodeUtf8` / `xcl_urlDecodeUtf8`；对外宽字符 `xcl_urlEncode` / `xcl_urlDecode`，窄字符 `xcl_urlEncodeA` / `xcl_urlDecodeA`

### 5.7 环境、进程与系统信息

- 命令行和路径：`xcl_getCommandLine`、`xcl_getRunDir`、`xcl_getCurrentDir`、`xcl_getRunFileFullPath`、`xcl_getRunFileName`、`xcl_GetModuleFileName`

- 执行外部程序：`xcl_runConsoleProgram`（启动无窗口控制台进程，重定向标准输出/错误并获取退出码）

- 环境变量：`xcl_getEnvironmentVariable`（单个）、`xcl_getEnvironmentStringsToMap`（全部导出到 `CXMap<CXText, CXText>`）

- 系统信息：`xcl_is64`（判断当前环境 32/64 位）；屏幕 `xcl_getScreenWidth` / `xcl_getScreenHeight`；消息循环与延时 `xcl_doMessage` / `xcl_delay`

### 5.8 剪贴板、消息框与对话框

剪贴板 `xcl_setClipboardText` / `xcl_getClipboardText`；消息框 `xcl_msgBox`（简单封装 `MessageBox`）；文件夹选择 `xcl_openFolderDlg`；打开文件 `xcl_openFileDlg`（单选）/ `xcl_openFilesDlg`（多选）；保存文件 `xcl_saveFileDlg`。

### 5.9 资源访问 `rc_*`

```text
二进制资源: rc_findFile / rc_findFileByID
           rc_findFileToBytes / rc_findFileToBytesByID
           rc_findFileToText / rc_findFileToTextByID / rc_findFileToTextA / rc_findFileToTextAByID
图标: rc_findIcon / rc_findIconByID / rc_findIcon2 / rc_findIcon2ByID
光标: rc_findCursor / rc_findCursorByID
位图: rc_findBitmap / rc_findBitmapByID
字符串: rc_findString
```

### 5.10 注册表 `reg_*`

- 打开/创建/删除：`reg_openKey` / `reg_createKey` / `reg_deleteKey` / `reg_deleteValue`

- 枚举与查询：`reg_enumValue`（枚举键值和数据）；原始数据 `reg_queryValueData`（到 `CXBytes`）；便捷查询 `reg_queryValueText` / `reg_queryValueInt` / `reg_queryValueInt64` / `reg_isExist`

- 设置：文本 `reg_setValueText`；整数 `reg_setValueInt` / `reg_setValueInt64`；二进制 `reg_setValueData`

### 5.11 日志与字符串构造

- **`xcl_mkStr` / `xcl_mkStrA` / `xcl_mkStr2`**：通过一组 `xcl_mkValue(CXText& / CXTextA&, T)` 模板和重载把各种类型安全地追加到字符串；不支持的类型统一输出「`?不支持类型?`」，避免静默失败。固定参数版本 `xcl_mkStr(...)` / `xcl_mkStrA(...)`（1～12 参数）；可变参数版本 `xcl_mkStr2(...)` / `xcl_mkStr2A(...)`，通过递归模板 `_xcl_mkStr2T` / `_xcl_mkStr2AT` 实现

- **`xcl_log` / `xcl_log2` / `xcl_xtrace`**（`DEBUG` 模式下启用）：`xcl_log(...)` 自动在参数之间插入逗号与空格、末尾加换行，通过 `OutputDebugStringW` 输出；`xcl_log2(...)` 无分隔符直接拼接；`xcl_xtrace` / `xcl_xtracew` 为 `printf` 风格格式化输出到调试器。非 `DEBUG` 模式下宏为空实现，不引入运行期开销

### 5.12 依赖与运行环境

- 平台：依赖 Windows 与 Win32 API，如 `GetModuleFileName`、`GetEnvironmentStrings`、`GetPrivateProfileString`、`CreateProcess`、`MessageBox`、`SHBrowseForFolder`、`GetOpenFileName`、`RegOpenKeyEx`、`LoadIcon` 等

- 运行库：C 运行库函数进行文件、字符串、时间与内存管理，如 `fopen/fread/fwrite`、`_ftelli64/_fseeki64`、`wcslen/strlen`、`sprintf_s/swprintf_s`、`_time64/localtime_s` 等

- 字符编码：使用系统代码页 `CP_ACP` 和 UTF-8 `CP_UTF8` 进行多字节与宽字符转换，统一对外封装为 `CXText` / `CXTextA` 接口

### 5.13 使用建议与最佳实践

- **优先使用封装类型**：文本在库内外统一用 `CXText` / `CXTextA`，避免混用原始 `std::string` / `std::wstring` + 原始 API；二进制（数据流、文件内容、网络帧）统一用 `CXBytes`，结合 `add*` / `get*` / `toHex`

- **统一字符串拼装**：调试和日志统一用 `xcl_mkStr` / `xcl_mkStrA` / `xcl_mkStr2` + `xcl_log`，避免手写 `swprintf_s/sprintf_s`，降低格式错误风险

- **Win32 API 封装优先**：文件、时间、对话框、注册表、资源等优先用 `xcl_*` / `CX*` 封装，封装不满足需求时再直接调用 WinAPI

- **跨编码约定**：内部逻辑以宽字符为主（`CXText`），与外部接口交互（网络/协议/配置文件）再通过 `W2U/A2W/U2A` 转换

- **调试与发布差异**：调试信息统一接入 `xcl_log` / `xcl_log2` / `xcl_xtrace`，发布版本相关宏自动为空，不需手工移除

### 5.14 易错点（项目里真实踩过）

- **`文本组合(...)` 参数数量上限**：`文本组合` 只有固定重载（通常**最多 12 个参数**），超过会直接编译失败（`C2672`）。推荐参数多时改用 `xcl_mkStr2(...)` / `xcl_mkStr2A(...)`，或拆成两段拼接。

- **`字节集.取地址()` 是只读指针**：官方基础模块中 `字节集.取地址()` / `CXBytes::getPtr()` 返回 **`const BYTE*`**（常量指针）。要写入字节集内容，不要把 `取地址()` 当作写入指针传给 `内存复制`；正确方式是用 `置大小(n)` / `调整大小(n)` 的返回值拿可写地址。

- **`内存拷贝` 不是官方函数名**：官方基础模块提供的是 `内存复制(...)` / `内存复制2(...)` 等（见 `module_base.h` → 「内存操作」分组）。

### 5.15 典型使用场景（保持源材料可编译形态）

**内存复制（字节集写入）**：把原始缓冲区 `src` 的前 `n` 字节复制到 `字节集 dstBytes`。

```text
字节集 dstBytes
正整型 n = 32
字节型* dst = (字节型*)dstBytes.置大小(n)   // 置大小返回可写地址
内存复制(dst, src, (size_t)n)               // 注意：第1参必须是可写指针
```

**日志拼接（超过 12 参数）**：`文本组合` 参数过多会编译失败，此时改用 `xcl_mkStr2/xcl_mkStr2A` 或拆两段。

```text
文本型 前缀 = 文本组合("[", id, "] flags=", flags, " len=", len)
写日志(前缀 + 文本组合(" type=", type, " body=", body))
```

其余场景（思路级）：**配置文件读取** `xcl_readFileTextA` 读 INI/文本 → `text_splitRow` / `text_trim` 解析行 → `xcl_textToInt` 转类型；**二进制协议封包/解包** 发送用 `CXBytes` 的 `addInt/addShort/addBytes` 顺序写入，接收用 `getInt/getShort/getMid` 按偏移读取，并用 `toHex` 生成调试日志；**URL 与 HTTP 参数** 先转 UTF-8（`W2U/A2U`）再用 `xcl_urlEncodeUtf8` 编码，或用 `xcl_urlDecodeUtf8` 解析查询串；**注册表配置读写** `reg_setValueText/reg_setValueInt` 落盘，`reg_queryValueText/reg_queryValueInt` 恢复，`reg_isExist` 判断存在；**工具/脚本型程序** `xcl_getCommandLine` 解析命令行，`xcl_runConsoleProgram` 调度外部命令并把标准输出/错误收集到 `CXText`。

### 5.16 @斗鱼55 关联点（文件读取 + 文本拆分）

`斗鱼55/index.xc` 的「拖入文件 → 解析 → 填表」流程依赖「读文件得到字节集/文本，然后分割成行与字段」：

- 文件读取 `文件读取(文件路径)` 得到 `字节集`

- 转文本 `字节集.取文本A(0, size)`（按需限制 size，避免大文件）

- 按行拆分 `文本分割A(内容, A"\n")`，并把 `\r` 替换掉

- 按分隔符拆字段：对 `\t` / `,` / `|` / 空格做优先级拆分

