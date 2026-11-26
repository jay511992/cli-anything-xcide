"""炫彩 XCGUI／炫语言 IDE 的命令行与有状态交互终端。"""

from __future__ import annotations

import json
import hashlib
import os
import shlex
from functools import wraps
from pathlib import Path
from typing import Any, Callable

import click

from cli_anything.xcide.core import archive as archive_core
from cli_anything.xcide.core import build as build_core
from cli_anything.xcide.core import doctor as doctor_core
from cli_anything.xcide.core import examples as examples_core
from cli_anything.xcide.core import files as files_core
from cli_anything.xcide.core import interface as interface_core
from cli_anything.xcide.core import ide as ide_core
from cli_anything.xcide.core import ide_tools
from cli_anything.xcide.core import modules as modules_core
from cli_anything.xcide.core import preview as preview_core
from cli_anything.xcide.core import project as project_core
from cli_anything.xcide.core import references as references_core
from cli_anything.xcide.core import runtime as runtime_core
from cli_anything.xcide.core import templates as templates_core
from cli_anything.xcide.core import themes as themes_core
from cli_anything.xcide.core import ui_templates as ui_templates_core
from cli_anything.xcide.core import ui_data as ui_data_core
from cli_anything.xcide.core.build import BuildError
from cli_anything.xcide.core.project import ProjectError, create_project, inspect_project, list_projects
from cli_anything.xcide.core.session import Session, SessionError
from cli_anything.xcide.utils.repl_skin import ReplSkin


__version__ = "1.0.0"


def handle_error(function: Callable[..., Any]) -> Callable[..., Any]:
    """将可处理的后端或工程错误统一输出为 JSON 或文本。"""
    @wraps(function)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        try:
            return function(*args, **kwargs)
        except click.exceptions.Exit:
            raise
        except (files_core.FileOperationError, modules_core.ModuleError, templates_core.TemplateError,
                examples_core.ExampleError, ui_templates_core.UITemplateError,
                themes_core.ThemeError,
                interface_core.InterfaceError, ProjectError, BuildError,
                FileNotFoundError, IsADirectoryError, OSError,
                RuntimeError, TimeoutError, ValueError) as exc:
            ctx = click.get_current_context(silent=True)
            use_json = bool(ctx and ctx.find_root().params.get("use_json"))
            payload = {"ok": False, "error": str(exc), "error_type": type(exc).__name__}
            if ctx and ctx.find_root().params.get("dry_run"):
                payload["dry_run"] = True
            if use_json:
                click.echo(json.dumps(payload, ensure_ascii=True, indent=2), err=True)
            else:
                click.secho(f"Error: {exc}", fg="red", err=True)
            raise click.exceptions.Exit(1) from None
    return wrapped


@handle_error
def _emit(value: Any, use_json: bool = True) -> None:
    # Persist before reporting a result, so post-commit bookkeeping cannot turn
    # an already completed filesystem operation into a retryable failure.
    ctx = click.get_current_context(silent=True)
    obj = ctx.find_root().obj if ctx else None
    session = obj.get("session") if obj else None
    if session and session.modified and not obj["dry_run"]:
        try:
            session.save()
        except (OSError, RuntimeError) as exc:
            if not ctx.find_root().meta.get("xcide_operation_completed"):
                raise
            value = {**value, "session_saved": False,
                     "session_warning": {"error": str(exc), "error_type": type(exc).__name__,
                                         "operation_completed": True, "retry_operation": False}}
            # Reload persisted selection for subsequent REPL commands. The
            # failed audit/selection save must not overwrite a newer session.
            try:
                obj["session"] = Session(session.path)
            except SessionError:
                # A concurrent invalid edit must not turn a completed operation
                # into a retryable error, or trigger another automatic save.
                session.modified = False
                obj["session"] = session
            obj["project"] = obj["session"].project
            obj["ide_root"] = obj["session"].state.get("ide_root")
    if use_json:
        click.echo(json.dumps(value, ensure_ascii=True, indent=2, default=str))
    elif isinstance(value, dict):
        for key, item in value.items():
            click.echo(f"{key}: {item if isinstance(item, (str, int, float, bool)) or item is None else json.dumps(item, ensure_ascii=False, indent=2, default=str)}")
    else:
        click.echo(value)


def _record(ctx: click.Context, action: str, **details: Any) -> None:
    obj = ctx.find_root().obj
    if not obj["dry_run"]:
        obj["session"].record_action(action, **details)
        if action != "project.open-selected":
            ctx.find_root().meta["xcide_operation_completed"] = True


def _project_path(ctx: click.Context, requested: str | None = None) -> str:
    selected = requested or ctx.find_root().obj["project"]
    if not selected:
        raise ValueError("Pass --project with the full path of the project the CLI should operate on.")
    return inspect_project(selected)["project_file"]


def _dry_plan(ctx: click.Context, action: str, **details: Any) -> bool:
    obj = ctx.find_root().obj
    if not obj["dry_run"]:
        return False
    _emit({"ok": True, "dry_run": True, "action": action, **details}, obj["use_json"])
    return True


def _guard_project(ctx: click.Context, requested: str | None = None) -> str:
    return _project_path(ctx, requested)


@click.group(invoke_without_command=True, no_args_is_help=False, context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--json", "use_json", is_flag=True, help="输出机器可读的 JSON。全局参数必须放在子命令之前。")
@click.option("--project", "project", type=click.Path(path_type=Path), help="选择本地 CLI 会话默认操作的准确 .xcproj 工程。")
@click.option("--ide", "ide_root", type=click.Path(path_type=Path, file_okay=False), envvar="XC_IDE_ROOT", help="包含炫彩IDE.exe 和 data/ 资源目录的安装根目录。")
@click.option("--session-file", "session_file", type=click.Path(path_type=Path, dir_okay=False), help="指定使用文件锁的持久命令行会话 JSON 文件。")
@click.option("--dry-run", "dry_run", is_flag=True, help="只生成操作计划，不调用 IDE、不写文件，也不保存会话。")
@click.pass_context
@handle_error
def cli(ctx: click.Context, use_json: bool, project: Path | None, ide_root: Path | None,
        session_file: Path | None, dry_run: bool) -> None:
    """通过本机文件与工程 XML 操作 XCGUI / 炫语言 IDE 工程。

    不指定子命令时启动有状态的交互式 REPL。
    """
    inherited = dict(ctx.obj or {}) if (ctx.obj or {}).get("_repl_context") else {}
    session = inherited.get("session") or Session(session_file)
    use_json = use_json or inherited.get("use_json", False)
    dry_run = dry_run or inherited.get("dry_run", False)
    explicit_project = str(project.expanduser().resolve()) if project else None
    if explicit_project:
        inspect_project(explicit_project)
    selected_project = explicit_project or inherited.get("project") or session.project
    selected_ide = str(ide_root.expanduser().resolve()) if ide_root else inherited.get("ide_root") or session.state.get("ide_root")
    if not dry_run and any(value is not None for value in (project, ide_root)):
        session.select(project=selected_project, ide_root=selected_ide)
    ctx.ensure_object(dict)
    ctx.obj.update({"session": session, "use_json": use_json,
                    "project": selected_project, "ide_root": selected_ide,
                    "dry_run": dry_run})
    ctx.meta["xcide_auto_save"] = True
    ctx.meta["xcide_operation_completed"] = False
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


@cli.result_callback()
@click.pass_context
@handle_error
def _auto_save_session(ctx: click.Context, result: Any, **kwargs: Any) -> Any:
    if ctx.obj["dry_run"] or not ctx.meta.get("xcide_auto_save"):
        return result
    obj = ctx.obj or {}
    session = obj.get("session")
    if session and session.modified:
        session.save()
    return result


@cli.command("repl")
@click.pass_context
@handle_error
def repl(ctx: click.Context) -> None:
    """进入持久的本地工程工作流交互终端；输入 help 查看帮助，输入 quit 退出。"""
    skin = ReplSkin("xcide", version=__version__)
    skin.print_banner()
    prompt_session = skin.create_prompt_session()
    commands = {
        "status": "检查本地工程、IDE 安装与会话信息",
        "project new DIR NAME [--template ID]": "根据 IDE 内置炫语言模板创建独立工程",
        "project template list [QUERY]": "搜索 IDE 内置炫语言工程模板",
        "project config list | set": "查看或切换工程内已定义的配置和架构",
        "project sources list | add | remove": "管理真实存在的炫语言源码登记",
        "project breakpoints list | add | remove": "读取或维护项目断点元数据",
        "project debug list | watch | bookmark": "管理断点以外的工程调试元数据",
        "ui-template list | info | copy": "浏览和复制 IDE 自带布局/皮肤素材",
        "theme list | info": "只读浏览 IDE 编辑器颜色、字体和设计器背景主题",
        "reference sources | search KIND [QUERY] | show KIND ID": "查询原生片段、语言、控件属性/事件与编译选项",
        "example list | example info | example copy": "浏览、检查并派生 IDE 示例工程",
        "project info FILE": "直接检查原生 .xcproj 工程",
        "project doctor": "检查源码登记、模块、布局和 UI ZIP",
        "project list DIR": "查找本地 .xcproj 工程文件",
        "interface list | interface check": "查看布局文件和检查结构",
        "interface nodes | node FILE [ID]": "按名称、属性和绑定定位磁盘或 ZIP 内布局节点",
        "resource list | show FILE [ID]": "查询磁盘或 ZIP 内原生资源表条目与资产路径",
        "archive list | read | export FILE": "检查 ZIP 成员、读取文本或向新文件导出单个成员",
        "editor read PATH": "直接从磁盘读取所选工程或 IDE 文件",
        "editor write PATH FILE": "直接写入本地工程文件并回读验证",
        "module list | module search TEXT": "扫描本地已安装模块库",
        "module dependencies FILE": "按本地头文件生成依赖顺序计划",
        "build [--diagnostics]": "后台独立桌面启动 IDE、定向 F7；可读取编译诊断",
        "runtime run | test": "后台运行输出/异常捕获，或 XCGUI 消息与截图验收",
        "ide start | list | tools | call | stop": "持久后台 IDE 原生会话及 30 个 xc_* 兼容调用（无需 MCP）",
        "preview capture [project|executable]": "发布本地工程检查预览数据",
        "preview latest [recipe]": "读取本地已保存预览包",
        "session status | session history | session undo | session redo": "管理本地 CLI 工程会话",
        "quit": "退出交互终端",
    }
    skin.help(commands)
    handlers: dict[str, Callable[[list[str]], Any]] = {
        "quit": lambda _args: "quit",
        "exit": lambda _args: "quit",
        "q": lambda _args: "quit",
    }
    try:
        while True:
            try:
                current = ctx.obj["session"].project
                line = skin.get_input(prompt_session, project_name=Path(current).name if current else "").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not line:
                continue
            try:
                words = shlex.split(line, posix=os.name != "nt")
                if os.name == "nt":
                    words = [word[1:-1] if len(word) >= 2 and word[0] == word[-1] and word[0] in "\"'" else word for word in words]
                command = words[0].lower()
                if command in ("help", "?"):
                    skin.help(commands)
                elif command in handlers:
                    result = handlers[command](words[1:])
                    if result == "quit":
                        break
                    if result is not None:
                        _emit(result, ctx.obj["use_json"])
                else:
                    command_context = {**ctx.obj, "_repl_context": True}
                    try:
                        cli.main(args=words, prog_name="cli-anything-xcide", standalone_mode=False,
                                 obj=command_context)
                    finally:
                        ctx.obj["session"] = command_context["session"]
                        ctx.obj["project"] = ctx.obj["session"].project
                        ctx.obj["ide_root"] = ctx.obj["session"].state.get("ide_root")
            except (click.ClickException, click.exceptions.Exit, files_core.FileOperationError,
                    modules_core.ModuleError, templates_core.TemplateError, examples_core.ExampleError,
                    ui_templates_core.UITemplateError,
                    interface_core.InterfaceError,
                    ProjectError, BuildError,
                    OSError, RuntimeError, ValueError) as exc:
                skin.error(str(exc))
    finally:
        if ctx.obj["session"].modified and not ctx.obj["dry_run"]:
            ctx.obj["session"].save()
    skin.print_goodbye()


@cli.command("status")
@click.pass_context
@handle_error
def status_command(ctx: click.Context) -> None:
    """检查本地工程和 CLI 会话；不连接 IDE。"""
    if _dry_plan(ctx, "status", project=ctx.obj["project"]):
        return
    root = Path(ctx.obj["ide_root"]) if ctx.obj["ide_root"] else None
    if root is None:
        try:
            root = __import__("cli_anything.xcide.core.project", fromlist=["resolve_ide_root"]).resolve_ide_root()
        except ProjectError:
            root = None
    result = {"ok": True, "software": "xcide", "backend": "local-filesystem",
              "project": inspect_project(ctx.obj["project"]) if ctx.obj["project"] else None,
              "ide_root": str(root) if root else None,
              "ide_executable": str(root / "炫彩IDE.exe") if root else None,
              "session": ctx.obj["session"].summary()}
    _emit(result, ctx.obj["use_json"])


@cli.group("ui-template")
def ui_template_group() -> None:
    """浏览、检查并复制 IDE 安装包中的布局模板和皮肤资源。"""


@ui_template_group.command("list")
@click.argument("query", required=False, default="")
@click.option("--category", type=click.Choice(["皮肤", "布局模板"]), help="只列出指定类别。")
@click.option("--limit", type=click.IntRange(1, 2000), default=200, show_default=True)
@click.pass_context
@handle_error
def ui_template_list(ctx: click.Context, query: str, category: str | None, limit: int) -> None:
    """按类别、名称、控件类型和说明搜索本地界面模板。"""
    _emit(ui_templates_core.list_ui_templates(ide_root=ctx.find_root().obj["ide_root"], query=query,
                                               category=category, limit=limit),
          ctx.find_root().obj["use_json"])


@ui_template_group.command("info")
@click.argument("template_id")
@click.pass_context
@handle_error
def ui_template_info(ctx: click.Context, template_id: str) -> None:
    """读取模板元数据和真实布局/资源文件清单。"""
    _emit(ui_templates_core.inspect_ui_template(template_id, ide_root=ctx.find_root().obj["ide_root"]),
          ctx.find_root().obj["use_json"])


@ui_template_group.command("copy")
@click.argument("directory", type=click.Path(path_type=Path, file_okay=False))
@click.argument("name")
@click.option("--id", "template_id", required=True, help="ui-template list 返回的准确相对 ID。")
@click.pass_context
@handle_error
def ui_template_copy(ctx: click.Context, directory: Path, name: str, template_id: str) -> None:
    """将完整素材目录复制到新目标；不覆盖目标或安装中的模板。"""
    obj = ctx.find_root().obj
    parent = directory.expanduser().resolve()
    if obj["dry_run"]:
        _emit({"ok": True, "dry_run": True, "action": "ui-template.copy", "directory": str(parent),
               "name": name, "template": template_id}, obj["use_json"])
        return
    result = ui_templates_core.copy_ui_template(parent, name, template_id, ide_root=obj["ide_root"])
    _record(ctx, "ui-template.copy", template=template_id, destination=result["destination"],
            file_count=result["file_count"])
    _emit(result, obj["use_json"])


@cli.group("reference")
def reference_group() -> None:
    """只读查询 IDE 原生代码片段、语言帮助、控件和编译选项定义。"""


@reference_group.command("sources")
@click.pass_context
@handle_error
def reference_sources(ctx: click.Context) -> None:
    """列出已知参考文件、可用性、条目数与 SHA-256。"""
    _emit(references_core.list_sources(ide_root=ctx.obj["ide_root"]), ctx.obj["use_json"])


@reference_group.command("search")
@click.argument("kind", type=click.Choice(list(references_core.CATALOGS)))
@click.argument("query", required=False, default="")
@click.option("--scope", help="仅匹配 scopes 返回的准确层级，不合并父级或子级。")
@click.option("--limit", type=click.IntRange(1, 2000), default=50, show_default=True)
@click.option("--offset", type=click.IntRange(min=0), default=0, show_default=True)
@click.pass_context
@handle_error
def reference_search(ctx: click.Context, kind: str, query: str, scope: str | None, limit: int, offset: int) -> None:
    """按原生名称、帮助、源码或声明搜索；返回准确 ID 与所属层级。"""
    _emit(references_core.search_references(kind, query, ide_root=ctx.obj["ide_root"],
                                           scope=scope, limit=limit, offset=offset), ctx.obj["use_json"])


@reference_group.command("show")
@click.argument("kind", type=click.Choice(list(references_core.CATALOGS)))
@click.argument("identifier")
@click.pass_context
@handle_error
def reference_show(ctx: click.Context, kind: str, identifier: str) -> None:
    """读取 search 返回的准确 ID；返回原生内容，不展开占位符或写入文件。"""
    _emit(references_core.show_reference(kind, identifier, ide_root=ctx.obj["ide_root"]), ctx.obj["use_json"])


@cli.group("theme")
def theme_group() -> None:
    """只读浏览 IDE 配置的代码编辑器主题。"""


@theme_group.command("list")
@click.argument("query", required=False, default="")
@click.option("--limit", type=click.IntRange(1, 2000), default=200, show_default=True)
@click.pass_context
@handle_error
def theme_list(ctx: click.Context, query: str, limit: int) -> None:
    """按主题名、字体、皮肤路径或颜色检索已安装主题。"""
    _emit(themes_core.list_themes(ide_root=ctx.find_root().obj["ide_root"], query=query, limit=limit),
          ctx.find_root().obj["use_json"])


@theme_group.command("info")
@click.argument("theme_id")
@click.pass_context
@handle_error
def theme_info(ctx: click.Context, theme_id: str) -> None:
    """读取某个安装主题的字体、行距、皮肤和编辑器颜色。"""
    _emit(themes_core.inspect_theme(theme_id, ide_root=ctx.find_root().obj["ide_root"]),
          ctx.find_root().obj["use_json"])


@cli.group("example")
def example_group() -> None:
    """浏览、检查并复制炫彩 IDE 自带的炫语言示例工程。"""


@example_group.command("list")
@click.argument("query", required=False, default="")
@click.option("--limit", type=click.IntRange(1, 2000), default=200, show_default=True)
@click.pass_context
@handle_error
def example_list(ctx: click.Context, query: str, limit: int) -> None:
    """按名称、相对路径或分类搜索本地示例工程。"""
    _emit(examples_core.list_examples(ide_root=ctx.find_root().obj["ide_root"], query=query, limit=limit),
          ctx.find_root().obj["use_json"])


@example_group.command("info")
@click.argument("example_id")
@click.pass_context
@handle_error
def example_info(ctx: click.Context, example_id: str) -> None:
    """读取本地示例工程元数据和可复用文件清单。"""
    _emit(examples_core.inspect_example(example_id, ide_root=ctx.find_root().obj["ide_root"]),
          ctx.find_root().obj["use_json"])


@example_group.command("copy")
@click.argument("directory", type=click.Path(path_type=Path, file_okay=False))
@click.argument("name")
@click.option("--id", "example_id", required=True, help="example list 返回的准确相对 .xcproj 路径。")
@click.pass_context
@handle_error
def example_copy(ctx: click.Context, directory: Path, name: str, example_id: str) -> None:
    """将本地示例复制为新工程；不会修改原示例或覆盖目标目录。"""
    obj = ctx.find_root().obj
    parent = directory.expanduser().resolve()
    if obj["dry_run"]:
        _emit({"ok": True, "dry_run": True, "action": "example.copy", "directory": str(parent),
               "name": name, "example": example_id}, obj["use_json"])
        return
    result = examples_core.copy_example(parent, name, example_id, ide_root=obj["ide_root"])
    obj["session"].select(project=result["project_file"], action="example.copy")
    _record(ctx, "example.copy", project=result["project_file"], example=example_id)
    _emit({"ok": True, "dry_run": False, **result}, obj["use_json"])


@cli.group("project")
def project_group() -> None:
    """创建、查找和检查原生 .xcproj 工程。"""


@project_group.command("new")
@click.argument("directory", type=click.Path(path_type=Path, file_okay=False))
@click.argument("name")
@click.option("--configuration", help="覆盖 IDE 模板中已存在的编译配置。")
@click.option("--platform", type=click.Choice(["x64", "x86"]), help="覆盖 IDE 模板的目标架构。")
@click.option("--template", "template_id", help="IDE 内置炫语言模板 ID；省略时使用标准空白窗口模板。")
@click.pass_context
@handle_error
def project_new(ctx: click.Context, directory: Path, name: str, configuration: str, platform: str,
                template_id: str | None) -> None:
    """使用 IDE 自带的炫语言模板，在新 DIRECTORY/NAME 下创建工程。"""
    obj = ctx.find_root().obj
    parent = directory.expanduser().resolve()
    if obj["dry_run"]:
        _emit({"ok": True, "dry_run": True, "action": "project.new",
               "directory": str(parent), "name": name, "template": template_id,
               "configuration": configuration or ("发布版" if not template_id else None),
               "platform": platform or ("x64" if not template_id else None)}, obj["use_json"])
        return
    if template_id:
        result = templates_core.create_from_template(directory, name, template_id, obj["ide_root"],
                                                    configuration=configuration, platform=platform)
    else:
        result = create_project(directory, name, obj["ide_root"], configuration=configuration or "发布版",
                                platform=platform or "x64")
    obj["session"].select(project=result["project_file"], action="project.new")
    _record(ctx, "project.new", project=result["project_file"])
    _emit({"ok": True, "dry_run": False, **result}, obj["use_json"])


@project_group.command("info")
@click.argument("project_file", type=click.Path(path_type=Path, dir_okay=False))
@click.pass_context
@handle_error
def project_info(ctx: click.Context, project_file: Path) -> None:
    """读取工程 XML、入口源码和本地模块列表，不调用 IDE。"""
    _emit({"ok": True, **inspect_project(project_file)}, ctx.find_root().obj["use_json"])


@project_group.command("list")
@click.argument("directory", type=click.Path(path_type=Path, file_okay=False))
@click.option("--recursive", is_flag=True, help="递归查找子目录；跳过编译生成目录。")
@click.pass_context
@handle_error
def project_list(ctx: click.Context, directory: Path, recursive: bool) -> None:
    """在本地目录中查找原生 .xcproj 工程。"""
    result = list_projects(directory, recursive=recursive)
    _emit({"ok": True, "count": len(result), "projects": result}, ctx.find_root().obj["use_json"])


@project_group.group("config")
def project_config_group() -> None:
    """查看或切换工程现有的编译配置和目标架构。"""


@project_config_group.command("list")
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False),
              help="准确的本地 .xcproj 路径。")
@click.pass_context
@handle_error
def project_config_list(ctx: click.Context, target_project: Path | None) -> None:
    """列出项目配置、架构、输出路径和当前选项。"""
    project_path = _project_path(ctx, str(target_project) if target_project else None)
    _emit({"ok": True, **project_core.list_configurations(project_path)}, ctx.find_root().obj["use_json"])


@project_config_group.command("set")
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False),
              help="准确的本地 .xcproj 路径。")
@click.option("--configuration", help="切换到工程内已定义的配置，例如 调试版 或 发布版。")
@click.option("--platform", type=click.Choice(["x86", "x64"]), help="切换到工程内已定义的目标架构。")
@click.pass_context
@handle_error
def project_config_set(ctx: click.Context, target_project: Path | None,
                       configuration: str | None, platform: str | None) -> None:
    """更新 .xcproj 的活动配置/架构；不会启动 IDE 或自动编译。"""
    if configuration is None and platform is None:
        raise ValueError("至少指定 --configuration 或 --platform。")
    project_path = _project_path(ctx, str(target_project) if target_project else None)
    obj = ctx.find_root().obj
    if _dry_plan(ctx, "project.config.set", project=project_path,
                 configuration=configuration, platform=platform):
        return
    result = project_core.set_configuration(project_path, configuration=configuration, platform=platform)
    _record(ctx, "project.config.set", project=project_path,
            before=result["before"], after=result["after"], changed=result["changed"])
    _emit(result, obj["use_json"])


@project_group.group("sources")
def project_sources_group() -> None:
    """列出工程内源码，或维护 .xcproj 的 codeExpand 登记。"""


@project_sources_group.command("list")
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False),
              help="准确的本地 .xcproj 路径。")
@click.pass_context
@handle_error
def project_sources_list(ctx: click.Context, target_project: Path | None) -> None:
    """列出工程中的 .xc/.xcs 文件和 codeExpand 登记状态。"""
    project_path = _project_path(ctx, str(target_project) if target_project else None)
    _emit({"ok": True, **project_core.list_project_sources(project_path)}, ctx.find_root().obj["use_json"])


@project_sources_group.command("add")
@click.argument("source_path")
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False),
              help="准确的本地 .xcproj 路径。")
@click.pass_context
@handle_error
def project_sources_add(ctx: click.Context, source_path: str, target_project: Path | None) -> None:
    """将工程内现有 .xc/.xcs 文件登记到工程树，不复制或删除源码。"""
    project_path = _project_path(ctx, str(target_project) if target_project else None)
    obj = ctx.find_root().obj
    if _dry_plan(ctx, "project.sources.add", project=project_path, source=source_path):
        return
    result = project_core.add_project_source(project_path, source_path)
    if result["added"]:
        _record(ctx, "project.sources.add", project=project_path, source=result["file"])
    _emit(result, obj["use_json"])


@project_sources_group.command("remove")
@click.argument("source_path")
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False),
              help="准确的本地 .xcproj 路径。")
@click.pass_context
@handle_error
def project_sources_remove(ctx: click.Context, source_path: str, target_project: Path | None) -> None:
    """取消源码的工程树登记；保留磁盘上的源码文件。"""
    project_path = _project_path(ctx, str(target_project) if target_project else None)
    obj = ctx.find_root().obj
    if _dry_plan(ctx, "project.sources.remove", project=project_path, source=source_path):
        return
    result = project_core.remove_project_source(project_path, source_path)
    if result["removed"]:
        _record(ctx, "project.sources.remove", project=project_path, source=result["file"])
    _emit(result, obj["use_json"])


@project_group.group("breakpoints")
def project_breakpoints_group() -> None:
    """读取或修改 .xcproj 文件中的源码断点元数据。"""


@project_breakpoints_group.command("list")
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False),
              help="准确的本地 .xcproj 路径。")
@click.pass_context
@handle_error
def project_breakpoints_list(ctx: click.Context, target_project: Path | None) -> None:
    """列出工程登记的断点，并核对源码行号范围。"""
    project_path = _project_path(ctx, str(target_project) if target_project else None)
    _emit({"ok": True, **project_core.list_project_breakpoints(project_path)}, ctx.find_root().obj["use_json"])


@project_breakpoints_group.command("add")
@click.argument("source_path")
@click.argument("line", type=click.IntRange(1))
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False),
              help="准确的本地 .xcproj 路径。")
@click.pass_context
@handle_error
def project_breakpoints_add(ctx: click.Context, source_path: str, line: int,
                            target_project: Path | None) -> None:
    """在工程内真实存在的源码行上添加一个断点记录。"""
    project_path = _project_path(ctx, str(target_project) if target_project else None)
    obj = ctx.find_root().obj
    if _dry_plan(ctx, "project.breakpoints.add", project=project_path, source=source_path, line=line):
        return
    result = project_core.set_project_breakpoint(project_path, source_path, line)
    if result["changed"]:
        _record(ctx, "project.breakpoints.add", project=project_path, source=result["file"], line=line)
    _emit(result, obj["use_json"])


@project_breakpoints_group.command("remove")
@click.argument("source_path")
@click.argument("line", type=click.IntRange(1))
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False),
              help="准确的本地 .xcproj 路径。")
@click.pass_context
@handle_error
def project_breakpoints_remove(ctx: click.Context, source_path: str, line: int,
                               target_project: Path | None) -> None:
    """移除工程 XML 中断点记录，不改动源码文件。"""
    project_path = _project_path(ctx, str(target_project) if target_project else None)
    obj = ctx.find_root().obj
    if _dry_plan(ctx, "project.breakpoints.remove", project=project_path, source=source_path, line=line):
        return
    result = project_core.set_project_breakpoint(project_path, source_path, line, remove=True)
    if result["changed"]:
        _record(ctx, "project.breakpoints.remove", project=project_path, source=result["file"], line=line)
    _emit(result, obj["use_json"])


@project_group.group("debug")
def project_debug_group() -> None:
    """查看、维护 .xcproj 保存的变量监视和源码书签。"""


@project_debug_group.command("list")
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False),
              help="准确的本地 .xcproj 路径。")
@click.pass_context
@handle_error
def project_debug_list(ctx: click.Context, target_project: Path | None) -> None:
    """列出工程保存的监视、书签和断点元数据。"""
    project_path = _project_path(ctx, str(target_project) if target_project else None)
    _emit({"ok": True, **project_core.list_project_debug_metadata(project_path)},
          ctx.find_root().obj["use_json"])


@project_debug_group.command("watch-add")
@click.argument("expression")
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False),
              help="准确的本地 .xcproj 路径。")
@click.pass_context
@handle_error
def project_debug_watch_add(ctx: click.Context, expression: str, target_project: Path | None) -> None:
    """向工程保存一个单行变量监视表达式，不执行表达式。"""
    project_path = _project_path(ctx, str(target_project) if target_project else None)
    obj = ctx.find_root().obj
    if _dry_plan(ctx, "project.debug.watch.add", project=project_path, expression=expression):
        return
    result = project_core.set_project_debug_item(project_path, "watches", expression)
    if result["changed"]:
        _record(ctx, "project.debug.watch.add", project=project_path, expression=expression)
    _emit(result, obj["use_json"])


@project_debug_group.command("watch-remove")
@click.argument("expression")
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False),
              help="准确的本地 .xcproj 路径。")
@click.pass_context
@handle_error
def project_debug_watch_remove(ctx: click.Context, expression: str, target_project: Path | None) -> None:
    """移除工程中保存的监视表达式。"""
    project_path = _project_path(ctx, str(target_project) if target_project else None)
    obj = ctx.find_root().obj
    if _dry_plan(ctx, "project.debug.watch.remove", project=project_path, expression=expression):
        return
    result = project_core.set_project_debug_item(project_path, "watches", expression, remove=True)
    if result["changed"]:
        _record(ctx, "project.debug.watch.remove", project=project_path, expression=expression)
    _emit(result, obj["use_json"])


@project_debug_group.command("bookmark-add")
@click.argument("source_path")
@click.argument("line", type=click.IntRange(1))
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False),
              help="准确的本地 .xcproj 路径。")
@click.pass_context
@handle_error
def project_debug_bookmark_add(ctx: click.Context, source_path: str, line: int,
                               target_project: Path | None) -> None:
    """为工程内的炫语言源码行添加书签元数据。"""
    project_path = _project_path(ctx, str(target_project) if target_project else None)
    obj = ctx.find_root().obj
    if _dry_plan(ctx, "project.debug.bookmark.add", project=project_path, source=source_path, line=line):
        return
    result = project_core.set_project_debug_item(project_path, "bookmarks", source_path, line=line)
    if result["changed"]:
        _record(ctx, "project.debug.bookmark.add", project=project_path, source=result["file"], line=line)
    _emit(result, obj["use_json"])


@project_debug_group.command("bookmark-remove")
@click.argument("source_path")
@click.argument("line", type=click.IntRange(1))
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False),
              help="准确的本地 .xcproj 路径。")
@click.pass_context
@handle_error
def project_debug_bookmark_remove(ctx: click.Context, source_path: str, line: int,
                                  target_project: Path | None) -> None:
    """移除工程中源码行上的书签元数据。"""
    project_path = _project_path(ctx, str(target_project) if target_project else None)
    obj = ctx.find_root().obj
    if _dry_plan(ctx, "project.debug.bookmark.remove", project=project_path, source=source_path, line=line):
        return
    result = project_core.set_project_debug_item(project_path, "bookmarks", source_path, line=line, remove=True)
    if result["changed"]:
        _record(ctx, "project.debug.bookmark.remove", project=project_path, source=result["file"], line=line)
    _emit(result, obj["use_json"])


@project_group.group("debug")
def project_debug_group() -> None:
    """查看、维护 .xcproj 保存的变量监视和源码书签。"""


@project_debug_group.command("list")
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False),
              help="准确的本地 .xcproj 路径。")
@click.pass_context
@handle_error
def project_debug_list(ctx: click.Context, target_project: Path | None) -> None:
    """列出工程保存的监视、书签和断点元数据。"""
    project_path = _project_path(ctx, str(target_project) if target_project else None)
    _emit({"ok": True, **project_core.list_project_debug_metadata(project_path)},
          ctx.find_root().obj["use_json"])


@project_debug_group.command("watch-add")
@click.argument("expression")
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False),
              help="准确的本地 .xcproj 路径。")
@click.pass_context
@handle_error
def project_debug_watch_add(ctx: click.Context, expression: str, target_project: Path | None) -> None:
    """向工程保存一个单行变量监视表达式，不执行表达式。"""
    project_path = _project_path(ctx, str(target_project) if target_project else None)
    obj = ctx.find_root().obj
    if _dry_plan(ctx, "project.debug.watch.add", project=project_path, expression=expression):
        return
    result = project_core.set_project_debug_item(project_path, "watches", expression)
    if result["changed"]:
        _record(ctx, "project.debug.watch.add", project=project_path, expression=expression)
    _emit(result, obj["use_json"])


@project_debug_group.command("watch-remove")
@click.argument("expression")
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False),
              help="准确的本地 .xcproj 路径。")
@click.pass_context
@handle_error
def project_debug_watch_remove(ctx: click.Context, expression: str, target_project: Path | None) -> None:
    """移除工程中保存的监视表达式。"""
    project_path = _project_path(ctx, str(target_project) if target_project else None)
    obj = ctx.find_root().obj
    if _dry_plan(ctx, "project.debug.watch.remove", project=project_path, expression=expression):
        return
    result = project_core.set_project_debug_item(project_path, "watches", expression, remove=True)
    if result["changed"]:
        _record(ctx, "project.debug.watch.remove", project=project_path, expression=expression)
    _emit(result, obj["use_json"])


@project_debug_group.command("bookmark-add")
@click.argument("source_path")
@click.argument("line", type=click.IntRange(1))
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False),
              help="准确的本地 .xcproj 路径。")
@click.pass_context
@handle_error
def project_debug_bookmark_add(ctx: click.Context, source_path: str, line: int,
                               target_project: Path | None) -> None:
    """为工程内的炫语言源码行添加书签元数据。"""
    project_path = _project_path(ctx, str(target_project) if target_project else None)
    obj = ctx.find_root().obj
    if _dry_plan(ctx, "project.debug.bookmark.add", project=project_path, source=source_path, line=line):
        return
    result = project_core.set_project_debug_item(project_path, "bookmarks", source_path, line=line)
    if result["changed"]:
        _record(ctx, "project.debug.bookmark.add", project=project_path, source=result["file"], line=line)
    _emit(result, obj["use_json"])


@project_debug_group.command("bookmark-remove")
@click.argument("source_path")
@click.argument("line", type=click.IntRange(1))
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False),
              help="准确的本地 .xcproj 路径。")
@click.pass_context
@handle_error
def project_debug_bookmark_remove(ctx: click.Context, source_path: str, line: int,
                                  target_project: Path | None) -> None:
    """移除工程中源码行上的书签元数据。"""
    project_path = _project_path(ctx, str(target_project) if target_project else None)
    obj = ctx.find_root().obj
    if _dry_plan(ctx, "project.debug.bookmark.remove", project=project_path, source=source_path, line=line):
        return
    result = project_core.set_project_debug_item(project_path, "bookmarks", source_path, line=line, remove=True)
    if result["changed"]:
        _record(ctx, "project.debug.bookmark.remove", project=project_path, source=result["file"], line=line)
    _emit(result, obj["use_json"])


@project_group.group("template")
def project_template_group() -> None:
    """浏览炫彩 IDE 自带的炫语言工程模板。"""


@project_template_group.command("list")
@click.argument("query", required=False, default="")
@click.option("--limit", type=click.IntRange(1, 2000), default=200, show_default=True)
@click.pass_context
@handle_error
def project_template_list(ctx: click.Context, query: str, limit: int) -> None:
    """按模板相对 ID 或名称搜索本地工程模板。"""
    _emit(templates_core.list_templates(ide_root=ctx.find_root().obj["ide_root"],
                                        query=query, limit=limit),
          ctx.find_root().obj["use_json"])


@project_group.command("doctor")
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False), help="完整且准确的目标工程路径。")
@click.option("--include-generated", is_flag=True, help="包括构建输出目录中的布局 XML。")
@click.pass_context
@handle_error
def project_doctor(ctx: click.Context, target_project: Path | None, include_generated: bool) -> None:
    """体检工程源码登记、模块引用、布局 XML 和 UI ZIP。"""
    project_path = _project_path(ctx, str(target_project) if target_project else None)
    if _dry_plan(ctx, "project.doctor", project=project_path, include_generated=include_generated):
        return
    result = doctor_core.inspect_project_health(project_path, ide_root=ctx.find_root().obj["ide_root"],
                                                include_generated=include_generated)
    _emit(result, ctx.find_root().obj["use_json"])
    if not result["ok"]:
        raise click.exceptions.Exit(1)


@project_group.command("open")
@click.argument("project_file", type=click.Path(path_type=Path, dir_okay=False))
@click.pass_context
@handle_error
def project_open(ctx: click.Context, project_file: Path) -> None:
    """选择本地 CLI 会话的活动工程；不会切换任何 GUI 窗口。"""
    obj = ctx.find_root().obj
    info = inspect_project(project_file)
    if obj["dry_run"]:
        _emit({"ok": True, "dry_run": True, "action": "project.select", "project": info["project_file"]}, obj["use_json"])
        return
    obj["session"].select(project=info["project_file"], action="project.open-selected")
    _record(ctx, "project.open-selected", project=info["project_file"])
    _emit({"ok": True, "selected": True, "note": "已选择本地 CLI 会话工程；不会远程控制 IDE 窗口。", **info}, obj["use_json"])


@cli.group("editor")
def editor_group() -> None:
    """直接读取或编辑本地工程、模块库中的文本文件。"""


@editor_group.command("read")
@click.argument("path", type=click.Path(path_type=Path, dir_okay=False))
@click.option("--allow-outside-project", is_flag=True, help="明确允许读取工程或所选 IDE 安装目录之外的文件。")
@click.pass_context
@handle_error
def editor_read(ctx: click.Context, path: Path, allow_outside_project: bool) -> None:
    target_project = _project_path(ctx) if ctx.obj["project"] else None
    if _dry_plan(ctx, "editor.read", project=target_project, path=str(path.resolve())):
        return
    if ctx.obj["dry_run"]:
        file_path = files_core.validate_path(path, project=target_project, ide_root=ctx.obj["ide_root"],
                                             allow_outside=allow_outside_project)
        if not file_path.is_file():
            raise FileNotFoundError(f"文本文件不存在：{file_path}")
        _emit({"ok": True, "dry_run": True, "action": "editor.read", "path": str(file_path)},
              ctx.obj["use_json"])
        return
    result = files_core.read_file(path, project=target_project, ide_root=ctx.obj["ide_root"],
                                  allow_outside=allow_outside_project)
    _emit({"ok": True, **result}, ctx.obj["use_json"])


@editor_group.command("write")
@click.argument("path", type=click.Path(path_type=Path, dir_okay=False))
@click.argument("input_file", type=click.Path(path_type=Path, dir_okay=False))
@click.option("--no-bom", is_flag=True, help="强制使用无 BOM 的 UTF-8；否则保留目标文件的 BOM 规则。")
@click.option("--allow-outside-project", is_flag=True, help="明确允许写入工程或所选 IDE 安装目录之外的文件。")
@click.pass_context
@handle_error
def editor_write(ctx: click.Context, path: Path, input_file: Path, no_bom: bool, allow_outside_project: bool) -> None:
    target_project = _project_path(ctx) if ctx.obj["project"] else None
    file_path = files_core.validate_path(path, project=target_project, ide_root=ctx.obj["ide_root"],
                                         allow_outside=allow_outside_project)
    input_path = input_file.expanduser().resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"输入文本文件不存在：{input_path}")
    raw_input = input_path.read_bytes()
    try:
        content = raw_input.decode("utf-8-sig")
    except UnicodeDecodeError:
        content = raw_input.decode("gb18030")
    if ctx.obj["dry_run"]:
        _emit({"ok": True, "dry_run": True, "action": "editor.write", "path": str(file_path),
               "input_file": str(input_file), "bytes": len(content.encode("utf-8")),
               "target_sha256": hashlib.sha256(content.encode()).hexdigest()}, ctx.obj["use_json"])
        return
    result = files_core.write_file(file_path, content, project=target_project,
                                   ide_root=ctx.obj["ide_root"],
                                   allow_outside=allow_outside_project, no_bom=no_bom)
    _record(ctx, "editor.write", path=str(file_path), sha256=result["sha256"])
    _emit({"ok": True, **result}, ctx.obj["use_json"])


@cli.group("interface")
def interface_group() -> None:
    """查看和验证炫彩窗口布局 XML、resource.res 与 UI ZIP。"""


@interface_group.command("list")
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False), help="准确的本地 .xcproj 路径。")
@click.option("--include-generated", is_flag=True, help="包括构建输出目录中的 XML。")
@click.pass_context
@handle_error
def interface_list(ctx: click.Context, target_project: Path | None, include_generated: bool) -> None:
    """列出工程内真实窗口/面板/列表模板布局和 UI ZIP。"""
    project_path = _project_path(ctx, str(target_project) if target_project else None)
    result = interface_core.inspect_interface(project_path, include_generated=include_generated)
    _emit({"ok": True, "project": result["project"], "layoutCount": result["layoutCount"],
           "uiZipCount": result["uiZipCount"], "layouts": result["layouts"],
           "uiArchives": result["uiArchives"]}, ctx.find_root().obj["use_json"])


@interface_group.command("check")
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False), help="准确的本地 .xcproj 路径。")
@click.option("--include-generated", is_flag=True, help="包括构建输出目录中的 XML。")
@click.pass_context
@handle_error
def interface_check(ctx: click.Context, target_project: Path | None, include_generated: bool) -> None:
    """校验炫彩多根布局 XML 和 UI ZIP 归档。"""
    project_path = _project_path(ctx, str(target_project) if target_project else None)
    result = interface_core.inspect_interface(project_path, include_generated=include_generated)
    _emit(result, ctx.find_root().obj["use_json"])
    if not result["ok"]:
        raise click.exceptions.Exit(1)


def _inspection_options(ctx: click.Context) -> dict:
    return {"project": ctx.obj["project"], "ide_root": ctx.obj["ide_root"]}


@interface_group.command("nodes")
@click.argument("path", type=click.Path(path_type=Path, dir_okay=False))
@click.argument("query", required=False, default="")
@click.option("--member", help="PATH 为 ZIP 时，指定 archive list 返回的准确成员 ID。")
@click.option("--tag", help="准确 XML 标签，例如 buttonUI。")
@click.option("--attribute", help="要求节点具有该属性，例如 name、id、itemID。")
@click.option("--value", help="与 --attribute 配合，对原生属性值做准确匹配。")
@click.option("--limit", type=click.IntRange(1, 2000), default=100, show_default=True)
@click.option("--offset", type=click.IntRange(min=0), default=0, show_default=True)
@click.pass_context
@handle_error
def interface_nodes(ctx, path, query, member, tag, attribute, value, limit, offset):
    """读取布局节点、父子位置、原生属性和数据绑定；不计算运行时几何。"""
    _emit(ui_data_core.list_nodes(path, member=member, query=query, tag=tag, attribute=attribute,
                                 value=value, limit=limit, offset=offset, **_inspection_options(ctx)), ctx.obj["use_json"])


@interface_group.command("node")
@click.argument("path", type=click.Path(path_type=Path, dir_okay=False))
@click.argument("identifier")
@click.option("--member", help="布局位于 ZIP 中时指定准确成员 ID。")
@click.pass_context
@handle_error
def interface_node(ctx, path, identifier, member):
    """按 nodes 返回的位置 ID 读取节点与完整子树 XML。"""
    _emit(ui_data_core.show_node(path, identifier, member=member, **_inspection_options(ctx)), ctx.obj["use_json"])


@cli.group("resource")
def resource_group():
    """检查显式指定的资源 XML，支持 resource.res 和 WmUi.res 等命名资源表。"""


@resource_group.command("list")
@click.argument("path", type=click.Path(path_type=Path, dir_okay=False))
@click.argument("query", required=False, default="")
@click.option("--member", help="资源表位于 ZIP 中时指定准确成员 ID。")
@click.option("--kind", help="原生资源节名，例如 type_image、type_font、type_bkInfo。")
@click.option("--limit", type=click.IntRange(1, 2000), default=100, show_default=True)
@click.option("--offset", type=click.IntRange(min=0), default=0, show_default=True)
@click.pass_context
@handle_error
def resource_list(ctx, path, query, member, kind, limit, offset):
    """列出资源条目、重复名称、原始属性和图片/字体文件位置。"""
    _emit(ui_data_core.list_resources(path, member=member, query=query, kind=kind, limit=limit,
                                     offset=offset, **_inspection_options(ctx)), ctx.obj["use_json"])


@resource_group.command("show")
@click.argument("path", type=click.Path(path_type=Path, dir_okay=False))
@click.argument("identifier")
@click.option("--member", help="资源表位于 ZIP 中时指定准确成员 ID。")
@click.pass_context
@handle_error
def resource_show(ctx, path, identifier, member):
    """按 list 返回的准确位置 ID 读取资源 XML，名称相同也不会自动择一。"""
    _emit(ui_data_core.show_resource(path, identifier, member=member, **_inspection_options(ctx)), ctx.obj["use_json"])


@cli.group("archive")
def archive_group():
    """检查 UI ZIP 目录、读取文本成员和原样导出单个成员。"""


@archive_group.command("list")
@click.argument("path", type=click.Path(path_type=Path, dir_okay=False))
@click.argument("query", required=False, default="")
@click.option("--limit", type=click.IntRange(1, 2000), default=100, show_default=True)
@click.option("--offset", type=click.IntRange(min=0), default=0, show_default=True)
@click.pass_context
@handle_error
def archive_list(ctx, path, query, limit, offset):
    """列出准确成员 ID、大小、压缩信息与路径问题；目录查询不验证全部 CRC。"""
    _emit(archive_core.list_archive(path, query=query, limit=limit, offset=offset,
                                   **_inspection_options(ctx)), ctx.obj["use_json"])


@archive_group.command("read")
@click.argument("path", type=click.Path(path_type=Path, dir_okay=False))
@click.argument("member")
@click.pass_context
@handle_error
def archive_read(ctx, path, member):
    """读取一个准确文本成员并校验 CRC；二进制请使用 export。"""
    _emit(archive_core.read_member(path, member, **_inspection_options(ctx)), ctx.obj["use_json"])


@archive_group.command("export")
@click.argument("path", type=click.Path(path_type=Path, dir_okay=False))
@click.argument("member")
@click.argument("output", type=click.Path(path_type=Path, dir_okay=False))
@click.pass_context
@handle_error
def archive_export(ctx, path, member, output):
    """原样导出单个成员到显式新文件；不覆盖目标或写入正式安装。"""
    result = archive_core.export_member(path, member, output, dry_run=ctx.obj["dry_run"], **_inspection_options(ctx))
    if not ctx.obj["dry_run"]:
        _record(ctx, "archive.export", path=result["destination"], sha256=result["sha256"])
    _emit(result, ctx.obj["use_json"])


@cli.group("module")
def module_group() -> None:
    """查询、搜索真实模块库，并按要求修改工程模块引用。"""


@module_group.command("list")
@click.option("--limit", type=click.IntRange(1, 10000), default=80, show_default=True)
@click.option("--project-only", is_flag=True, help="只列出当前工程引用的模块。")
@click.pass_context
@handle_error
def module_list(ctx: click.Context, limit: int, project_only: bool) -> None:
    if _dry_plan(ctx, "module.list", limit=limit, project_only=project_only):
        return
    project = _project_path(ctx) if ctx.obj["project"] else None
    _emit(modules_core.list_modules(ide_root=ctx.obj["ide_root"], project_file=project,
                                    limit=limit, project_only=project_only), ctx.obj["use_json"])


@module_group.command("search")
@click.argument("query")
@click.option("--limit", type=click.IntRange(1, 10000), default=40, show_default=True)
@click.option("--depends-on", help="查找依赖这个模块名称的已安装模块。")
@click.pass_context
@handle_error
def module_search(ctx: click.Context, query: str, limit: int, depends_on: str | None) -> None:
    if _dry_plan(ctx, "module.search", query=query, limit=limit, depends_on=depends_on):
        return
    project = _project_path(ctx) if ctx.obj["project"] else None
    _emit(modules_core.search_modules(query, ide_root=ctx.obj["ide_root"], project_file=project,
                                      limit=limit, depends_on=depends_on), ctx.obj["use_json"])


@module_group.command("add")
@click.option("--file", "module_file", required=True, help="已安装模块的准确头文件名，例如 module_xcgui.h。")
@click.option("--with-dependencies", is_flag=True, help="按依赖顺序添加完整且无缺失/歧义的依赖模块集合。")
@click.option("--name", "module_name", help="可选的显示别名；不会解析为仅存在于工程中的文件路径。")
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False), help="完整且准确的目标工程路径。")
@click.pass_context
@handle_error
def module_add(ctx: click.Context, module_file: str, with_dependencies: bool,
               module_name: str | None, target_project: Path | None) -> None:
    if ctx.obj["dry_run"]:
        _emit({"ok": True, "dry_run": True, "action": "module.add", "file": module_file,
               "with_dependencies": with_dependencies}, ctx.obj["use_json"])
        return
    project_path = _guard_project(ctx, str(target_project) if target_project else None)
    result = modules_core.add_modules(project_path, [module_file], ide_root=ctx.obj["ide_root"],
                                      with_dependencies=with_dependencies, name=module_name)
    _record(ctx, "module.add", file=Path(module_file).name, project=project_path,
            with_dependencies=with_dependencies, added=result["added"])
    _emit({"ok": True, **result}, ctx.obj["use_json"])


@module_group.command("dependencies")
@click.argument("module_file")
@click.pass_context
@handle_error
def module_dependencies(ctx: click.Context, module_file: str) -> None:
    """只读解析本地模块头文件的直接和递归依赖。"""
    result = modules_core.plan_module_dependencies(module_file, ide_root=ctx.find_root().obj["ide_root"])
    _emit(result, ctx.find_root().obj["use_json"])
    if not result["ok"]:
        raise click.exceptions.Exit(1)


@module_group.command("remove")
@click.option("--file", "module_file", required=True, help="从工程 <modules> 块移除的准确模块头文件名。")
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False), help="完整且准确的目标工程路径。")
@click.pass_context
@handle_error
def module_remove(ctx: click.Context, module_file: str, target_project: Path | None) -> None:
    if ctx.obj["dry_run"]:
        _emit({"ok": True, "dry_run": True, "action": "module.remove", "file": module_file}, ctx.obj["use_json"])
        return
    project_path = _guard_project(ctx, str(target_project) if target_project else None)
    result = modules_core.remove_module(project_path, module_file)
    _record(ctx, "module.remove", file=Path(module_file).name, project=project_path)
    _emit({"ok": True, **result}, ctx.obj["use_json"])


@cli.command("build")
@click.option("--diagnostics", is_flag=True, help="在隔离 IDE 中编译/加载本地输出桥接，读取真实编译诊断；需要 MSVC。")
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False), help="完整 .xcproj 路径；未指定时使用全局 --project 或会话中的工程。")
@click.option("--timeout", type=click.IntRange(30, 1200), default=240, show_default=True)
@click.pass_context
@handle_error
def build_command(ctx: click.Context, target_project: Path | None, timeout: int, diagnostics: bool) -> None:
    obj = ctx.find_root().obj
    project_to_build = target_project or (Path(obj["project"]) if obj["project"] else None)
    if project_to_build is None and obj["session"].project:
        project_to_build = Path(obj["session"].project)
    if project_to_build is None:
        raise ValueError("Pass --project with the full path of the project the native IDE should compile.")
    path = str(Path(inspect_project(project_to_build)["project_file"]).resolve())
    if obj["dry_run"]:
        _emit({"ok": True, "dry_run": True, "action": "build", "project": path,
               "compiler": "本机炫彩 IDE GUI + F7", "diagnostics": diagnostics}, obj["use_json"])
        return
    obj["session"].select(project=path, action="build.target")
    result = build_core.build_project(path, ide_root=obj["ide_root"], timeout=timeout, diagnostics=diagnostics)
    _record(ctx, "build", project=path, ok=result["ok"], exe=result["exe"])
    _emit(result, obj["use_json"])
    if not result["ok"]:
        raise click.exceptions.Exit(1)


@cli.group("runtime")
def runtime_group() -> None:
    """在后台独立桌面启动 EXE，捕获调试事件或执行 XCGUI 交互验收。"""


def _runtime_options(function: Callable[..., Any]) -> Callable[..., Any]:
    for option in (
        click.option("--exe", type=click.Path(path_type=Path, dir_okay=False), required=True, help="本次启动并测试的准确 EXE。"),
        click.option("--arg", "arguments", multiple=True, help="程序参数，可重复；每项按原样传递，不经过 shell。"),
        click.option("--cwd", type=click.Path(path_type=Path, file_okay=False), help="程序工作目录；默认 EXE 所在目录。"),
        click.option("--output", type=click.Path(path_type=Path, file_okay=False), required=True, help="报告根目录；每次创建唯一 run-* 子目录。"),
        click.option("--timeout", type=click.FloatRange(0.1, 1200), default=30.0, show_default=True),
    ):
        function = option(function)
    return function


@runtime_group.command("run")
@_runtime_options
@click.option("--expected-exit-code", type=click.IntRange(0, 0xFFFFFFFF), default=0)
@click.pass_context
@handle_error
def runtime_run(ctx: click.Context, exe: Path, arguments: tuple[str, ...], cwd: Path | None,
                output: Path, timeout: float, expected_exit_code: int) -> None:
    """捕获 OutputDebugString、异常、stdout/stderr 与退出码；超时终止本次进程树。"""
    if _dry_plan(ctx, "runtime.run", executable=str(exe), arguments=list(arguments), output=str(output)):
        return
    result = runtime_core.execute(exe, arguments=list(arguments), cwd=cwd, output=output,
                                  timeout=timeout, expected_exit_code=expected_exit_code)
    _record(ctx, "runtime.run", report=result["report"], ok=result["ok"])
    _emit(result, ctx.obj["use_json"])
    if not result["ok"]:
        raise click.exceptions.Exit(1)


@runtime_group.command("test")
@click.argument("scenario", type=click.Path(path_type=Path, dir_okay=False, exists=True))
@_runtime_options
@click.pass_context
@handle_error
def runtime_test(ctx: click.Context, scenario: Path, exe: Path, arguments: tuple[str, ...],
                 cwd: Path | None, output: Path, timeout: float) -> None:
    """执行后台 JSON 场景：原生消息/状态断言/GDI 截图；程序需接入测试适配器。"""
    plan = runtime_core.load_scenario(scenario)
    if _dry_plan(ctx, "runtime.test", executable=str(exe), scenario=plan, output=str(output)):
        return
    result = runtime_core.execute(exe, arguments=list(arguments), cwd=cwd, output=output,
                                  timeout=timeout, scenario=plan)
    _record(ctx, "runtime.test", report=result["report"], ok=result["ok"])
    _emit(result, ctx.obj["use_json"])
    if not result["ok"]:
        raise click.exceptions.Exit(1)


@cli.group("preview")
def preview_group() -> None:
    """发布本地工程文件检查预览，或读取已有预览包。"""


@preview_group.command("recipes")
@click.pass_context
def preview_recipes(ctx: click.Context) -> None:
    """列出可信的检查配方；不伪造内容，也不截取 GUI 窗口图像。"""
    _emit({"ok": True, "software": "xcide", "protocol_version": "preview-bundle/v1",
           "previews_compilation": False, "recipes": preview_core.recipe_names()}, ctx.find_root().obj["use_json"])


@preview_group.command("capture")
@click.option("--recipe", type=click.Choice(["project", "executable"]), default="project", show_default=True)
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False), help="准确的本地 .xcproj 路径。")
@click.option("--root", "root_dir", type=click.Path(path_type=Path, file_okay=False), help="可选的隔离预览包根目录。")
@click.option("--force", is_flag=True, help="忽略缓存并重新扫描本地工程状态，发布新的不可变预览包。")
@click.pass_context
@handle_error
def preview_capture(ctx: click.Context, recipe: str, target_project: Path | None,
                    root_dir: Path | None, force: bool) -> None:
    obj = ctx.find_root().obj
    requested = str(target_project) if target_project else None
    if _dry_plan(ctx, "preview.capture", recipe=recipe, project=requested or obj["project"]):
        return
    project_path = _guard_project(ctx, requested)
    result = preview_core.capture(recipe=recipe, project_path=project_path, ide_root=obj["ide_root"],
                                  root_dir=str(root_dir.resolve()) if root_dir else None, force=force)
    _record(ctx, "preview.capture", recipe=recipe, bundle_id=result.get("bundle_id"), cached=result.get("cached"))
    _emit(result, obj["use_json"])


@preview_group.command("latest")
@click.option("--recipe", type=click.Choice(["project", "executable"]))
@click.option("--project", "target_project", type=click.Path(path_type=Path, dir_okay=False), help="要在已发布预览索引中查找的准确源工程。")
@click.option("--root", "root_dir", type=click.Path(path_type=Path, file_okay=False), help="可选的预览包根目录。")
@click.pass_context
@handle_error
def preview_latest(ctx: click.Context, recipe: str | None,
                   target_project: Path | None, root_dir: Path | None) -> None:
    """读取最新本地预览清单；不会打开 IDE 或重新编译。"""
    path = _project_path(ctx, str(target_project) if target_project else None)
    _emit(preview_core.latest(recipe=recipe, project_path=path,
                              root_dir=str(root_dir.resolve()) if root_dir else None),
          ctx.find_root().obj["use_json"])


@cli.group("session")
def session_group() -> None:
    """查看持久会话，或安全地撤销/重做本地工程选择。"""


@session_group.command("status")
@click.pass_context
def session_status(ctx: click.Context) -> None:
    _emit({"ok": True, **ctx.find_root().obj["session"].summary()}, ctx.find_root().obj["use_json"])


@session_group.command("history")
@click.option("--limit", type=click.IntRange(1, 50), default=20, show_default=True)
@click.pass_context
def session_history(ctx: click.Context, limit: int) -> None:
    _emit({"ok": True, "project": ctx.find_root().obj["session"].project,
           "entries": ctx.find_root().obj["session"].history(limit)}, ctx.find_root().obj["use_json"])


@session_group.command("undo")
@click.pass_context
@handle_error
def session_undo(ctx: click.Context) -> None:
    obj = ctx.find_root().obj
    if obj["dry_run"]:
        _emit({"ok": True, "dry_run": True, "action": "session.undo"}, obj["use_json"])
    else:
        _emit({"ok": True, **obj["session"].undo()}, obj["use_json"])


@session_group.command("redo")
@click.pass_context
@handle_error
def session_redo(ctx: click.Context) -> None:
    obj = ctx.find_root().obj
    if obj["dry_run"]:
        _emit({"ok": True, "dry_run": True, "action": "session.redo"}, obj["use_json"])
    else:
        _emit({"ok": True, **obj["session"].redo()}, obj["use_json"])


@cli.group("ide")
@click.option("--instance", type=click.Path(path_type=Path, file_okay=False), help="ide start 返回的会话目录。")
@click.pass_context
def ide_group(ctx: click.Context, instance: Path | None) -> None:
    """持续运行的后台 IDE 会话；通过原生桥接调用 xc_* 工具，无需 MCP。"""
    ctx.ensure_object(dict)
    ctx.obj["ide_instance"] = instance


def _ide_instance(ctx: click.Context) -> Path:
    location = ctx.obj.get("ide_instance")
    if location is None:
        raise ValueError("请在 ide 后指定 --instance 会话目录；先用 ide start 创建。")
    return location


@ide_group.command("tools")
@handle_error
def ide_tools_command() -> None:
    """列出全部兼容工具、参数 schema、写入属性与行为差异。"""
    ctx = click.get_current_context()
    _emit(ide_tools.catalog(), ctx.find_root().obj["use_json"])


@ide_group.command("start")
@click.option("--directory", type=click.Path(path_type=Path, file_okay=False), help="新建的会话目录；已有目录不会覆盖。")
@click.option("--timeout", type=click.FloatRange(5, 180), default=120, show_default=True)
@click.option("--idle-timeout", type=click.FloatRange(10, 86400), default=1800, show_default=True, help="空闲后自动关闭 IDE，单位秒。")
@click.pass_context
@handle_error
def ide_start(ctx: click.Context, directory: Path | None, timeout: float, idle_timeout: float) -> None:
    """创建独立 Windows 桌面和私有 IDE，保留到 stop 或空闲超时。"""
    obj = ctx.find_root().obj
    project_file = _project_path(ctx)
    if _dry_plan(ctx, "ide.start", project=project_file, directory=directory, idle_timeout=idle_timeout):
        return
    result = ide_core.start(project_file, ide_root=obj["ide_root"], directory=directory,
                            timeout=timeout, idle_timeout=idle_timeout)
    _record(ctx, "ide.start", directory=result["directory"], pid=result["pid"])
    _emit(result, obj["use_json"])


@ide_group.command("list")
@click.option("--root", type=click.Path(path_type=Path, file_okay=False), help="查找此目录下的会话；默认用户应用数据目录。")
@click.pass_context
@handle_error
def ide_list(ctx: click.Context, root: Path | None) -> None:
    """发现后台会话，并核对进程身份。"""
    _emit(ide_core.instances(root), ctx.find_root().obj["use_json"])


@ide_group.command("call")
@click.argument("tool", type=click.Choice(list(ide_tools.TOOLS)))
@click.option("--args-json", default=None, help="JSON 参数对象。Windows 下推荐 --args-file。")
@click.option("--args-file", type=click.Path(exists=True, dir_okay=False, path_type=Path), help="UTF-8 JSON 参数文件。")
@click.option("--timeout", type=click.FloatRange(.1, 180), default=15, show_default=True)
@click.pass_context
@handle_error
def ide_call(ctx: click.Context, tool: str, args_json: str | None, args_file: Path | None, timeout: float) -> None:
    """按旧 xc_* 工具名调用本地实现；不连接 MCP。"""
    if args_json is not None and args_file is not None:
        raise ValueError("--args-json 和 --args-file 只能选择一个。")
    if args_file is not None:
        if args_file.stat().st_size > ide_core.MAX_MESSAGE:
            raise ValueError("参数文件超过大小上限。")
        args_json = args_file.read_text(encoding="utf-8-sig")
    args = ide_tools.validate(tool, json.loads(args_json or "{}"))
    location = _ide_instance(ctx)
    if _dry_plan(ctx, "ide.call", tool=tool, instance=location, arguments=args,
                 mutates=ide_tools.TOOLS[tool]["mutates"]):
        return
    result = ide_tools.call(location, tool, args, timeout=timeout)
    if ide_tools.TOOLS[tool]["mutates"]:
        _record(ctx, "ide.call", tool=tool, instance=str(location), ok=result.get("ok"))
    _emit(result, ctx.find_root().obj["use_json"])
    if not result.get("ok"):
        raise click.exceptions.Exit(1)


@ide_group.command("stop")
@click.pass_context
@handle_error
def ide_stop(ctx: click.Context) -> None:
    """关闭本次私有 IDE 和子进程，清理临时 IDE 副本。"""
    location = _ide_instance(ctx)
    if _dry_plan(ctx, "ide.stop", instance=location):
        return
    result = ide_core.stop(location)
    _record(ctx, "ide.stop", instance=str(location))
    _emit(result, ctx.find_root().obj["use_json"])
    if not result.get("ok"):
        raise click.exceptions.Exit(1)


def main() -> None:
    """Click 单次命令和 REPL 共用的控制台入口。"""
    cli()


if __name__ == "__main__":
    main()
