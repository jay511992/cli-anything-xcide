# D2D 失败后的进程清理修复

2026-11-25：已确认 CLI 清理等待的缺陷并完成最小修复。独立仓库的完整安装命令测试为 **195 项通过，耗时 93.63 秒**。此前搬迁验收的失败记录保留在 [STANDALONE_VALIDATION.md](STANDALONE_VALIDATION.md)。

## 原因与证据

- 严重程度：中。
- 文件位置：[win_debug.py](xcide/agent-harness/cli_anything/xcide/utils/win_debug.py)，`DebugProcess.close()` 和 `_OwnedProcess.wait()`。
- 问题描述：旧实现先等待调试退出事件最多 5 秒，之后固定只等进程句柄 1 秒。收到 `EXIT_PROCESS_DEBUG_EVENT`、成功执行 `ContinueDebugEvent`，甚至读到退出码，均不等于进程句柄已经 signaled。最后一次等待还会覆盖此前的清理错误；异常等待结果也被统一当作超时。
- 触发条件：后台程序退出较慢，尤其本机 D2D 截图被拒绝后走强制清理时；也可能影响其他需要强制终止的程序。x64/x86 均有历史失败，不能归因于架构或仓库目录。
- 影响范围：`runtime run/test` 的本次进程回收可能提前报清理超时，或丢失先前清理错误。D2D 截图本身仍不受支持，操作返回失败是预期行为。
- 最小修复建议：调试事件处理与最终进程等待共用一个有限截止时间；等待原生句柄确认结束；累积保留清理错误，并区分超时与等待 API 失败。本轮已按此实施。
- 不确定之处：底层退出延迟究竟来自图形驱动、输入法组件还是其他系统资源，现有证据不能确定。此次修复解决 CLI 的等待预算和错误保留问题，不宣称修复 Windows 或 D2D 的内部退出过程。

真实 x86 时序以各次启动的单调时钟为起点，单位为秒：

| 证据 | 终止请求 | 收到退出事件 | 后续等待返回 | 原生等待结果 |
| --- | --- | --- | --- | --- |
| [第一次原始追踪](xcide/automation-evidence/cleanup-fix/before-x86-exit-event-wait-timeout.json) | 0.555415 | 0.573787 | 1.574417 | 258，WAIT_TIMEOUT；已有退出码 0xE0000001 |
| [第二次原始追踪](xcide/automation-evidence/cleanup-fix/before-x86-repeat-timeout.json) | 0.598486 | 0.651970 | 1.660147 | 258，WAIT_TIMEOUT；已有退出码 0xE0000001 |

第二次追踪在 0.651985 秒确认 `ContinueDebugEvent` 成功，仍未使后续 1 秒等待成功。因此不能用“已收到退出事件”代替进程句柄结束核验。

## 改动与行为影响

- `utils/win_debug.py`：清理开始时建立 10 秒截止时间，调试事件处理和最终句柄等待共用剩余预算。正常进程结束后立即返回，不固定等待 10 秒；超出期限仍报告失败。
- 同文件追加清理错误，保留原有原因；仅 `WAIT_TIMEOUT` 产生 `TimeoutExpired`，其他异常结果报告 `OSError`。
- `tests/test_core.py`：增加 4 项确定性用例，覆盖晚到的退出事件、超过 1 秒的句柄结束延迟、共同截止时间与多个错误，以及 API 失败区分。
- `tests/test_full_e2e.py`：加强真实 x86/x64 后台适配器测试，核验退出码及可访问的进程句柄已结束。
- 其他变更为测试记录、取证和技能交付说明；原生桥接、前台输入方式、成功判定与 D2D 截图限制均未修改。

行为变化集中在异常回收阶段：旧的“最多 5 秒处理事件，再等 1 秒”改为共用约 10 秒预算。运行超时之后可能额外经历这段清理时间；调用方应为清理和写报告留出时间。没有新增前台窗口激活、桌面切换或鼠标操作。

## 验证

1. 4 项确定性回归在旧实现上失败、修复后通过；包含退出事件已到但进程句柄再延迟 1.4 秒、以及退出事件延迟 5.2 秒的情况。
2. 真实定向测试 **10 项通过、26 项未选中**，覆盖 x86/x64 后台模式及异常/超时等路径。原始日志：[targeted-tests.txt](xcide/automation-evidence/cleanup-fix/targeted-tests.txt)。
3. 真实 D2D 失败回收重复检查 **24/24 通过**（x86、x64 各 12 次）：操作仍为 `ok=false`，`terminated=true`，退出码为 `0xE0000001`，`cleanup_error=null`，进程句柄已结束。该批最终等待最大 0.296064 秒，超过 1 秒的场景由确定性测试覆盖，不把随机复测当作延迟上限证明。[汇总](xcide/automation-evidence/cleanup-fix/summary.json) 和 [原始成功回收追踪](xcide/automation-evidence/cleanup-fix/after-d2d-process-signaled.json)。
4. 使用独立仓库 `.venv` 中的已安装 CLI，完整测试 **195/195 通过**（159 项核心测试、36 项端到端测试），包含真实 IDE 正确/错误源码编译和后台输入、点击、GDI 截图。完整输出：[full-suite.txt](xcide/automation-evidence/cleanup-fix/full-suite.txt)。
5. 正式 IDE 配置的 SHA-256 保持 `977e1d599024cb3a119cd1c6ebfa4cb64c0a5f87ce73e5c3b0600de234ed9d1c`。

XC 开发技能也已补入独立仓库；携带哪些文件、哪些 MCP 项目为可选外部工具，见 [DEPENDENCIES.md](DEPENDENCIES.md)。
