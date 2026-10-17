"""Convert an adilet.zan.kz act (JSON from /api/documents/by-ngr/<code>?language=rus) to Markdown.

Usage: python3 -I research/adilet_to_md.py <act.json> <out.md>
Paragraph ids (zNN) are kept as <a id="zNN"></a> anchors, so links like
https://adilet.zan.kz/rus/docs/<code>#zNN map 1:1 onto the Markdown file.
"""
import html
import json
import re
import sys

ADILET = "https://adilet.zan.kz"


def inline(fragment: str) -> str:
    """HTML fragment -> one line of Markdown text with links."""
    s = re.sub(r"<br\s*/?>", " ", fragment)
    s = re.sub(
        r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>',
        lambda m: f"[{m.group(2)}]({ADILET + m.group(1) if m.group(1).startswith('/') else m.group(1)})",
        s,
        flags=re.S,
    )
    s = re.sub(r"</b>\s*<b>", "", s)  # adilet splits words across adjacent <b> tags
    s = re.sub(r"<b>(.*?)</b>", r"**\1**", s, flags=re.S)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s.replace("*****", "")


def table_to_md(tbl: str) -> str:
    rows = [
        [inline(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)]
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tbl, flags=re.S)
    ]
    rows = [r for r in rows if any(r)]
    if not rows:
        return ""
    if len(rows) == 1:  # layout table: signature or appendix header
        return " — ".join(c for c in rows[0] if c)
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    esc = lambda c: c.replace("|", "\\|")
    lines = ["| " + " | ".join(esc(c) for c in rows[0]) + " |", "|" + "---|" * width]
    lines += ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows[1:]]
    return "\n".join(lines)


def heading_level(text: str) -> str:
    if text.startswith("Параграф"):
        return "###"
    return "##"


# Block boundaries; everything between two boundaries is one Markdown paragraph.
# Splitting (instead of matching <p>…</p>) keeps text that adilet puts outside <p>:
# red ИЗПИ notes in bare <font>, "Сноска"/"Исключен" spans, tails of forms.
BOUNDARY = re.compile(r"(<p\b[^>]*>|</p>|<br\s*/?>|<h3\b[^>]*>|</h3>|\x00T\d+\x00)")
ANCHOR = re.compile(r'<a name="(z\d+)"></a>|<(?:p|h3)\b[^>]*\bid="(z\d+)"')
NOTE_MARKERS = ("<font", 'class="note"')


def convert(text_content: str) -> str:
    """Act HTML body -> Markdown body (no title header)."""
    tables: list[str] = []

    def stash(m: re.Match) -> str:
        tables.append(m.group(0))
        return f"\x00T{len(tables) - 1}\x00"

    t = re.sub(r"<table.*?</table>", stash, text_content, flags=re.S)
    out: list[str] = []
    anchors: list[str] = []
    in_heading = False
    for chunk in BOUNDARY.split(t):
        table = re.fullmatch(r"\x00T(\d+)\x00", chunk)
        scope = tables[int(table.group(1))] if table else chunk
        anchors += [a or pid for a, pid in ANCHOR.findall(scope)]
        if chunk.startswith("<h3"):
            in_heading = True
        if chunk == "</h3>":
            in_heading = False
        text = table_to_md(tables[int(table.group(1))]) if table else (
            "" if BOUNDARY.fullmatch(chunk) else inline(chunk)
        )
        if not text:
            continue
        tag = "".join(f'<a id="{a}"></a>' for a in dict.fromkeys(anchors))
        anchors = []
        if table and text.startswith("|"):
            out += ([tag] if tag else []) + [text, ""]
        elif in_heading:
            out += [f"{heading_level(text)} {tag}{text}", ""]
        elif bold := re.fullmatch(r"\*\*((?:Раздел|Глава|Параграф|Статья) \d.*?)\*\*", text):
            # laws mark structure as a bold <p>, not <h3>
            level = {"Раздел": "##", "Глава": "##", "Параграф": "###"}.get(bold.group(1).split()[0], "###")
            out += [f"{level} {tag}{bold.group(1)}", ""]
        elif any(mk in chunk for mk in NOTE_MARKERS) or text.startswith(("Сноска", "Примечание ИЗПИ")):
            out += [f"> {tag}{text}", ""]
        else:
            out += [tag + text, ""]
    return "\n".join(out).rstrip() + "\n"


def main() -> None:
    src, dst = sys.argv[1], sys.argv[2]
    data = json.load(open(src, encoding="utf-8"))
    doc = data.get("document")
    if not doc or "text_content" not in doc:
        sys.exit(f"{src}: no document.text_content, not an adilet act JSON")
    code = re.search(r"([VZPK][\w]+?)(?:\.json)?$", src.rsplit("/", 1)[-1]).group(1)
    url = f"{ADILET}/rus/docs/{code}"
    # "voa" = the requisites line adilet prints under the title (also in its PDF export).
    # is_actual stays true for repealed acts, so status comes from this line instead.
    requisites = (doc.get("extended_metadata") or {}).get("voa", "").strip()
    is_repealed = "утратил силу" in requisites.lower() or not doc.get("is_actual")
    status = "**УТРАТИЛ СИЛУ (см. реквизиты)**" if is_repealed else "действующий"
    header = (
        f"# {doc['title_ru']}\n\n"
        + (f"{requisites}\n\n" if requisites else "")
        + f"> Источник: [{url}]({url}) · редакция adilet от {doc['updated_at'][:10]} · {status}\n\n"
    )
    with open(dst, "w", encoding="utf-8") as f:
        f.write(header + convert(doc["text_content"]))


if __name__ == "__main__":
    main()
