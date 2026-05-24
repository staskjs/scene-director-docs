#!/usr/bin/env python3
"""Build static HTML docs from docs-site/content/*.md. Stdlib only — no pip.

Usage (from docs-site/):
  python build_docs.py              # one-shot build
  python build_docs.py --watch      # rebuild when sources change (poll)
  python build_docs.py -w -i 1.0    # poll every 1.0 s

Upload the dist/ folder to your static host (SFTP, etc.).

Tabbed Blueprint / C++ blocks (no JS — CSS + radio inputs):

  <<<DOCtabs>>>
  === Blueprint
  ...markdown...
  === C++
  ...markdown...
  <<<ENDtabs>>>

The first tab is selected by default (put Blueprint first).
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIST = HERE / "dist"
MANIFEST = HERE / "manifest.json"
ASSETS_SRC = HERE / "assets"
DOCS_ROOT = HERE / "content"
DOCS_IMAGES = HERE / "images"
PLUGIN_ROOT = HERE.parent / "Plugins" / "SceneDirector"
UPLUGIN = PLUGIN_ROOT / "SceneDirector.uplugin"


def load_plugin_meta() -> tuple[str, str]:
    if not UPLUGIN.is_file():
        return "Scene Director", ""
    data = json.loads(UPLUGIN.read_text(encoding="utf-8"))
    name = data.get("FriendlyName") or "Scene Director"
    desc = (data.get("Description") or "").strip()
    return name, desc


def normalize_md_paths(md: str) -> str:
    md = re.sub(r"\]\(Resources/", "](assets/images/", md)
    md = re.sub(r"\]\(DocumentationImages/", "](assets/images/", md)
    return md


_FENCED_BLOCK_RE = re.compile(r"(```[\s\S]*?```)", re.MULTILINE)


def _build_md_href_map(pages: list[dict]) -> dict[str, str]:
    """Map lowercase *.md basename -> output html (e.g. index.html / slug.html)."""
    m: dict[str, str] = {}
    for p in pages:
        key = Path(p["source"]).name.lower()
        href = "index.html" if p["slug"] == "index" else f"{p['slug']}.html"
        m[key] = href
    return m


def rewrite_cross_doc_links(fragment: str, href_map: dict[str, str]) -> str:
    """Turn [text](./PAGE.md) into [text](slug.html). Skips http(s) and other schemes."""

    def repl(match: re.Match[str]) -> str:
        label = match.group(1)
        url = match.group(2).strip()
        if re.match(r"^[a-z][a-z0-9+.-]*:", url, re.I):
            return match.group(0)
        if url.startswith("#"):
            return match.group(0)
        anchor = ""
        path = url
        if "#" in url:
            path, _, frag = url.partition("#")
            anchor = "#" + frag
        path_stripped = path.strip()
        if path_stripped in (".", "./", ""):
            return f"[{label}](index.html{anchor})"
        if path_stripped.startswith("./"):
            path_stripped = path_stripped[2:]
        key = Path(path_stripped).name.lower()
        if key.endswith(".md") and key in href_map:
            return f"[{label}]({href_map[key]}{anchor})"
        return match.group(0)

    return re.sub(r"\[([^\]]*)\]\(([^)]+)\)", repl, fragment)


def rewrite_backtick_doc_refs(fragment: str, pages: list[dict]) -> str:
    """Turn `SOME.md` (manifest sources) into [Nav title](slug.html). Outside code only."""
    for p in sorted(pages, key=lambda x: -len(x["source"])):
        name = Path(p["source"]).name
        href = "index.html" if p["slug"] == "index" else f"{p['slug']}.html"
        label = p["nav"]
        fragment = re.sub(
            re.compile(re.escape(f"`{name}`"), re.IGNORECASE),
            f"[{label}]({href})",
            fragment,
        )
    return fragment


def prepare_markdown_for_site(md_raw: str, pages: list[dict]) -> str:
    href_map = _build_md_href_map(pages)

    def map_outside_fences(s: str) -> str:
        s = rewrite_cross_doc_links(s, href_map)
        s = rewrite_backtick_doc_refs(s, pages)
        return s

    parts = _FENCED_BLOCK_RE.split(md_raw)
    out: list[str] = []
    for part in parts:
        if part.startswith("```"):
            out.append(part)
        else:
            out.append(map_outside_fences(part))
    return "".join(out)


def escape_attr(s: str) -> str:
    return html.escape(s, quote=True)


def slugify_heading(html_fragment: str) -> str:
    """GitHub-like slug: strip tags, lowercase, keep [a-z0-9-], spaces -> '-'."""
    plain = re.sub(r"<[^>]+>", "", html_fragment)
    plain = html.unescape(plain).lower()
    plain = re.sub(r"[^a-z0-9\s-]", "", plain)
    plain = re.sub(r"\s+", "-", plain.strip())
    plain = re.sub(r"-+", "-", plain)
    return plain


def inline_md(text: str) -> str:
    """Limited inline: code `...`, **bold**, *italic*, [text/url], ![alt](url).

    Bold/italic must be able to span across inline code / links / images, e.g.
    `**Mark every field as ` + "`SaveGame`" + `.**`. To make that work we first
    tokenize HTML-producing spans into placeholders, then apply bold/italic on
    the combined text, then restore placeholders.
    """
    if not text:
        return ""

    html_pieces: list[str] = []

    def emit_html(rendered: str) -> str:
        idx = len(html_pieces)
        html_pieces.append(rendered)
        return f"\x00H{idx}\x00"

    parts: list[str] = []
    pos = 0
    n = len(text)
    while pos < n:
        if text[pos] == "`":
            end = text.find("`", pos + 1)
            if end != -1:
                raw = text[pos + 1 : end]
                inner = highlight_cpp(raw)
                parts.append(emit_html(f'<code class="hl-inline">{inner}</code>'))
                pos = end + 1
                continue
        if text.startswith("![", pos):
            m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", text[pos:])
            if m:
                alt, url = m.group(1), m.group(2)
                parts.append(
                    emit_html(
                        f'<img src="{escape_attr(url)}" alt="{escape_attr(alt)}">'
                    )
                )
                pos += m.end()
                continue
        if text[pos] == "[":
            m = re.match(r"\[([^\]]*)\]\(([^)]+)\)", text[pos:])
            if m:
                label, url = m.group(1), m.group(2)
                parts.append(
                    emit_html(
                        f'<a href="{escape_attr(url)}">{inline_md(label)}</a>'
                    )
                )
                pos += m.end()
                continue
        next_code = text.find("`", pos)
        next_img = text.find("![", pos)
        next_link = text.find("[", pos)
        candidates = [p for p in (next_code, next_img, next_link) if p != -1]
        nxt = min(candidates) if candidates else -1
        # Unmatched "[...]" (no link) would leave nxt == pos forever.
        if nxt == pos:
            parts.append(text[pos : pos + 1])
            pos += 1
            continue
        segment = text[pos:nxt] if nxt != -1 else text[pos:]
        parts.append(segment)
        pos = nxt if nxt != -1 else n

    combined = _bold_italic_segment("".join(parts))

    def restore(m: re.Match) -> str:
        return html_pieces[int(m.group(1))]

    return re.sub(r"\x00H(\d+)\x00", restore, combined)


def _bold_italic_segment(s: str) -> str:
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*(?!\*)([^*]+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", s)
    return s


_CPP_KEYWORDS = frozenset(
    {
        "alignas",
        "alignof",
        "and",
        "and_eq",
        "asm",
        "auto",
        "bitand",
        "bitor",
        "bool",
        "break",
        "case",
        "catch",
        "char",
        "char8_t",
        "char16_t",
        "char32_t",
        "class",
        "compl",
        "concept",
        "const",
        "consteval",
        "constexpr",
        "constinit",
        "const_cast",
        "continue",
        "co_await",
        "co_return",
        "co_yield",
        "decltype",
        "default",
        "delete",
        "do",
        "double",
        "dynamic_cast",
        "else",
        "enum",
        "explicit",
        "export",
        "extern",
        "false",
        "final",
        "float",
        "for",
        "friend",
        "goto",
        "if",
        "import",
        "inline",
        "int",
        "long",
        "module",
        "mutable",
        "namespace",
        "new",
        "noexcept",
        "not",
        "not_eq",
        "nullptr",
        "operator",
        "or",
        "or_eq",
        "override",
        "private",
        "protected",
        "public",
        "register",
        "reinterpret_cast",
        "requires",
        "return",
        "short",
        "signed",
        "sizeof",
        "static",
        "static_assert",
        "static_cast",
        "struct",
        "switch",
        "template",
        "this",
        "thread_local",
        "throw",
        "true",
        "try",
        "typedef",
        "typeid",
        "typename",
        "union",
        "unsigned",
        "using",
        "virtual",
        "void",
        "volatile",
        "wchar_t",
        "while",
        "xor",
        "xor_eq",
    }
)

_CPP_TYPES = frozenset(
    {
        "size_t",
        "int8_t",
        "int16_t",
        "int32_t",
        "int64_t",
        "uint8_t",
        "uint16_t",
        "uint32_t",
        "uint64_t",
        "intptr_t",
        "uintptr_t",
        "ptrdiff_t",
        "TCHAR",
        "FString",
        "FName",
        "FText",
        "TArray",
        "TMap",
        "TSet",
        "TSubclassOf",
        "TSoftObjectPtr",
        "TSoftClassPtr",
        "TSharedPtr",
        "TUniquePtr",
        "TWeakPtr",
        "TObjectPtr",
        "UObject",
        "AActor",
        "UActorComponent",
        "UWorld",
        "FVector",
        "FRotator",
        "FTransform",
        "FQuat",
        "FBox",
        "FColor",
        "FLinearColor",
    }
)

_CPP_MACROS = frozenset(
    {
        "TEXT",
        "UPROPERTY",
        "UFUNCTION",
        "UCLASS",
        "USTRUCT",
        "UENUM",
        "UMETA",
        "GENERATED_BODY",
        "SUPER",
        "offsetof",
    }
)


def _cpp_line_start(code: str, i: int) -> bool:
    j = i - 1
    while j >= 0 and code[j] in " \t":
        j -= 1
    return j < 0 or code[j] == "\n"


def highlight_cpp(code: str) -> str:
    """Return HTML (already escaped inside spans) for a C++ code block."""
    parts: list[str] = []
    i = 0
    n = len(code)

    def emit_span(cls: str, text: str) -> None:
        parts.append(f'<span class="hl-{cls}">{html.escape(text)}</span>')

    while i < n:
        ch = code[i]

        if ch == "/" and i + 1 < n and code[i + 1] == "/":
            j = i
            while j < n and code[j] != "\n":
                j += 1
            emit_span("comment", code[i:j])
            i = j
            continue

        if ch == "/" and i + 1 < n and code[i + 1] == "*":
            end = code.find("*/", i + 2)
            if end == -1:
                emit_span("comment", code[i:])
                break
            emit_span("comment", code[i : end + 2])
            i = end + 2
            continue

        if ch == '"':
            j = i + 1
            while j < n:
                if code[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if code[j] == '"':
                    j += 1
                    break
                j += 1
            emit_span("string", code[i:j])
            i = j
            continue

        if ch == "'":
            j = i + 1
            while j < n:
                if code[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if code[j] == "'":
                    j += 1
                    break
                j += 1
            emit_span("string", code[i:j])
            i = j
            continue

        if _cpp_line_start(code, i) and ch == "#":
            j = i
            while j < n and code[j] != "\n":
                j += 1
            emit_span("preproc", code[i:j])
            i = j
            continue

        if ch.isdigit() or (ch == "." and i + 1 < n and code[i + 1].isdigit()):
            j = i
            if ch == "0" and i + 1 < n and code[i + 1] in "xX":
                j = i + 2
                while j < n and code[j] in "0123456789abcdefABCDEF":
                    j += 1
            else:
                while j < n and (code[j].isdigit() or code[j] in "._eE+-"):
                    j += 1
                while j < n and code[j] in "fFlLuUzZ":
                    j += 1
            emit_span("number", code[i:j])
            i = j
            continue

        if ch.isalpha() or ch == "_":
            j = i + 1
            while j < n and (code[j].isalnum() or code[j] == "_"):
                j += 1
            word = code[i:j]
            if word in _CPP_KEYWORDS:
                emit_span("keyword", word)
            elif word in _CPP_MACROS:
                emit_span("macro", word)
            elif word in _CPP_TYPES:
                emit_span("type", word)
            elif len(word) >= 2 and word[0] in "FUTHEDA" and word[1].isupper():
                emit_span("type", word)
            else:
                parts.append(html.escape(word))
            i = j
            continue

        parts.append(html.escape(ch))
        i += 1

    return "".join(parts)


def _is_cpp_fence_lang(lang: str) -> bool:
    l = lang.lower().strip()
    return l in (
        "cpp",
        "c++",
        "cxx",
        "c",
        "h",
        "hpp",
        "hh",
        "hxx",
        "inl",
        "ue",
        "unreal",
    )


def _split_tab_panels(inner: str) -> list[tuple[str, str]]:
    lines = inner.split("\n")
    panels: list[tuple[str, str]] = []
    current_label: str | None = None
    current_lines: list[str] = []
    for line in lines:
        m = re.match(r"^===\s+(.+)$", line)
        if m:
            if current_label is not None:
                panels.append((current_label, "\n".join(current_lines).strip()))
            current_label = m.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_label is not None:
        panels.append((current_label, "\n".join(current_lines).strip()))
    return panels


def _render_doc_tabs(inner: str, counter: list[int]) -> str:
    panels = _split_tab_panels(inner)
    if len(panels) < 2:
        return convert_markdown_body(inner)

    gid = counter[0]
    counter[0] += 1
    base = f"doctab-{gid}"
    wrap_class = f"doc-tabs-g{gid}"
    radios: list[str] = []
    labels_html: list[str] = []
    panels_html: list[str] = []
    style_rules: list[str] = [
        f".{wrap_class} .doc-tabs-panel {{ display: none; }}",
        f".{wrap_class} .doc-tabs-labels label {{ color: var(--text-muted); border-bottom-color: transparent; font-weight: 500; }}",
    ]
    for idx, (label, body) in enumerate(panels):
        rid = f"{base}-{idx}"
        checked = " checked" if idx == 0 else ""
        radios.append(
            f'<input type="radio" name="{escape_attr(base)}" id="{escape_attr(rid)}" class="doc-tabs-sr"{checked}>'
        )
        labels_html.append(
            f'<label for="{escape_attr(rid)}">{html.escape(label)}</label>'
        )
        body_html = convert_markdown_body(body) if body.strip() else ""
        panels_html.append(
            f'<div class="doc-tabs-panel doc-tabs-panel--{idx}"><div class="doc-tabs-panel-inner">{body_html}</div></div>'
        )
        style_rules.append(
            f".{wrap_class} #{rid}:checked ~ .doc-tabs-panels .doc-tabs-panel--{idx} {{ display: block; }}"
        )
        style_rules.append(
            f".{wrap_class} #{rid}:checked ~ .doc-tabs-labels label:nth-child({idx + 1}) "
            f"{{ color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; }}"
        )

    style_html = "<style>" + " ".join(style_rules) + "</style>"

    return (
        f'<div class="doc-tabs {wrap_class}">'
        + style_html
        + "".join(radios)
        + '<div class="doc-tabs-labels">'
        + "".join(labels_html)
        + '</div><div class="doc-tabs-panels">'
        + "".join(panels_html)
        + "</div></div>"
    )


def _convert_markdown_lines(lines: list[str]) -> str:
    blocks: list[tuple] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            lang = line[3:].strip()
            i += 1
            buf: list[str] = []
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            raw = "\n".join(buf)
            if _is_cpp_fence_lang(lang):
                code = highlight_cpp(raw)
            else:
                code = html.escape(raw)
            fence = f'<pre><code class="language-{html.escape(lang)} hl-code">{code}</code></pre>'
            blocks.append(("raw", fence))
            continue

        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            blocks.append(("h", level, inline_md(m.group(2))))
            i += 1
            continue

        if re.match(r"^(-{3,}|\*{3,})\s*$", stripped):
            blocks.append(("hr",))
            i += 1
            continue

        if re.match(r"^\s*>\s?", line):
            quote_lines: list[str] = []
            while i < len(lines):
                ln = lines[i]
                qm = re.match(r"^\s*>\s?(.*)$", ln)
                if qm:
                    quote_lines.append(qm.group(1))
                    i += 1
                    continue
                # Keep a plain blank line if it separates quoted chunks.
                if not ln.strip() and i + 1 < len(lines) and re.match(r"^\s*>\s?", lines[i + 1]):
                    quote_lines.append("")
                    i += 1
                    continue
                break
            quote_body = convert_markdown_body("\n".join(quote_lines))
            blocks.append(("blockquote", quote_body))
            continue

        ulm = re.match(r"^[-*]\s+(.*)$", line)
        olm = re.match(r"^(\d+)\.\s+(.*)$", line)
        if ulm or olm:
            ordered = bool(olm)
            start_num = int(olm.group(1)) if olm else 1
            items: list[str] = []
            while i < len(lines):
                ln = lines[i]
                um = re.match(r"^[-*]\s+(.*)$", ln)
                om = re.match(r"^(\d+)\.\s+(.*)$", ln)
                if ordered and om:
                    items.append(inline_md(om.group(2)))
                    i += 1
                elif not ordered and um:
                    items.append(inline_md(um.group(1)))
                    i += 1
                elif not ln.strip():
                    break
                else:
                    break
            blocks.append(("list", "ol" if ordered else "ul", items, start_num))
            continue

        para: list[str] = []
        while i < len(lines):
            ln = lines[i]
            if not ln.strip():
                break
            if ln.startswith("```"):
                break
            if re.match(r"^(#{1,6})\s+", ln):
                break
            if re.match(r"^(-{3,}|\*{3,})\s*$", ln.strip()):
                break
            if re.match(r"^\s*>\s?", ln):
                break
            if re.match(r"^[-*]\s+", ln) or re.match(r"^\d+\.\s+", ln):
                break
            para.append(ln.strip())
            i += 1
        merged = " ".join(para)
        blocks.append(("p", inline_md(merged)))
        continue

    out: list[str] = []
    for b in blocks:
        if b[0] == "raw":
            out.append(b[1])
        elif b[0] == "h":
            slug = slugify_heading(b[2])
            if slug:
                out.append(f'<h{b[1]} id="{escape_attr(slug)}">{b[2]}</h{b[1]}>')
            else:
                out.append(f"<h{b[1]}>{b[2]}</h{b[1]}>")
        elif b[0] == "hr":
            out.append("<hr>")
        elif b[0] == "p":
            out.append(f"<p>{b[1]}</p>")
        elif b[0] == "list":
            tag = b[1]
            items = b[2]
            start = b[3] if len(b) > 3 else 1
            lis = "".join(f"<li>{item}</li>" for item in items)
            if tag == "ol" and start != 1:
                out.append(f'<ol start="{start}">{lis}</ol>')
            else:
                out.append(f"<{tag}>{lis}</{tag}>")
        elif b[0] == "blockquote":
            out.append(f"<blockquote class=\"footnote\">{b[1]}</blockquote>")
    return "\n".join(out)


def convert_markdown_body(md_chunk: str) -> str:
    if not md_chunk.strip():
        return ""
    lines = md_chunk.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return _convert_markdown_lines(lines)


def convert_markdown(md_raw: str, pages: list[dict] | None = None) -> str:
    md_raw = normalize_md_paths(md_raw)
    if pages:
        md_raw = prepare_markdown_for_site(md_raw, pages)
    md_raw = md_raw.replace("\r\n", "\n").replace("\r", "\n")
    tab_rx = re.compile(r"<<<DOCtabs>>>\s*\n(.*?)<<<ENDtabs>>>\s*", re.DOTALL)
    counter: list[int] = [0]
    out: list[str] = []
    pos = 0
    for m in tab_rx.finditer(md_raw):
        if m.start() > pos:
            prefix = md_raw[pos : m.start()]
            if prefix.strip():
                out.append(convert_markdown_body(prefix))
        out.append(_render_doc_tabs(m.group(1), counter))
        pos = m.end()
    if pos < len(md_raw):
        suffix = md_raw[pos:]
        if suffix.strip():
            out.append(convert_markdown_body(suffix))
    return "\n".join(out)


def load_manifest() -> tuple[list[dict], list[dict]]:
    """Return (flat page list, sidebar groups). Supports legacy flat ``pages`` manifest."""
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if "sidebar" in data:
        groups = data["sidebar"]
        pages: list[dict] = []
        for group in groups:
            pages.extend(group.get("pages", []))
        return pages, groups
    pages = data["pages"]
    return pages, [{"label": "Sections", "pages": pages}]


def nav_html(groups: list[dict], current_slug: str) -> str:
    parts: list[str] = []
    for index, group in enumerate(groups):
        label = html.escape(group.get("label", "Sections"))
        items: list[str] = []
        for p in group.get("pages", []):
            slug = p["slug"]
            href = "index.html" if slug == "index" else f"{slug}.html"
            cls = ' class="is-active"' if slug == current_slug else ""
            item_label = html.escape(p["nav"])
            items.append(f'<li><a{cls} href="{escape_attr(href)}">{item_label}</a></li>')
        spaced = " sidebar__group--spaced" if index > 0 else ""
        parts.append(
            f'<div class="sidebar__group{spaced}">'
            f'<p class="sidebar__label">{label}</p><ul>'
            + "".join(items)
            + "</ul></div>"
        )
    return "".join(parts)


def page_shell(
    *,
    site_name: str,
    tagline: str,
    doc_title: str,
    body: str,
    nav: str,
) -> str:
    title_el = html.escape(doc_title)
    site_el = html.escape(site_name)
    tag_el = html.escape(tagline) if tagline else ""
    home_href = "index.html"
    tagline_block = (
        f'<p class="site-header__tagline">{tag_el}</p>' if tag_el else ""
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title_el} — {site_el}</title>
  <meta name="description" content="{tag_el}">
  <link rel="stylesheet" href="assets/docs.css">
</head>
<body>
  <header class="site-header">
    <div class="site-header__inner">
      <img class="site-header__icon" src="assets/images/ActionGraph.svg" alt="" width="40" height="40">
      <div class="site-header__brand">
        <h1 class="site-header__title"><a href="{home_href}">{site_el}</a></h1>
        {tagline_block}
      </div>
    </div>
  </header>
  <div class="layout">
    <nav class="sidebar" aria-label="Documentation sections">
      {nav}
    </nav>
    <main class="content">
      <article class="prose">
        {body}
      </article>
    </main>
  </div>
</body>
</html>
"""


def copy_images() -> None:
    dest = DIST / "assets" / "images"
    dest.mkdir(parents=True, exist_ok=True)
    if DOCS_IMAGES.is_dir():
        for f in DOCS_IMAGES.iterdir():
            if f.is_file():
                shutil.copy2(f, dest / f.name)
    res = PLUGIN_ROOT / "Resources"
    if res.is_dir():
        for f in res.iterdir():
            if f.is_file() and f.suffix.lower() in (
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".webp",
                ".svg",
            ):
                shutil.copy2(f, dest / f.name)


SCRIPT_PATH = Path(__file__).resolve()


def _watched_paths(pages: list[dict]) -> list[Path]:
    """Files whose mtime should trigger a rebuild."""
    raw: list[Path] = [MANIFEST, UPLUGIN, SCRIPT_PATH]
    if ASSETS_SRC.is_dir():
        raw.extend(p for p in ASSETS_SRC.rglob("*") if p.is_file())
    for page in pages:
        raw.append(DOCS_ROOT / page["source"])
    if DOCS_IMAGES.is_dir():
        raw.extend(f for f in DOCS_IMAGES.iterdir() if f.is_file())
    res = PLUGIN_ROOT / "Resources"

    seen: set[str] = set()
    out: list[Path] = []
    for p in raw:
        try:
            key = str(p.resolve())
        except OSError:
            continue
        if key in seen:
            continue
        seen.add(key)
        if p.is_file():
            out.append(p)
    return out


def _mtime_snapshot(paths: list[Path]) -> dict[str, float]:
    snap: dict[str, float] = {}
    for p in paths:
        k = str(p.resolve())
        try:
            snap[k] = p.stat().st_mtime
        except OSError:
            snap[k] = -1.0
    return snap


def build_site() -> bool:
    if not DOCS_ROOT.is_dir():
        print(f"Docs content folder not found: {DOCS_ROOT}", file=sys.stderr)
        return False

    pages, groups = load_manifest()
    site_name, tagline = load_plugin_meta()

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    shutil.copytree(ASSETS_SRC, DIST / "assets")
    copy_images()

    for p in pages:
        slug = p["slug"]
        md_path = DOCS_ROOT / p["source"]
        if not md_path.is_file():
            print(f"Missing source: {md_path}", file=sys.stderr)
            return False

        body = convert_markdown(md_path.read_text(encoding="utf-8"), pages)
        m = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.DOTALL)
        doc_title = re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else p["nav"]

        nav = nav_html(groups, slug)
        out_name = "index.html" if slug == "index" else f"{slug}.html"
        html_out = page_shell(
            site_name=site_name,
            tagline=tagline,
            doc_title=doc_title,
            body=body,
            nav=nav,
        )
        (DIST / out_name).write_text(html_out, encoding="utf-8")

    print(f"Wrote {len(pages)} page(s) to {DIST}", flush=True)
    return True


def run_watch(interval_sec: float) -> None:
    print(
        f"Watching docs sources (poll every {interval_sec} s). Ctrl+C to stop.",
        flush=True,
    )
    last_snap: dict[str, float] | None = None
    try:
        while True:
            pages, _groups = load_manifest()
            paths = _watched_paths(pages)
            snap = _mtime_snapshot(paths)
            if snap != last_snap:
                if last_snap is not None:
                    print("Change detected, rebuilding…", flush=True)
                build_site()
                last_snap = snap
            time.sleep(max(0.1, interval_sec))
    except KeyboardInterrupt:
        print("\nStopped.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Scene Director static docs.")
    parser.add_argument(
        "-w",
        "--watch",
        action="store_true",
        help="Rebuild when manifest, .md, assets, uplugin, or this script change.",
    )
    parser.add_argument(
        "-i",
        "--interval",
        type=float,
        default=0.7,
        metavar="SEC",
        help="Poll interval in watch mode (default: 0.7).",
    )
    args = parser.parse_args()

    if args.watch:
        run_watch(args.interval)
    elif not build_site():
        sys.exit(1)


if __name__ == "__main__":
    main()
