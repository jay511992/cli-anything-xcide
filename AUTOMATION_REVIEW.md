# XCIDE 后台自动化审查与修复记录

本次按用户后续“请修复问题”的授权实施修复；没有启动子代理。范围限于编译诊断、运行调试、后台交互及其测试/文档。此前 20 轮与 50 轮数据探索记录仍见对应报告，不将本次测试数计作挖掘轮次。

## 1. IDE 启动与运行输入会占用前台（已修复）

- 严重程度：高
- 文件位置：`xcide/agent-harness/cli_anything/xcide/core/build.py`；`utils/win_debug.py`；`utils/win_desktop.py`。
- 问题描述：旧构建用默认桌面启动 IDE；运行测试通过前台焦点、光标定位和全局输入操作，违反用户“编译和测试均后台进行”的要求。检查和发送之间也存在窗口变化的竞争窗口。
- 触发条件：启动 IDE、界面测试输入或截图时，用户同时使用前台桌面。
- 影响范围：前台焦点/鼠标，以及运行测试的输入目标和截图可信度。
- 最小修复建议：在执行入口创建独立 Windows 桌面，使用 CreateProcess 的 lpDesktop，所有窗口操作限定本次 PID/EXE；不提供前台回退。已在现有调用链落地，旧命令名保留。
- 不确定之处：已验证本机登录会话；Windows 服务、锁屏、RDP 断线、其他 DPI 未测。独立桌面不是文件/网络沙箱。

## 2. F7 可能发给输入法辅助窗口（已修复）

- 严重程度：中
- 文件位置：`xcide/agent-harness/cli_anything/xcide/core/build.py`，`_post_f7`。
- 问题描述：原实现取枚举结果第一个 HWND。本机后台 IDE 实际枚举到两个输入法辅助窗口排在 XCGUI 主窗口前，导致 F7 未发起编译，等待至超时。
- 触发条件：同一 IDE PID 包含可见辅助窗口，且枚举顺序先于主窗口。
- 影响范围：普通与诊断构建的启动、超时和新产物判定。
- 最小修复建议：过滤类名为 XCGUI 且标题非空的唯一主窗口；歧义时中止，并使用正确的 F7 扫描码/按下抬起状态。已修复。
- 不确定之处：主窗口类名依据当前 IDE 实测；版本改变会明确拒绝，不自动选择首个窗口。

## 3. 关闭失败会覆盖构建主错误（已修复）

- 严重程度：中
- 文件位置：`xcide/agent-harness/cli_anything/xcide/core/build.py`，构建异常处理与 finally；`utils/win_debug.py`，`BackgroundProcess`。
- 问题描述：原 finally 直接调用可能抛错的关闭函数，原生模态框可导致关闭超时，覆盖原始诊断并留下隔离 IDE。此前临时 IDE 曾出现 XWnd_GetHWND 原生错误框；其底层原因未确认。
- 触发条件：编译/启动出错后 IDE 正在模态窗口中，正常关闭未完成。
- 影响范围：失败报告完整性、后台进程/临时目录清理，以及自动化重试判断。
- 最小修复建议：分别保留主错误、原生对话框文字和 cleanup_error；暂停启动即加入本次 Job，正常关闭超时只回收该 Job，标记 terminated 和失败。已修复，并加入回归用例。
- 不确定之处：具体 IDE 内部句柄错误根因未确认；没有声称修复 IDE 自身，也不自动确认模态按钮。

## 4. 普通后台消息/截图返回不证明炫彩交互成功（已处理）

- 严重程度：中
- 文件位置：`xcide/agent-harness/cli_anything/xcide/utils/win_desktop.py`；`native/automation_bridge.h`；`core/runtime.py`。
- 问题描述：实测普通鼠标 PostMessage/SendMessage 未触发示例按钮，PrintWindow 返回成功但图像全黑；单独 XWnd_DrawWindow 只画出窗框，不包含控件。这些返回值不能用作测试成功证据。
- 触发条件：在后台桌面直接驱动 XCGUI 自绘控件，或用普通窗口截图判断渲染。
- 影响范围：点击、输入、截图和自动化通过结果的可信度。
- 最小修复建议：被测工程主动接入小型适配器，在 UI 线程经 XC_SendMessage 分派输入；GDI 截图读取 XWM_PAINT_END 完整缓冲。结果必须有业务日志/标题断言，截图还检查非黑帧；缺适配器和 D2D 截图明确失败。已实现，不直接调用业务回调。
- 不确定之处：覆盖的是原生消息路径，不代表硬件输入、Raw Input、IME 或任意第三方框架都可用；D2D 后台截图尚未支持。

## 5. MSVC 环境大小写与错误文本编码（已修复）

- 严重程度：低
- 文件位置：`xcide/agent-harness/cli_anything/xcide/utils/native_build.py`。
- 问题描述：环境合并同时可能保留 Path/PATH 两个键，工具链查找可能读取旧值；编译器 UTF-8 错误文本用 mbcs 解码曾出现中文乱码。
- 触发条件：父进程以不同大小写提供环境键，或 cl 输出 UTF-8 中文错误。
- 影响范围：本地桥接编译器选择、失败诊断可读性。
- 最小修复建议：环境键统一为大写并读取 PATH；诊断先严格 UTF-8，失败再用系统编码。辅助 cmd/cl 启动使用 CREATE_NO_WINDOW。已修复。
- 不确定之处：错误文本乱码已实测；环境键导致选错工具链在本机本轮没有复现，属于经代码路径确认的条件性风险。

## 验证与行为影响

完整已安装命令回归 **191 项通过**（155 核心、36 端到端）。包括原有两个无插件 IDE 构建、诊断成功和故意错误源码构建、x86/x64 调试输出/异常/超时、后台中文输入/按钮/退格及 GDI 绘制截图。正式配置 SHA-256 仍为 `977E1D599024CB3A119CD1C6EBFA4CB64C0A5F87CE73E5C3B0600DE234ED9D1C`。

旧文件命令、普通 build 的产物语义和空插件行为保留；新增 --diagnostics 才要求真实编译诊断。所有构建/运行改为后台独立桌面。runtime test 需程序主动接入测试头；普通启动不启用测试入口，runtime run 不要求适配器。异常/超时清理只针对本次创建的 Job。

更新文件还包括 `xcide_cli.py`、`core/diagnostics.py`、`native/output_bridge.cpp`、计数器源码/场景、`setup.py`、两个测试文件及中文 README/架构/调用手册/技能和离线阅读版。没有重构其他工程模块，也没有修改正式 IDE 或原示例源码。

本轮留存证据：[汇总](xcide/automation-evidence/summary.json)、[编译成功](xcide/automation-evidence/build-success.json)、[错误源码诊断](xcide/automation-evidence/build-source-error.json)、[后台交互](xcide/automation-evidence/runtime-success.json)、[静止鼠标对照](xcide/automation-evidence/runtime-stationary-cursor.json)。最终复测期间用户在操作鼠标，因此坐标有变化；前台句柄保持一致，CLI 不锁定或恢复鼠标。此前静止鼠标对照中每步前后坐标一致。
