# 本地模块调用：详细说明

按需参考；常规调用先看[短入口](../xc-modules.md)。`scripts/`、`references/` 路径相对 XC 开发指南所在目录。

模块根目录：`I:\xcide\data\XC-Module`。这是本机当前模块调用的路径依据；`../module-packaging.md` 早期仓库地图及旧示例中的 `常规/网络/kyozy/炫++扩展` 等路径属于历史布局，不能直接拼接到此目录。

本仓库不附带旧机器生成的索引。首次运行 `rebuild` 后，返回的 `output` 目录下有 `catalog.json`、`api.jsonl` 和供浏览的 `catalog.md`。默认目录是 `%LOCALAPPDATA%\cli-anything-xcide\module-index`，可用 `XC_MODULE_INDEX_DIR` 指定其他目录。重建和后续查询须使用同一缓存目录。

## 1. 按需求直接找调用

先查模块，再查该模块的接口；任务已明确模块时直接限定入口查函数。所有命令只读模块源码，`rebuild` 仅更新本机索引。脚本仅依赖 Python 标准库。

```powershell
# 从 XC 开发指南所在目录运行。
$xc = Join-Path (Get-Location).Path 'scripts/xc_modules.py'
python $xc --root 'I:\xcide\data\XC-Module' rebuild

# 按用途、模块名、作者或路径查找；无参数列出全部模块包
python $xc list 'HTTP'
python $xc list 'JSON操作'
python $xc list '01_基础与综合/u91584168-炫++扩展'

# 使用 list 返回的完整入口路径，避免同名模块被混用
python $xc show '12_算法与识别/A星寻路模块/module_astar.h'
python $xc search '寻路' --module '12_算法与识别/A星寻路模块/module_astar.h'
python $xc search '取类型' --module '02_文本与数据格式/JSON操作/module_json.h'

# 中文原生函数、英文签名、纯 .xc 函数和冒号后的英文别名也能检索
python $xc search '系统_进程音频峰值' --module 'luren1234-综合模块'
python $xc search 'yyjson_read' --module '02_文本与数据格式/YYJSON/module_yyjson.h'
python $xc search '全局_取版本号' --module 'OP插件0450'

# 原始注释、参数说明、生命周期或未抽取的拼写，用 --raw 搜当前磁盘源码
python $xc search '释放' --module '03_文件与压缩/michardhl-Libzip/module_libzip.h' --raw

# 找到真实调用后，按返回的 file + line 读取上下文
python $xc examples '02_文本与数据格式/JSON操作/module_json.h' 'JSON'
python $xc source '02_文本与数据格式/JSON操作/module_json.h' --line 29 --before 10 --after 35
```

`search` 多个词为同时匹配；默认返回 12 条，用 `--limit 30 --offset 12` 分页。检索数据为索引目录中的 `api.jsonl`，可用 `rg` 按原始签名搜索；不要整份加载进上下文。

返回字段：

- `file`、`line`、`declaration_line`：真实源码位置，行号从 1 开始。
- `alias`：原样的 `@别名`，保留中文参数名；`declaration`：原始英文或炫语言声明候选，保留类型、指针、引用和默认参数。
- `scope_hint`：词法推断的类/命名空间，**需由源码确认**，不可据此把成员函数写成全局函数。
- `entrypoints`：沿本地 `#include` 实际找到的所属标准模块。空数组表示未证明导入链；改用 `list`/`show` 查所属包，不直接把辅助头当成工程模块。
- `source_status`：本次展示的源码与建索引时的 SHA256 是否一致。出现 `missing-or-changed` 时先 `rebuild`，再重新定位行号。

索引包含别名、类型/常量/宏、无别名声明候选和 `.xc` 函数，**条目数不是可调用函数数**。它不执行 C++ 预处理，也不替代 IDE AST：条件编译分支、`@隐藏`、`/*@声明`、成员访问级别与模板实参以当前源码和目标架构为准。备份头 `cxxbackup.h` 属于辅助材料，不作为默认调用入口；`xcgui_rebuild/xcgui_recovered` 下的重建/分析副本不重复收录。

## 2. 把选定模块接入当前工程

`show` 给出完整模块路径、原始 `@版本/@作者/@依赖/@lib/@lib64/@复制文件/@复制文件64/@包含目录/@src`、本包示例以及 `project_import`：

1. 先确认用户需要的作者/底层库/接口版本。JSON、SQLite、MySQL、大漠、WebView2、QuickJS、XML、压缩、Sunny 等同类包不能互换调用名。
2. `ordered_paths` 是明确 `@依赖` 的递归展开结果，依赖在前；逗号分隔、多行注解和 `无` 均已处理。头文件依赖单列为 `header_dependencies`，不伪装成模块入口。
3. 仅当无未解析依赖、无文件名冲突且选中了标准入口时才输出 `modules_xml`。把需要的 `<item>` 合并到现有 `*.xcproj` 的 `<modules>`，按现有格式去重，保留工程其他设置。**不要用整个输出块覆盖已有模块列表。**
4. 本机示例的 `<item path="module_xxx.h" name="模块名" />` 使用文件名由 IDE 解析。出现 `basename_collisions`（例如两个 `module_json.h`，或大小写不同的 SQLite 头）时，按完整源路径在 IDE 中确认引用的是哪个包；不要随便选第一个，也不要猜绝对路径导入格式。
5. `@依赖` 展开不等于全部依赖：还要检查当前头的包含链及目标 x86/x64、Debug/Release、静态/动态分支，保留源码中的 `@src`、链接库及运行时复制逻辑。资源、模型、外部 SDK 和初始化/释放顺序按实际示例处理。
6. 炫语言 `.xc` 中使用已核实的中文类型/函数别名，或模块原有的中文标识符。C++ 封装侧使用真实 C++ 标识符；类型转换规则见 `../module-packaging.md` §5。**不要在 `common.xh` 里 `#include module_*.h`。**

按当前实测头文件，线程池的模块导入示例如下；用于合并 `<item>`，不是完整工程：

```xml
<modules>
  <item path="module_base.h" name="基础模块" />
  <item path="module_threadpool.h" name="线程池" />
</modules>
```

接口形式来自 `05_线程与并发/线程池/module_threadpool.h` 中的原始说明及声明：

```text
线程池类 池
池.创建(10)
池.销毁()
```

这是类成员调用片段；实际任务函数、投递及退出时机继续读同一头文件或 `../xcgui-code.md` §9，不把创建成功等同于业务任务已完成。

## 3. 分类速查

每类的所有模块及子模块见索引目录中 `catalog.md` 的对应标题；也可 `list '07_网络与通信'` 直接列出。

| 类别 | 需求关键词 |
| --- | --- |
| 核心[官方] | 基础模块、炫彩界面库、COM、易语言核心、系统API、前缀系统API |
| 01_基础与综合 | 易加加、炫扩展、STD、MtBase、wrapper_tools、炫++扩展、XM_羽蝶、炫易 |
| 02_文本与数据格式 | JSON、YYJSON、cJSON、XML、DOM、正则、拼音、数组、哈希、URI、md4c |
| 03_文件与压缩 | zlib、minizip、minizip-ng、Libzip、gzip、SIni、压缩解压 |
| 04_系统与进程 | 系统操作、CPU、CPUID、时间、内存模块、注入、Detours、APIHOOK、日志、异常 |
| 05_线程与并发 | 线程池、无锁队列、纤程、coost、锁 |
| 06_键鼠与自动化 | 大漠、OP、奥迦、模拟器、DD、幽灵键鼠、Accessible、RX78、扫码 |
| 07_网络与通信 | HTTP、WinHttp、CURL、Socket、HPSocket、WebSocket、FTP、SMTP、SSH、串口、NTP、Sunny、QQBot |
| 08_浏览器与网页 | WebView2、Miniblink、网页填表 |
| 09_数据库 | SQLite、sqlite3mc、连接池、MySQL、ADO、LMDB |
| 10_界面与绘图 | Direct2D、Gdiplus、OpenGL、Qt5Core、界面扩展、黑月、Overlay、DPI、颜色、位图 |
| 11_音视频与多媒体 | 音频、miniaudio、VLC、SDL3、SDL3_image、SDL3_mixer、SDL3_TTF、WebP |
| 12_算法与识别 | A星、OCR、PaddleOCR、dddocr、yolo、二维码、条码、数学 |
| 13_加密与安全 | AES、HMAC、OpenSSL、bcrypt、VMProtect、UPX、机器码、网络验证 |
| 14_脚本与运行时 | Python39、Python库、Lua、LuaJIT、QuickJS |
| 15_办公与行业 | LibXL、Word、FC表格、报表、打印机、通达信 |

## 4. 已知限制与更新

- 本地 `README-整理说明.md` 是整理历史和已知风险的来源，里面的包数和部分旧目录名已与当前磁盘不同；精确调用以本索引和实际源码为准。未主动改名、修复或重打包任何模块。
- `YYJSON/module_yyjson.h` 的元数据占位及疑似复制的 include guard、部分 `.xcproj` 的失效路径、`hxznhf-Python库` 的外部 Python 环境、部分静态分支/SDK/运行 DLL 缺失，不能因索引有条目就视为可构建。使用相关包时读原始说明并核实本机依赖。
- `show`/`verify` 会保留无法唯一定位的依赖诊断。索引刻意不猜同名 SQLite 等模块；未知依赖要结合实际 include 和本包示例确认。
- `03_文件与压缩/minizip-ng/xpl_def/mz_strm_lzma.h` 无法以无损 UTF-8/GB18030/带 BOM 的 UTF-16 解码，已列入 `scan_problems`，未改写或以乱码入库。标准模块入口 `module_minizip-ng.h` 及其可读声明仍正常索引；以后重建时以诊断里的实际文件名为准。
- `verify` 验证已索引源码哈希、标准入口覆盖和依赖诊断；它不运行编译器，也不检查全部二进制依赖。应用到项目后，只有用户任务需要构建验收时再按 `../module-packaging.md` §13 做真实构建。

```powershell
python $xc stats
python $xc verify

# 模块新增、删改或移动后重新生成；不会改动模块源码
python $xc rebuild

# IDE 安装路径改变时覆盖根路径，保持索引仍在 skill 中
python $xc --root 'D:\xcide\data\XC-Module' rebuild
# 也可以设置 XC_MODULE_ROOT；--root 优先
```

维护时运行 `rebuild` 后再 `verify`；确认入口覆盖、中文/英文/纯 `.xc`/子头文件检索和真实示例均可用。新增注解或特殊声明若未被抽取，先用 `--raw` 取得确切源码，再按实际语法修正脚本，不生成猜测的调用签名。
