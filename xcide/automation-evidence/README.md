# 后台自动化验收证据

这里保存了 2026-11-25 的真实 IDE 编译与测试程序后台运行结果。汇总见 [summary.json](summary.json)，相应测试步骤和边界见 [审查记录](../../AUTOMATION_REVIEW.md)。

| 文件 | 说明 |
| --- | --- |
| `build-success.json` | 使用真实 IDE 完成编译和新 EXE 验证 |
| `build-source-error.json` | 错误源码的诊断与失败结果 |
| `runtime-success.json` | 后台消息输入、断言、截图和退出的成功运行 |
| `runtime-expected-failure.json` | 故意失败的断言，验证失败不会误报成功 |
| `runtime-stationary-cursor.json` | 静止鼠标对照运行，记录前台句柄和光标观测 |
| [004-initial.png](004-initial.png) | 输入前的 GDI 绘制截图 |
| [012-clicked.png](012-clicked.png) | 输入和按钮点击后的 GDI 绘制截图 |

JSON 是原始结果副本，保留当时绝对路径、进程 ID、时间与 SHA-256。临时目录可能已经清理，阅读截图时使用本目录中的副本；这些记录不会因克隆仓库而自动重放。`summary.json` 的 `source_sha256` 对应 `../agent-harness/cli_anything/xcide/` 下同名文件。

最终一次运行期间用户正在移动鼠标，因此前后坐标可能不同；前台句柄保持一致。另附的静止鼠标对照用于核对不移动光标的行为，工具不会锁定或恢复用户鼠标。

搬迁后的独立安装复测另存于 `standalone-validation/`，包含全量测试、定向重试和两次清理超时的原始报告；结果说明见 [独立仓库验收](../../STANDALONE_VALIDATION.md)。本页上表保留的是搬迁之前的历史验收。
