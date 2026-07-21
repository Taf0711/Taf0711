"""Render the GitHub contribution graph as a RobCo-style phosphor CRT readout.

Fetches the public /users/{user}/contributions fragment (no token needed),
parses data-date / data-level / grid position, and emits an SVG that shares
its visual language with assets/terminal-header.svg (same bezel, scanlines,
phosphor greens, glow). Runs in GitHub Actions, output pushed to `output/`.

No third-party deps.
"""
from __future__ import annotations

import datetime as dt
import re
import sys
import urllib.request

USER = "Taf0711"
URL = f"https://github.com/users/{USER}/contributions"

# --- layout ---------------------------------------------------------------
W = 680
BEZEL = 2
INSET_X = 18
HEADER_Y = 22
RULE_Y = 32
CELL = 10
GAP = 2
STEP = CELL + GAP
COLS = 53
ROWS = 7
GRID_X = INSET_X
GRID_Y = 46
FOOTER_Y = GRID_Y + ROWS * STEP + 18
H = FOOTER_Y + 14

# phosphor scale by contribution level (0 = empty slot)
LEVEL_FILL = ["#0a2818", "#1a9940", "#22cc55", "#33ff66", "#9fff9f"]
BG = "#020803"
FACE = "#041006"
BORDER = "#0d2818"
DIM = "#1a9940"
FAINT = "#0a3d18"
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"


def parse(html: str) -> tuple[list[tuple[int, int, int]], int]:
    """Return ([(col, row, level)], total_contributions) from the fragment."""
    # id is component-ROW-COL (row = day-of-week 0..6, col = week 0..52)
    cells = re.findall(
        r'id="contribution-day-component-(\d+)-(\d+)" data-level="(\d)"', html
    )
    if not cells:
        raise RuntimeError("no contribution cells parsed — markup changed?")
    grid = [(int(c), int(r), int(l)) for r, c, l in cells]

    m = re.search(r"([\d,]+)\s+contributions\s+in the last year", html)
    total = int(m.group(1).replace(",", "")) if m else -1
    return grid, total


def fetch() -> tuple[list[tuple[int, int, int]], int]:
    req = urllib.request.Request(URL, headers={"User-Agent": "activity-log"})
    html = urllib.request.urlopen(req, timeout=20).read().decode()
    return parse(html)


def render(grid: list[tuple[int, int, int]], total: int) -> str:
    rects = []
    for col, row, level in grid:
        x = GRID_X + col * STEP
        y = GRID_Y + row * STEP
        fill = LEVEL_FILL[min(level, 4)]
        # hot cells (level 4) get the phosphor bloom
        flt = ' filter="url(#glow)"' if level >= 3 else ""
        rects.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
            f'fill="{fill}"{flt}/>'
        )

    total_s = f"{total:,}" if total >= 0 else "N/A"
    year = dt.date.today().year

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub activity log: {total_s} contributions in the last year">
<defs>
<filter id="glow" x="-30%" y="-30%" width="160%" height="160%" color-interpolation-filters="sRGB">
<feGaussianBlur in="SourceGraphic" stdDeviation="1.4" result="b"/>
<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
<radialGradient id="vignette" cx="50%" cy="48%" r="70%">
<stop offset="55%" stop-color="{BG}" stop-opacity="0"/>
<stop offset="100%" stop-color="{BG}" stop-opacity="0.85"/>
</radialGradient>
<pattern id="scan" width="3" height="3" patternUnits="userSpaceOnUse">
<rect width="3" height="2" fill="#000000" opacity="0"/>
<rect y="2" width="3" height="1" fill="#000000" opacity="0.28"/>
</pattern>
</defs>
<rect width="{W}" height="{H}" rx="4" ry="4" fill="{BG}" stroke="{BORDER}" stroke-width="{BEZEL}"/>
<rect x="4" y="4" width="{W - 8}" height="{H - 8}" rx="2" ry="2" fill="{FACE}"/>
<rect width="{W}" height="{H}" fill="url(#scan)" opacity="0.9"/>
<text x="{INSET_X}" y="{HEADER_Y}" font-family="{FONT}" font-size="12" font-weight="700" letter-spacing="1.4" fill="{DIM}">ACTIVITY LOG // USER: {USER}</text>
<text x="{W - INSET_X}" y="{HEADER_Y}" text-anchor="end" font-family="{FONT}" font-size="11" font-weight="700" letter-spacing="1.2" fill="{DIM}">ONLINE</text>
<line x1="{INSET_X}" y1="{RULE_Y}" x2="{W - INSET_X}" y2="{RULE_Y}" stroke="{FAINT}" stroke-width="1"/>
{''.join(rects)}
<text x="{INSET_X}" y="{FOOTER_Y}" font-family="{FONT}" font-size="11" font-weight="600" letter-spacing="1" fill="{DIM}">&gt; {total_s} OPERATIONS LOGGED [365D]</text>
<rect width="{W}" height="{H}" fill="url(#vignette)"/>
</svg>'''


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "activity-log.svg"
    src = sys.argv[2] if len(sys.argv) > 2 else None
    if src:  # local test: read a curl'd fragment instead of fetching
        grid, total = parse(open(src).read())
    else:
        grid, total = fetch()
    assert len(grid) > 300, f"suspiciously few cells: {len(grid)}"
    svg = render(grid, total)
    with open(out, "w") as f:
        f.write(svg)
    print(f"wrote {out} ({len(svg)} bytes, {len(grid)} cells, {total} contributions)")
