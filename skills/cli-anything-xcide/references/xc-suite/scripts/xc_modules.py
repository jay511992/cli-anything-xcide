#!/usr/bin/env python3
"""Build and query a source-backed XC-Module call index (standard library only)."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
from xml.sax.saxutils import quoteattr


_cache_root = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".cache")
DATA = Path(os.environ.get("XC_MODULE_INDEX_DIR") or _cache_root / "cli-anything-xcide" / "module-index").expanduser().resolve()
DEFAULT_ROOT = r"I:\xcide\data\XC-Module"
EXTENSIONS = {".h", ".hpp", ".xh", ".xc"}
SKIP = {".git", ".vs", "obj", "cache", "__pycache__", "sessions",
        ".codegraph", "xcgui_rebuild", "xcgui_recovered"}
ANNOTATION = re.compile(r"(?:^\s*(?://\s*|/\*\s*|\*\s*)?|//\s*)@([^\s{}]+)\s*(.*)")
ALIAS = re.compile(r"@别名\s+([^\r\n]+)")
MODULE_NAME = re.compile(r"(?m)^\s*//\s*@模块名称\s+([^\r\n]+)")
INCLUDE = re.compile(r'^\s*(?:#\s*include|#头文件|#包含)\s*"([^"]+)"')
XC_FUNCTION = re.compile(r"^\s*(?:函数|def)\s+(.+)")
TYPE = re.compile(r"^(?:class|struct|enum(?:\s+class)?|namespace|类|结构体)\s+([\w:]+)")


def dump(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def read_text(path):
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16"), "utf-16", raw
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return raw.decode(encoding), encoding, raw
        except UnicodeDecodeError:
            pass
    raise ValueError(f"Cannot decode source without loss: {path}")


def package_of(relative):
    return "/".join(Path(relative).parts[:2])


def source_path(root, relative):
    path = (root / relative.replace("\\", "/")).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Source path must stay inside the module root")
    return path


def clean_value(value):
    return value.strip().removesuffix("*/").strip()


def declarations(lines, position):
    """Keep original spelling. This is a locator, not a C++/IDE parser."""
    inline = lines[position].split("//", 1)[0].strip()
    if ALIAS.search(lines[position]) and inline and not inline.startswith(("/*", "*", "@")):
        return position, inline
    start = position + 1 if ALIAS.search(lines[position]) else position
    result = []
    first = start
    for index in range(start, min(len(lines), start + 50)):
        line = lines[index].strip()
        if not line or line.startswith(("//", "/*", "*", "@", "#if", "#else", "#endif")):
            continue
        if not result:
            first = index
        result.append(line)
        if ";" in line or "{" in line or lines[index].lstrip().startswith(("#define", "函数 ", "类 ", "结构体 ")):
            break
        if len(" ".join(result)) > 3000:
            break
    return first, "\n".join(result)


def scope_lines(lines, is_xc):
    """Approximate lexical owners; conditions and IDE declaration blocks remain raw."""
    owners = []
    if is_xc:
        stack = []
        for line in lines:
            stripped = line.lstrip()
            indent = len(line.expandtabs(4)) - len(stripped)
            if stripped and not stripped.startswith(("//", "#")):
                while stack and indent <= stack[-1][0]:
                    stack.pop()
            owners.append("::".join(item[1] for item in stack))
            match = TYPE.match(stripped)
            if match:
                stack.append((indent, match.group(1)))
        return owners
    depth = 0
    stack = []
    pending = None
    in_comment = False
    for line in lines:
        owners.append("::".join(item[1] for item in stack))
        # @声明 block contents are visible to the IDE, unlike ordinary C comments.
        if "/*@声明" in line or re.search(r"^\s*/\*\s*$", line):
            in_comment = "/*@声明" not in line
        if in_comment:
            if "*/" in line:
                in_comment = False
            continue
        code = line.split("//", 1)[0].strip()
        code = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', '""', code)
        match = TYPE.match(code)
        if match and ";" not in code.split("{", 1)[0]:
            pending = match.group(1)
        if pending and "{" in code:
            stack.append((depth + 1, pending))
            pending = None
        if ";" in code and "{" not in code:
            pending = None
        depth += code.count("{") - code.count("}")
        while stack and depth < stack[-1][0]:
            stack.pop()
    return owners


def api_records(relative, text):
    lines = text.splitlines()
    is_xc = Path(relative).suffix.lower() == ".xc"
    scopes = scope_lines(lines, is_xc)
    covered = set()
    records = []
    for index, line in enumerate(lines):
        alias = ALIAS.search(line)
        if not alias:
            continue
        at, declaration = declarations(lines, index)
        covered.add(at)
        records.append({"file": relative, "line": index + 1,
                        "declaration_line": at + 1, "kind": "alias",
                        "alias": clean_value(alias.group(1)),
                        "scope_hint": scopes[at] if at < len(scopes) else "",
                        "declaration": declaration})
    for index, line in enumerate(lines):
        if index in covered:
            continue
        code = line.split("//", 1)[0].strip()
        if not code or code.startswith(("//", "/*", "*", "@", "#嵌入")):
            continue
        kind = None
        if is_xc and XC_FUNCTION.match(line):
            kind = "xc-function"
        elif TYPE.match(code):
            kind = "type"
        elif code.startswith(("#define ", "#define\t", "#宏定义 ", "#函数类型 ", "#DLL导入表 ")):
            kind = "macro-or-import"
        elif not is_xc and re.match(r"[\w~][\w\s:*&<>\[\],~]*[\s*&][\w~]+\s*\(", code):
            if not re.match(r"(?:return|if|while|for|switch|throw|delete|new|static_assert)\b", code):
                kind = "declaration-candidate"
        if kind:
            at, declaration = declarations(lines, index)
            records.append({"file": relative, "line": index + 1,
                            "declaration_line": at + 1, "kind": kind,
                            "alias": "", "scope_hint": scopes[index],
                            "declaration": declaration})
    return records


def build(root):
    if not root.is_dir():
        raise ValueError(f"Module root is missing: {root}")
    sources = {}
    graph = {}
    decoded = {}
    modules = []
    problems = []
    projects = []
    examples = defaultdict(list)
    example_sources = []
    parse_headers = defaultdict(list)
    packages = []
    for category in sorted(root.iterdir()):
        if category.is_dir() and (re.match(r"^\d\d_", category.name) or category.name == "核心[官方]"):
            for package in sorted(category.iterdir()):
                if package.is_dir():
                    packages.append({"path": package.relative_to(root).as_posix(),
                                     "category": category.name, "name": package.name})
    paths = sorted(p for p in root.rglob("*") if p.is_file()
                   and not any(part.casefold() in SKIP for part in p.relative_to(root).parts))
    for path in paths:
        relative = path.relative_to(root).as_posix()
        if path.suffix.lower() == ".xcproj":
            try:
                text, _, _ = read_text(path)
                tree = ET.fromstring(text)
                imports = [item.attrib.get("path", "") for item in tree.findall(".//modules/item")]
                item = {"path": relative, "imports": imports}
                projects.append(item)
                examples[package_of(relative)].append(item)
            except (ValueError, ET.ParseError) as exc:
                problems.append({"file": relative, "error": str(exc)})
            continue
        if path.suffix.lower() not in EXTENSIONS:
            continue
        try:
            text, encoding, raw = read_text(path)
        except ValueError as exc:
            problems.append({"file": relative, "error": str(exc)})
            continue
        includes = [m.group(1) for line in text.splitlines() if (m := INCLUDE.match(line))]
        graph[relative] = includes
        parse_next = False
        for line in text.splitlines():
            if "@解析头文件" in line:
                parse_next = True
            match = INCLUDE.match(line)
            if parse_next and match:
                parse_headers[relative].append(match.group(1))
                parse_next = False
        name = MODULE_NAME.search(text)
        primary = path.name.lower().startswith("module_")
        relevant = primary or name or re.search(r"@(?:别名|声明|解析头文件|分组)", text)
        decoded[relative] = text
        if path.suffix.lower() in {".xc", ".xh"} and not primary:
            example_sources.append(relative)
        if not relevant:
            continue
        sources[relative] = {"sha256": hashlib.sha256(raw).hexdigest(), "encoding": encoding,
                             "package": package_of(relative), "lines": len(text.splitlines())}
        if primary or name:
            metadata = defaultdict(list)
            for line in text.splitlines():
                match = ANNOTATION.search(line)
                if match and match.group(1) in {"模块名称", "版本", "日期", "作者", "依赖", "模块备注",
                        "lib", "lib64", "复制文件", "复制文件64", "包含目录", "src", "doc", "默认安装位置"}:
                    metadata[match.group(1)].append(clean_value(match.group(2)))
            modules.append({"path": relative, "file": path.name,
                            "package": package_of(relative),
                            "name": clean_value(name.group(1)) if name else path.stem,
                            "entrypoint": primary,
                            "role": "entrypoint" if primary else "support-metadata",
                            "backup": "backup" in path.stem.lower(),
                            "metadata": dict(metadata)})
    # Follow actual quoted includes only; never guess a module from a similar name.
    by_name = defaultdict(list)
    canonical = {relative.casefold(): relative for relative in graph}
    for relative in graph:
        by_name[Path(relative).name.casefold()].append(relative)
    resolved_graph = {}
    for relative, includes in graph.items():
        resolved = []
        for include in includes:
            local = (root / Path(relative).parent / include.replace("\\", "/")).resolve()
            candidate = local.relative_to(root).as_posix() if local.is_relative_to(root) else ""
            if candidate.casefold() in canonical:
                resolved.append(canonical[candidate.casefold()])
            elif Path(include).name.lower().startswith("module_"):
                matches = by_name.get(Path(include.replace("\\", "/")).name.casefold(), [])
                if len(matches) == 1:
                    resolved.append(matches[0])
        resolved_graph[relative] = resolved
    # Explicit @解析头文件 can expose unaliased C/C++ APIs too.
    for relative, includes in parse_headers.items():
        for include in includes:
            local = (root / Path(relative).parent / include.replace("\\", "/")).resolve()
            candidate = local.relative_to(root).as_posix() if local.is_relative_to(root) else ""
            target = canonical.get(candidate.casefold())
            if target and target not in sources:
                text, encoding, raw = read_text(root / target)
                sources[target] = {"sha256": hashlib.sha256(raw).hexdigest(), "encoding": encoding,
                                   "package": package_of(target), "lines": len(text.splitlines())}
    owners = defaultdict(list)
    entrypoints = {m["path"] for m in modules if m["entrypoint"]}
    for module in modules:
        if not module["entrypoint"]:
            continue
        seen = set()
        todo = [module["path"]]
        while todo:
            current = todo.pop()
            if current in seen:
                continue
            seen.add(current)
            if current in sources:
                owners[current].append(module["path"])
            for included in resolved_graph.get(current, []):
                if included not in entrypoints:
                    todo.append(included)
    for relative, info in sources.items():
        info["entrypoints"] = sorted(set(owners[relative]))
        info["includes"] = resolved_graph.get(relative, [])
    if not packages or not entrypoints:
        raise ValueError("No classified module packages/entrypoints found; existing index was not replaced")
    record_counts = Counter()
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / "api.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for relative in sorted(sources):
            records = api_records(relative, decoded[relative])
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
                record_counts[record["kind"]] += 1
            sources[relative]["records"] = len(records)
    for module in modules:
        module["examples"] = [p["path"] for p in examples[module["package"]]
                              if module["file"].casefold() in [v.casefold() for v in p["imports"]]]
        module["package_examples"] = [p["path"] for p in examples[module["package"]]]
        module["sources"] = [s for s, info in sources.items() if module["path"] in info["entrypoints"]]
    for package in packages:
        package["modules"] = [m["path"] for m in modules if m["package"] == package["path"]]
        package["examples"] = [p["path"] for p in examples[package["path"]]]
    result = {"schema": 1, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "root": str(root), "note": "Source index only; not a compilation or runtime certification.",
              "counts": {"packages": len(packages),
                         "official_packages": sum(p["category"] == "核心[官方]" for p in packages),
                         "entrypoints": len(entrypoints), "metadata_entries": len(modules),
                         "sources": len(sources), "example_projects": len(projects),
                         "api_records": sum(record_counts.values()), "api_kinds": dict(record_counts)},
              "packages": packages, "modules": modules, "sources": sources,
              "example_projects": projects, "example_sources": example_sources,
              "scan_problems": problems}
    (DATA / "catalog.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    render_catalog(result)
    return {"root": str(root), "output": str(DATA), "counts": result["counts"], "scan_problems": problems}


def render_catalog(data):
    lines = ["# 本地 XC-Module 完整模块包目录", "",
             f"来源：`{data['root']}`；生成时间：`{data['generated_at']}`。", "",
             "由 `scripts/xc_modules.py rebuild` 生成。函数调用检索、依赖与示例用法见技能内的模块检索指南。",
             "此表按实际文件列入口；不把头文件存在视为编译通过。辅助元数据头不是默认项目入口。", ""]
    modules = {m["path"]: m for m in data["modules"]}
    for category in sorted({p["category"] for p in data["packages"]}):
        lines += [f"## {category}", "", "| 模块包 | 标准入口（相对模块包） | 辅助元数据头 | 示例工程数 |",
                  "| --- | --- | --- | ---: |"]
        for package in data["packages"]:
            if package["category"] != category:
                continue
            primary, support = [], []
            for path in package["modules"]:
                module = modules[path]
                short = path[len(package["path"]) + 1:]
                value = f"`{short}`（{module['name']}）"
                (primary if module["entrypoint"] else support).append(value)
            lines.append(f"| `{package['name']}` | {'<br>'.join(primary) or '未发现 module_ 入口，需查看辅助头'} | "
                         f"{'<br>'.join(support) or '—'} | {len(package['examples'])} |")
        lines.append("")
    (DATA / "catalog.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_data():
    path = DATA / "catalog.json"
    if not path.exists():
        raise ValueError(f"Index missing at {path}; run rebuild first")
    return json.loads(path.read_text(encoding="utf-8"))


def matches_module(module, term):
    term = term.casefold().replace("\\", "/")
    return term in " ".join([module["path"], module["name"],
                              *module["metadata"].get("作者", [])]).casefold()


def select_modules(data, term):
    term = term.replace("\\", "/").casefold()
    exact = [m for m in data["modules"] if term == m["path"].casefold()]
    if exact:
        return exact
    return [m for m in data["modules"] if matches_module(m, term)]


def selected_sources(data, module_term):
    if not module_term:
        return set(data["sources"])
    modules = select_modules(data, module_term)
    selected = {m["path"] for m in modules}
    for module in modules:
        selected.update(module["sources"])
        if not module["entrypoint"]:
            selected.add(module["path"])
    # Package names also match wrappers without a direct include relation.
    term = module_term.casefold().replace("\\", "/")
    selected.update(s for s, info in data["sources"].items() if term in info["package"].casefold())
    return selected


def dependency_plan(data, module):
    by_name = defaultdict(list)
    for item in data["modules"]:
        if item["entrypoint"]:
            by_name[item["file"].casefold()].append(item)
    items, unresolved, seen, header_dependencies = [], [], set(), []
    all_sources = defaultdict(list)
    for path in data["sources"]:
        all_sources[Path(path).name.casefold()].append(path)

    def dependencies(raw):
        raw = raw.split("//", 1)[0].strip()
        if raw.casefold() in {"", "无", "none", "null"}:
            return []
        quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'|([^,，;；\s]+)', raw)
        return [next(part for part in token if part) for token in quoted]

    def visit(item):
        if item["path"] in seen:
            return
        seen.add(item["path"])
        for raw in item["metadata"].get("依赖", []):
            for token in dependencies(raw):
                dep = Path(token.replace("\\", "/")).name
                found = by_name.get(dep.casefold(), [])
                local = (Path(item["path"]).parent / token.replace("\\", "/")).as_posix().casefold()
                nearby = [m for m in found if m["path"].casefold() == local]
                if nearby:
                    found = nearby
                if len(found) == 1:
                    visit(found[0])
                elif not found and not dep.lower().startswith("module_"):
                    candidates = [p for p in all_sources.get(dep.casefold(), []) if p.casefold() == local]
                    if not candidates:
                        candidates = all_sources.get(dep.casefold(), [])
                    header_dependencies.append({"from": item["path"], "header": token,
                                                "indexed_candidates": candidates,
                                                "note": "Header dependency, not a module_ project item; inspect the source include path."})
                else:
                    unresolved.append({"from": item["path"], "dependency": token,
                                       "candidates": [m["path"] for m in found]})
        items.append(item)

    visit(module)
    collisions = [{"file": item["file"], "candidates": [m["path"] for m in by_name[item["file"].casefold()]]}
                  for item in items if len(by_name[item["file"].casefold()]) > 1]
    block = "<modules>\n" + "\n".join(
        f"  <item path={quoteattr(item['file'])} name={quoteattr(item['name'])} />" for item in items) + "\n</modules>"
    return {"ordered_paths": [m["path"] for m in items], "unresolved": unresolved,
            "basename_collisions": collisions,
            "header_dependencies": header_dependencies,
            "modules_xml": block if not unresolved and not collisions and module["entrypoint"] else None,
            "note": "Only explicit @依赖 is expanded. Merge items into the existing project; confirm conditional/include dependencies in source."}


def query(data, args, root):
    files = selected_sources(data, args.module)
    terms = [term.casefold() for term in args.terms]
    hits = []
    if args.raw:
        for relative in sorted(files):
            text, _, _ = read_text(source_path(root, relative))
            for index, line in enumerate(text.splitlines()):
                if all(term in line.casefold() for term in terms):
                    hits.append({"file": relative, "line": index + 1, "text": line,
                                 "entrypoints": data["sources"][relative]["entrypoints"]})
    else:
        with (DATA / "api.jsonl").open(encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                if record["file"] not in files:
                    continue
                haystack = " ".join([record["alias"], record["declaration"], record["scope_hint"]]).casefold()
                if all(term in haystack for term in terms):
                    record["entrypoints"] = data["sources"][record["file"]]["entrypoints"]
                    hits.append(record)
    hits.sort(key=lambda r: (0 if any(re.split(r"[（(]", r.get("alias", ""))[0].casefold() == t for t in terms) else 1,
                             r["file"], r["line"]))
    shown = hits[args.offset:args.offset + args.limit]
    status = {}
    for relative in sorted({hit["file"] for hit in shown}):
        path = source_path(root, relative)
        status[relative] = "unchanged" if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == data["sources"][relative]["sha256"] else "missing-or-changed; rebuild index"
    return {"total": len(hits), "offset": args.offset, "limit": args.limit,
            "source_status": status, "matches": shown,
            "note": "Candidates, not an AST. Read source for owner, access, @隐藏, @声明 and active architecture. Use --raw for comments/unindexed spellings."}


def verify(data, root):
    missing, changed = [], []
    for relative, info in data["sources"].items():
        path = source_path(root, relative)
        if not path.exists():
            missing.append(relative)
        elif hashlib.sha256(path.read_bytes()).hexdigest() != info["sha256"]:
            changed.append(relative)
    actual_entries = {p.relative_to(root).as_posix() for p in root.rglob("*")
                      if p.is_file() and p.suffix.lower() in EXTENSIONS
                      and p.name.lower().startswith("module_")
                      and not any(part.casefold() in SKIP for part in p.relative_to(root).parts)}
    indexed = {m["path"] for m in data["modules"] if m["entrypoint"]}
    unresolved = []
    for module in data["modules"]:
        if module["entrypoint"]:
            unresolved.extend(dependency_plan(data, module)["unresolved"])
    unique_unresolved = {json.dumps(item, ensure_ascii=False, sort_keys=True): item for item in unresolved}
    return {"ok": not missing and not changed and actual_entries == indexed,
            "counts": data["counts"], "missing_sources": missing, "changed_sources": changed,
            "new_entrypoints": sorted(actual_entries - indexed), "removed_entrypoints": sorted(indexed - actual_entries),
            "unresolved_explicit_dependencies": list(unique_unresolved.values()),
            "scan_problems": data["scan_problems"],
            "note": "ok checks indexed source freshness and entrypoint coverage; dependency diagnostics do not certify builds."}


def find_examples(data, args, root):
    packages = {m["package"] for m in select_modules(data, args.module)}
    files = [p for p in data["example_sources"] if package_of(p) in packages]
    hits = []
    for relative in files:
        if not args.terms:
            hits.append({"file": relative})
            continue
        text, _, _ = read_text(source_path(root, relative))
        for index, line in enumerate(text.splitlines()):
            if all(term.casefold() in line.casefold() for term in args.terms):
                hits.append({"file": relative, "line": index + 1, "text": line})
    return {"total": len(hits), "matches": hits[:args.limit],
            "note": "Live .xc/.xh files in the selected package; inspect its .xcproj imports before reusing a sample."}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="Override XC_MODULE_ROOT or the catalog source root")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("rebuild", help="Read local modules and regenerate only the skill index")
    sub.add_parser("stats")
    sub.add_parser("verify", help="Check source hashes, coverage, and unresolved explicit dependencies")
    listing = sub.add_parser("list", help="List module metadata; no query lists every package")
    listing.add_argument("query", nargs="?", default="")
    showing = sub.add_parser("show", help="Get one module's imports, dependencies, directives, and examples")
    showing.add_argument("module")
    searching = sub.add_parser("search", help="Search Chinese aliases, English declarations, and .xc functions")
    searching.add_argument("terms", nargs="+")
    searching.add_argument("--module", default="", help="Filter by exact entry path, module, author, or package")
    searching.add_argument("--raw", action="store_true", help="Search the live indexed source files line by line")
    searching.add_argument("--limit", type=int, default=12)
    searching.add_argument("--offset", type=int, default=0)
    example = sub.add_parser("examples", help="Locate real .xc/.xh sample calls in a module package")
    example.add_argument("module")
    example.add_argument("terms", nargs="*")
    example.add_argument("--limit", type=int, default=12)
    reading = sub.add_parser("source", help="Read a bounded range of live module/example source")
    reading.add_argument("file")
    reading.add_argument("--line", type=int, default=1)
    reading.add_argument("--before", type=int, default=12)
    reading.add_argument("--after", type=int, default=35)
    args = parser.parse_args()
    if args.command == "rebuild":
        root = (args.root or Path(os.environ.get("XC_MODULE_ROOT", DEFAULT_ROOT))).resolve()
        dump(build(root))
        return
    data = load_data()
    root = (args.root or Path(os.environ.get("XC_MODULE_ROOT", data["root"]))).resolve()
    if args.command == "stats":
        dump({"root": str(root), "generated_at": data["generated_at"], "counts": data["counts"]})
    elif args.command == "list":
        if not args.query:
            dump(data["packages"])
        else:
            selected = select_modules(data, args.query)
            dump([{"path": m["path"], "name": m["name"], "role": m["role"],
                   "backup": m["backup"], "version": m["metadata"].get("版本", []),
                   "author": m["metadata"].get("作者", []), "examples": len(m["examples"])} for m in selected])
    elif args.command == "show":
        selected = select_modules(data, args.module)
        if len(selected) != 1:
            dump({"error": "Choose one exact path", "candidates": [m["path"] for m in selected]})
            sys.exit(2)
        module = selected[0]
        dump({**module, "absolute_path": str(source_path(root, module["path"])),
              "project_import": dependency_plan(data, module)})
    elif args.command == "search":
        if not 1 <= args.limit <= 200 or args.offset < 0:
            raise ValueError("--limit must be 1..200 and --offset must be nonnegative")
        dump(query(data, args, root))
    elif args.command == "source":
        if args.line < 1 or min(args.before, args.after) < 0 or args.before + args.after > 240:
            raise ValueError("Use positive line numbers and a window no larger than 240 lines")
        path = source_path(root, args.file)
        text, encoding, raw = read_text(path)
        lines = text.splitlines()
        if args.line > len(lines):
            raise ValueError(f"Requested line is past EOF ({len(lines)} lines)")
        low = max(0, args.line - args.before - 1)
        high = min(len(lines), args.line + args.after)
        dump({"path": str(path), "encoding": encoding, "sha256": hashlib.sha256(raw).hexdigest(),
              "lines": [{"line": i + 1, "text": lines[i]} for i in range(low, high)]})
    elif args.command == "examples":
        if not 1 <= args.limit <= 200:
            raise ValueError("--limit must be 1..200")
        dump(find_examples(data, args, root))
    elif args.command == "verify":
        result = verify(data, root)
        dump(result)
        if not result["ok"]:
            sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        print(f"xc_modules: {error}", file=sys.stderr)
        sys.exit(1)
