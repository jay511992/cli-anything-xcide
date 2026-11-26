# 原生 IDE 会话与 MCP 工具迁移

本项目通过 `ide call xc_*` 提供 XC-MCP-Next 注册的 30 个工具名。调用链为 **Agent → CLI → 本地带令牌的消息文件 → 私有 IDE 内的原生 DLL → IDE/XCGUI API**。没有 MCP 客户端、HTTP 服务或 XC-MCP-Next DLL 运行依赖；原有离线工程命令、`build --diagnostics` 与 `runtime run/test` 继续可用。

这是工具功能迁移，不是 MCP 协议服务器，也不保证旧 JSON 字段逐字兼容。下表列出具体行为差异。需要实时 IDE 状态的功能仍须由 IDE 进程内桥接执行，不能仅靠读工程文件完成。

## 准备环境

Windows 10/11、64 位 Python、AMD64 炫彩 IDE ABI v3、MSVC C++ 桌面工具和 Windows SDK。CLI 在每次会话的私有 IDE 副本内编译 `native/ide_bridge.cpp`；不向正式安装复制插件。桥接代码、工具映射、本文及 HTML 均随 wheel 提供。

会话使用独立 Windows 桌面和所属进程 Job；不切换当前桌面、不调用全局输入或移动鼠标。只接受 `ide start` 创建的会话，不能接管用户已有的前台 IDE。不要让另一个 IDE 同时保存同一工程。

## Agent 调用步骤

先列出完整参数 schema、写入属性和行为备注：

```powershell
cli-anything-xcide --json ide tools

# --project 指向已经存在的工程；会话目录必须尚不存在。
cli-anything-xcide --json --ide 'I:\xcide' --project 'E:\work\Demo\Demo.xcproj' ide start --directory 'E:\work\Demo-session'

cli-anything-xcide --json ide --instance 'E:\work\Demo-session' call xc_get_project
cli-anything-xcide --json ide --instance 'E:\work\Demo-session' call xc_get_output
cli-anything-xcide --json ide --instance 'E:\work\Demo-session' stop
```

省略 `--directory` 时，目录位于 `%LOCALAPPDATA%\cli-anything-xcide\ide` 下；从启动 JSON 的 `directory` 读取真实路径。默认空闲 1800 秒后关闭，`--idle-timeout` 可设 10..86400 秒。`ide list` 枚举默认目录；自选目录使用 `ide list --root 父目录`。停止后保留会话描述和日志，删除临时 IDE 副本。

参数使用 UTF-8 JSON 文件，避免 PowerShell 原生命令的引号处理差异。所有全局选项放在 `ide` 前，`--instance` 放在 `ide` 后、`call` 前。持久 IDE 会话与全局 `--session-file` 的 CLI 历史记录是两件事。

```python
import json
import os
import subprocess
from pathlib import Path

cli = r"E:\tools\cli-anything-xcide\.venv\Scripts\cli-anything-xcide.exe"
instance = r"E:\work\Demo-session"
args_file = Path(r"E:\work\symbol-args.json")
args_file.write_text(json.dumps({"name": "入口函数_窗口"}, ensure_ascii=False), encoding="utf-8")
p = subprocess.run(
    [cli, "--json", "ide", "--instance", instance, "call", "xc_symbol",
     "--args-file", str(args_file), "--timeout", "15"],
    capture_output=True, text=True, encoding="utf-8",
    env={**os.environ, "PYTHONUTF8": "1"}, check=False, timeout=30,
)
data = json.loads(p.stdout or p.stderr)
if p.returncode or not data.get("ok"):
    # 保留完整结果；created=true 或超时结果未知时，先回读再决定是否重试。
    raise RuntimeError(data)
print(data)
```

兼容入口中的相对文件路径通常基于 **当前 IDE 工程目录**；`xc_list_projects.root` 和 `xc_module_info.path` 使用进程工作目录解析相对路径，建议始终传绝对路径。修改目标路径不会隐式跨出工程；`xc_read_file`/`xc_editor_set` 可用显式 `allowOutsideProject`，`xc_open_in_ide` 本身允许明确打开外部路径。模块生成的 `location=dev/main` 会写所选 IDE 安装目录的模块库，应由调用方明确选择。

## 30 个工具的对应行为

| 工具名 | CLI 行为 | 差异与确认方式 |
| --- | --- | --- |
| `xc_status` | 当前桥接 PID、UI 线程、ABI、解析计数支持状态 | 返回 `mcp=false`，无 HTTP 连接状态 |
| `xc_get_project` | 原生 ABI 读取当前工程名、路径、配置 | 后续文件操作以此路径为准 |
| `xc_parse_status` | 读取实时解析计数 | 固定偏移仅对通过 EXE SHA-256 门禁的版本开放 |
| `xc_reset_parse_count` | 重置该版本的解析计数 | 属于恢复操作；不可在正常解析过程中随意调用 |
| `xc_server` | `status/start` 查询现有会话，`stop` 关闭私有 IDE | 实际创建用 `ide start`；不启动 MCP/HTTP 服务器 |
| `xc_ide_log` | 在 IDE UI 线程追加调试文本 | 可用 `xc_get_output` 回读 |
| `xc_build` | 后台投递 F7 | `compiled=null`；完成判定使用 `build --diagnostics` 的独立构建工作流 |
| `xc_menu_cmd` | `compile`、`recompile`、`compile_all` | 和参考插件一样投递 F7 或 Ctrl+F5；不声称已完成重新编译/全部编译 |
| `xc_get_output` | 读取真实输出面板，支持 `tailLines/maxChars` | `clear` 不清空面板，返回 `cleared=false` |
| `xc_get_dialogs` | 读取本 IDE UI 线程的原生/XCGUI 弹窗 | 未验证的直接绘制正文返回 `body_available=false`；有界扫描可返回 `partial=true` |
| `xc_read_file` | 磁盘文本、编码、BOM、换行和 SHA-256 | 不能代表未保存的编辑缓冲 |
| `xc_editor_get` | 读取已打开文件的实际编辑缓冲 | 包括未保存文本；可不传 path 读取当前编辑器 |
| `xc_editor_set` | 原子写入磁盘，默认保留编码和换行 | 延续参考插件的磁盘写入语义；`reload_required=true`，不直接更新编辑内存 |
| `xc_new_file` | 创建 UTF-8 BOM 的 `.xc/.xh` 并导入 | 目标已存在则拒绝；导入失败仍报告已创建的文件 |
| `xc_add_file` | 导入当前工程内文件；分号分隔 | 返回每项结果；部分完成不应整批重试 |
| `xc_add_dir_files` | 导入指定目录的同扩展名文件 | 非递归，最多 2000 项，先验证全部路径 |
| `xc_list_projects` | 按 root 递归列出 `.xcproj` | 文件系统发现，不等于正在运行的 IDE 实例 |
| `xc_open_in_ide` | 通过 IDE 导入/打开明确路径 | 不存在或不支持的文件返回失败；之后查询当前工程确认 |
| `xc_tree_probe` | 工程目录、文件类型和大小 | 和参考工具一样，`select/clean` 不选择或删除 GUI 树节点 |
| `xc_symbol` | 原生符号查询，可传 name/path/lineno | 使用当前官方结构；原生行列保留 IDE 定义，不与静态行号混用 |
| `xc_goto_function` | 查询定义、打开对应文件并移动光标 | 检查 `moved`；不支持重名函数的交互选择器 |
| `xc_list_functions` | 静态读取磁盘 `.xc`，跳过注释和生成目录 | 1 基行号；不承诺完整语言语义分析或未保存文本覆盖 |
| `xc_module_info` | ABI 查询已索引模块元数据 | path/name/module 查询；沿用旧 `author` 字段名，它映射 ABI 别名参数 |
| `xc_module_list` | 本机模块库及工程引用 | 支持 limit/all/projectOnly/withDeps；结果格式沿用 CLI 模块目录 |
| `xc_module_search` | 名称搜索与 dependsOn 依赖反查 | 同名歧义按现有 CLI 规则处理 |
| `xc_module_add` | 更新磁盘工程引用，支持本地相对头文件路径 | `restartRequired`；需要让 IDE 重新加载工程 |
| `xc_module_remove` | 移除准确文件引用或唯一名称匹配 | 不删除头文件；本地相对引用也可移除 |
| `xc_module_create` | 创建带库、复制文件、包含目录注解的 `.h/.cpp` | 默认 project、addToProject=true；显式 force 才覆盖，x86/x64 列表分别指定，不做路径猜测 |
| `xc_save_all` | 向私有 IDE 线程投递 Ctrl+S | 延续参考插件的投递语义；`saved=null`，不是“所有标签已保存”的证明 |
| `xc_probe_cmd` | 原生 ABI 诊断调用 | 20/21 可直接调用；其他需 allow_unsafe=true 和 confirm=`I-UNDERSTAND-THE-RISK`，可能终止私有 IDE |

参数的准确名称和类型以 `ide tools` 的 `inputSchema` 为准。模块列表/搜索的 `all=false` 排除开发模块库；列表数量、路径和错误不得沿用旧插件假设。

## 模块骨架示例

以下内容保存成参数文件后调用 `ide --instance ... call xc_module_create --args-file ...`：

```json
{
  "name": "sample",
  "alias": "样例",
  "location": "project",
  "subdir": "modules/sample",
  "libs": "x64/sample.lib",
  "libs86": "x86/sample.lib",
  "dlls": "x64/sample.dll",
  "dlls86": "x86/sample.dll",
  "includes": "include",
  "addToProject": true,
  "force": false
}
```

多个库或目录使用分号或 `|` 分隔，路径相对于模块目录；不自动下载或复制外部 SDK。不存在的依赖列入 `missing`。名称必须是 C++ 英文标识符，生成函数是返回 1 的初始化占位函数。源码内容须由 Agent 按实际 API 实现后再编译。修改模块引用后，停止当前会话、用新会话目录重新打开工程，或用 `build --diagnostics` 新建一次性构建。

## 结果、并发和版本边界

- `ide call` 返回 `ok=false` 时退出码为 1，但业务诊断可能写在 stdout；参数、传输及文件错误通常在 stderr。两者都须保留。
- 同一会话的工具调用串行执行；消息含会话令牌、请求 ID、PID 和截止时间。已过期且尚未处理的请求不执行；已开始后超时的操作结果未知，先读取文件、输出和弹窗，禁止盲目重试。
- 原生 API 进入模态循环时，只允许嵌套 `status/dialogs/output` 诊断；其他调用明确失败。无消息循环的 IDE 卡死只能超时，`ide stop` 有界关闭并回收所属进程。
- 每条原生消息上限 8 MiB。编辑/输出文本读取限制约 2M UTF-16 单元；静态函数索引最多 2000 个文件、每文件 4 MiB、20000 个函数；批量导入最多 2000 文件。
- 解析计数固定偏移仅支持 EXE SHA-256 为 `896fb8c8a9c2c26ee70668fc3691bc982358434ec6257f267f0d26a89cffb891` 的实测版本。版本不符时明确返回不支持，其他 ABI v3 功能仍可使用。XMsg 正文也有独立版本/对象身份检查。
- 只迁移所参考 XC-MCP-Next 源码版本注册的 30 个工具名，不推断未来插件版本能力。协议消费者若仍要求 MCP，应继续使用独立 MCP 服务；本 CLI 不伪装成 MCP endpoint。
- 被测程序的 `runtime test` 仍要求主动接入 `automation_bridge.h`，支持后台消息输入及 GDI 截图；本次 IDE 工具迁移不会自动适配任意第三方程序。

## 验证范围

安装命令端到端测试在真实私有 IDE 中调用全部 30 个工具名，核对当前工程、缓冲、符号、导航、输出、磁盘与模块修改，F7 生成新 AMD64 EXE，并检查停止后修改保留及正式安装配置哈希。另有空闲回收、过期请求拒绝、参数/路径/回滚测试；真实 XCGUI 的小型 ABI 测试宿主验证模态调用超时后读取正文和版本门禁。

这不代表所有参数组合或未知 IDE 版本均已验证。重编译与保存的投递结果仍为未知完成状态；完整测试数量及环境见 `tests/TEST.md` 的最新记录。
