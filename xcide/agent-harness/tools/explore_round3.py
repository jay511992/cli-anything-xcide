"""Replay 50 native-file investigations, with explicit questions and hashed evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from cli_anything.xcide.core import archive, ui_data


def explore(ide: Path):
    cli = shutil.which("cli-anything-xcide")
    if not cli:
        raise RuntimeError("Install the CLI first")
    hashes = {}
    cache = {}
    rounds = []
    session = Path(tempfile.gettempdir()) / ("xcide-round3-" + uuid.uuid4().hex + ".json")
    calls = []
    base = [cli, "--json", "--dry-run", "--ide", str(ide), "--session-file", str(session)]

    def read(path):
        path = Path(path).resolve()
        if not path.is_relative_to(ide):
            raise ValueError(f"Source outside installation: {path}")
        if path not in cache:
            raw = path.read_bytes()
            cache[path] = raw
            hashes[str(path)] = hashlib.sha256(raw).hexdigest()
        return cache[path]

    def relative(path):
        return Path(path).relative_to(ide).as_posix()

    def record(question, sources, facts, conclusion, implemented=False):
        rounds.append({"round": len(rounds) + 1, "question": question,
                       "sources": [relative(s) for s in sources], "facts": facts,
                       "conclusion": conclusion, "status": "implemented" if implemented else "observed"})

    def run(args):
        command = base + args
        proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=True, timeout=30)
        result = json.loads(proc.stdout)
        if not result.get("ok"):
            raise AssertionError(result)
        calls.append({"args": args, "dry_run": True, "ok": True})
        return result

    config = ide / "data/config/config.config"
    read(config)
    skip = {"debug", "debug64", "release", "release64", "obj", ".git", ".cli-anything", "__pycache__"}
    corpus = []
    roots = [ide / p for p in ("data/示例", "data/template", "data/xml", "例子/炫彩界面AI项目", "例子/音量控制")]
    for root in roots:
        for directory, dirs, names in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d.casefold() not in skip and not (Path(directory) / d).is_symlink())
            corpus.extend(Path(directory) / name for name in sorted(names)
                          if Path(name).suffix.casefold() in {".xml", ".res", ".xcproj", ".css"}
                          or name.casefold() == "ui_zip.zip")
    res_paths = [p for p in corpus if p.suffix.casefold() == ".res"]
    resources = [(p, ET.fromstring(read(p))) for p in res_paths]
    def resource_leaves(section):
        for node in section:
            if node.tag == "folder":
                yield from resource_leaves(node)
            else:
                yield node

    entries = [(p, section.tag, n) for p, root in resources for section in root for n in resource_leaves(section)]
    images = [(p, n) for p, kind, n in entries if kind == "type_image"]
    fonts = [(p, n) for p, kind, n in entries if kind == "type_font"]
    records = {p: ui_data.resource_records(p, ide_root=ide) for p in res_paths}

    record("图片加载方式和缩放样式是否统一？", res_paths,
           {"images": len(images), "load_types": dict(Counter(n.get("loadType", "(absent)") for _, n in images)),
            "styles": dict(Counter(n.get("style", "(absent)") for _, n in images))},
           "资源命令保留 loadType/style；不能把所有图片都按同一种缩放方式导入。", True)
    nine = [(p, n) for p, n in images if n.get("style") == "image9" or n.get("rect9")]
    record("九宫图片还需要哪些原生参数？", sorted({p for p, _ in nine}),
           {"count": len(nine), "rect9_values": dict(Counter(n.get("rect9", "(absent)") for _, n in nine))},
           "rect9 必须与图片一起保留；本轮只展示，不重算切片边距。", True)
    svg = [(p, n) for p, n in images if n.get("value", "").lower().endswith(".svg")]
    record("SVG 是否只有文件路径？", sorted({p for p, _ in svg}),
           {"count": len(svg), "attribute_keys": sorted({k for _, n in svg for k in n.attrib}),
            "alpha": dict(Counter(n.get("svgAlpha", "(absent)") for _, n in svg))},
           "SVG 注册还有透明度和旋转中心等字段，资源查询原样返回。", True)
    record("字体名称和字体文件是否能混为一谈？", sorted({p for p, _ in fonts}),
           {"count": len(fonts), "fontFile": sum(bool(n.get("fontFile")) for _, n in fonts),
            "fontName": sum(bool(n.get("fontName")) for _, n in fonts),
            "legacy_value": sum(bool(n.get("value")) for _, n in fonts)},
           "仅 fontFile 是物理文件引用；fontName 和旧 value 保留为原生属性。", True)
    assets = [(p, a) for p, data in records.items() for e in data["entries"] for a in e["assets"]]
    record("资源文件能否按资源表所在目录定位？", res_paths,
           {"asset_references": len(assets), "states": dict(Counter(a["status"] for _, a in assets)),
            "missing_samples": [{"source": relative(p), **a} for p, a in assets if a["exists"] is False][:8]},
           "按表所在目录解析相对路径并检查作用域；缺失仅报告，不擅自从别处补文件。", True)
    cross = defaultdict(set)
    for p, _, n in entries:
        if n.get("name"):
            cross[n.get("name")].add(relative(p))
    record("分类名与资源名能否混同；资源名称是否唯一？", res_paths,
           {"within_catalog": {relative(p): d["duplicate_names"] for p, d in records.items() if d["duplicate_names"]},
            "folders": {relative(p): d["folders"] for p, d in records.items() if d["folders"]},
            "resource_count": sum(len(d["entries"]) for d in records.values()),
            "names_reused_across_catalogs": sum(len(v) > 1 for v in cross.values()),
            "reused_samples": {k: sorted(v)[:3] for k, v in list((k, v) for k, v in cross.items() if len(v) > 1)[:5]}},
           "递归展开 folder，分类名不计为注册资源重名；名称不能作为全局 ID，查询使用源文件哈希加位置 ID。", True)
    ids = [(p, n) for p, kind, n in entries if kind == "type_id"]
    record("符号 ID 的原值是否可直接重排？", sorted({p for p, _ in ids}),
           {"count": len(ids), "non_integer_values": [n.attrib for _, n in ids if not re.fullmatch(r"-?\d+", n.get("value", ""))],
            "sample": [n.attrib for _, n in ids[:6]]},
           "保留符号名和值；未验证源码引用前不能重排。", True)
    colors = [n.get("value", "") for _, kind, n in entries if kind == "type_color"]
    record("工程资源颜色是否只有十六进制一种表示？", res_paths,
           {"count": len(colors), "hex": sum(v.startswith("#") for v in colors),
            "signed_integer": sum(bool(re.fullmatch(r"-?\d+", v)) for v in colors)},
           "当前样本全部为带符号或无符号的十进制整数字符串；展示原值，不猜测通道位序或推断其他格式。", True)
    backgrounds = [n.get("bkInfoM", "") for _, kind, n in entries if kind == "type_bkInfo"]
    record("背景样式能否作为普通颜色替换？", res_paths,
           {"count": len(backgrounds), "versions": dict(Counter(v for b in backgrounds for v in re.findall(r"99:([^;]+)", b))),
            "with_state_map": sum("98:" in b for b in backgrounds)},
           "bkInfoM 带版本和状态索引，查询返回完整序列，本轮不重写绘制段。", True)
    record("资源节是否允许空表或非固定顺序？", res_paths,
           {"section_orders": [list(order) for order in sorted({tuple(s.tag for s in r) for _, r in resources})],
            "empty_sections": dict(Counter(s.tag for _, r in resources for s in r if len(s) == 0))},
           "保留空节、原始顺序及未知节，不按固定序号解释类型。", True)

    layouts = []
    for p in (p for p in corpus if p.suffix.casefold() == ".xml"):
        text = read(p).decode("utf-8-sig")
        wrapped = ET.fromstring("<wrapper>" + re.sub(r"^\s*<\?xml[^?]*\?>", "", text) + "</wrapper>")
        layouts.append((p, wrapped))
    layout_paths = [p for p, _ in layouts]
    elements = [(p, n) for p, r in layouts for n in r.iter() if n.tag not in {"wrapper", "head"}]
    record("模板根节点是否都已在旧布局检查器范围内？", layout_paths,
           {"root_tags": dict(Counter(n.tag for _, r in layouts for n in r if n.tag != "head"))},
           "节点查询新增支持实际出现的 xc_template_object；heiyue 仍作为独立未支持格式拒绝。", True)
    heads = [{"file": relative(p), "tag": n.tag, "attributes": n.attrib}
             for p, r in layouts for h in r.findall("head") for n in h if any(n.attrib.values())]
    record("布局 head 是否包含有用的代码绑定？", layout_paths, {"nonempty_bindings": heads},
           "保留 head 子树，可读取 bindClassName 等绑定，不因它不是控件而丢弃。", True)
    duplicates = {}
    for p, r in layouts:
        counts = Counter(n.get("name") for n in r.iter() if n.get("name"))
        if any(v > 1 for v in counts.values()):
            duplicates[relative(p)] = {k: v for k, v in counts.items() if v > 1}
    record("布局节点能否仅凭 name 定位？", layout_paths, {"duplicate_names": duplicates},
           "节点位置 ID 能区分重名对象；返回父 ID 和深度，不能自动挑第一个同名对象。", True)
    record("id、uid、itemID 是否属于同一种定位字段？", layout_paths,
           {k: {"count": sum(k in n.attrib for _, n in elements),
                "sample_values": list(dict.fromkeys(n.get(k) for _, n in elements if k in n.attrib))[:8]}
            for k in ("id", "uid", "itemID")},
           "三种属性分别返回和过滤，不将 itemID 当全局 UID。", True)
    record("showT 能否代表运行时可见性？", layout_paths,
           {"showT_values": dict(Counter(n.get("showT") for _, n in elements if "showT" in n.attrib)),
            "show_values": dict(Counter(n.get("show") for _, n in elements if "show" in n.attrib)),
            "explicit_disagreement": sum("showT" in n.attrib and "show" in n.attrib and n.get("showT") != n.get("show") for _, n in elements)},
           "设计器与运行时属性分别保留；不推算屏幕可见性。", True)
    dims = [v for _, n in elements for k, v in n.attrib.items() if k in {"layout.width", "layout.height"}]
    record("布局尺寸能否统一转换为像素？", layout_paths,
           {"values": dict(Counter(dims)), "weighted": sum(v.startswith(":") for v in dims), "percentage": sum(v.startswith("%") for v in dims)},
           "包含 fill/auto/权重等值；节点查询保留表达式，不给出伪造的实际像素。", True)
    nonboxes = [{"file": relative(p), "tag": n.tag, "name": n.get("name")}
                for p, n in elements if n.tag in {"elementUI", "buttonUI", "shapeText"}
                and any(c.get("layout.width") or c.get("layout.height") for c in n)]
    record("声明了布局宽高是否就意味着父容器会排版？", layout_paths,
           {"non_layout_parent_candidates": len(nonboxes), "sample": nonboxes[:8]},
           "父子树可定位风险点，但实际排版仍需 IDE/运行验证；不自动调整父节点。", True)
    bindings = [(p, k, v) for p, n in elements for k, v in n.attrib.items() if "{binding" in v]
    record("数据绑定是否只出现于文本属性？", layout_paths,
           {"attributes": dict(Counter(k for _, k, _ in bindings)),
            "fields": sorted({f for _, _, v in bindings for f in re.findall(r"\bfield=([^\s}]+)", v)})},
           "content/image/bkInfoM 等属性都可能绑定；新命令返回完整绑定字符串，不求值。", True)
    template_refs = [{"file": relative(p), "attribute": k, "value": v}
                     for p, n in elements for k, v in n.attrib.items() if "template" in k.casefold()]
    record("列表项模板是否有可发现的文件引用？", layout_paths,
           {"count": len(template_refs), "sample": template_refs[:12]},
           "可通过 --attribute 和节点子树定位模板声明；相对目录与运行加载方式仍需结合宿主。", True)
    record("控件样式是否总是内联 bkInfoM？", layout_paths,
           {"class_names": dict(Counter(n.get("className") for _, n in elements if n.get("className"))),
            "css_names": dict(Counter(n.get("css.name") for _, n in elements if n.get("css.name")))},
           "className、css.name 和 bkInfoM 是不同原生字段，查询不会混成一个样式名。", True)

    zip_paths = [p for p in corpus if p.name.casefold() == "ui_zip.zip"]
    archives = {}
    members = {}
    for p in zip_paths:
        raw = read(p)
        listing = archive.list_archive(p, ide_root=ide, limit=2000)
        with ZipFile(BytesIO(raw)) as z:
            if sum(i.file_size for i in z.infolist()) > 64 * 1024 * 1024:
                raise ValueError("Sample archive exceeds investigation budget")
            contents = {i.filename.replace("\\", "/"): z.read(i) for i in z.infolist() if not i.is_dir()}
        archives[p] = listing
        members[p] = contents
    record("真实 ZIP 成员是否采用一致分隔符？", zip_paths,
           {"backslash_original_names": sum("\\" in e["original_name"] for d in archives.values() for e in d["items"]),
            "archive_count": len(zip_paths)},
           "统一成员 ID，另存原始名字；按 ZipInfo 读取，避免用规范化名字回查原始目录失败。", True)
    record("只列目录能否证明归档 CRC 正确？", zip_paths,
           {"verified_members": sum(len(v) for v in members.values()), "crc_errors": 0},
           "本轮读取了样本全部成员并完成 ZIP CRC；list 仍明确 crc_verified=false，read/export 才校验选中项。", True)
    counterparts = []
    for p, content in members.items():
        for name, raw in content.items():
            disk = p.parent / name
            if disk.is_file() and disk.resolve().is_relative_to(ide):
                counterparts.append({"archive": relative(p), "member": name,
                                     "same_bytes": hashlib.sha256(read(disk)).digest() == hashlib.sha256(raw).digest()})
    record("同名磁盘文件与 ZIP 副本是否总是相同？", zip_paths,
           {"counterparts": counterparts},
           "磁盘与归档必须作为不同来源；命令返回两级哈希，不能只按文件名判断已同步。", True)
    dark = next(p for p in zip_paths if "暗黑UI" in str(p))
    skin_names = {}
    for name in ("WmUi/Dark/WmUi.res", "WmUi/Light/WmUi.res"):
        tree = ET.fromstring(members[dark][name])
        skin_names[name] = {n.get("name"): n.attrib for section in tree for n in section if n.get("name")}
    a, b = skin_names.values()
    record("暗色和亮色资源表能否按名称对应？", [dark],
           {"dark_names": len(a), "light_names": len(b), "shared_names": len(a.keys() & b.keys()),
            "same_name_different_attributes": sum(a[k] != b[k] for k in a.keys() & b.keys())},
           "命名资源表可独立查询并比较，不能因为名称相同就把主题内容去重。", True)
    font_result = run(["resource", "list", str(dark), "--member", "WmUi/WmUi_Base.res", "--kind", "type_font"])
    record("ZIP 中的字体文件能否相对资源表定位？", [dark],
           {"fonts": [{"name": n["name"], "assets": n["assets"]} for n in font_result["items"]]},
           "解析资源表所在虚拟目录；能定位 WmUi/font，系统字体不误报缺文件。", True)
    css = {name: raw.decode("utf-8-sig") for name, raw in members[dark].items() if name.endswith(".css")}
    record("主题 CSS 是否也存在独立来源和差异？", [dark],
           {"members": {name: {"characters": len(t), "sha256": hashlib.sha256(t.encode()).hexdigest()} for name, t in css.items()},
            "contents_equal": len(set(css.values())) == 1},
           "archive read 可查看 CSS 原文；没有解析选择器级联或自动切换主题。", True)
    record("真实归档中是否存在路径歧义或越界条目？", zip_paths,
           {relative(p): {"entries": d["entry_count"], "problem_count": d["problem_count"]} for p, d in archives.items()},
           "样本结果不代表任意 ZIP；新命令对重名、路径、加密和链接逐项拒绝，并有合成边界测试。", True)
    sizes = [n for d in archives.values() for n in d["items"]]
    record("选择性读取需要怎样的体积边界？", zip_paths,
           {"largest_member": max(sizes, key=lambda n: n["bytes"]),
            "largest_expansion_ratio": max(n["bytes"] / max(1, n["compressed_bytes"]) for n in sizes)},
           "归档 64 MiB、成员 8 MiB、XML 4 MiB 的读取上限覆盖本机样本；不进行无限制整包提取。", True)
    packed_assets = []
    for p, content in members.items():
        for name in content:
            if name.endswith(".res"):
                parsed = ui_data.resource_records(p, member=name, ide_root=ide)
                packed_assets.extend({"archive": relative(p), "member": name, **asset}
                                     for e in parsed["entries"] for asset in e["assets"])
    record("归档资源表所需资产是否都随包存在？", zip_paths,
           {"references": len(packed_assets), "states": dict(Counter(a["status"] for a in packed_assets)),
            "missing": [a for a in packed_assets if a["exists"] is False][:10]},
           "报告归档内的存在性，不拿磁盘上的同名文件冒充已打包资产。", True)
    export_parent = Path(tempfile.mkdtemp(prefix="xcide-round3-export-"))
    output = export_parent / "packed-main.xml"
    run(["archive", "export", str(dark), "main.xml", str(output)])
    if output.exists():
        raise AssertionError("dry-run wrote output")
    real_args = [cli, "--json", "--ide", str(ide), "--session-file", str(export_parent / "session.json"),
                 "archive", "export", str(dark), "main.xml", str(output)]
    result = json.loads(subprocess.run(real_args, capture_output=True, text=True, encoding="utf-8", check=True, timeout=30).stdout)
    if not result.get("ok") or output.read_bytes() != members[dark]["main.xml"]:
        raise AssertionError("Export bytes differ")
    calls.append({"args": real_args[6:], "dry_run": False, "ok": True})
    record("单成员导出能否复用真实布局且保持字节一致？", [dark],
           {"destination": str(output), "sha256": result["sha256"], "verified": result["verified"], "dry_run_wrote_file": False},
           "已通过安装命令导出到独立临时新文件；不覆盖已有文件，也不根据归档路径批量落盘。", True)

    project_paths = [p for p in corpus if p.suffix.casefold() == ".xcproj" and
                     ("data/示例/" in relative(p) or "data/template/项目模板/炫语言/" in relative(p))]
    projects = [(p, ET.fromstring(read(p))) for p in project_paths]
    configurations = [(p, c.get("name"), platform.tag, platform) for p, root in projects
                      for c in root.findall("./vc/setting/config") for platform in c if platform.tag in {"x86", "x64"}]
    record("工程 UI 加载标志是否只有一种？", project_paths,
           {"projects": len(projects), "ui_loadType": dict(Counter(r.get("ui_loadType", "(absent)") for _, r in projects))},
           "发现多个加载标志；仅 XML 值不足以证明运行时选择磁盘还是 ZIP，未增加切换写命令。")
    record("是否每个配置都同时定义 x86/x64？", project_paths,
           {"config_platform_records": len(configurations),
            "platform_sets": dict(Counter(",".join(n.tag for n in c if n.tag in {"x86", "x64"}) for _, r in projects for c in r.findall("./vc/setting/config")))},
           "配置切换必须使用工程中实际存在的架构；不能自动补另一架构。")
    common_nodes = [node.find("common") for _, _, _, node in configurations]
    record("调试标志与运行库字符串是否可相互推断？", project_paths,
           {"pairs": dict(Counter(f"{n.get('debug')} | {n.get('runtimeLibrary')}" for n in common_nodes if n is not None))},
           "debug 与运行库是分别保存的字段，不能只凭配置中文名覆盖 /MD 或 /MT。")
    dirs = [{"file": relative(p), "config": c, "platform": a, "section": section.tag, "attributes": child.attrib}
            for p, c, a, node in configurations for section in node if section.tag in {"include_path", "lib_path", "exe_path"} for child in section]
    record("附加目录是否包含需要上下文展开的宏？", project_paths,
           {"count": len(dirs), "samples": dirs[:12], "with_macros": [x for x in dirs if "$(" in str(x["attributes"])]},
           "可做原始编译目录清单；宏展开与继承顺序未经验证，尚未增加目录写入。")
    opts = [{"file": relative(p), "config": c, "platform": a, "section": s.tag, "attributes": s.attrib}
            for p, c, a, node in configurations for s in node if s.tag in {"options", "options_link"} and any(s.attrib.values())]
    record("显式编译/链接选项是否存在于 common 之外？", project_paths,
           {"nonempty_options": opts}, "options/options_link 是额外原始参数；不能把 common 当完整编译命令。")
    outputs = [{"file": relative(p), "config": c, "platform": a, "attributes": s.attrib}
               for p, c, a, node in configurations for s in node if s.tag == "out" and any(s.attrib.values())]
    record("输出目录与名称是否都使用默认值？", project_paths, {"overrides": outputs},
           "存在输出覆写时需按实际配置定位产物；本轮不改变现有构建目标核验。")
    libs = Counter((s.tag, item.get("name", item.get("path", ""))) for _, _, _, node in configurations
                   for s in node if s.tag in {"lib_import", "lib_ignore"} for item in s)
    record("附加库与忽略库是否为独立设置？", project_paths,
           {"entries": [{"section": k[0], "name": k[1], "occurrences": v} for k, v in libs.items()]},
           "分别保留 lib_import/lib_ignore，不自动合并或从文件名猜运行库。")
    macros = Counter(str(item.attrib) for _, _, _, n in configurations for item in n.findall("./macro/item"))
    record("工程级宏定义是否值得独立封装？", project_paths,
           {"definitions": dict(macros)}, "已定位 macro/item；宏值形式和系统继承需进一步验证后才能安全编辑。")
    sections = Counter(s.tag for _, _, _, n in configurations for s in n)
    other = Counter(n.tag for _, r in projects for n in r if any(word in n.tag.casefold() for word in ("exclude", "file", "debug")))
    record("编译工具覆写与排除项有哪些原生形态？", project_paths,
           {"platform_sections": dict(sections), "other_project_tags": dict(other)},
           "旧样本含 exe_cl/exe_lib/exe_rc，新样本含 exe_path；没有将旧字段静默迁移。")
    vc_path = ide / "data/config/sys/vc.config"
    vc = ET.fromstring(read(vc_path))
    sdks = {n.get("name") for n in vc.findall("./sdk/config")}
    toolsets = {n.get("name") for n in vc.findall("./platformToolset/config")}
    record("样本指定的 SDK/工具集能否在安装定义中找到？", project_paths + [vc_path],
           {"defined_sdks": sorted(sdks), "defined_toolsets": sorted(toolsets),
            "unknown_sdks": sorted({n.get("sdk", "") for n in common_nodes if n is not None} - sdks),
            "unknown_toolsets": sorted({n.get("platformToolset", "") for n in common_nodes if n is not None} - toolsets)},
           "定义存在仍不等于编译器可执行；此轮只验证配置交叉引用，不调用未知工具。")

    module_root = ide / "data/XC-Module"
    known = {}
    for filename in ("module_sub_cxxastar.h", "cxxastardevice.h", "module_xcgui.h", "module_base.h", "module_threadpool.h"):
        paths = sorted(module_root.rglob(filename))
        if len(paths) != 1:
            raise ValueError(f"Expected unique targeted source {filename}")
        known[filename] = paths[0]
    module_text = {name: read(path).decode("utf-8-sig") for name, path in known.items()}
    record("包装头的空别名结果是否等于没有接口？", [known["module_sub_cxxastar.h"], known["cxxastardevice.h"]],
           {name: {"aliases": len(re.findall(r"//@别名", module_text[name])),
                   "has_forward_marker": "//@解析头文件" in module_text[name]} for name in ("module_sub_cxxastar.h", "cxxastardevice.h")},
           "真实声明在转发头；后续模块 API 索引必须跟踪明确转发，不能以包装头空结果作结论。")
    record("模块隐藏区与别名声明是否可能相邻？", list(known.values()),
           {name: {"hidden_starts": text.count("//@隐藏{"), "hidden_ends": text.count("//@隐藏}"),
                   "alias_lines": len(re.findall(r"(?m)^\s*//@别名", text))} for name, text in module_text.items()},
           "文本计数不是可调用 API 数；访问控制、隐藏区和架构分支仍需上下文。")
    directives = {name: re.findall(r'(?m)^\s*//@(?:src|包含目录|lib)\s+([^\r\n]+)', text)
                  for name, text in module_text.items()}
    record("模块除了依赖头还需要哪些编译输入？", list(known.values()),
           {"directives": directives}, "src、包含目录和库声明需随模块保留；单个头文件复制不是完整模块导入。")
    dep = run(["module", "dependencies", "module_threadpool.h"])
    record("现有依赖闭包命令能否解释真实线程池模块？", [known["module_threadpool.h"]],
           {"plan": dep}, "继续复用已实现的依赖计划；不新增重复的模块依赖解析器。")
    encoding_counts = Counter("utf-8-bom" if raw.startswith(b"\xef\xbb\xbf") else "utf-16-bom" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "no-bom"
                              for path, raw in cache.items() if path.suffix.casefold() in {".xml", ".res", ".h"})
    record("模块与布局是否能用同一种 BOM 写回规则？", list(known.values()) + layout_paths + res_paths,
           {"bom_counts": dict(encoding_counts), "module_bom": {n: read(p).startswith(b"\xef\xbb\xbf") for n, p in known.items()}},
           "导出保持原始字节；读取展示编码，未把整个资源集合统一转码。", True)
    completion = ide / "data/config/sys/autoMatch_function.txt"
    lines = read(completion).decode("utf-8-sig").splitlines()
    declaration = [line for line in module_text["module_xcgui.h"].splitlines() if "XBtn_Create(" in line]
    record("补全表声明与当前头文件签名完全相同吗？", [completion, known["module_xcgui.h"]],
           {"completion": [line for line in lines if "XBtn_Create(" in line], "header": declaration[:4]},
           "补全与真实声明应交叉核对；默认参数和调用约定不能由补全表单独推断。")
    prop_path = ide / "data/config/sys/propertyList.json"
    event_path = ide / "data/config/sys/events.xml"
    read(prop_path); read(event_path)
    prop = run(["reference", "search", "properties", "--limit", "2000"])
    events = run(["reference", "search", "events", "--limit", "2000"])
    prop_scopes = {s["id"] for s in prop["scopes"]}
    event_scopes = {s["id"] for s in events["scopes"]}
    record("属性和事件作用域大小写能否直接合并？", [prop_path, event_path],
           {"case_only_differences": [(p, e) for p in sorted(prop_scopes) for e in sorted(event_scopes) if p != e and p.casefold() == e.casefold()]},
           "保留各自原始作用域；有大小写差异时不能自动改写布局标签。")
    declared = {e["attribute"] for e in prop["items"]}
    used = Counter(k for _, n in elements for k in n.attrib)
    absent = {k: v for k, v in used.items() if k not in declared}
    record("原生属性参考表能否作为严格 XML 白名单？", [prop_path] + layout_paths,
           {"used_attributes_absent_from_table": absent},
           "真实布局含设计器/绑定等额外字段；不能据此把参考表未列出的属性判为非法。")
    custom_path = ide / "data/config/customObject.config"
    custom = ET.fromstring(read(custom_path))
    custom_refs = [{"object": obj.get("customName"), "tag": n.tag, "attribute": k, "value": v}
                   for obj in custom for n in obj.iter() for k, v in n.attrib.items() if "@" in v or "{binding" in v]
    record("组合控件片段是否可无条件复制进任意窗口？", [custom_path],
           {"references_or_bindings": custom_refs, "named_nodes": sum(bool(n.get("name")) for n in custom.iter()),
            "nonzero_ids": [n.attrib for n in custom.iter() if n.get("id") not in (None, "0", "")]},
           "只有当前样本的引用/ID情况可确认；复用前仍要检查目标工程资源和名字冲突。")
    qualified = Counter(ref for _, _, n in entries for v in n.attrib.values() for ref in re.findall(r"@([^\s;(){}]+)", v) if ":" in ref)
    record("带命名空间的资源引用能否按文件名直接解析？", res_paths,
           {"qualified_reference_count": sum(qualified.values()), "sample": dict(list(qualified.items())[:12])},
           "@resource1: 等前缀涉及装载上下文，资源查询保留原文并标为未解析，不当作本地绝对路径。")

    # Installed-command checks for the added query chain, including special roots.
    ai_zip = ide / "例子/炫彩界面AI项目/UI_ZIP.zip"
    listing = run(["archive", "list", str(ai_zip), "main.xml"])
    member = listing["items"][0]["id"]
    run(["archive", "read", str(ai_zip), member])
    node_list = run(["interface", "nodes", str(ai_zip), "--member", member, "--tag", "buttonUI", "--limit", "1"])
    if node_list["items"]:
        run(["interface", "node", str(ai_zip), node_list["items"][0]["id"], "--member", member])
    style_list = run(["resource", "list", str(dark), "--member", "WmUi/Dark/WmUi.res", "--kind", "type_bkInfo", "--limit", "1"])
    run(["resource", "show", str(dark), style_list["items"][0]["id"], "--member", "WmUi/Dark/WmUi.res"])
    nested = ide / "data/示例/炫彩界面库-高级示例/xc-QQ音乐/resource.res"
    nested_result = run(["resource", "list", str(nested), "--kind", "type_image", "--limit", "2000"])
    folder = next(n for n in nested_result["folders"] if n["name"] == "音乐馆")
    if sum(folder["id"] in n["folder_ids"] for n in nested_result["items"]) != 12:
        raise AssertionError("Nested image resources were missed")
    after = {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in hashes}
    if len(rounds) != 50 or after != hashes or session.exists():
        raise AssertionError("Expected 50 rounds, unchanged sources, and no dry-run session file")
    return {"schema": "xcide-exploration/v2", "captured_at": datetime.now(timezone.utc).isoformat(),
            "ide_root": str(ide), "round_count": len(rounds), "source_files_checked": len(hashes),
            "sources_unchanged": True, "source_hashes_before": hashes, "source_hashes_after": after,
            "installed_command_checks": calls, "export_artifact": str(output), "rounds": rounds}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ide", type=Path, default=Path(r"I:\xcide"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ide = args.ide.resolve()
    output = args.output.resolve()
    if output.is_relative_to(ide):
        parser.error("Evidence must be written outside the installation")
    evidence = explore(ide)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rounds": evidence["round_count"], "source_files": evidence["source_files_checked"],
                      "unchanged": evidence["sources_unchanged"], "command_checks": len(evidence["installed_command_checks"]),
                      "output": str(output)}, ensure_ascii=False))
