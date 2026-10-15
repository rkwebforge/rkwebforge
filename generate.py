"""Render profile.svg: ASCII portrait + live GitHub stats in a CRT terminal.

Standard library only. Set GITHUB_TOKEN to include contribution stats.
"""
import json
import os
import re
import time
import urllib.request
from datetime import datetime, timezone
from xml.sax.saxutils import escape

USER = "rkwebforge"
ROLE = "Full-Stack Developer"
STATUS = "Building | Learning | Shipping"
FRONTEND = "React, Next.js, TanStack, Tailwind CSS"
BACKEND = "Laravel, SQL, AWS & more"
CONTACT = f"github.com/{USER}"

W, H = 980, 470
GREEN, DIM, BG = "#4dffa0", "#1f7a4d", "#03100a"
TOKEN = os.environ.get("GITHUB_TOKEN")

# portrait glyphs, sparse -> dense; no '-' or '=' since runs of them read as bars
RAMP = " .,:;i1tfLCG08@"


def api(path, query=None):
    url = "https://api.github.com" + path
    data = json.dumps({"query": query}).encode() if query else None
    req = urllib.request.Request(url, data=data, headers={"User-Agent": USER})
    if TOKEN:
        req.add_header("Authorization", f"bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def stats():
    user = api(f"/users/{USER}")
    repos = [r for r in api(f"/users/{USER}/repos?per_page=100") if not r["fork"]]
    s = {
        "name": user.get("name") or USER,
        # the USER/USER profile repo is just this card, so leave it out
        "repos": sum(1 for r in repos if r["name"].lower() != USER.lower()),
        "followers": user["followers"],
        "stars": sum(r["stargazers_count"] for r in repos),
        "contributions": "-",
        "active_days": "-",
    }
    if TOKEN:
        q = """{ user(login: "%s") { contributionsCollection { contributionCalendar {
                totalContributions weeks { contributionDays { contributionCount } } } } } }""" % USER
        cal = api("/graphql", q)["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        s["contributions"] = f"{cal['totalContributions']:,}"
        s["active_days"] = sum(
            1 for w in cal["weeks"] for d in w["contributionDays"] if d["contributionCount"]
        )
    return s


def ascii_block(x, y, w, h):
    lines = open(os.path.join(os.path.dirname(__file__), "ascii.txt")).read().splitlines()
    cols = max(len(l) for l in lines)
    lh = h / len(lines)
    lines = [l.ljust(cols) for l in lines]
    out = [f'<g class="art" xml:space="preserve" font-size="{lh * 1.08:.2f}">']
    # one layer per glyph so its brightness can follow its density
    for level, ch in enumerate(RAMP[1:], 1):
        opacity = 0.18 + 0.82 * (level / (len(RAMP) - 1)) ** 1.2
        rows = []
        for i, line in enumerate(lines):
            if ch not in line:
                continue
            layer = "".join(c if c == ch else " " for c in line)
            # textLength pins every row to the same width whatever monospace font renders it
            rows.append(
                f'<text x="{x}" y="{y + (i + 0.85) * lh:.2f}" textLength="{w}" '
                f'lengthAdjust="spacingAndGlyphs">{escape(layer)}</text>'
            )
        if rows:
            out.append(f'<g opacity="{opacity:.2f}">' + "".join(rows) + "</g>")
    out.append("</g>")
    return "\n".join(out)


def info_rows(s, x, y, w, h):
    rows = [
        ("Subject", s["name"]),
        ("Handle", f"@{USER}"),
        ("Role", ROLE),
        ("Status", STATUS),
        ("Frontend", FRONTEND),
        ("Backend", BACKEND),
        ("Public Repos", s["repos"]),
        ("Contributions", s["contributions"]),
        ("Stars", s["stars"]),
        ("Followers", s["followers"]),
        ("Active Days", s["active_days"]),
        ("Contact", CONTACT),
    ]
    out, step = [], h / (len(rows) - 1)
    vx = x + 135
    for i, (k, v) in enumerate(rows):
        ry = y + i * step
        v = str(v)
        # squeeze values wider than the panel (monospace glyph ~0.6em at 14px)
        fit = f' textLength="{x + w - vx}" lengthAdjust="spacingAndGlyphs"' if len(v) * 8.4 > x + w - vx else ""
        out.append(
            f'<g class="row" style="animation-delay:{0.4 + i * 0.18:.2f}s">'
            f'<text x="{x}" y="{ry:.1f}" class="key">{escape(k)}</text>'
            f'<text x="{vx}" y="{ry:.1f}" class="val"{fit}>{escape(v)}</text>'
            f'<line x1="{x}" y1="{ry + 11:.1f}" x2="{x + w}" y2="{ry + 11:.1f}" class="sep"/></g>'
        )
    return "\n".join(out)


def render(s):
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lx, ly, lw, lh = 24, 58, 430, 388  # left panel
    rx, ry, rw = lx + lw + 20, ly, W - (lx + lw + 20) - 24
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
  <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
    <feGaussianBlur stdDeviation="1.6" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">
    <rect width="4" height="2" fill="#000" opacity="0.28"/>
  </pattern>
  <radialGradient id="vig" cx="50%" cy="50%" r="75%">
    <stop offset="60%" stop-color="#000" stop-opacity="0"/>
    <stop offset="100%" stop-color="#000" stop-opacity="0.55"/>
  </radialGradient>
</defs>
<style>
  text {{ font-family: 'JetBrains Mono','Fira Code',Menlo,Consolas,'Courier New',monospace; fill: {GREEN}; }}
  .art text {{ white-space: pre; }}
  .title {{ font-size: 13px; letter-spacing: 1px; }}
  .label {{ font-size: 11px; fill: {GREEN}; letter-spacing: 2px; font-weight: 700; }}
  .key {{ font-size: 14px; font-weight: 700; }}
  .val {{ font-size: 14px; opacity: .9; }}
  .sep {{ stroke: {DIM}; stroke-width: 1; stroke-dasharray: 2 3; }}
  .panel {{ fill: none; stroke: {GREEN}; stroke-width: 1.5; }}
  .row {{ opacity: 0; animation: in .35s ease-out forwards; }}
  .blink {{ animation: blink 1.1s steps(1) infinite; }}
  .crt {{ animation: flicker 6s infinite; }}
  .sweep {{ animation: sweep 5s linear infinite; }}
  @keyframes in {{ from {{ opacity: 0; transform: translateX(-6px); }} to {{ opacity: 1; transform: none; }} }}
  @keyframes blink {{ 50% {{ opacity: 0; }} }}
  @keyframes flicker {{ 0%,100% {{ opacity: 1; }} 92% {{ opacity: 1; }} 93% {{ opacity: .85; }} 94% {{ opacity: 1; }} }}
  @keyframes sweep {{ from {{ transform: translateY(-40px); }} to {{ transform: translateY({H}px); }} }}
</style>
<rect width="{W}" height="{H}" rx="18" fill="{BG}"/>
<g class="crt" filter="url(#glow)">
  <rect x="6" y="6" width="{W - 12}" height="{H - 12}" rx="14" class="panel" stroke-width="2"/>
  <text x="{lx}" y="34" class="label">VISUAL.RAW</text>
  <text x="{W / 2}" y="34" class="title" text-anchor="middle">{USER}@github: ~ $ ./profile-scan --live<tspan class="blink">_</tspan></text>
  <text x="{W - 24}" y="34" class="label" text-anchor="end"><tspan class="blink">●</tspan> LIVE</text>

  <rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" rx="10" class="panel"/>
  {ascii_block(lx + 14, ly + 10, lw - 28, lh - 20)}

  <rect x="{rx}" y="{ry}" width="{rw}" height="{lh}" rx="10" class="panel"/>
  <text x="{rx + 18}" y="{ry + 26}" class="label">SYSTEM.INFO</text>
  <text x="{rx + rw - 18}" y="{ry + 26}" class="label" text-anchor="end" opacity=".6">{stamp}</text>
  <line x1="{rx}" y1="{ry + 38}" x2="{rx + rw}" y2="{ry + 38}" class="sep" stroke-dasharray="none"/>
  {info_rows(s, rx + 18, ry + 66, rw - 36, lh - 66 - 26)}
</g>
<rect class="sweep" x="0" y="0" width="{W}" height="40" fill="{GREEN}" opacity=".04"/>
<rect width="{W}" height="{H}" rx="18" fill="url(#scan)"/>
<rect width="{W}" height="{H}" rx="18" fill="url(#vig)"/>
</svg>
"""


if __name__ == "__main__":
    svg = render(stats())
    with open(os.path.join(os.path.dirname(__file__) or ".", "profile.svg"), "w") as f:
        f.write(svg)
    # bump ?v= so GitHub's image cache fetches the new card instead of a stale one
    readme = os.path.join(os.path.dirname(__file__) or ".", "README.md")
    text = open(readme).read()
    with open(readme, "w") as f:
        f.write(re.sub(r"profile\.svg(\?v=\d+)?", f"profile.svg?v={int(time.time())}", text))
    print("wrote profile.svg")
