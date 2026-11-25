#!/usr/bin/env python3
"""Render the XCIDE Markdown handbooks as self-contained offline HTML."""

from __future__ import annotations

import argparse
import html
import os
import re
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit


def _inline(value: str, markdown_root: Path, protected: list[str] | None = None,
            *, output_root: Path | None = None) -> str:
    protected = protected if protected is not None else []

    def hold(fragment: str) -> str:
        protected.append(fragment)
        return f"\x00{len(protected) - 1}\x00"

    value = re.sub(r"`([^`]+)`", lambda match: hold(f"<code>{html.escape(match.group(1))}</code>"), value)

    def link(match: re.Match[str]) -> str:
        label, target = match.groups()
        target = target.strip()
        parsed = urlsplit(target)
        if parsed.scheme.casefold() in {"javascript", "data", "vbscript", "file"}:
            return html.escape(match.group(0))
        if not parsed.scheme and not target.startswith("#"):
            source_target = (markdown_root / unquote(parsed.path)).resolve()
            if not source_target.exists():
                sibling_target = (markdown_root / Path(unquote(parsed.path)).name).resolve()
                if sibling_target.exists():
                    source_target = sibling_target
            if source_target.suffix.casefold() == ".md":
                html_target = source_target.with_suffix(".html")
                if html_target.is_file():
                    source_target = html_target
            if source_target.is_file():
                try:
                    relative = os.path.relpath(source_target, output_root or markdown_root)
                except ValueError:  # A separate Windows drive cannot have a relative link.
                    return html.escape(match.group(0))
                target = quote(Path(relative).as_posix(), safe="/.")
                if parsed.query:
                    target += "?" + parsed.query
                if parsed.fragment:
                    target += "#" + parsed.fragment
        href = html.escape(target, quote=True)
        return hold(f'<a href="{href}">{_inline(label, markdown_root, protected, output_root=output_root)}</a>')

    value = re.sub(r"\[([^\]]+)\]\(([^\s)]+)(?:\s+\"[^\"]*\")?\)", link, value)
    value = html.escape(value)
    for token, pattern, tag in (
        ("b", r"\*\*(.+?)\*\*|__(.+?)__", "strong"),
        ("i", r"(?<!\*)\*([^*\n]+)\*(?!\*)|(?<!_)_([^_\n]+)_(?!_)", "em"),
        ("s", r"~~(.+?)~~", "del"),
    ):
        del token
        value = re.sub(pattern, lambda match: f"<{tag}>{next(group for group in match.groups() if group is not None)}</{tag}>", value)
    value = re.sub(r"\x00(\d+)\x00", lambda match: protected[int(match.group(1))], value)
    return value


def _slug(value: str) -> str:
    normalized = re.sub(r"[^\w\- ]+", "", value.casefold(), flags=re.UNICODE)
    return re.sub(r"[\s\-]+", "-", normalized).strip("-") or "section"


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def render(source: str, markdown_root: Path, output_root: Path | None = None) -> tuple[str, str, list[tuple[int, str, str]]]:
    lines = source.splitlines()
    body: list[str] = []
    headings: list[tuple[int, str, str]] = []
    used_ids: dict[str, int] = {}
    paragraph: list[str] = []
    in_list: str | None = None
    list_items: list[str] = []

    def inline(value: str) -> str:
        return _inline(value, markdown_root, output_root=output_root)

    def flush_paragraph() -> None:
        if paragraph:
            body.append("<p>" + inline(" ".join(line.strip() for line in paragraph)) + "</p>")
            paragraph.clear()

    def flush_list() -> None:
        nonlocal in_list
        if in_list:
            body.append(f"<{in_list}>" + "".join(f"<li>{item}</li>" for item in list_items) + f"</{in_list}>")
            list_items.clear()
            in_list = None

    index = 0
    while index < len(lines):
        line = lines[index]
        if line.strip().startswith("```"):
            flush_paragraph()
            flush_list()
            language = re.sub(r"[^\w+-]", "", line.strip()[3:])
            code_lines: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            cls = f' class="language-{html.escape(language, quote=True)}"' if language else ""
            body.append(f"<pre><code{cls}>{html.escape(chr(10).join(code_lines))}</code></pre>")
            index += 1
            continue
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if heading:
            flush_paragraph()
            flush_list()
            level, text = len(heading.group(1)), heading.group(2)
            identifier = _slug(text)
            used_ids[identifier] = used_ids.get(identifier, 0) + 1
            if used_ids[identifier] > 1:
                identifier += f"-{used_ids[identifier]}"
            headings.append((level, text, identifier))
            if level != 1:  # The document title is displayed once in the reader banner.
                body.append(f'<h{level} id="{identifier}">{inline(text)}</h{level}>')
            index += 1
            continue
        if index + 1 < len(lines) and "|" in line and re.match(r"^\s*\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)+\|?\s*$", lines[index + 1]):
            flush_paragraph()
            flush_list()
            headers = _cells(line)
            aligns = ["center" if item.startswith(":") and item.endswith(":") else
                      "left" if item.startswith(":") else "right" if item.endswith(":") else "left"
                      for item in _cells(lines[index + 1])]
            cells = "".join(f'<th style="text-align:{aligns[col] if col < len(aligns) else "left"}">{inline(cell)}</th>'
                            for col, cell in enumerate(headers))
            rows = [f"<tr>{cells}</tr>"]
            index += 2
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                values = _cells(lines[index])
                rows.append("<tr>" + "".join(
                    f'<td style="text-align:{aligns[col] if col < len(aligns) else "left"}">{inline(cell)}</td>'
                    for col, cell in enumerate(values)) + "</tr>")
                index += 1
            body.append('<div class="table-wrap"><table>' + "".join(rows) + "</table></div>")
            continue
        if re.match(r"^\s*([-*_]\s*){3,}$", line):
            flush_paragraph()
            flush_list()
            body.append("<hr>")
            index += 1
            continue
        if line.lstrip().startswith("> "):
            flush_paragraph()
            flush_list()
            body.append("<blockquote><p>" + inline(line.lstrip()[2:]) + "</p></blockquote>")
            index += 1
            continue
        unordered = re.match(r"^\s*[-*+]\s+(.+)$", line)
        ordered = re.match(r"^\s*\d+[.)]\s+(.+)$", line)
        if unordered or ordered:
            flush_paragraph()
            kind = "ol" if ordered else "ul"
            if in_list and in_list != kind:
                flush_list()
            in_list = kind
            list_items.append(inline((ordered or unordered).group(1)))
            index += 1
            continue
        if not line.strip():
            flush_paragraph()
            flush_list()
            index += 1
            continue
        paragraph.append(line)
        index += 1

    flush_paragraph()
    flush_list()
    title = next((text for level, text, _identifier in headings if level == 1),
                 next((text for level, text, _identifier in headings if level == 2), "炫彩 IDE 本地自动化文档"))
    return "\n".join(body), title, headings


def page(source_path: Path, target_path: Path) -> str:
    markdown = source_path.read_text(encoding="utf-8-sig")
    if markdown.startswith("---\n") or markdown.startswith("---\r\n"):
        lines = markdown.splitlines()
        closing = next((index for index in range(1, min(len(lines), 32))
                        if lines[index].strip() == "---"), None)
        if closing is not None:
            markdown = "\n".join(lines[closing + 1:]).lstrip()
    body, title, headings = render(markdown, source_path.parent, target_path.parent)
    outline = "".join(f'<a class="depth-{min(level, 4)}" href="#{identifier}">{html.escape(text)}</a>'
                       for level, text, identifier in headings if level >= 2)
    launcher = target_path.parent / "DOCS.html"
    if launcher.is_file() and launcher.resolve() != target_path.resolve():
        body = '<p class="doc-home"><a href="DOCS.html">← 返回文档总览</a></p>' + body
    path = target_path.name
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data: file:; font-src 'none'; script-src 'none'; base-uri 'none'; form-action 'none'">
<meta name="color-scheme" content="light dark"><title>{html.escape(title)}｜炫彩 IDE</title>
<meta name="description" content="离线阅读版：{html.escape(title, quote=True)}">
<style>
:root{{color-scheme:light dark;--bg:#f3f5f9;--panel:#fff;--ink:#1f2937;--soft:#617086;--line:#e4e9f0;--accent:#145bce;--code:#eef2f8;--shadow:0 16px 46px #25385814;font:16px/1.76 "Microsoft YaHei UI","Microsoft YaHei",system-ui,sans-serif}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(ellipse at 85% -12%,#dbeafe 0,transparent 34rem),var(--bg);color:var(--ink)}}
.top{{max-width:1380px;margin:auto;padding:30px 34px 12px;display:flex;align-items:center;justify-content:space-between;color:var(--soft);font-size:13px;letter-spacing:.04em}}
.brand{{display:flex;align-items:center;gap:10px;font-weight:700;color:var(--accent)}}.mark{{display:grid;place-items:center;width:28px;height:28px;border-radius:8px;background:linear-gradient(140deg,#4e91ff,#1758c9);color:white;font-size:15px}}
.wrap{{max-width:1380px;margin:0 auto 72px;padding:14px 28px;display:grid;grid-template-columns:minmax(0,1fr) 245px;gap:26px;align-items:start}}
main{{min-width:0;background:var(--panel);border:1px solid var(--line);box-shadow:var(--shadow);border-radius:18px;padding:54px clamp(24px,6vw,86px) 66px}}.eyebrow{{color:var(--accent);font-weight:700;letter-spacing:.1em;text-transform:uppercase;font-size:12px}}h1{{font-size:clamp(32px,5vw,47px);line-height:1.2;letter-spacing:-.04em;margin:12px 0 32px}}h2{{font-size:25px;line-height:1.35;letter-spacing:-.025em;margin:52px 0 18px;padding-bottom:10px;border-bottom:1px solid var(--line)}}h3{{font-size:20px;margin:34px 0 10px;line-height:1.4}}h4,h5,h6{{margin:28px 0 8px}}p{{margin:14px 0}}a{{color:var(--accent);text-decoration:none}}a:hover{{text-decoration:underline}}strong{{font-weight:750}}ul,ol{{padding-left:1.55em;margin:12px 0 20px}}li{{padding-left:.18em;margin:6px 0}}code{{font-family:Consolas,"Cascadia Code","Microsoft YaHei",monospace;font-size:.91em;background:var(--code);border-radius:5px;padding:.13em .42em;overflow-wrap:anywhere}}pre{{margin:20px 0;padding:19px 22px;background:#111827;color:#e2e8f0;border:1px solid #334155;border-radius:11px;overflow:auto;line-height:1.65;white-space:pre}}pre code{{padding:0;background:none;border-radius:0;color:inherit;font-size:13px;overflow-wrap:normal}}.table-wrap{{overflow:auto;margin:19px 0 24px;border:1px solid var(--line);border-radius:10px}}table{{border-collapse:collapse;width:100%;font-size:14px;line-height:1.55}}th,td{{padding:10px 13px;border-bottom:1px solid var(--line);vertical-align:top}}th{{background:var(--code);font-weight:700;white-space:nowrap}}tr:last-child td{{border-bottom:0}}blockquote{{margin:20px 0;padding:2px 20px;border-left:4px solid #86aaf1;background:var(--code);border-radius:0 8px 8px 0;color:var(--soft)}}hr{{border:0;border-top:1px solid var(--line);margin:32px 0}}.meta{{color:var(--soft);font-size:13px;margin-top:-20px;margin-bottom:36px}}
aside{{position:sticky;top:16px;max-height:calc(100vh - 32px);overflow:auto;padding:20px 16px;background:color-mix(in srgb,var(--panel) 84%,transparent);border:1px solid var(--line);border-radius:14px}}aside b{{display:block;margin:0 8px 9px;font-size:13px}}aside a{{display:block;padding:4px 8px;color:var(--soft);font-size:12px;line-height:1.5;border-radius:5px}}aside a:hover{{background:var(--code);color:var(--accent);text-decoration:none}}aside .depth-3{{padding-left:18px}}aside .depth-4{{padding-left:29px}}.foot{{max-width:1380px;margin:-48px auto 30px;padding:0 34px;color:var(--soft);font-size:12px}}
@media(prefers-color-scheme:dark){{:root{{--bg:#12151c;--panel:#1b2029;--ink:#e3e9f2;--soft:#a6b1c2;--line:#303948;--accent:#7eaeff;--code:#252e3a;--shadow:0 20px 50px #0004}}body{{background:radial-gradient(ellipse at 85% -12%,#172b46 0,transparent 36rem),var(--bg)}}aside{{background:color-mix(in srgb,var(--panel) 87%,transparent)}}}}
@media(max-width:940px){{.wrap{{grid-template-columns:minmax(0,1fr);padding:10px 16px}}aside{{position:relative;top:0;max-height:240px;order:-1;columns:2}}main{{padding:38px clamp(18px,5vw,48px) 48px}}.top{{padding:23px 20px 10px}}}}
@media(max-width:560px){{.wrap{{padding:8px}}main{{border-radius:12px;padding:30px 20px 42px}}aside{{columns:1}}.top{{padding:18px 14px 8px}}h2{{font-size:22px}}}}
@media print{{:root{{color-scheme:light;--bg:#fff;--panel:#fff;--ink:#171717;--soft:#444;--line:#ccc;--accent:#164f98;--code:#f1f1f1}}body{{background:#fff}}.top,aside,.foot{{display:none}}.wrap{{display:block;max-width:none;margin:0;padding:0}}main{{border:0;box-shadow:none;padding:0}}h2{{break-after:avoid}}pre,table{{break-inside:avoid}}a{{color:inherit;text-decoration:underline}}}}
</style></head><body>
<header class="top"><div class="brand"><span class="mark">炫</span><span>炫彩 IDE · 本地自动化文档</span></div><span>离线 HTML · 可直接浏览器打开 / 打印为 PDF</span></header>
<div class="wrap"><main><div class="eyebrow">XCGUI / Xuan Language</div><h1>{html.escape(title)}</h1><div class="meta">本页由本地 Markdown 生成；样式内嵌，无网络、MCP 或浏览器脚本依赖。</div>{body}</main>
<aside><b>本页目录</b>{outline or '<span>无需目录</span>'}</aside></div>
<footer class="foot">源 Markdown：{html.escape(source_path.name)} · 独立 HTML 副本：{html.escape(path)}</footer></body></html>'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    arguments = parser.parse_args()
    destination = arguments.destination.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(page(arguments.source.expanduser().resolve(), destination), encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
