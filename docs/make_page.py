#!/usr/bin/env python3
"""Write docs/index.html: a static project page (title, claim, figure, links, the case browser).

Standard library only. The page is one self-contained HTML file plus the images in docs/img/. It loads no
script, font, stylesheet or tracker from anywhere, so it can be opened from disk or served by GitHub Pages.
Text and links come from docs/page.json; the case browser is docs/cases.md converted to HTML. Run from the repo root:

    python3 docs/make_page.py
"""
import html
import json
import pathlib
import re
import shutil

DOCS = pathlib.Path(__file__).resolve().parent
ROOT = DOCS.parent
CFG = json.loads((DOCS / "page.json").read_text(encoding="utf-8"))

CSS = """
:root{--ink:#1c1c1a;--ink2:#55554f;--line:#dcdbd6;--bg:#fbfaf7;--card:#ffffff;--accent:#0b5cad}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.6 Georgia,'Times New Roman',serif}
main{max-width:860px;margin:0 auto;padding:48px 20px 80px}
h1{font-size:2.1rem;line-height:1.2;text-align:center;margin:0 0 10px}
h2{font-size:1.35rem;margin:44px 0 10px;padding-top:14px;border-top:1px solid var(--line)}
h3{font-size:1.05rem;margin:30px 0 6px;font-family:ui-monospace,Menlo,Consolas,monospace}
.by{text-align:center;color:var(--ink2);margin:0 0 18px}
.claim{font-size:1.15rem;text-align:center;margin:18px auto 22px;max-width:720px}
.links{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin:0 0 28px;padding:0;list-style:none}
.links a{display:inline-block;padding:7px 16px;border-radius:999px;background:var(--ink);color:#fff;
  text-decoration:none;font:600 .9rem/1.4 system-ui,-apple-system,'Segoe UI',sans-serif}
.links a:hover{background:var(--accent)}
figure{margin:0 0 8px}
figure img{width:100%;height:auto;border:1px solid var(--line);border-radius:6px;background:#fff}
figcaption{color:var(--ink2);font-size:.92rem;margin-top:8px}
a{color:var(--accent)}
code{font:.88em ui-monospace,Menlo,Consolas,monospace;background:#f0efea;padding:1px 4px;border-radius:3px}
pre{font:.82rem/1.5 ui-monospace,Menlo,Consolas,monospace;background:var(--card);border:1px solid var(--line);
  border-radius:6px;padding:12px 14px;overflow-x:auto;white-space:pre-wrap;word-break:break-word}
pre code{background:none;padding:0}
blockquote{margin:8px 0 8px 0;padding:6px 14px;border-left:3px solid var(--line);color:var(--ink2);
  font-size:.92rem;overflow-wrap:anywhere}
details{margin:8px 0;padding:6px 12px;border:1px solid var(--line);border-radius:6px;background:var(--card)}
summary{cursor:pointer;font:.92rem/1.5 system-ui,-apple-system,'Segoe UI',sans-serif}
footer{margin-top:56px;padding-top:14px;border-top:1px solid var(--line);color:var(--ink2);font-size:.88rem}
@media (max-width:600px){body{font-size:16px}h1{font-size:1.6rem}main{padding:28px 16px 60px}}
"""


def inline(s, escaped=False):
    """Markdown inline code and bold to HTML. `escaped` means &, < and > are already entities."""
    if not escaped:
        s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)


def cases_html(md):
    """Convert docs/cases.md (a fixed, generated structure) to HTML. Returns (intro, body)."""
    out, para, quote, items = [], [], [], []
    lines = md.split("\n")

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>"); para.clear()
        if quote:
            out.append("<blockquote>" + "<br>".join(inline(q, escaped=True) for q in quote) + "</blockquote>"); quote.clear()
        if items:
            out.append("<ul>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ul>"); items.clear()

    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("````"):
            flush()
            j = i + 1
            while not lines[j].startswith("````"):
                j += 1
            out.append("<pre>" + html.escape("\n".join(lines[i + 1:j]), quote=False) + "</pre>")
            i = j
        elif ln.startswith("# "):
            flush()                                  # the page has its own title
        elif ln.startswith("## "):
            flush(); out.append(f"<h3>{inline(ln[3:])}</h3>")
        elif ln.startswith("<details>") or ln.startswith("</details>"):
            flush(); out.append(ln)                  # written by make_cases.py with its own escaping
        elif ln.startswith(">"):
            if para or items:
                flush()
            quote.append(ln[1:].strip())
        elif ln.startswith("- "):
            if para or quote:
                flush()
            items.append(ln[2:])
        elif not ln.strip():
            flush()
        else:
            if quote or items:
                flush()
            para.append(ln)
        i += 1
    flush()
    return "\n".join(out)


def main():
    img = DOCS / "img"
    img.mkdir(exist_ok=True)
    for f in CFG["figures"]:
        shutil.copyfile(ROOT / f["src"], img / pathlib.Path(f["src"]).name)
    e = lambda s: inline(s)  # noqa: E731
    links = "".join(f'<li><a href="{html.escape(u)}">{html.escape(t)}</a></li>' for t, u in CFG["links"])
    figs = "".join(
        f'<figure><img src="img/{pathlib.Path(f["src"]).name}" alt="{html.escape(f["alt"])}">'
        f'<figcaption>{e(f["caption"])}</figcaption></figure>' for f in CFG["figures"][:1])
    more = "".join(
        f'<h2>{html.escape(f["heading"])}</h2><figure><img src="img/{pathlib.Path(f["src"]).name}" '
        f'alt="{html.escape(f["alt"])}"><figcaption>{e(f["caption"])}</figcaption></figure>' for f in CFG["figures"][1:])
    bullets = "".join(f"<li>{e(b)}</li>" for b in CFG["bullets"])
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(CFG["title"])}</title>
<meta name="description" content="{html.escape(CFG["description"])}">
<style>{CSS}</style>
</head>
<body>
<main>
<h1>{html.escape(CFG["title"])}</h1>
<p class="by">{html.escape(CFG["byline"])}</p>
<p class="claim">{e(CFG["claim"])}</p>
<ul class="links">{links}</ul>
{figs}
<h2>Summary</h2>
<ul>{bullets}</ul>
<h2>Reproduce</h2>
<pre>{html.escape(CFG["reproduce"], quote=False)}</pre>
{more}
<h2 id="cases">{html.escape(CFG["cases_heading"])}</h2>
{cases_html((DOCS / "cases.md").read_text(encoding="utf-8"))}
<h2>Cite</h2>
<pre>{html.escape(CFG["bibtex"], quote=False)}</pre>
<footer>{e(CFG["footer"])}</footer>
</main>
</body>
</html>
"""
    out = DOCS / "index.html"
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}: {out.stat().st_size} bytes")


if __name__ == "__main__":
    main()
