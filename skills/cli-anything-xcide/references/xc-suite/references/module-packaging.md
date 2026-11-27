# module-packaging — XC-Module 封装：//@ 注解 / 类型映射 / 编码铁律 / 预编译库 / 示例工程 / 易语言迁移 / 发布清单

> 来源：`xc-模块封装\skill.md`、`xc-模块封装\reference.md`、`xc-模块封装\examples.md`、`xc-代码\模块封装.mdc`。
> 所有 `//@` 注解名、目录名、路径、命令逐字保留；示例代码保持可复制形态。数字为**基准仓库当场复核值**，复核命令一并给出。
> 历史源材料基准仓库：`I:\炫彩ide\data\XC-Module`（正式模块目录）、`I:\炫彩ide\data\XC-Module-dev`（开发模块目录）。本机当前正式模块根目录为 `I:\xcide\data\XC-Module`；现成模块的实际路径、完整入口及调用用法见 [xc-modules.md](xc-modules.md) 和 `scripts/xc_modules.py`，下述旧仓库分类/计数不代表当前安装。

## 1. 决策表与总目标

| 你的情况 | 走哪条路 | 骨架 | 参考示例 |
|---------|---------|------|---------|
| 有现成 `.lib` + `.dll`（vcpkg / 官方预编译） | **预编译库** | `x86/` `x64/` + `//@lib` + `//@复制文件` | 示例 3 |
| 只有源码，要跟着模块一起编译 | **vendor 内嵌** | 源码放模块根，每个文件一行 `//@src` | 示例 6 / 7 |
| 自己写几百行逻辑 / 少量 API | **薄封装** | `module_xxx.h` + `module_xxx.cpp` | 示例 1 |
| COM / ActiveX 插件 | **COM 对象** | `IDispatch*` + `//@隐藏` | 示例 4 |
| 完全不想写 C++ | **纯炫语言模块** | `module_xxx.xc`（`#DLL导入表` / `#宏定义`） | 示例 10 |
| 从易语言 `.e` 迁移 | **易语言迁移** | 中文函数名直译，DLL 命令改静态链接或 `#DLL导入表` | 示例 2 |

**库形态优先级**：**静态库 > 动态库 > 源码**；尽可能提供编译好的库以提速。静态库不产生运行时 DLL 依赖、IDE 解析负担最小；动态库次之（需 `//@复制文件` 随模块分发）；源码内嵌最末（编译慢、易受第三方头文件解析限制影响）。
**交付质量约束**：可能与其他库重名就加前缀，相同关键字尽量前置；相同功能用 `@分组` 分类（支持多级）；不需识别的内容用 `@隐藏` 提高解析速度；模块目录需包含基础使用示例；模块说明尽量详细（封装者、QQ、开源地址、注意事项）；别名尽量简短直观、备注用简单句；类 or C 接口以用户体验为先；非必要文件删除、过大则给下载地址；实现尽量放 `*.cpp`、`*.h` 只声明；复杂代码能简化就简化，不能简化则 `@隐藏` 再用 `@声明` 补齐可识别接口。
**三个总目标**：统一规范（IDE 中更好检索/分类/显示，减少冲突）、提升体验（中文别名易用、示例齐全、体积可控、编译更快）、便于解析（用 `@隐藏/@声明/@解析头文件` 规避复杂代码与模板解析限制）。

## 2. 历史仓库地图与命名事实

此节保留原始基准仓库取证及封装范例；当前模块调用请按本机重建的 `catalog.md` 定位扩展与官方目录，不照搬这里的 `常规/网络/kyozy` 等旧分类路径。

**顶层分类目录（21 个）** —— 复核命令：`(Get-ChildItem -LiteralPath 'I:\炫彩ide\data\XC-Module' -Directory).Count` → **21**

```text
.cursor           22897350-易加加模块   常规        核心        核心[官方]
键鼠辅助          卡卡                  汨酴模块    欧阳逸洛    数据库
网络              小轩                  炫++扩展    炫扩展      炫易模块
易炫彩            用户                  imgui       kyozy       Like
XCGUI远程管理模块
```

内容要点：`核心[官方]/` = `基础模块`、`炫彩界面库`、`系统API`、`系统API(前缀分类法)`、`易语言核心模块`、`COM操作`；`常规/` = 社区主力区（`HaiTang-haitang2018k`、`OpenSSL`、`线程池`、`YYJSON对象`、`luren1234-综合模块`、`u36298509-ExDUIR界面库`、`u36298509-黑月界面类模块` 等 30+）；`网络/` = `HPSocket`、`WinHttp`、`FiddlerXPL`、`BSPHP网络验证`、`hxznhf-网络服务`；`数据库/` = `sqlite3`、`数据库mysql`、`数据库ADO`；`键鼠辅助/` = `大漠对象模块`、`大漠模块`、`cainiao_84002751-OP插件0450`、`奥迦插件`、`模拟器操作`、`nanxiaoyu-南_DD鼠标键盘`；`Like/` `kyozy/` `卡卡/` `小轩/` `用户/` `欧阳逸洛/` `汨酴模块/` = 作者个人模块区；`22897350-易加加模块/` = **聚合包**（下辖 `易加加/`、`易核心模块/`、`curl/`、`kyozy-libzip修改版/` 四个子模块，**三级嵌套**）；`炫易模块/` `易炫彩/` `炫扩展/` `炫++扩展/` `imgui/` `核心/` = 易语言风格 API、界面库、扩展。
> **`核心` 与 `核心[官方]` 是两个不同目录**（前者实测仅 `m3678131-数组`）。`imgui_docking/` 位于 **`imgui\imgui_docking\`**（非根级）。

**规模事实（当场复核）**

| 事实 | 复核值 | 复核命令 |
|------|---------|---------|
| `module_*.h` | **154**（排除 `\obj\` 缓存）／158（含缓存） | `-Filter 'module_*.h'` + `Where-Object { $_.FullName -notmatch '\\obj\\' }` |
| `module_*.xc` / 一级目录 / `md5.txt` / `*.xcproj` | **6** / **21** / **73** / **106** | `-Filter` / `-Directory` |
| `示例-*/` 目录 | **17** | `-Recurse -Directory \| Where-Object { $_.Name -like '示例-*' }` |
| `@模块信息结束` | **29** | `-Filter 'module_*.h'`（排除 `\obj\`）+ `Select-String -Pattern '@模块信息结束' -List` |
| `XC_MOUDLE` / `XC_MODULE` | **54** / **24** | 全 `*.h/*.cpp/*.xc/*.hpp/*.cc`（排除 `\obj\`）+ `Select-String -List` |
| `//@lib64` / `//@复制文件64` | **1** / **3** | 同上 |
| `//@解析头文件` / `//@包含目录` / `//@默认安装位置` | **37** / **25** / **20** | 同上 |
| `@doc` / `@示例` | **2** / **8** | 同上 |
| `#智能指针` / `@跳过` | **0** / **0** | 精确串；为**文档化能力**（注解语义保留，仓库当前无使用实例） |
| 含 `()`/`[]` 的目录 | **13** | `-Recurse -Directory \| Where-Object { $_.Name -match '[\(\)\[\]]' }` |

`module_*.h` 的 4 个差值来源：`\obj\cache\` 下的 IDE 编译中间产物 `module_*__.h` 会被 `-Filter` 命中，必须排除 `\obj\` 才是真实模块数。
实测 6 个 `module_*.xc`：`常规\cainiao_84002751-大漠模块_72424\module_大漠模块7.2424.xc`、`常规\u61597848-QX模块\module_弹出消息框类.xc`、`键鼠辅助\cainiao_84002751-奥迦插件\module_奥迦插件_main.xc`、`键鼠辅助\cainiao_84002751-模拟器操作\module_模拟器操作_main.xc`、`键鼠辅助\cainiao_84002751-OP插件0450\module_OP插件0450_main.xc`、`卡卡\s1d21992-NZ_远程内存模块\module_NZ_远程内存模块.xc`。

**命名与路径事实 🔴**

- **目录命名**：`作者标识-模块中文名` —— `Like-蓝奏云直链解析`、`HaiTang-haitang2018k`、`s1d21992-NZ_远程内存模块`；**分类文件夹**：在模块文件夹外再套一级分类（如「核心/常规/网络」）
- **模块文件命名**：`module_xxx.h`（**以 `module_` 开头的 `.h` 视为模块文件**）；纯炫语言模块为 `module_xxx.xc`；**避免重名**可加作者名第二前缀 → `module_作者名_模块名.h`
- 🔴 **目录名可含括号和中文**：`核心[官方]`、`系统API(前缀分类法)`、`炫易模块(MD5)` 等。**任何脚本处理这些路径必须用 `-LiteralPath`（PowerShell）或加引号 —— `[` `]` 会被当通配符。** 实测含 `()`/`[]` 的目录共 **13 个**：`核心[官方]`、`核心[官方]\系统API(前缀分类法)`、`数据库\数据库mysql\示例\数据库\xc-mysql类\MySQL5.7绿色版(免安装)`、`炫易模块\炫易模块(程序)`、`炫易模块\炫易模块(窗口)`、`炫易模块\炫易模块(加解密)`、`炫易模块\炫易模块(键盘鼠标)`、`炫易模块\炫易模块(进程线程)`、`炫易模块\炫易模块(网络)`、`炫易模块\炫易模块(网页)`、`炫易模块\炫易模块(文件目录)`、`炫易模块\炫易模块(系统)`、`炫易模块\炫易模块(MD5)`
- **`基础模块` 唯一路径**：`核心[官方]/基础模块/module_base.h`；**模块文件编码**：`UTF-8-BOM`

```text
IDE 运行时目录（IDE 启动自动搜索目录下模块文件）
炫彩IDE/data/XC-Module/       ← 正式模块目录（本仓库）
炫彩IDE/data/XC-Module-dev/   ← 开发模块目录（IDE 更新不会覆盖；同名不会被更新覆盖）
```

`XC-Module-dev/` 实测内容：`op483/` ✅（`lib\op_c_api_x64.lib`/`lib\op_c_api_x86.lib`、`module_op.h/.cpp`、`tool\run_compile.ps1`）、`s1d21992-OL插件6853/` ✅、`远程内存模块/` ✅（`RemoteHook.cpp/.h`）、`炫语言模块/` ✅（`module_xcl_demo.xc`）、`skill-炫模块封装/` ✅（官方注解速查镜像：`SKILL.md` + `reference.md`/`examples.md`）、`WorkBuddy-A星寻路模块/` ✅；`xc-module-wrapper/` ❌ **已不存在**。

| 场景 | 参考路径 |
|------|------|
| 最小薄封装 / 预编译 lib + DLL 复制 | `Like/Like-蓝奏云直链解析/` / `Like/Like-CURL网络访问2/` |
| vendor 源码内嵌 + 多 `//@src` | `常规/HaiTang-haitang2018k/` |
| COM / `IDispatch*` 对象 | `键鼠辅助/大漠对象模块/`、`常规/cainiao_84002751-大漠模块_72424/` |
| 多 cpp + 纯 C 源 | `常规/YYJSON对象/`、`22897350-易加加模块/kyozy-libzip修改版/` |
| 模板 + `/*@声明` | `常规/线程池/`、`核心[官方]/基础模块/`（哈希表） |
| 中文函数名（易语言风格） | `常规/luren1234-综合模块/`、`22897350-易加加模块/易加加/` |
| 拆分双头文件 | `核心[官方]/炫彩界面库/`（`module_xcgui.h` + `module_xcgui_class.h`） |
| 多级分组 `//@分组{ A.B` | `常规/u36298509-黑月界面类模块/module_DarkMoon.h`、`核心[官方]/基础模块/module_base.h` |
| 纯 `.xc` 模块（`#DLL导入表`） | `键鼠辅助/cainiao_84002751-OP插件0450/`、`卡卡/s1d21992-NZ_远程内存模块/` |
| 巨型聚合包（三级目录） / C++17 完整工程 | `22897350-易加加模块/` / `常规/u36298509-ExDUIR界面库/`、`小轩/xiaoxuan-小轩ImGui/` |
| 命名规范原文 | `核心[官方]/基础模块/module_base.h` 头部注释 |

> `常规/OpenSSL/` 实测为 `常规\OpenSSL\module_openssl.h`。**`module_tiandun_td_sdk.h` 实测在 `XC-Module` 与 `I:\炫彩ide\data` 下均不存在** —— 源材料中的引用按示例性引用处理，不作为可查路径。

## 3. 标准模块目录结构

```text
开发期 作者-模块名/
├── module_xxx.h          # 注解 + 对外声明（IDE 解析入口）
├── module_xxx.cpp        # 封装实现（CX 类型转换）
├── md5.txt               # 第一行 MD5，第二行时间戳（IDE/发布流程生成）
├── doc/                  # 可选，配合 //@doc
├── x86/ x64/             # 可选，预编译 lib + dll
├── lib/ vendor/          # 可选，内嵌第三方源码
└── 示例-模块名/  main.xc / common.xh / exe.rc / *.xcproj
     # main.xc 入口，子程序用「函数 返回类型 名(参数)」
     # common.xh 预编译头：仅注释/宏，**禁止 #include 模块头**
     # *.xcproj 的 <modules> 节点引用 module_*.h
发布期 作者名-模块名.zip/
├── module_xxx.h           # 头文件（@src/@lib 注解正确）
├── module_xxx.cpp         # 实现文件
├── lib/ x64/ xxx.lib + xxx.dll  ·  lib/ x86/（如有 32 位支持）
└── xxx-include/           # 第三方库头文件（仅封装所需的 .h）
```

**目录布局两版并存（都是真实用例）**：**注解/开发期用一级 `x64/`、`x86/`**（仓库主流：`Like\Like-CURL网络访问2\x64`、`核心[官方]\炫彩界面库\x64`、`常规\zlib\x64`、`网络\HPSocket\x64`、`数据库\sqlite3\x64` 等 20+ 模块）；**打发布 zip 时**再按 `lib/x64/`、`lib/x86/` 组织（仓库内如 `常规\lua模块\lib\x64`）。**理由**：注解里的相对路径必须与磁盘实际布局一致才能被 IDE 解析。
**拆分双头文件**：`module_xcgui.h`（`//@依赖 module_base.h`，常量/自由函数）+ `module_xcgui_class.h`（`//@依赖 module_xcgui.h`，类）。大界面库按此拆分避免单头过大（实测 `核心[官方]\炫彩界面库\` 下还有 `module_xcgui_embed.h`）。

## 4. 头文件元信息与 //@ 注解全集

| 元信息注解 | 必填 | 说明 |
|------|------|------|
| `//@模块名称` | 是 | IDE 显示名 |
| `//@版本` / `//@日期` / `//@作者` / `//@QQ` | 推荐 | 语义化版本 / `YYYY-MM-DD` / 作者 / QQ |
| `//@模块备注` | 推荐 | 功能、changelog、运行库 / C++ 版本要求 |
| `//@依赖` | 是* | `module_base.h` 或逗号/分行多个头文件 |
| `//@src` | 是 | 每行一个源文件，引号包裹 |
| `//@模块信息结束` | 否 | 实测 29 / 154 个模块使用 |

**两个不在 `reference.md` 清单里、但仓库真实存在的元信息注解**（出处 `xc-代码\线程池.mdc` 第 1–5 行，官方线程池模块 `module_threadpool.h` 头）：

```cpp
//@模块名称  线程池
//@基于文件  module_threadpool.h, threadpool.cpp
//@版本信息  头文件标注 v1.1 (2023-08-27)
//@依赖      module_base.h（以及 Windows API）
//@备注      示例见：示例\模块示例\xc-线程池
```

- `//@基于文件`：声明本模块由哪些文件构成，语义上替代 `//@src`；用空格分隔多个文件（此处为 `.h` + `.cpp` 两个），**不是** `//@src` 的「每行一个、引号包裹」写法。
- `//@版本信息`：自由文本版本说明（可写「头文件标注 v1.1 (2023-08-27)」），与 `//@版本`（语义化版本号）**并存但不同**。
- 两者属**历史写法**，`reference.md`/`skill.md` 的推荐模板未收录。**新建模块优先用 `//@版本` + `//@src`**；读到老模块里的这两个注解时按本节理解，不要当作写错。

`*` 特殊模块（炫扩展核心等）可不依赖 base，但绝大多数模块依赖 `module_base.h`。
**`//@模块信息结束` 机制**：信息不完整时可**提前结束扫描**，提高解析效率 —— **默认最多扫描 300 行**；文档提示**该命令未来可能废弃**。
**基础模块的「标准开头写法」（可直接套用）**：① 头文件最开头用 `@隐藏` 包住系统 include / pragma（避免 IDE 解析噪音、也能放编译告警开关）② 紧接着写模块信息头（允许在模块备注里追加「变更记录」）③ 用 `@src` 指定实现文件，例如 `//@src "module_base.cpp"`（避免 `.h` include `.cpp` 导致重复实现）④ 尽早写 `@模块信息结束`。

```cpp
// 推荐头文件模板
#pragma once
//@模块名称  我的模块
//@版本  1.0.0
//@日期  2026-09-12
//@作者  作者名
//@QQ  123456
//@模块备注  功能说明；C++17；运行库 /MT
//@依赖  module_base.h
//@src "module_mymod.cpp"
//@模块信息结束
#include "module_base.h"
#pragma comment(lib, "xxx.lib")   // 系统库可直接用此行
//@分组{ 工具类
//@别名  我的工具
class CMyTool {
public:
    //@别名  取版本()
    static CXTextA GetVersion();
};
//@分组}
// 仓库中并存的变体（勿强行统一）
// 变体 A：guard 宏放 //@隐藏（module_base.h、module_yyy.h）
#pragma once
#ifndef XCL_XXX_H
//@隐藏{
#define XCL_XXX_H
//@隐藏}
//@模块名称 ...
#include "module_base.h"
// 变体 B：元信息在 include 前（HaiTang、curl2、lanzou）
#pragma once
//@模块名称 ...
#include "module_base.h"
// 变体 C：XC_MODULE / XC_MOUDLE 守卫 include（curl2、zlib、mysql、xc-module-wrapper）
#pragma once
#if defined(XC_MOUDLE) || defined(XC_MODULE)
#include "module_base.h"
#endif
//@模块名称 ...
// //@依赖 与 //@src 写法
//@依赖  module_base.h
//@依赖  module_base.h,module_kyozy_libcurl.h
//@依赖  module_xcgui.h          // 子模块依赖父模块头
//@依赖  eplpinyin.hpp           // 也可依赖同目录非 module_ 头文件
//@src "module_xxx.cpp"
//@src "tools.cpp"
//@src "lib/yyjson.c"              // C 源
//@src "format.cc"                 // .cc 扩展名
//@src "module_zhmk.CPP"           // 大小写不敏感
```

| 变体补充 | 写法 | 出处 |
|------|------|------|
| `//@src` 位置 | 元信息块内 或 `#include` 之后，两种均合法 | 全仓库 |
| 多源文件 | 每个文件单独一行 `//@src` | `YYJSON对象`、HaiTang |
| 双头拆分 | `module_xcgui.h` + `module_xcgui_class.h`（后者 `//@依赖` 前者） | `核心[官方]/炫彩界面库/` |

> 变体 C 实际用法：`Like/Like-CURL网络访问2/module_curl2.h` 写 `#if XC_MODULE`，部分模块写 `#ifdef XC_MOUDLE`，`imgui\imgui_docking\module_imgui_docking.h` 两种都判断。**新建模块请用双判断写法。**
> `.xc` 模块依赖常带引号：`//@依赖 "module_windowsApi.h","module_e_ProcessThread.h"`；`@依赖` **逗号分隔；可加双引号**。
> **规则**：一行一个文件；wrapper cpp 通常第一行；vendor 源紧随其后。**同一头文件末尾可追加第二个 `//@src`** —— 实测 `核心[官方]/基础模块/module_base.h` 元信息块内写 `//@src "module_base.cpp"`（:177），文件末尾（:6012）追加 `//@src  "xc_mkStr.cpp"`。

**注解完整列表**

| 注解 | 用途 |
|------|------|
| `//@别名` | 炫语言中文名，含参数名 `方法(参数1, 参数2)` |
| `//@备注` | 功能说明，可多行（后续行用 `//` 续写） |
| `//@参数` | 参数文档；可用 `[in]` / `[out]` / `[in,out]` 标方向 |
| `//@返回` | 返回值说明 |
| `//@示例` | 炫语言示例（IDE 提示） |
| `//@doc "doc\xxx.txt"` | 外链 doc，内容为炫语言示例 |
| `//@分组{` / `//@分组}` | IDE 分组折叠，支持点号多级 |
| `//@启用枚举前缀` / `//@禁用枚举前缀` | 枚举成员显示为 `类型名_成员名` |
| `//@跳过 A, B, C` | 跳过指定标识符解析（如 `WNAPI_1` 这类修饰宏） |
| `//@隐藏{` / `//@隐藏}` | 隐藏不解析内容 |
| `@声明`（多行注释块 `/*@声明 … */`，块内注解前缀是 `@` 而非 `//@`） | 为已存在类/函数做「声明/别名补齐」 |
| `//@lib "path\\foo.lib"` | 链接库，常配合 `_WIN64` / `_DEBUG` 分支；`//@lib64 "x64\\foo.lib"` = **仅 64 位**链接（`.xc` 模块常用） |
| `//@复制文件 @当前模块路径 "x64\\a.dll"` | 编译后复制 DLL 到 **exe 目录**；`//@复制文件64 @当前模块路径 "op_x64.dll"` = **仅 64 位**工程复制 |
| `//@包含目录 @当前模块路径 "native\\include"` | 追加 include 路径（可相对 IDE 目录，或相对当前模块目录 + `@当前模块路径`） |
| `//@默认安装位置 炫扩展\\` | 模块管理器默认安装子目录 |
| `//@解析头文件` | 解析**下一行** include 的头文件内容；**支持「注释 include」（仅用于 IDE 识别/高亮，不加入编译列表）** |
| `//@预处理宏  XC_DLL` | 编译时自动加入预处理宏（**不影响全局项目设置**） |
| `//@编译选项` / `//@链接选项` | 附加编译 / 链接参数（可配合 `_DEBUG`/`_WIN64` 条件） |

```cpp
//@解析头文件
#include "xxx.h"                          // 解析外部头文件（将第三方 .h 的函数/类型导入 IDE）
//@复制文件  @当前模块路径 "dll\xxx.dll"   // 安装时复制 DLL 到输出目录
//@包含目录  @当前模块路径 "my_src\include"
//@预处理宏  XC_DLL
// @参数 --参数名 绑定
//@参数  输入一个整数a           // 普通写法：无参数名绑定
//@参数  --a  输入一个整数a      // --参数名：显式绑定参数名，IDE 按名对应
// __in / __out / __in_out 传参方向宏
__in       // 输入参数（单向传入）
__out      // 输出参数（函数通过引用传出）
__in_out   // 输入输出参数
// a:  输入参数
// out: 输出参数, 函数计算结果通过此参数传出
// io:  输入输出参数, 传入初始值并接收新值
int Func(__in int a, __out int& out, __in_out int& io);
// 静态函数封装（extern "C"）
//@备注  获取元素ID
//@参数  hXCGUI 对象句柄
//@返回  返回元素ID
//@别名  窗口组件_取ID(对象句柄)
extern "C" int WINAPI XWidget_GetID(HXCGUI hXCGUI);
// 可见性控制
//@隐藏{
// 头文件保护宏、#include、构造/析构、模板实现、COM 指针、void* _impl、std:: 成员
//@隐藏}
/*@声明
// IDE 展示用简化声明（模板、变参、已实现的外部接口）
*/
// 类继承的隐藏写法（隐藏基类，IDE 只看到类名）
//@别名  矩形类
class CRect123
//@隐藏{
: public RECT
//@隐藏}
{
    //@别名 添加()
    void Add() {}
};
// 智能指针
#智能指针  CefRefPtr<CefBrowser>  CefBrowserPtr                      // 完整声明（自动生成包装类）
#智能指针_仅声明  CefRefPtr<CefBrowser>  CefBrowserPtr  浏览器智能指针  // 仅声明类型（不生成实现代码）
// 编译条件宏
_WIN64              // 64 位
_DEBUG              // 调试版
XC_MODULE           // 模块编译期（正确拼写）
XC_MOUDLE           // 模块编译期（漏 D 的历史拼写）
XCL_MODULE_USE_DLL  // 模块优先使用动态库
XCL_MODULE_USE_LIB  // 模块优先使用静态库
// //@lib 按平台分支（推荐写法）
#ifdef _WIN64
//@lib "x64\tdx64.lib"
#else
//@lib "x86\Tdx86.lib"
#endif
// @编译选项 / @链接选项 条件化用例
#ifdef _DEBUG
    #ifdef _WIN64
    //@编译选项  /D "_WINDOWS64" /D "_UNICODE"
    #else
    //@编译选项  /D "_WINDOWS32" /D "TEST" /std:c++17
    //@链接选项  /nologo /DEBUG
    #endif
#else
    #ifdef _WIN64
    //@编译选项  /D "_WINDOWS64" /D "_UNICODE"
    #else
    //@编译选项  /D "_WINDOWS32" /D "_UNICODE"
    #endif
#endif
// 分组语法
//@分组{ 工具类
class CMyTool { ... };
//@分组}
// 多级分组（点号分隔）——不同位置相同组名会合并显示
//@分组{ 一级分组
int var1 = 10;
//@分组}
//@分组{ 一级分组.二级分组
int var2 = 20;
//@分组}
//@分组{ 一级分组.二级分组.三级分组
int var3 = 30;
//@分组}
//@分组{ 全局变量
//@备注  测试全局变量
//@别名  全局变量_var
static int test_var = 10;
//@分组}
//@分组{ 宏定义
//@备注  测试备注
//@别名  测试别名
#define SW_SSAA 123
//@分组}
//@分组{ 枚举
//@备注  枚举备注
//@别名  枚举类型别名
enum my_enum_type {
    //@备注  枚举项备注
    //@别名  枚举别名
    my_enum_item1 = 0,
    my_enum_item2 = 10,
};
//@启用枚举前缀  // 枚举值会带前缀
//@禁用枚举前缀  // 枚举值不带前缀
//@分组}
//@分组{ 类型定义
typedef int my_int_type;
typedef RECT* RECT_PTR;
//@分组}
//@分组{ 函数类型
typedef int (*fun_callback)(int, int);
typedef int (__stdcall *fun_callback2)(int, int);
//@分组}
//@启用枚举前缀  自动给枚举成员加上类型前缀
//@别名  枚举类型1
enum my_enum1 {
    //@别名 成功
    my_enum1_ok,   // IDE 显示: 枚举类型1_成功
    //@别名 失败
    my_enum1_fail, // IDE 显示: 枚举类型1_失败
};
```

- **`@别名` 三条硬规则**：① 在别名后附上**形参名列表**（有参数：`//@别名 天盾_置机器码(szMacCode)`、`//@别名 天盾_初始化(szIp, wPort, szSoftVer, szSoftName)`；无参数：`//@别名 天盾_取机器码()`、`//@别名 天盾_频率验证()`，**保留空括号 `()`**；可变参：**别名括号内不要写 `...`**（易触发「不符合变量命名规则」解析错误），只写第一个形参名，其余在 `@备注` 中说明「支持可变参数」）② 形参名应与下方真实声明中的参数名**一致**；`/*@声明 ... */` 内为第三方头文件补中文别名时同样适用 ③ 参数列表必须**逐个写出参数名**，禁止 `参数1..参数10` 省略写法 —— IDE 报「错误的模块命令」。
- **`@示例` 多行写法**：示例代码可多行，**不支持缩进；用 `--` 代替缩进**。
- **`@doc` 用法**：`@doc "doc\xxx.txt"` 把示例写到文本文件（**相对当前模块目录**）；**文档内用 `//@示例` 分隔多个示例**；支持函数 / 类 / 结构体。短函数直接在 `.h` 内写 `@备注/@参数/@返回/@示例`；**类/复杂函数 → 拆到 `doc\` 下用 `@doc` 引用**。基础模块广泛使用 `@doc "doc\\xxx.txt"`（`bytes_class.txt`、`vector_class.txt`、`map_class.txt`、`queue_class.txt`、`xcl_urlEncode*.txt`）。实测 `@doc` 命中 2 个文件：`常规\HaiTang-haitang2018k\module_haitang2018k.h`、`核心[官方]\基础模块\module_base.h`。
- **`@参数 --参数名` 机制**：**IDE 解析会跳过参数名，仅辅助写作与阅读**。`//@参数` 的 `[in]/[out]/[in,out]` 与 `__in/__out/__in_out` 是**两套并行约定**：前者只作文档，后者影响 IDE 生成代码。
- **`//@lib` 按平台分支**：**x64 / x86 两套静态库不要并列写两条 `@lib`** 让链接器同时拉进 32/64 库，应用 `#ifdef _WIN64` … `#else` … `#endif` 包住，**按目标平台只保留一条 `@lib`**；`//@lib` 仍写在分支内，由预处理器决定只展开一条；库文件放在模块目录下 `x64\`、`x86\` 等子目录即可；`@复制文件` 若需区分 DLL，同样可用 `#ifdef _WIN64` 分包指定。
- **适合放进 `//@隐藏{ ... //@隐藏}` 的典型内容**：平台条件 / typedef / 宏（如 `vint/uvint`、`__in/__out/__in_out` 等兜底定义）；只为 C++ 编译服务、对炫语言提示无价值的实现细节；模板、重载、内部构造/运算符等「类型实现」，只在外观层暴露必要接口。
- **智能指针机制**：自动模拟 C++ 智能指针常用接口与 `operator->()`。**默认会模拟** `T* get()`、`addRef/addref/AddRef`、`Release/release`、`T* operator->()`。`#智能指针_仅声明` 用于 **C++ 源码已定义类型时仅声明接口，避免重复定义**，可附中文别名。状态：**文档化能力**，实测仓库 0 个文件使用。
- **枚举前缀自动化**：`@启用枚举前缀` / `@禁用枚举前缀`。枚举是全局类型，避免成员名冲突；启用后枚举成员在 IDE 显示时自动带「枚举别名_成员别名」前缀。
- **可分组的内容类型**：**类、函数、全局变量、宏定义、枚举、结构体、typedef、函数指针类型**。**仓库真实用例**：`//@分组{  虚拟键码.字母键`（`核心[官方]/基础模块/module_base.h:5625`，注意 `{` 后有**两个空格**）、`//@分组{ 虚拟键码.数字键`（`module_base.h:5655`）、`//@分组{ 虚拟键码.F键`（:5693）、`//@分组{ 虚拟键码.其他`（:5745）、`//@分组{ 控件入口.界面基类`（`常规/u36298509-黑月界面类模块/module_DarkMoon.h:262`，另 :721 重复出现）、`//@分组{ 控件入口.通用控件`（`module_DarkMoon.h:1123`）。
- **`@src "xxx.cpp"`** 声明需要加入编译的 cpp（**避免在 `.h` 直接 include cpp 造成重复实现**）；`#pragma comment(lib, "winhttp.lib")` 与 `//@lib` 可混用。
- **编译条件宏**：⚠ **`XC_MODULE` / `XC_MOUDLE` 两种拼写并存，必须同时判断**。仓库里最稳妥的写法（`imgui\imgui_docking\module_imgui_docking.h:27`）：`#if defined(XC_MOUDLE) || defined(XC_MODULE)` / `#include <windows.h>` / `#endif`。使用 `XC_MODULE` 的模块示例：`Like/Like-CURL网络访问2/module_curl2.h:18`、`数据库/数据库mysql/module_mysql.h:14`、`网络/WinHttp/module_winhttp.h`、`常规/zlib/module_ev_zlib.h:17`、`常规/u36298509-Gdiplus模块/module_gdiplus.h:5`、`炫易模块/*` 全套。**实测计数**：`XC_MOUDLE` **54** 个文件、`XC_MODULE` **24** 个文件。`XCL_MODULE_USE_DLL` / `XCL_MODULE_USE_LIB` 出处：**项目属性可设置**。

**`/*@声明` 块详解 🔴 —— 注解前缀：块内用 `@`，不用 `//@`。这是最容易写错的地方。** 官方示例（`22897350-易加加模块/curl/module_curl.h:38`）：

```cpp
/*@声明
@分组{ 常量
@别名 CURL错误码
@备注 libcurl 执行结果，成功为 CURLE_OK(0)
enum CURLcode
{
	@别名 CURLE_OK
	CURLE_OK = 0,
	@别名 CURLE_不支持协议
	CURLE_UNSUPPORTED_PROTOCOL = 1,
	@别名 CURLE_初始化失败
	CURLE_FAILED_INIT = 2,
};
@分组}
*/
```

块内写 `//@备注` 也有效（`22897350-易加加模块/易核心模块/module_易语言核心模块.h:2186`）：

```cpp
/*@声明
//@备注  将指定数据转换为文本后返回
//@参数  待转换的数据  通用型
//@返回  文本型
//@别名  到文本(待转换的数据)
template<class T> CXText 到文本(T 待转换的数据);
*/
// 三种典型用途
// 1. 隐藏复杂模板实现，只暴露一行签名
/*@声明
//@备注 取键对应的值
//@别名 取值(键, 结果)
值类型 取值(键类型 键, BOOL* 结果=nullptr);
*/
//@隐藏{
template<class K, class V>
inline V _ht_getV(const wchar_t* k, BOOL* r, void* h, V*);
// ...所有重载实现...
//@隐藏}
// 2. 暴露变参函数
/*@声明
    //@别名  投递任务()
    BOOL PostTask(Fun &&fun, ...);
*/
//@隐藏{
    template <typename Fun, typename... Args>
    inline BOOL PostTask(Fun&& fun, Args&&...args) { /* ... */ }
//@隐藏}
// 3. 声明已实现的外部接口
/*@声明
@分组{ 声明_已实现的外部接口
@备注  函数功能说明
@参数  参数a说明
@参数  参数b说明
@返回  返回值说明
@别名  中文函数名(参数a, 参数b)
int fun_test5786(int a, int b);
@分组}
*/
```

> **实测补充（`常规\hxznhf-JSON操作\module_json.h`）**：同一个 `/*@声明 ... */` 块内**可混用** `@` 无斜杠形式与 `//@` 形式 —— :126–:158 块内既写 `//@别名 到逻辑型()`，也写 `@备注 添加一个JSON成员` / `@别名 添加成员(JSON)` / `@参数 JSON`。另可见**同名注解连写两行**（:105–:106 连续两条 `//@别名`）—— IDE 取后者为命令名。
> `@声明` 的定义：**对已存在（类/函数等）做「声明/别名补齐」**，用多行注释包裹 `/*@声明 ... */`；块内为函数写 `//@别名` 时，建议采用上文的「中文名(形参…)/无参用 ()」格式。

**可变参函数的落地范式**：基础模块对 `xcl_log(...)` / `xcl_log2(...)`、`xcl_mkStr(...)` / `xcl_mkStrA(...)`（**最多 12 参**的「文本组合」）、`xcl_mkStr2(...)` / `xcl_mkStr2A(...)`（**不限参数**的「文本组合2」）使用了 `/*@声明 */ + ...`。**经验**：当实现层为了兼容性/性能需要 variadic 或模板展开时，**模块文件层用 `...` 即可**。
**`std` 兼容也靠 `@声明` 补齐**：基础模块用 `/*@声明 ... */` 在 `module_base.h` 里补了 `namespace std` 下的 `std::wstring / std::string`（提示用户炫语言侧更推荐 `文本型/文本型A`）、`std::vector<T>` 的常用接口（`operator[]/push_back/resize/pop_back/size/empty/back/front/data`）。**可复用经验**：要暴露第三方类型（尤其模板容器）给炫语言时，**优先用 `@声明` 做一层「可解析外观」**。
**第三方库「随模块内置编译」范式**（参考 `常规\hxznhf-JSON操作\module_json.h`）：**源码放模块目录 + `@src` 加入编译 + `@隐藏` 隔离细节 + `@声明` 提供外观 + 入口包装类 + 示例工程**。要点：顶部 `@隐藏` 只 include 第三方总头，避免 IDE 解析细节；用 `typedef` 把第三方类型起「模块内部名」并用 `@隐藏` 包住；`@声明` 里写 `@src "xxx.cpp"` 把第三方 `.cpp` 加入编译，并写「同名类外观」只列用户需要的成员加中文 `@别名`；对模板/可变参/自动匹配类型的接口可在外观里用 `...`；适当提供更易用的二次包装类（含 `parse()`、`getErr()`）；示例覆盖真实用法（`root[A"a"][0][A"b"]`、`取对象()`、`取成员数()`、`[]` 链式访问）。

| 源材料描述（`JSON操作`） | 实测现状（以此为准） |
|---|---|
| `typedef Json::Value CJsonValue;`（被 `@隐藏` 包住） | **该行已被注释掉**：`// typedef  Json::Value   CJsonValue;`（:14） |
| 外部入口类名 `CJsonReader` | 实测为 **`Xjson`**，且**继承**第三方类型：`class Xjson : public Json::Value`（:56） |
| `set(...) / insert(...) / append(...)` 用 `...` 表达 | 实测外观用**具体类型签名**：`Value& append(JSON value);`、`bool removeIndex(UINT index, Value* removed = 0);`（:146、:152） |
| `@src` 写在 `@声明` 里 | 实测 `//@src` 写在**元信息块内**（:16–:19，共 4 行） |
| 示例路径 `示例/模块示例/xc-json/main.xc` | 实测为 **`示例\JSON例子\main.xc`**，演示 API 为 `解析(A"...")` / `到文本()` / `取类型()` / `添加成员(记录)` / `删除成员(1)` / `删除键(A"age")` |

- **显式优先于隐式**：基础模块在 `CXBytes` 等类里明确提到：**自动转换不安全，可能造成难以发现的意外 bug**。因此不在 C++ 层做隐式转换（或减少隐式转换），通过显式成员函数/显式操作符（如 `explicit operator bool()`）提供「安全可控」的用法。**通用规范：能显式就别隐式**，尤其是指针 / 内存 / 生命周期相关类型。
- **命名空间**：不同模块中同名函数/类用命名空间区分。

```cpp
//@别名  模块A
namespace nameA {
    //@别名  测试函数(参数a, 参数b)
    static int test(__in int a, __in int b) { return a + b; }
    //@别名  测试类
    class CA123 { public: int Add(int a, int b) { return a + b; } };
}
//@别名  模块B
namespace nameB {
    static int test(__in int a, __in int b) { return a * b; }
}
```

炫语言调用：不指定命名空间则匹配第一个找到的，指定则调用对应空间（`nameA::test(1, 2)` / `nameB::test(1, 2)`）。支持命名空间的类型：**类、枚举、函数、变量、typedef。宏不支持。** 补充：`@别名` 可给命名空间提供中文显示/调用名；**一个模块可多个命名空间**；**不同模块也可以使用相同命名空间名**（常用于拆分模块、加速编译）。

## 5. CX 类型映射

| 炫语言 | C++ 封装用 | 说明 |
|--------|-----------|------|
| `文本型` / `文本型A` | `CXText` / `CXTextA` | 底层 `std::wstring`（`get()` → `const wchar_t*`）/ `std::string`（UTF-8/ANSI） |
| `字节集` | `CXBytes` | 底层 `std::vector<BYTE>`；**无 `.data()`** |
| `动态数组<T>` / `字典<K,V>` / `队列类<T>` | `CXVector<T>` / `CXMap<K,V>` / `CXQueue<T>` | |
| `短整型` / `正短整型` | `short` / `unsigned short` / `USHORT` | 2 字节 |
| `整型` / `正整型` | `int` / `unsigned int` / `UINT` | 4 字节 |
| `长整型` / `正长整型` | `__int64` / `INT64`、`unsigned long long` / `UINT64` | 8 字节 |
| `变整型` / `正变整型` | `vint` / `uvint` | x64=`__int64`/`unsigned __int64`，x86=`int`/`unsigned int` |
| `逻辑型` / `逻辑型c` | `BOOL` / `bool` | **4 字节**（对外接口不要用 `bool`）/ 1 字节 |
| `字节型` | `BYTE` / `unsigned char` | 不是 `char` |
| `字符型A` / `字符型` | `char` / `wchar_t` | ANSI / 宽字符 |
| `浮点型` / `双浮点型` | `float` / `double` | |
| `空类型` / `空类型*` | `void` / `void*` | 泛型指针 |
| 结构体 | `struct` + `//@别名` | 字段用 CX 类型，写 `toCxXxx()` / `fromCxXxx()` 转换 |

**std 容器直接互通**：基础模块通过 `/*@声明` 暴露了标准库容器，**可直接作为返回值，无需手写转换** —— `std::wstring` → `文本型`（`文本型 t = func()`）、`std::string` → `文本型A`、`std::vector<T>` → `动态数组<T>`（`动态数组<整型> arr = func()`）。

```cpp
// 边界转换（wrapper cpp 内）
static std::string cxAtoStr(const CXTextA& s) {
    return s.empty() ? std::string{} : std::string(s.get(), s.size());
}
static CXTextA strToCxA(const std::string& s) { return CXTextA(s.c_str()); }
```

内部用 `std::string`，对外一律 CX 类型。可选文本用空 `CXTextA` 表示 `nullopt`；可选整数用哨兵值（如 `-1`，需在 `//@备注` 说明）。

```cpp
// CXBytes 读写（最高频的坑）
readMemory(h, addr, const_cast<void*>(static_cast<const void*>(bin.get())), bin.size());  // 读 —— get() 返回 const BYTE*
void* buf = out.resize(len);                                                            // 写 —— 用 resize()/alloc() 的返回值拿可写指针
readMemory(h, addr, buf, len);
// ❌ bin.data() 不存在！CXBytes 没有 std::vector 风格的 data()
// ❌ 含 '\0' 会被截断
return CXBytes(data.c_str());
// ✅ 用 (指针, 长度) 构造
return CXBytes((const BYTE*)data.data(), data.size());
// 签名级细节（含中文别名）
const BYTE* get() const;                    // 读指针（const）
const BYTE* getPtr() const;
BYTE* alloc(size_t length);                 // 别名 置大小 —— 不保留原数据
BYTE* resize(size_t length);                // 别名 调整大小 —— 保留原数据，不足则截断
void  addSize(size_t length);               // 别名 添加大小 —— 末尾追加
CXBytes(const BYTE* data, size_t length);
CXBytes(const std::vector<BYTE>& list);
CXBytes(const std::initializer_list<BYTE> list);
void set(const void* data, size_t length);
void add(const void* data, size_t length, size_t off = -1);        // 别名 添加数据
void addText(const wchar_t* pText, BOOL bTerminator = FALSE, size_t off = -1);
void addTextA(const char* pText, BOOL bTerminator = FALSE, size_t off = -1);
void replace(const void* data, size_t length, size_t off, size_t old_length = -1);
void swap(CXBytes& right);
size_t size() const;
BOOL empty() const;
BYTE& operator[](size_t index);
BOOL operator==(const CXBytes& _that);
// CXText / CXTextA / CXVector
const wchar_t* get();   // CXText（等价 getPtr()）
const char* get();      // CXTextA
const wchar_t* getPtr() const;
const char* getPtr() const;
size_t size();
BOOL empty() const;
explicit operator bool() const;
CXVector(size_t size_);
const BYTE* getPtr() const;              // 底层连续内存
void set(size_t off, T& value);
void set(size_t off, T&& value);
BOOL empty() const;
// 支持 push_back、size、operator[]、data() 等，详见 module_base.h
```

**写入 Win32 API / `readMemory` 时**：优先 `void* p = bytes.resize(n)`；只读场景用 `bytes.get()`，必要时 `const_cast`。

| 参数与返回值约定 | 做法 |
|------|------|
| 入参 UTF-8 文本 / Unicode 文本 | `const CXTextA&` / `const CXText&` 或 `const wchar_t* pText` |
| 出参 / 返回文本 | `CXTextA&` 或返回 `CXTextA` |
| 可选文本（C++ optional） / 可选整数 | 空 `CXTextA` → `nullopt` / 哨兵值如 `-1`（需在 `//@备注` 说明） |
| 逻辑值对外 / 回调 | `BOOL`，内部转 `bool` / `typedef` + 函数指针，通常放 `//@隐藏` 或不暴露 |
| 需要释放的字符串/字节 | **返回值**用 `CXText` / `CXBytes`，不返回裸指针 |
| 不需要释放的字符串 | 可用 `const wchar_t*` |

口径补充：**指针参数命名**以 `p` 开头（`const wchar_t* pText`）；**字符串参数**优先 `const wchar_t*`；**结构体/对象参数**尽量用引用传递（`RECT &rc`）；**逻辑型统一**使用 `BOOL`。

**基础模块工具（`module_base.h` 提供）** —— 编码时使用英文函数名，右列为炫语言端 `//@别名`：

| 英文函数（编码用） | 炫语言别名 | 说明 |
|------------------|-----------|------|
| `U2W` / `W2U` / `U2A` / `A2U` / `A2W` / `W2A` | — | 编码转换 |
| `xcl_log()` / `xcl_log2()` | `调试输出()` / `调试输出2()` | IDE 调试窗口输出 / 不分隔参数 |
| `xcl_logFormat()` / `xcl_logFormatA()` | `调试输出格式化()` / `调试输出格式化A()` | 格式化输出 |
| `xcl_getMax()` / `xcl_getMin()` | `取最大值()` / `取最小值()` | 比较两个同类型值 |
| `xcl_getScreenWidth()` / `xcl_getScreenHeight()` | `取屏幕宽度()` / `取屏幕高度()` | 不含任务栏 |
| `xcl_writeFile()` / `xcl_readFile()` / `xcl_readFileTextA()` | `文件写入()` / `文件读取()` / `文件读取文本A()` | |
| `malloc` / `free` | `内存分配()` / `内存释放()` | C 标准库 |
| `_wtoi()` / `_wtoi64()` / `_wtof()` | `文本到整型()` / `文本到长整型()` / `文本到双精度浮点型()` | |
| `xcl_intToHexText()` / `xcl_int64ToHexText()` | `整型到十六进制文本()` / `长整型到十六进制文本()` | |

```cpp
#define cx_iterator  auto   // 自动类型迭代器
#define 事件定义             // 事件声明标记（空宏，IDE 识别用）
```

**🔴 长度单位必须在注释里写明**：基础模块对 `W2A/A2W/W2U/U2W/A2U/U2A` 这类接口的注释，都会强调 `length` 传入时的**单位（字符 or 字节）**，以及**允许 `-1` 表示自动取长度**。封装时建议把「长度单位」作为 `@参数` 说明的**必填项**，避免调用方误传导致截断/越界/乱码。
**命名规范原文（`module_base.h` 头部注释）**：① 小驼峰：`xcl_log()`、`text_getLeft()`、`text_skipSpaceWrapRight()` ② 前缀分类：全局函数 `xcl_`，界面库 `XC_`；**别名中不加下划线**；相同单词尽量向前排列以获得更好补全效果 ③ 系统 API：中文别名遵守规范，英文名称不变（`printf_s()` → 控制台格式输出A）④ 类名：`CXAaaBbbCcc`（`C`=类，`X`=防重名前缀）⑤ 类成员函数：小驼峰，私有 `_` 开头（`CXAaaa::_getPtr()`）⑥ 类成员变量：`m_` 前缀，私有 `_` 前缀（`_length`）⑦ 结构体：名称小写+下划线+末尾下划线，成员小驼峰 ⑧ **枚举名同结构体风格，末尾加下划线，例如 `listBox_item_flag_`**。

## 6. Handle / 全局映射表生命周期与线程安全

```cpp
// Handle 模式（单实例 / 少量实例 / 调用频繁）
// .h
class CXxx {
private:
    void* _handle = nullptr;      // 放在 //@隐藏 块里
public:
    CXxx() : _handle(nullptr) {}
    ~CXxx() { close(); }
    BOOL init(...);               //@别名 初始化()
    void close();                 //@别名 关闭()
};
// .cpp
struct XXXImpl { void* resource = nullptr; };
BOOL CXxx::init(...) {
    close();                                  // 幂等：先清理
    auto* p = new XXXImpl;
    p->resource = CreateSomething(...);
    if (!p->resource) { delete p; return FALSE; }
    _handle = p; return TRUE;
}
void CXxx::close() {
    auto* p = (XXXImpl*)_handle;
    if (!p) return;
    ReleaseSomething(p->resource);
    delete p; _handle = nullptr;
}
// 全局映射表（可达数千实例 / 需要拷贝移动语义）
static std::unordered_map<CXXxx*, XxxImpl*> g_xxxMap;
static std::mutex g_mapMutex;
static XxxImpl* _getImpl(CXXxx* obj);   // ← 前向声明，见 §8 铁律 1
CXXxx::CXXxx() {
    auto* impl = new XxxImpl();
    { std::lock_guard<std::mutex> lk(g_mapMutex); g_xxxMap[this] = impl; }
}
CXXxx::~CXXxx() {
    std::lock_guard<std::mutex> lk(g_mapMutex);
    auto it = g_xxxMap.find(this);
    if (it != g_xxxMap.end()) { delete it->second; g_xxxMap.erase(it); }
}
static XxxImpl* _getImpl(CXXxx* obj) {   // 获取器 — 加锁查找（定义须在调用之前，否则加前向声明）
    std::lock_guard<std::mutex> lk(g_mapMutex);
    auto it = g_xxxMap.find(obj);
    return (it != g_xxxMap.end()) ? it->second : nullptr;
}
CXXxx::CXXxx(const CXXxx& other) {       // 拷贝构造 — 新建 impl + 深拷贝数据
    auto* impl = new XxxImpl();
    { std::lock_guard<std::mutex> lk(g_mapMutex); g_xxxMap[this] = impl; }
    auto* oi = _getImpl(const_cast<CXXxx*>(&other));
    if (oi) impl->data = oi->data;   // 拷贝数据
}
CXXxx::CXXxx(CXXxx&& other) {            // 移动构造 — 转移映射条目，other 析构时不会 double-free
    std::lock_guard<std::mutex> lk(g_mapMutex);
    auto it = g_xxxMap.find(&other);
    if (it != g_xxxMap.end()) { g_xxxMap[this] = it->second; g_xxxMap.erase(it); }
}
// PIMPL _impl 指针
// .h
class CHaitangUpdate {
    //@隐藏{ void* _impl; //@隐藏}
};
// .cpp
CHaitangUpdate::CHaitangUpdate() { _impl = new haitang::api2018k::Update(); }
CHaitangUpdate::~CHaitangUpdate() { delete (haitang::api2018k::Update*)_impl; }
```

> 拷贝/移动构造与运算符重载是前向声明问题的**高频触发点**（见 §8 铁律 1）。

| 选型条件 | Handle | 全局映射表 |
|------|--------|----------|
| 1 个实例 / ≤10 实例 / 调用频繁 | ✅ / ✅ / ✅ | 过重 / 可选 / 锁开销 |
| 可达数千 / 需要拷贝移动 | ❌ / ❌ | ✅ / ✅ |
| 线程安全场景 | 方法 |
|------|------|
| 全局映射表 | `std::mutex` + `lock_guard`，构造/析构/获取器全加锁 |
| 单次初始化 | `std::atomic<bool>` + CAS，或 `std::call_once` |
| 析构安全 | 锁内取指针，解锁后再释放（避免锁重入） |
| 每线程数据 | `thread_local`，无需加锁 |
| 跨线程窗口消息 | `GWLP_USERDATA` 访问加 `CRITICAL_SECTION` |

**审查侧巡检重点**：全局变量无锁读写、懒初始化（改 `std::call_once`）、跨线程窗口消息、可视化回调的 `WM_DESTROY` 释放竞态。

## 7. 模板类封装与 `/*@声明` 隐藏

炫语言 IDE **支持类型模板参数**，不支持非类型模板参数、显式特化、`::` 嵌套。

```text
✅ template<class K, class V> class CT { ... }
✅ template<class T> T Fun(T a)          // 参数推导返回类型
❌ template<int N> class CT { ... }      // IDE 无法解析
❌ template<> struct _vtype<int> { ... } // IDE 不支持显式特化
❌ CT<A::B, C::D>                        // IDE 无法解析 ::
// 模式 A — 基础类型直接当模板参数（最简）
//@别名 哈希表
template<class K, class V>
class CXHashMap { ... };
// 模式 B — 标签分发代替特化
// ❌ IDE 报错
template<> struct _ht_vtype<int> { using type = int; };
// ✅ 同名函数 + 不同参数类型重载，用 decltype 取类型
inline int    _ht_vtype_impl(int*)    { return 0; }
inline INT64  _ht_vtype_impl(INT64*)  { return 0; }
inline CXText _ht_vtype_impl(CXText*) { return 0; }
using V = decltype(_ht_vtype_impl((VT*)nullptr));
// 模式 C — /*@声明 控制 IDE 显示：每函数一个 /*@声明 块（IDE 只看到干净的一行签名），
//          所有重载实现塞进下方 //@隐藏{ … //@隐藏}
/*@声明
    //@别名  投递任务()
    BOOL PostTask(Fun &&fun, ...);
*/
//@隐藏{
    template <typename Fun, typename... Args>
    inline BOOL PostTask(Fun&& fun, Args&&...args) { /* ... */ }
//@隐藏}
//@隐藏{
inline int    _ht_vtype_impl(int*)    { return 0; }
inline INT64  _ht_vtype_impl(INT64*)  { return 0; }
inline CXText _ht_vtype_impl(CXText*) { return 0; }
inline int    _ht_getV(const wchar_t* k, BOOL* r, void* h, int*);
inline CXText _ht_getV(const wchar_t* k, BOOL* r, void* h, CXText*);
//@隐藏}
// 说明：`PostTask` / `_ht_vtype_impl` / `_ht_getV` 的 `/*@声明` + `//@隐藏` 组合写法与 §4 同一范式，此处不再重复注释文字。
//@别名 哈希表
template<class K, class V>
class CXHashMap {
public:
    //@别名 取值(键, 结果)
    V get(K key, BOOL* result = nullptr) {
        return _ht_getV(key, result, handle, (V*)nullptr);   // 空指针决定重载
    }
};
// 参数输入推导：返回类型 T1 取第一个参数的类型
template<class T1, class T2> T1 funName(T1 a, T2 b);
// 函数模板类（重载 operator()，封装回调）
/*@声明
//@别名 函数类
template<class T>
class 函数类;
*/
//@隐藏{
template<typename T>
class 函数类;
template<class R, class... Args>          // 特化：提取函数类型 R(Args...)
class 函数类<R(Args...)> {
public:
    using FuncType = R(*)(Args...);
    FuncType _func = nullptr;
    函数类() = default;
    函数类(FuncType func) : _func(func) {}
    void operator=(FuncType func) { _func = func; }
    R operator()(Args... args) { return _func(std::forward<Args>(args)...); }
};
//@隐藏}
// 避免「值 → CXText → wchar_t* → 解析」往返，值直接透传
// ❌ 浪费：int 123 → CXText("123") → _wtoi → 123
CXText a(key), b(value);                    // b(value) 对 int 做 swprintf
return _ht_addTxt(a.get(), b.get(), ...);   // b.get() 拿 wchar_t* 再被 _wtoi 解析
// ✅ 直通：值直接传递，跳过 CXText 往返
int _ht_addKV(const wchar_t* k, int v, BOOL no, void* h) {
    HashVal hv; hv.type = 3; hv.i32 = v;    // int 直接写入
    ...
}
哈希表<文本型, 整型> hash
文本型 ret = funName(text, 2)   // T1=文本型 → 返回文本型
浮点型 ret = funName(2.5, 2)    // T1=浮点型 → 返回浮点型
函数类<int(int, int)> func = add   // 绑定函数
整型 ret = func(1, 2)              // 通过 operator() 调用
```

| 模板类型推导（IDE 支持 4 种） | 示例 | 说明 |
|---------|------|------|
| 变量声明指定 | `CT<整型> var` | 定义变量时显式指定 |
| 函数调用指定 | `funName<整型>()` | 调用时尖括号指定 |
| 参数输入推导 | `整型 ret = funName(100)` | 根据参数类型自动推导 |
| 函数模板类 | `函数类<int(int,int)> func = add` | 函数类型作为模板参数 |

**其他要点**：**避免模板依赖型 friend 声明**（与 .cpp 具体重载二义性 C2668）→ 改命名空间级前向声明；`operator[]` 返回类型可由模板参数决定（`CT<整型> ct; 整型 ret = ct[0];`）；继承固定模板参数（`class CT2 : public CT<int> { };`）；**模板继承 / 模板指针的模拟思路** —— 复杂模板代码用 `@隐藏` 隐藏原模板，再用 `/*@声明 ... */` **模拟一个「非模板外观类」**，把可用接口暴露给 IDE。

## 8. 编码铁律

**🔴 命名铁律：`.h` / `.cpp` 里的实际 C++ 标识符必须是英文，中文只出现在 `//@别名` 注解里。**

```cpp
// ✅ 正确
int getWindowWidth(HWND hWnd);          //@别名 取窗口宽度(HWND 窗口句柄)
// ❌ 错误 —— 编译失败
整型 取窗口宽度(HWND 窗口句柄);
//@别名  AES加密_HEX密钥(明文UTF8, 密钥UTF8)
static CXTextA EncryptHexKey(const CXTextA& plainUtf8, const CXTextA& hexKeyUtf8);
```

> 例外：**易语言迁移风格**允许中文函数名（`常规/luren1234-综合模块`、`22897350-易加加模块/易加加` 大量使用）。新模块优先英文+别名。
> C++ 原库有重载时，用不同英文名 + 不同别名（`EncryptHexKey` / `EncryptPasswordSalt`），**禁止同名重载暴露给 IDE**。

| 元素 | 规范 |
|------|------|
| 全局函数 | `xcl_` + 小驼峰（`xcl_log`）；别名不加下划线 |
| 类名 | `CXAaaBbb`（`C`=类，`X`=防重名前缀） |
| 类成员函数 | 小驼峰；私有 `_` 开头（`_getPtr`） |
| 类成员变量 | `m_` 前缀；私有 `_` 前缀 |
| 结构体 / 枚举 | 全小写+下划线，**末尾加下划线**（`listBox_item_`），成员小驼峰 |
| 指针参数 | `p` 前缀（`const wchar_t* pText`） |
| 宏 | 大写前缀（`XCL_max`、`XCL_PI`） |
| **重载** | 炫语言**不支持重载** → `func()` / `func2()` / `func3()`，参数少的编号小 |
| 前缀聚集 | 相同前缀函数连续排列，方便补全：`XList_GetItemText` / `XList_GetItemCount` |
| 常用单词中英对照（起名 / 翻译别名用） | | | | | |
|------|------|------|------|------|------|
| get | 取 | set | 置 | add | 添加 |
| delete | 删除 | find | 查找 | query | 查询 |
| count | 数量 | size | 大小 | item | 项 |
| group | 组 | member | 成员 | user | 用户 |
| account | 账号 | password | 密码 | create | 创建 |
| run | 运行 | enable | 启用 | state | 状态 |
| color | 颜色 | event | 事件 | data | 数据 |
| addr | 地址 | dest | 目标 | src | 源 |
| width | 宽度 | height | 高度 | info | 信息 |
| opt | 选项 | flag | 标识 | select | 选择 |
| wnd/window | 窗口 | rect | 矩形/坐标 | point | 坐标点 |

```bash
# 铁律 1 — 前向声明 🔴 反复出错：在 .cpp 新增代码调用 static 辅助函数前，先确认定义位置
grep -n "static.*_getXxxImpl" module_xxx.cpp   # 定义在哪
grep -n "_getXxxImpl("        module_xxx.cpp   # 调用在哪
```

定义在调用之后 → 调用前加 `static XxxImpl* _getImpl(CXXxx* obj);`。高频触发：拷贝构造 / 移动构造 / 运算符重载。

```cpp
// 铁律 2 — const void* → const char* 必须显式转换 🔴
// ❌ C2664
std::string s(h.first.getData(), h.first.getSize());
// ✅
std::string s((const char*)h.first.getData(), (size_t)h.first.getSize());
// 铁律 3 — .c_str() 生命周期
return _a2w(str).c_str();          // ✅ CXText 构造时拷贝
const wchar_t* p = _a2w(str).c_str();  // ❌ 悬垂
someStruct.key = p;                     // ❌ 悬垂
// 铁律 4 — 异步 Lambda 必须值捕获 🔴 严重 bug
// ❌ 引用捕获 → 局部变量析构后访问 = 崩溃
auto fut = std::async(std::launch::async, [&]{ return exec->execute(...); });
fut.wait_for(timeout);   // ❌ std::async future 析构会阻塞等待任务完成
// ✅ thread + promise + detach + 全部值捕获
std::promise<Response> prom;
auto fut = prom.get_future();
std::thread([exec, m=std::string(method), p=std::string(url.path),
             h=headers, b=bodyPtr, prom=std::move(prom)]() mutable {
    try { prom.set_value(exec->execute(m.c_str(), p.c_str(), h, b, nullptr)); }
    catch (...) { try { prom.set_exception(std::current_exception()); } catch(...) {} }
}).detach();
auto status = fut.wait_for(std::chrono::milliseconds(timeout));
// 铁律 5 — 中文路径文件 I/O 🔴 Windows 特有
// ❌ ifstream(const char*) 按 GBK 解析路径 → 中文路径失败
// ❌ std::filesystem 需要 C++17，炫彩 IDE 默认不支持（C2039 "filesystem" 不是 "std" 成员）
// ✅ _wfopen 原生支持 Unicode
FILE* fp = _wfopen(wpath.c_str(), L"rb");
fseek(fp, 0, SEEK_END); long size = ftell(fp); fseek(fp, 0, SEEK_SET);
std::string content(size, '\0');
fread(&content[0], 1, size, fp);
fclose(fp);
// 铁律 8 — 字节布局
// ❌ sizeof(CXText) 只有约 16 字节（内部是指针），memcpy 整个对象是错的
memcpy(&txt, data, sizeof(CXText));
// ✅ 先落栈缓冲，再构造对象
char buf[8192];
memcpy(buf, data, size);
CXText txt(buf);
```

遍历 headers/maps 优先用 `.std_str()`，比 `.getData()` 安全。**路径含括号与中文时，脚本侧必须用 `-LiteralPath`** —— 见 §2。
- **铁律 6 — 优先使用基础模块自带的转换函数**：`U2W` / `W2U` / `U2A` / `A2U` / `A2W` / `W2A`，不要手写。
- **铁律 7 — 编码一致性 🔴**：`.h` 和 `.cpp` **均必须 UTF-8-BOM**。混用 UTF-8 / ANSI 会导致中文字符串编译或运行时乱码。
  > 实测 BOM 字节（前 3 字节 `EF BB BF`）：`module_base.h`、`module_haitang2018k.h`、`module_json.h`、`module_lanzou.h` 均为 `EF BB BF`。
  > 复核命令：`$fs=[System.IO.File]::OpenRead($p); $b=New-Object byte[] 3; $null=$fs.Read($b,0,3); $fs.Close(); ($b|%{$_.ToString('X2')}) -join ' '`
- **铁律 9 — 能显式就别隐式**：指针 / 内存 / 生命周期相关类型一律走显式成员函数或显式操作符；不在 C++ 层做隐式转换。

## 9. x86/x64 预编译库与 //@lib、//@复制文件

```cpp
#ifdef _WIN64
//@lib  "x64\libcurl.lib"
//@复制文件 @当前模块路径 "x64\libcurl.dll"
#else
//@lib  "x86\libcurl.lib"
//@复制文件 @当前模块路径 "x86\libcurl.dll"
#endif
//@包含目录 @当前模块路径 "native\include"   // WebView2、CXXCore 等
//@复制文件64 @当前模块路径 "op_x64.dll"      // 仅 64 位工程复制
//@lib64 "op_x64.lib"                        // 仅 64 位链接
//@默认安装位置 炫扩展\                        // 模块管理器默认路径
// 条件包含 Windows 头（两种拼写都判断，写法见 §4「编译条件宏」）
#if defined(XC_MOUDLE) || defined(XC_MODULE)
#include <windows.h>
#endif
```

`#pragma comment(lib, "winhttp.lib")` 与 `//@lib` 可混用。

```cpp
// 完整预编译库模块头（实测 Like/Like-CURL网络访问2/module_curl2.h，v2.1.4）
#pragma once
//@模块名称  CURL网络访问2
//@版本  2.1.4 (完善修正版)
//@日期  2026-03-25
//@作者  Like
//@QQ 120663035
//@依赖 module_base.h
//@模块备注  封装自开源 CURL 项目，支持 HTTP/HTTPS/WebSocket 常用能力
//@src "module_curl2.cpp"
//@模块信息结束
#include <string>
#include <vector>
#if defined(XC_MOUDLE) || defined(XC_MODULE)
#include "module_base.h"
#endif
#ifdef _WIN64
#include "x64/include/curl/curl.h"
//@lib  "x64\libcurl.lib"
//@lib  "x64\libcrypto.lib"
//@lib  "x64\libssl.lib"
//@lib  "x64\zlib.lib"
//@lib  "x64\nghttp2.lib"
//@复制文件 @当前模块路径 "x64\libcurl.dll"
//@复制文件 @当前模块路径 "x64\libcrypto-3-x64.dll"
//@复制文件 @当前模块路径 "x64\libssl-3-x64.dll"
//@复制文件 @当前模块路径 "x64\zlib1.dll"
//@复制文件 @当前模块路径 "x64\nghttp2.dll"
#else
#include "x86/include/curl/curl.h"
//@lib  "x86\libcurl.lib"
//@lib  "x86\libcrypto.lib"
//@lib  "x86\libssl.lib"
//@lib  "x86\zlib.lib"
//@复制文件 @当前模块路径 "x86\libcurl.dll"
//  ... x86 其余 dll 同理
#endif
//@别名  CURL全局初始化()
int CXCurl2_GlobalInit();
```

**要点**：每个 `.lib` 一行 `//@lib`；每个 `.dll` 一行 `//@复制文件`；**vcpkg 安装命令写进 `//@模块备注` 方便他人复现**。

```text
预编译库目录骨架
x86/ x64/  include/...  *.lib  *.dll
module_xxx.h   → #ifdef _WIN64 + //@lib + //@复制文件
module_xxx.cpp → 仅 wrapper
```

**第三方库编译要点**：① **运行时库统一**：Release `/MT`，Debug `/MTd`（与基础模块、第三方 lib 一致，否则 LNK2005 或结构体大小不一致崩溃）② **obj 文件名冲突**：同名 `.cpp` 在不同目录 → 路径替换生成唯一 obj 名 ③ **平台分目录**：`x64/xcRelease`、`x64/xcDebug`、`x86/...` ④ **`.lib` 条件链接**：`#ifdef _WIN64` / `#ifdef _DEBUG` 分支 ⑤ 编译加 `/utf-8` 消除中文 C2001/C4819。

```xc
// 纯炫语言 .xc 模块的 32/64 位写法
//@模块名称  炫语言模块-演示
//@版本  1.0
//@作者  XCGUI
//@模块备注 炫语言模块-备注
//@依赖  "module_base.h"
//32位文件:
//@lib     "x86\XCGUI.lib"
//@复制文件  @当前模块路径 "x86\dll.dll"
//64位文件:
//@lib64     "x64\XCGUI.lib"
//@复制文件64  @当前模块路径 "x64\dll.dll"
//@备注 全局变量1备注
整型 全_变量1 = 100
//@备注  函数备注说明
//@参数  参数a说明
//@参数  参数b说明
//@返回  函数返回值说明
函数 整型 两个数相加(整型 a, 整型 b)
	整型 c = a + b
	返回 c
//@备注  模块测试类1
类 模块测试类1
	整型 _ca = 10
	函数 整型 成员函数(整型 a, 整型 b)
		整型 c = a + b
		返回 c
```

要点：**全局变量习惯用 `全_` 前缀；类成员变量用 `_` 前缀；函数体用 Tab 缩进，无需大括号。**

| `.xc` 与 C++ 头文件的注解差异 | C++ `.h` | `.xc` |
|----|---------|-------|
| 32 位库 | `//@lib "x86\\a.lib"` | `//@lib "x86\\a.lib"` |
| 64 位库 | `//@lib` + `#ifdef _WIN64` | `//@lib64 "x64\\a.lib"` |
| 64 位复制 | `//@复制文件` + `#ifdef` | `//@复制文件64 @当前模块路径 "a_x64.dll"` |
| 源文件 | `//@src "a.cpp"` | `//@src "a.xc"` |
| 依赖写法 | 可不带引号 | 通常带引号 |

## 10. 示例工程 common.xh / xcproj 约定

**铁律：`common.xh` 不能 `#include` 模块头。** 炫语言 `common.xh` 是预编译头；模块由 `*.xcproj` 的 `<modules>` 注入 IDE/编译器。

```xc
// common.xh — 正确：仅注释
// 预编译头：模块通过 xcproj 的 <modules> 节点引用，勿在此 #include 模块头文件
// common.xh — 错误（IDE 会报错或重复注入）
// #include "module_base.h"
// #include "module_curl2.h"
```

| `示例-*/` 文件 | 作用 |
|------|------|
| `main.xc` | 入口与演示代码；**不要** `#include "module_xxx.h"` |
| `common.xh` | 预编译头；**禁止** `#include` 任何模块头，仅注释/工程级宏 |
| `exe.rc` | 资源 |
| `*.xcproj` | 炫语言工程；**在 `<modules>` 中引用** `module_*.h` |

```xml
<!-- *.xcproj -->
<modules>
    <item path="../../核心[官方]/基础模块/module_base.h" name="基础模块" />
    <item path="../module_xxx.h" name="我的模块" />
</modules>
<!-- 依赖其它模块时 -->
<item path="../../核心[官方]/系统API(前缀分类法)/module_windowsApi.h" name="系统API" />
```

炫语言侧调用 `A进程_取当前进程ID()` 等别名，**仍不要**写进 `common.xh` 的 `#include`。`main.xc` 可直接写 `类名::静态方法(...)`，**无需 `#include "common.xh"`**（除非工程显式启用预编译且 pch 内仅有宏）。

```xc
// main.xc —— 子程序必须带「函数」关键字
函数 整型 入口函数()
	我的模块_初始化()
	整型 pid = A进程_取当前进程ID()
	返回 0
// main.xc —— 演示：依赖 NZ_远程内存模块（xcproj <modules> 中引用 module_base + 远程内存模块）
函数 整型 演示_远程CALL(整型 pid)
	长整型 addr = CTRMemory::GetProcAddressEx(pid, A"kernel32.dll", A"GetTickCount")
	长整型 tick = CTRMemory::RemoteCall(pid, 0, 0, addr, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
	返回 0
函数 整型 入口函数()
	演示_远程CALL(A进程_取当前进程ID())
	返回 0
// 炫语言调用约定速查：静态成员 类名::成员(...)；实例成员 变量.成员(...)
蓝奏云引擎::设置调试输出(真)
海棠工具::置软件ID(A"your_id")
海棠更新验证  更新
海棠初始化结果  结果
如果 (更新.初始化("", "", "", 结果))
	调试输出(结果.config.softwareName, 结果.config.versionNumber)
否则
	调试输出(结果.message)
// COM 模块
大漠对象  dm
dm.注册("", "")
dm.创建对象()
```

`文本型A` 字面量 → `A"..."`；`动态数组<整型>` / `字典<文本型, 整型>`；`如果` / `否则` 子句用 **Tab 缩进**。

## 11. 易语言 `.e` 迁移

| 易语言 | C++ 封装 | 易语言 | C++ 封装 |
|--------|----------|--------|----------|
| 文本型 | `CXText` | 文本型A / UTF-8 | `CXTextA` |
| 字节集 | `CXBytes` | 整数型 / 长整数型 | `int` / `__int64` |
| 逻辑型 | `BOOL` | 小数型 | `double` |
| 日期时间型 | `SYSTEMTIME`、`time_t` + 封装 | 类 | C++ `class` + `//@别名` |
| DLL 命令 | 静态链接 / `#DLL导入表` / `LoadLibrary` 封装类 | | |

**从 `.e` 解包迁移的注意事项**：原版运行时读入的 `image/*.bin` → **编译期内嵌** `const unsigned char kXxx[]`（用生成脚本产出 `.cpp`）；`fasmdll.dll` + 动态加载 → 可选保留资源，或用纯 C++ 替代；`//@复制文件` 随模块发 bin → **尽量避免**，改用 `//@src` 内嵌；**内嵌字节数组生成脚本模式**：`emit("kXxxX86", "image/x86bin.bin")` → 输出 `.cpp`；**中文函数名直译是被允许的**（见 `22897350-易加加模块/易加加/`），新模块仍建议英文+别名。

```cpp
// 中文函数名（易语言风格）可复制示例
// 参考：常规/luren1234-综合模块/（module_zhmk.h + module_zhmk.CPP）、22897350-易加加模块/易加加/
//@src "module_zhmk.CPP"
//@别名  坐标类型
struct 坐标类型 { int X = 0; int Y = 0; };
//@备注 获取系统运行时间纳秒
UINT64 高精度_取现行纳秒();
//@备注 坐标取最近点
//@参数 坐标集  候选坐标集合
//@参数 当前坐标X
//@参数 当前坐标Y
//@返回 最近点的索引
int 算法_坐标取最近点(CXVector<CXText>& 坐标集, int 当前坐标X, int 当前坐标Y);
// 纯 .xc + #DLL导入表 的迁移落点
//@模块名称  NZ_远程内存模块
//@依赖 "module_windowsApi.h","module_e_ProcessThread.h"
#宏定义 内存属性_可读 2
#DLL导入表["ntdll.dll"]
    函数 整型 WINAPI NtReadVirtualMemory(...)
结构体 hook信息
    句柄型 目标进程句柄
函数 逻辑型 进程_进程提权()
```

C++ 封装是 `.xc` 中 DLL 命令、复杂逻辑的替代方案。

### 11.1 从易语言界面迁移到原生 XCGUI：最小闭环

1. **先保护再转换**：对原 `src/`、`project/`、模块／资源目录和根目录既有文件建立逐文件 SHA-256 基线；新工程独立目录，不回退用户已有改动，完成后重新逐文件比较而非只比较清单文件哈希。
2. **界面转换不是功能转换**：逐项核对窗口 `name`、列表模板、树适配器、按钮动作 ID、配置字段。由生成器产出的绑定表应与映射清单一致，同时检查生成后源码是否确实被 IDE 编译。
3. **保留真实接口**：本地数据继续可编辑保存，运行按钮接实际实现；失败、未连接、无效输入返回明确结果。不要用空处理器、固定成功返回值或仅改文案／复选状态冒充迁移。
4. **路由要按控件语义分类**：页签与普通按钮可能共享数值动作 ID，按名称前缀或显式类型分流，不以数字范围代替控件身份；刷新／保存／重载等动作必须真实调用数据接口并传播失败。
5. **保存原有成果**：部署不得清空输出目录未知文件；自测写入独立数据根，不使用用户生产 Map/Hotkey/Config/Logs。测试结果和诊断按每次唯一目录保留，失败的构建／测试证据也不删除。
6. **收尾看闭环**：最新源码 → IDE 零错误 → 新 EXE／匹配架构 DLL → 完整资源 → 实际事件与数据回归 → 正常关闭清理。旧 EXE、旧报告或静态扫描不能替代任何一环。

## 12. 调试到生产切换与发布清单

```text
// .cpp 顶部
#define MODULE_DEBUG 0    // 开发 1，发布 0
发布前清单
[ ] 所有调试宏改为 0
[ ] 无裸 OutputDebugStringW 调用（必须包在 #if 块内）
[ ] 可视化窗口代码都在 #if 块内
[ ] 调试用全局变量（static vector / HWND 等）受 #if 保护
[ ] 编译无未引用函数/变量警告
[ ] 功能回归测试（确认 #if 0 后功能正常）
发布清单
[ ] .h 元信息完整（@模块名称/@版本/@日期/@依赖/@lib/@src/@模块备注）
[ ] @src 指向正确的 .cpp 文件名
[ ] @lib 包含所有系统库 + 第三方 lib
[ ] .cpp 中 #pragma comment 路径与 @lib 一致
[ ] lib/ 目录含所有运行时 .dll
[ ] xxx-include/ 只含模块实际引用的 .h
[ ] 无硬编码绝对路径
[ ] Release x64 编译通过 + 基础功能测试通过
[ ] 不支持的平台/架构在 @模块备注 中说明
新建模块工作流
- [ ] 1. 选参考模块（见 §2），先读它的 .h 和 .cpp
- [ ] 2. 建目录 + module_xxx.h（元信息 / //@依赖 / //@src / //@别名）；仅暴露 C 接口时用 extern "C" 声明 + //@别名
- [ ] 3. 写 module_xxx.cpp（边界转换 cxAtoStr / strToCxA，内部用 std::string）
- [ ] 4. 配 //@lib / //@复制文件 / //@包含目录（如需）
- [ ] 5. 自检：无重载暴露、字符串返回 CX 类型、模板已 //@隐藏、CXBytes 不用 .data()
- [ ] 6. 编译排错：C3861 → 前向声明；C2664 → 显式转换
- [ ] 7. 测试：基础功能 / 边界（空输入、无效参数、未初始化）/ 资源（重复 init/close）/ 多线程
- [ ] 8. 可选：md5.txt、doc/、示例工程（xcproj 引用模块，common.xh 不 include）
代码审查：全维度审查 内存管理 / 未初始化变量 / 作用域 / 逻辑错误 / 边界情况 /
          代码重复 / 管线逻辑 / 线程安全 / 类型安全 / 完整性
          要求输出：问题 + 行号 + 严重级别（CRITICAL / WARNING / INFO）
```

- 两个函数共享 >80% 代码 → 提取私有辅助函数（`_doWorkImpl`）
- 线程安全巡检重点：全局变量无锁读写、懒初始化（改 `std::call_once`）、跨线程窗口消息、可视化回调的 `WM_DESTROY` 释放竞态

**第三方 C API 陷阱**：① **版本 Breaking Changes**：不同版本可能改函数签名，封装前固定目标版本，不要混用新旧 API ② **返回值必须检查**：`if (library_func(&result) != 0) return error();` —— 忽略返回值会让后续代码拿到垃圾指针 ③ **可选功能静默降级**：非必需的插件/子功能加载失败不阻断整体初始化（不检查返回值，直接 `return TRUE`）④ **资源所有权明确**：库分配的用库的 `Free`/`Release`；自己 `new` 的自己 `delete`；库返回的用对应 `Release`。

| 手动数据处理陷阱 | 说明 |
|------|------|
| **颜色通道顺序** | `GUID_WICPixelFormat24bppBGR` 是 BGR 不是 RGB。用错顺序结果全错但**不报错**。传 AI 模型前尤其注意 |
| **坐标系方向** | 屏幕/图像原点左上角 Y↓；数学坐标系原点左下角 Y↑。写旋转/翻转/透视变换前先用 3×4 矩阵跑四个角点验证 |
| **字节布局假设** | 不要假设 `sizeof(对象) == 数据长度`（见 §8 铁律 8） |

```text
md5.txt
907911c61e5b61a76318d20b70ec65f2
2026-04-11 20:51:35
```

第一行 MD5，第二行时间戳。IDE / 发布流程生成；手写模块可用占位符。仓库中 **73 个模块**带此文件。

## 13. 编译、真实构建与验收

炫彩 IDE 自带 VC2022（`炫彩ide/data/VC/VC2022/...`，实测 `I:\炫彩ide\data\VC\VC2022` 存在），可用其 `cl.exe` 做纯语法验证（`/c`，不链接）：

```text
tool/run_compile.ps1   # 对所有 //@src 执行 /c，输出 build/verify-x64|x86/*.obj
tool/build_verify.bat  # 调用 run_compile.ps1
```


> ⚠️ **当前仓库（`I:\炫彩ide\data\XC-Module`）中没有**任何 `run_compile.ps1` / `build_verify.bat`。需要时自行按下列要点编写，不要假设它已存在。**可参照的现存实现**：`I:\炫彩ide\data\XC-Module-dev\op483\tool\run_compile.ps1`（实测存在），其产物落在 `op483\build\verify-x64\module_op.obj` 与 `op483\build\verify-x86\module_op.obj`。

- 参数：`/utf-8`、`/c`、`/DXC_MOUDLE`、`/DUNICODE`、`/D_WIN64`（或 `_WIN32`）
- Include 路径：模块根、`核心[官方]/基础模块`、`VC/include`、`VC/atlmfc/include`、Windows SDK（ucrt / shared / um）
- **路径含中文或 `[` `]` 时「必须」用 `-LiteralPath`**（PowerShell 会把 `[` `]` 当通配符）
- 动态解析 `module_base.h`：`Get-ChildItem -Recurse -Filter module_base.h`
> `Get-ChildItem -Recurse -Filter module_base.h` 的结果路径会含 `核心[官方]`；后续任何 `Test-Path` / `Get-Content` / `Select-String` 都必须带 `-LiteralPath`，否则 `[官方]` 会被展开成字符集而静默匹配失败。

### 13.1 真正的 IDE／MCP x64 发布构建（2026-11-07 实战补充）

`cl /c`、静态 XML 检查、资源存在和旧 EXE 可启动都只是局部证据，**都不能代替 IDE 对最新 `.xcproj` 的真实发布构建**。以下以本机现有 XC-MCP-Next 为例；端口、工具数和构建器行为必须以当前安装的实际源码／schema 为准，不把一次版本观察硬编码为跨版本保证。

1. **保留现场与依赖边界**：构建前保存受保护源码的逐文件哈希。只读定位现有 IDE、VC/SDK、官方基础模块、XCGUI 头文件／库。明确目标配置为发布版 x64，检查 `moduleLib="dll"` 或 `lib` 对应的实际库是否存在；不要为了过编译安装、下载、替换或修改 IDE／全局模块。
2. **正确打开目标工程**：用绝对 `.xcproj` 路径、明确工作目录和 `UseShellExecute=false` 启动自有 IDE，环境／临时缓存指向会话 scratch。启动参数正确仍不能证明 IDE 没恢复旧工程，后续必须查询当前工程。

```powershell
$project = (Resolve-Path -LiteralPath '.\Kx Pro.xcproj').Path
$ide = New-Object Diagnostics.Process
$ide.StartInfo.FileName = $existingIdeExe  # 由现有环境只读探测得到
$ide.StartInfo.Arguments = '"' + $project + '"'
$ide.StartInfo.WorkingDirectory = Split-Path $project
$ide.StartInfo.UseShellExecute = $false
$ide.Start() | Out-Null
$ownedIdePid = $ide.Id
# 自动化调用中在后台任务保持该对象并 $ide.WaitForExit()，不要让 IDE 随短命令退出而消失。
```

3. **先发现当前端点和合法认证**：当前安装的 `xcbuild.py` 定义 health／MCP 地址和令牌读取顺序；用 `X-XC-Token` 访问 `/health`，再用 mcp-cli `ping`、`list`、`desc` 获取实际工具。本次已验证为 18766、29 个工具，旧注册信息却仍是 18765、24 个工具；解决方式是在**会话 scratch 放临时客户端配置**，不改全局 `servers.json` 或 IDE 文件。重启后若 401，核对当前合法令牌文件与进程环境；令牌不写报告、日志或仓库，更不能绕过认证。
4. **构建前查工程归属**：调用 `xc_get_project`，规范化解析后的 `project_file` 与批准目标逐字比较；不同则拒绝发送构建。此次启动器曾恢复另一个最近工程，路径检查在编译前拦住了误操作。本次 `xc_open_in_ide` 实际走 `importFile`，是导入文件接口，**不能当项目切换 API**；先 `desc` 查 schema，需要判断语义时只读当前 `tools.cpp` 实现。
5. **不要把 dispatched 当成功**：本次 `xc_build` 通过 `PostMessage WM_KEYDOWN/UP` 向 IDE 投递 F7，返回只代表已发送。需轮询 `xc_get_output`，等到真实编译完成／失败标志，解析前端诊断和 MSVC 错误。当前构建器说明同一 IDE 生命周期仅首次 F7 有效，复建时只正常 `CloseMainWindow()` 自己启动且核对过路径／启动时间的 IDE，再重新打开；**禁止按进程名全局 taskkill，不能结束他人 IDE**。
6. **核对新产物**：实际输出须出现 `错误列表: 错误(0)`，并保存 build 结果、原／新 EXE 时间、长度、SHA-256。新 EXE 必须在本次构建触发后生成；源码已改但 EXE 哈希没变时需要解释，不能拿旧文件充数。x64 同时核对 PE Machine `0x8664`（AMD64）及配套 XCGUI DLL 的架构。还应检查 IDE 输出确实列出预期 `.xc` 页面与 `//@src` 对应 cpp，而不是只核对 `.xcproj` 文本。
7. **真实诊断最小修复**：`解析遇到错误` 按 `.xc` 源文件／行号处理，C/C++ 的 `? :` 可换成明确的如果／否则；生成目录的 `main__.cpp` 只用于观察签名和语义，修改源 `.xc` 后必须重开有效构建会话再编。保留每次失败与成功报告，不重写历史证据。

### 13.2 部署、PowerShell 退出码与隔离验证

**完整部署 ≠ 复制 EXE**。磁盘 UI 至少验证匹配架构 DLL、实际数量的窗口布局、列表／树／组合框模板、项目 resources、完整 WmUi Base／主题／CSS 以及资源登记指向的字体。源与部署文件逐个 SHA-256 比对，保留未知输出文件；路径逐级拒绝 reparse，不能让部署越过工作区。IDE 若提示输出 XML 与源不同，显式部署后重新核对，不把警告当资源已更新。

等待 GUI 测试程序时保留实际进程句柄。PowerShell 中进程已退出后再 `Refresh()` 可能造成退出码读取异常；没有拿到真实退出码就不能写成 exit=0，应换全新输出目录重跑。

```powershell
$p = Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory (Split-Path $exe) -PassThru
$heldHandle = $p.Handle
if (-not $p.WaitForExit(120000)) {
	# 超时：只清理这个已持有句柄的自有测试进程，强制清理不算测试通过。
	throw ('Owned test timeout: PID=' + $p.Id)
}
$p.WaitForExit()
if ($null -eq $p.ExitCode -or $p.ExitCode -ne 0) { throw ('Test failed: ' + $p.ExitCode) }
```

- **独立运行层回归**：若合同要求 C++14／C++17，分别真实编译运行，记录源码哈希、编译器／SDK、native_exit 和每份新报告的 `executed/passed/failed/not_run`。`/W4 /WX /MT` 和真实基础模块证明没有以 stub 代替；82 项、163 项等是具体项目合同，不是所有工程通用下限。`not_run` 逐项写原因，不计入 passed，不把“接口存在”说成“物理效果已验证”。
- **UI 与实际事件**：不只检查句柄存在，覆盖真实页签事件、页面互斥可见和正尺寸、列表／树适配器、普通按钮与复选按钮失败状态、数据保存／取消、辅助窗关闭／重开。每个检查独立计数并输出总失败数；窗口生命周期使用 XWnd 路径，详见 `xcgui-code.md` §6.5–§6.6。
- **外部副作用隔离**：本次内存／输入回归只启动带私有 nonce、管道和 kill-on-close job 的自有 x64 fixture，仅向它发定向消息。需要外部目标／全局输入时另行明确授权，不借 UI 自测扫描或操作用户进程。UI 测试数据根独立，smoke 模式不枚举或连接真实游戏窗口。
- **清理证据**：自有 fixture／runner／EXE 进程退出，owner 关系正确的六个顶层窗口全部关闭，主窗 WM_CLOSE 后正常 exit=0、未强制终止；脚本工作线程、hook 装卸和连续状态释放由实际用例分别断言。不要声称“系统全局 hook 已枚举为零”。
- **保护既有输出**：测试 run 目录唯一，拒绝覆盖未知报告／日志。部署合并而不删除未知文件；构建和测试后再次计算受保护原工程哈希。清单 JSON 的整体哈希可因时间戳不同，验收应比较路径集合、文件尺寸和每个文件的 SHA-256。

建议最终报告按“已实现、已实测、未实现、未实测”四类写明，并逐条列出验收项及证据。零错误 IDE 构建与静态检查分别记录，不相互冒充；若工具链缺失则报告具体阻塞，保留已完成成果，不能降低真实构建标准。

### 13.3 IDE 内存态、原生迁移与证据闭环（2026-11-07 大型迁移复盘）

以下规则来自一次多模块原生桌面迁移的真实构建与回归。它们解决的是“源码已改但构建仍旧”“测试已派发但未完成”“有窗口但无法操作”等容易误判的问题；不包含具体项目的业务规则，也不把一次版本观察写成所有 IDE 的永久行为。

1. **隔离 IDE，不污染 SDK 与他人工程**。需要自动构建但不允许改 SDK 时，把所需 IDE 可执行文件、配置、模块与插件复制到会话 scratch，临时目录、缓存和 MCP 端点均使用私有实例；原 SDK 只读引用。发现端口实例碰撞或 401 时，先核对实际进程、端点和合法配置，不连接来源不明的 IDE，不绕过认证，不盲目重跑会覆盖现有私有环境的准备脚本。准备脚本与运行脚本分开保存。
2. **磁盘源码、IDE 编辑缓冲和 AST 是三份状态**。直接编辑磁盘 `.xc` 后，IDE 可能仍使用旧解析树。可靠顺序是：逐个 `xc_open_in_ide` 打开实际改动文件 → 用当前工具的编辑接口（本次为 `xc_editor_set`）写入并读回核对 → 再重新编译。只打开 `.xcproj` 标签不等于激活构建工程，仍需 `xc_get_project` 校验目录、工程文件、发布版和 x64。
3. **工程配置也有磁盘与 RAM 两份**。曾出现磁盘 `ui_loadType=0`，而 `xc_get_project` 仍报告缓存值 `1`。修改 `.xcproj` 后要明确重载工程并分别记录磁盘值、IDE 缓存值和实际资源加载结果，不能用其中一个替代另外两个。临时文件只落 scratch／项目允许的构建目录；若辅助工具给出错误工程根，显式传批准的项目根，不沿用其推断出的 SDK 临时目录。
4. **生成文件与工具链限制要按真实输出处理**。当前工具链强制 C++14 时，将 `/std:c++14` 写回工程并移除 C++17 依赖；不要为了过编译改用更高标准的本机旁路编译。IDE 可能重写 `exe.rc`，自定义版本资源应保留完整 `VS_VERSION_INFO VERSIONINFO` 及所需子块，残缺资源会导致 `RC2127`，不能只修生成后的缓存文件。
5. **原生发布同时核对文件与运行依赖**。本次验证过的一种组合是 `moduleLib="dll"` + `/MT`，发行目录携带匹配架构的 `XCGUI.dll`；不要改用来源不明的静态 trampoline 库而引入额外加载器。构建后检查 PE Machine `0x8664`、Optional Header Magic `0x20B`、CLR 目录 `(0,0)`、导入 DLL 和实际启动；需要证明“运行时无 CLR”时另做进程模块观察，不能只靠静态推断。干净分发包不包含 `.iobj`、`.ipdb` 等链接中间件。
6. **GUI 测试必须拿到真实退出与报告**。预先创建输出根目录，测试程序不一定会代为创建；使用 `Start-Process -Wait -PassThru` 或持有进程对象 `WaitForExit()`，不要依赖 PowerShell `&` 调用 GUI 后立即返回的状态。报告目录不存在、JSON 未生成、进程异常退出或超时都不是通过。每次运行使用新目录，保留失败输出，不按进程名全局结束程序。
7. **后台任务与 UI 分离并定义退出顺序**。耗时读取／扫描在单一串行 worker 中执行，worker 不操作 XCGUI 控件；完成后把不可变结果交回 UI，避免请求对象被下一次输入覆盖。退出时先停止接收新任务并 join worker，再释放外部句柄和 `炫彩_退出()`，防止后台仍访问已销毁状态。
8. **证据按层级陈述**：真实 IDE 构建、自动 fixture、原生 UI 输入检查、外部实机验证分别报告。fixture 必须显式启用、标明样本并限制写入隔离根，普通启动不得加载测试数据；静态检查、命令已派发、适配器有数据、截图或演示数据都不能单独算作运行时验收。动态实机字段需注明读取时间和变化原因，不制造“逐字段一致”。
9. **导出与部署同样纳入回归**。写 UTF-8 前先移除文本开头已有 `FEFF`，由文件写入函数统一决定是否加 BOM，避免双 BOM；同时断言“恰好一个 BOM”和实际列数／中文内容。资源部署合并且不覆盖用户配置与离线数据，构建测试后再次核对受保护文件哈希。失败报告应包含错误、调用栈、当时状态和对话框树，不能只保存最后一次成功记录。

### 13.4 迁移续做收尾、独立取证与便携验收（2026-11-09 Orbis 复核）

适用：Windows x64 炫语言／XCGUI 工程已经迁移完成，需要继续上一会话、重新验收或收尾交付。补充 §13.1–§13.3 的证据管理与内嵌 UI 部署，不替代真实 IDE 构建。下列原则可复用，末尾数字仅为 Orbis 这轮实测样本，**不是其他工程的固定门槛**。

#### 13.4.1 原始基线、历史证据与本轮证据必须分开

1. **“上次已通过”不等于“本轮已验收”**。先阅读目标、HANDOFF、当前报告，再实际核对源码／XML／EXE 指纹；没有实证缺陷时重新执行约定检查即可，不为制造改动而重新迁移、重构或扩展业务。旧报告、截图、Rust 结果及 IDE 设计器观察标为历史，不把打开请求或旧截图算本轮运行证明。
2. **保留两个层次的 before**。原指纹基线、已冻结迁移 before 永不覆盖；续做每轮另建唯一 `RunId` 和独立 before。更新活动报告前，将会被覆盖的文档、报告、脚本及旧交付物归档到批准的 Temp／会话 scratch，并记录源路径、归档路径、长度和 SHA-256。before／历史目录已存在时拒绝覆盖，不借 `-Create` 消除历史差异。
3. **原基线差异与本轮保护是两回事**。即使旧工具因历史 Missing／Changed／Unexpected 退出 1，本轮仍可证明执行前后现存受保护文件完全一致；比较的是路径集合、长度、逐文件 SHA-256 和相同差异清单。不得把“现存文件未再改动”说成“全部等于旧基线”，也不回滚、删除或擅自归因既有用户改动。无 Git 的恢复工程同样可用这一方法。
4. **本轮记录要绑定到真实执行，不只比较旧时间戳**。每个检查保存程序／完整参数、RunId、开始／完成 UTC、真实及预期退出码、独立日志、生成报告的长度／哈希；报告须在本次命令窗口内新生成。运行校验使用本轮 before 的时间，拒绝无 RunId、跨轮次、旧产物、失败命令和被改写报告，不能默认回退到首次迁移快照。
5. **原工具退出码与外层入口退出码分开**。预期拒绝用例可退出 1/2，入口验证预期后返回 0，但记录仍保留原始 1/2；启动失败、未取得退出码或未生成报告不得伪写 0。时间比较先解析时区，不能按 ISO 字符串字典序比较；共享命令记录的检查顺序执行，不并行写同一文件。

#### 13.4.2 当前源码、内嵌 XML、资源和便携包闭环

1. **目录重排之后验证“引用 + 字节”，不是只数文件**。核对正式工程源码／模块／RC 引用、唯一源码文件名、唯一正式 `common.xh`、迁移映射和探针排除项。保存本次实际参与构建的输入路径／长度／哈希，并检查构建期间未变。过滤 Temp／obj／Release64 等中间目录应匹配**相对源码根**路径；探针工程本身位于 Temp 时，匹配完整绝对路径中的 Temp 会错误排除所有探针源码。主入口、业务源码与预编译头分别计数，不混用。
2. **全量／增量及警告以实际日志为准**。`All N functions were compiled` 与 `0 of N functions … the rest were copied` 是不同事实；本轮新生成 EXE 可以来自真实增量重链接，不能写成全量重编。移动掉 IPDB/IOBJ 后，下轮可能因无可用缓存全量编译。逐类记录警告**出现次数**，重复头文件诊断不等于独立缺陷数，更不能据次数变化宣称修复；错误列表 0 不代表警告 0。
3. **先判定 UI 是磁盘部署还是内嵌部署**。磁盘 UI 沿用 §13.2 的完整资源同步；内嵌 UI 的主布局／模板／样式改动必须重建 EXE，设计器本地副本不自动成为运行依赖。XML 为唯一静态定义时，炫语言只负责资源加载、类型/name/id/唯一性绑定、事件、适配器和数据；错误应诊断并退出，不创建备用 API 界面。记忆的窗口几何、预览比例和数据列宽是动态数据，不能与固定控件布局混淆。
4. **按新 PE 的实际资源树核对**。逐项比较源文件与内嵌资源的类型／名称／长度／SHA-256，同时记录当前 XML／UI 源码与构建指纹。RC 标识符未按标准宏展开时，资源类型可能是字符串，例如本例实际类型名 `RT_RCDATA`；不要想当然按数值 10 查找或只检查 RC 文本。原 ZIP／加密包如要求保持，应核对只读来源；不重打包或分发解密明文。
5. **便携包不带链接中间件，留存步骤纳入复现命令**。构建完成且文件解锁后，确认 IOBJ/IPDB 是本轮已知产物，再按源长度／哈希完整移动到项目 Temp，移动后重核并记录去向；已有留存记录只复核，不覆盖。遇到未知文件、重解析路径、旧记录或不符哈希时拒绝清理。留存脚本首次移动、重复核验和未知文件保留分别做隔离文件操作测试，不计入业务回归。
6. **“仅 EXE + DLL”必须实测，不能泛化**。只在该工程的最小已验证依赖集合中制作隔离副本；独立 profile/AppData/Temp，PATH 仅 Windows，验证复制哈希、普通可见离线启动和正常退出。不要把 Python/MCP、设计器、原工程或全局 WmUi 目录当成运行依赖；工程确实使用额外 DLL／OCR／磁盘资源时如实保留和验收，不能一律裁成两个文件。
7. **无控制台证明要同时核对 PE、存活 PID 和可见窗口**。正式 GUI 入口检查 AMD64 `0x8664`／PE32+ `0x20B`／Subsystem 2 及匹配 DLL。使用普通 creation flags，不隐藏窗口、不显式重定向被测程序的标准流；窗口 class 从 XML／实际定义读取，不写死旧 API 默认 XCGUI。仅让验证进程对自身 `FreeConsole`，确认自有被测进程仍存活，再多次 `AttachConsole(pid)`；失败必须核对具体错误，本例 `ERROR_INVALID_HANDLE=6`，`ERROR_ACCESS_DENIED` 或失效 PID 不能冒充无控制台。WM_CLOSE 前复核 HWND 所属 PID；正常退出及本进程窗口／子进程残留另验，强杀不能计通过。

#### 13.4.3 收尾顺序、文档指纹与校验器自测

推荐闭环：

```text
唯一 RunId + 独立 before + 旧活动证据归档
→ 源码／工程／XML 静态检查
→ 当前工程真实构建 + 输入／PE／EXE 指纹
→ 已知链接中间件留存
→ 全量离线回归 + Release／原生 UI + 普通便携启动
→ 资源树校验 + 原文件 after + 历史差异原工具
→ 按本轮实测更新 README／HANDOFF／FINAL／映射／控件清单
→ 链接／元数据／最终汇总
→ 最终报告状态更新后重算文档指纹 + 只读文件与进程核对
```

- **活动文档也是验收输入**。同时更新 EXE/XML 指纹、RunId、UTC、实际数量、全量／增量方式、警告、主题／paint 数据及依赖说明；历史观察单列。链接只指向存在的文件。文档修改后重跑链接、元数据和最终汇总，避免结果仍签的是修改前说明；不能跳过人工同步未知文档，却宣称单条命令会自动收尾。
- **验收阈值来自当前已批准覆盖，不沿用旧界面门槛**。本例旧检查仍接受 695 桌面断言，续做合同要求保留 864，修复应收紧到 864，而不是删除用例或放宽到旧值。核对控件唯一绑定、页面数、输入数、事件、实际渲染、草稿／偏好保存、预览及关闭语义，数量不能代替行为。
- **校验器也需要负向自测**。覆盖旧时间戳、跨轮次、缺失命令、错误退出码、真假类型、报告哈希被改、重复 before、无 RunId 和时区等价；验证拒绝时原文件／冻结基线未改。文件操作夹具、取证自测和业务断言分别计数，不以自测通过代替真实构建／UI。
- **避免最终报告与命令日志自引用哈希**。最终程序先产生报告，再由持有退出状态的外层记录该次 Final 的实际退出码和报告指纹；报告可引用命令日志路径／已完成命令快照，不要求它同时签入未来的自身完成记录。结束前独立只读核对当前文件与末次日志，不制造虚假的完成项。
- **PowerShell 长 Python 命令优先写脚本文件**。Windows 原生命令传参可能剥掉 `python -c $hereString` 内的引号，导致审计根本未执行；在会话 scratch 写 UTF-8 脚本后 `python -B <脚本>`，确认真实退出码。临时文件／缓存只在批准 Temp 或会话 scratch；外部技能文档更新使用确定性、唯一锚点及旧字节／哈希检查，保留备份，遇到内容变化先重读，不猜编辑行号。

**Orbis 2026-11-09 已观察样本（不得作为通用常量）**：正式 60 源码／九类目录，61 份正式构建输入；全量 10415 函数，集成 59 输入、0/10470 函数重编；离线 4109/0、视觉 69/69、24 模板；Release 18/18，三轮各 864/0/50，126/126 唯一绑定、74 输入；资源 6/6、13 地图、五次无控制台、正常 exit 0；77 原文件／79 业务输入／79 归档副本一致，原 76 文件基线仍有九项历史差异；六份说明、434 链接／0 失效，七项汇总均 true。告警出现次数 C4146 67／C4244 1／C4267 18，不是修复数量。真实游戏、真实 OCR、实机性能及新截图／设计器观察未执行。

实测来源为旧工程 `E:\AIWork\Orbis-recovered\orbis-rs\orbis-xc\reports` 下的 `FINAL-VERIFICATION.md`（本轮最终说明）、`resume-20261109-1300-commands.json`（命令与退出码）和 `resume-20261109-1300-protected-after.json`（独立保护核验）。这些是该工程实例的来源位置，不是技能随附文件；换机器或工程不得假定路径存在，也不得复制这轮哈希／数字充当新证据。

## 14. 错误速查表

| 症状 | 原因 | 修复 |
|------|------|------|
| C3861 找不到标识符 | `static` 函数定义在调用下方 | grep 确认位置，加前向声明 |
| C2664 类型转换 | `const void*` 无法隐式转换 | 加 `(const char*)` 或改用 `.std_str()` |
| C2039 `filesystem` 不是 `std` 成员 | 非 C++17 模式 | 改用 `_wfopen` |
| C2001 / C4819 中文 | 编码不匹配 | 文件存 UTF-8-BOM；编译加 `/utf-8`（或 `#pragma warning(disable:4819)`） |
| C2535 函数已定义 | `/*@声明` 里重复声明了可见区已有的声明 | 删掉重复声明 |
| C2668 重载调用不明确 | friend 声明含模板参数与 .cpp 重载冲突 | 改命名空间级前向声明 |
| C2440 CXBytes 构造失败 | 二进制含 `\0` 被 `c_str()` 截断 | `CXBytes((const BYTE*)d, n)` |
| C2589 / C2146 模板语法错误 | IDE 不支持 `template<int>` | 改 `template<class K, class V>` |
| IDE 解析模板失败 | 用了 `template<>` 显式特化 / 模板参数含 `::` 嵌套 | 改函数重载 + `decltype` 标签分发 / 改扁平命名 |
| `CXBytes` 无成员 `data()` | 不是 `std::vector` | 读用 `get()`，写用 `resize()` 返回值 |
| `PROCESSENTRY32` 比较失败 | `UNICODE` 下宽字符 | `compareModuleName(pe.szExeFile, wtarget)` |
| x64 编译器报 `CONTEXT.Eip` | 32 位线程劫持 | 改用 `Wow64GetThreadContext` |
| 成员函数遮蔽 `GetProcAddress` | 名字查找 | 调 Win32 时写 `::GetProcAddress` |
| 找不到 `atlbase.h` | include 路径缺失 | 追加 `VC/atlmfc/include` |
| LNK2005 运行库冲突 | /MT 与 /MD 混用 | 统一与基础模块一致 |
| Debug/Release 混用崩溃 | CRT 不匹配 → 结构体大小不同 | 统一 `/MT` 或 `/MTd` |
| 中文路径打开文件失败 | `ifstream` 按 ANSI 解析路径 | `_wfopen(wpath, L"rb")` |
| 找不到 `module_base.h`（脚本编译） | 路径未解析 | `Get-ChildItem -Recurse -Filter module_base.h`，含中文路径用 `-LiteralPath` |
| 找不到 `nlohmann/json.hpp` | vendor 未就位 | vendor 放 `nlohmann/json.hpp` 于模块根 |
| 模板暴露导致 IDE 报错 | 模板直接可见 | 移入 `//@隐藏` + `/*@声明` 伪签名 |
| x86/x64 混用 lib | 未按平台分支 | `#ifdef _WIN64` 分支 + 对应 `//@lib` |
| IDE 报「错误的模块命令」 | `//@别名` 参数列表写成了 `参数1..参数N` 省略形式 | 逐个写出参数名 |
| IDE 报「不符合变量命名规则」 | `//@别名` 可变参写法在括号内写了 `...` | 只写第一个形参名，其余在 `@备注` 说明 |
| 解析结果与预期不符 / 标识符被误解析 | 复杂声明干扰 | 用 `@跳过 A,B,C` 剔除该标识 |
| 枚举成员名与其它模块冲突 | 全局枚举成员 | 加 `@启用枚举前缀`，成员显示为「枚举别名_成员别名」 |
| 长度参数误传导致截断/越界/乱码 | `length` 单位未写明 | `@参数` 说明里必须写明单位（字符 or 字节）与 `-1` 表示自动取长度 |


