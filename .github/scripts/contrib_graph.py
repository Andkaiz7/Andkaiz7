import json
import math
import os
import sys
import urllib.request
from pathlib import Path

BG = "#0d1117"
BORDER = "#1d2533"
SANS = "'Segoe UI', -apple-system, BlinkMacSystemFont, Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', 'SF Mono', Menlo, Consolas, monospace"
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
COLORS = ["#1f2733", "#2f5280", "#4f7bb0", "#6f97c4", "#b4cdea"]
MUTED, SUB, HI = "#6b7686", "#a9c2e0", "#b4cdea"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
QUERY = """query($login: String!) { user(login: $login) { contributionsCollection { contributionCalendar {
  totalContributions weeks { contributionDays { date weekday contributionCount contributionLevel } } } } } }"""
T = 12.0


def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "contrib-graph"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    user = (body.get("data") or {}).get("user")
    if body.get("errors") or not user:
        raise SystemExit(f"GraphQL error: {body.get('errors')}")
    return user["contributionsCollection"]["contributionCalendar"]


def f(x):
    return f"{x:.2f}".rstrip("0").rstrip(".")


def longest_streak(counts):
    best = cur = 0
    for c in counts:
        cur = cur + 1 if c else 0
        best = max(best, cur)
    return best


def render(cal):
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    counts = [d["contributionCount"] for d in days]
    total = cal["totalContributions"]
    stats = [(f"{sum(1 for c in counts if c):,}", "active days"), (f"{max(counts, default=0):,}", "peak day"),
             (f"{longest_streak(counts):,}", "longest streak")]

    h, cx, cy, r0, L = 380, 880, 190, 74, 68
    n, mx = len(days), max(counts, default=0) or 1
    bars = []
    for i, d in enumerate(days):
        ang = -math.pi / 2 + 2 * math.pi * i / n
        c, lvl = d["contributionCount"], LEVELS.get(d["contributionLevel"], 0)
        ln = 4 + (L - 4) * math.sqrt(c / mx) if c else 2.5
        ca, sa = math.cos(ang), math.sin(ang)
        p = f'x1="{f(cx + r0 * ca)}" y1="{f(cy + r0 * sa)}" x2="{f(cx + (r0 + ln) * ca)}" y2="{f(cy + (r0 + ln) * sa)}"'
        if not c:
            bars.append(f'<line {p} stroke="{COLORS[0]}"/>')
            continue
        lvl = max(lvl, 1)
        a = i / n
        pre, post = max(0.001, a - 0.004), min(0.999, a + 0.05)
        bars.append(f'<line {p} stroke="{COLORS[lvl]}"><animate attributeName="stroke" dur="{T}s" repeatCount="indefinite" '
                    f'values="{COLORS[lvl]};{COLORS[lvl]};#eef3fa;{COLORS[lvl]};{COLORS[lvl]}" keyTimes="0;{f(pre)};{f(min(a + 0.002, 0.998))};{f(post)};1"/></line>')

    labels, prev = [], None
    for i, d in enumerate(days):
        m = int(d["date"][5:7])
        if m != prev and i > 3:
            ang = -math.pi / 2 + 2 * math.pi * i / n
            r = r0 + L + 18
            labels.append(f'<text x="{f(cx + r * math.cos(ang))}" y="{f(cy + r * math.sin(ang) + 4)}" text-anchor="middle">{MONTHS[m - 1]}</text>')
        prev = m

    rs = r0 + L + 4
    sweep = (f'<g><animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" to="360 {cx} {cy}" dur="{T}s" repeatCount="indefinite"/>'
             f'<path d="M{cx} {cy} L{cx} {cy - rs} A{rs} {rs} 0 0 0 {f(cx - rs * math.sin(math.radians(24)))} {f(cy - rs * math.cos(math.radians(24)))} Z" fill="url(#sweep)"/>'
             f'<line x1="{cx}" y1="{cy - r0 + 6}" x2="{cx}" y2="{cy - rs}" stroke="#8fb4e0" stroke-opacity="0.55"/></g>')

    stat_svg = "".join(
        f'<text x="{70 + i * 150}" y="214" font-family="{SANS}" font-size="30" font-weight="700" fill="{HI}">{num}</text>'
        f'<text x="{70 + i * 150}" y="238" font-family="{MONO}" font-size="12" fill="{MUTED}">{label}</text>'
        for i, (num, label) in enumerate(stats))

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 {h}" width="1200" height="{h}" role="img" aria-label="{total:,} contributions in the last 12 months">
<defs>
  <linearGradient id="num" x1="0" x2="1"><stop offset="0" stop-color="#eef3fa"/><stop offset="1" stop-color="#6f97c4"/></linearGradient>
  <linearGradient id="sweep" x1="1" y1="0" x2="0" y2="0.3"><stop offset="0" stop-color="#6f97c4" stop-opacity="0.16"/><stop offset="1" stop-color="#6f97c4" stop-opacity="0"/></linearGradient>
  <pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="#6f97c4" fill-opacity="0.05"/></pattern>
</defs>
<rect width="1200" height="{h}" rx="18" fill="{BG}"/>
<rect width="1200" height="{h}" rx="18" fill="url(#dots)"/>
<rect x="0.5" y="0.5" width="1199" height="{h - 1}" rx="18" fill="none" stroke="{BORDER}"/>
<text x="70" y="96" font-family="{MONO}" font-size="14" fill="{MUTED}">contribution activity · last 12 months</text>
<text x="69" y="146" font-family="{SANS}"><tspan font-size="44" font-weight="700" fill="url(#num)">{total:,}</tspan><tspan dx="10" font-size="18" fill="{SUB}">contributions</tspan></text>
{stat_svg}
<text x="70" y="{h - 70}" font-family="{MONO}" font-size="12" fill="{MUTED}">{days[0]["date"]} → {days[-1]["date"]}</text>
<circle cx="{cx}" cy="{cy}" r="{r0 - 8}" fill="none" stroke="{BORDER}"/>
{sweep}
<g stroke-width="2.2" stroke-linecap="round">{"".join(bars)}</g>
<g font-family="{MONO}" font-size="11" fill="{MUTED}">{"".join(labels)}</g>
<text x="{cx}" y="{cy + 2}" text-anchor="middle" font-family="{SANS}" font-size="26" font-weight="700" fill="url(#num)">{total:,}</text>
<text x="{cx}" y="{cy + 20}" text-anchor="middle" font-family="{MONO}" font-size="10" fill="{MUTED}">12 months</text>
</svg>
"""


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    cal = fetch(os.environ["GH_USER"], os.environ["GITHUB_TOKEN"])
    (out / "contrib-ring.svg").write_text(render(cal))
