import json
import os
import sys
import urllib.request
from pathlib import Path

BG = "#0d1117"
SANS = "'Segoe UI', -apple-system, BlinkMacSystemFont, Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', 'SF Mono', Menlo, Consolas, monospace"
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
COLORS = ["#273040", "#2f5280", "#4f7bb0", "#6f97c4", "#b4cdea"]
RADII = [2.0, 3.0, 3.8, 4.6, 5.4]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
QUERY = """query($login: String!) { user(login: $login) { contributionsCollection { contributionCalendar {
  totalContributions weeks { contributionDays { date weekday contributionCount contributionLevel } } } } } }"""
T = 9.0


def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "neural-contrib"},
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
    weeks = cal["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    counts = [d["contributionCount"] for d in days]
    stats = [(f"{sum(1 for c in counts if c):,}", "active days"), (f"{max(counts, default=0):,}", "peak day"),
             (f"{longest_streak(counts):,}", "longest streak")]

    sp = 19.5
    width = (len(weeks) - 1) * sp
    x0 = (1200 - width) / 2
    xe = x0 + width
    y0 = 140
    cols = [[(x0 + wi * sp, y0 + d["weekday"] * sp, LEVELS.get(d["contributionLevel"], 0)) for d in w["contributionDays"]]
            for wi, w in enumerate(weeks)]

    edges = []
    for a, b in zip(cols, cols[1:]):
        targets = [n for n in b if n[2]]
        for x1, y1, l1 in a:
            if not l1:
                continue
            for x2, y2, l2 in sorted(targets, key=lambda n: abs(n[1] - y1))[:2]:
                edges.append(f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" stroke-opacity="{f(0.1 + 0.05 * min(l1, l2))}"/>')

    nodes = []
    for col in cols:
        for x, y, lvl in col:
            if not lvl:
                nodes.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{RADII[0]}" fill="{COLORS[0]}"/>')
                continue
            a = 0.04 + 0.8 * (x - x0) / width
            pre, post = max(0.001, a - 0.02), min(a + 0.08, 0.999)
            r, c = RADII[lvl], COLORS[lvl]
            glow = ' filter="url(#glow)"' if lvl == 4 else ""
            nodes.append(
                f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r + 5)}" fill="{c}" fill-opacity="0">'
                f'<animate attributeName="fill-opacity" dur="{T}s" repeatCount="indefinite" values="0;0;0.3;0;0" '
                f'keyTimes="0;{f(pre)};{f(a)};{f(post)};1"/></circle>'
                f'<circle cx="{f(x)}" cy="{f(y)}" r="{r}" fill="{c}"{glow}/>')

    months, last_x = [], -100
    for wi, w in enumerate(weeks):
        m = int(w["contributionDays"][0]["date"][5:7])
        prev = int(weeks[wi - 1]["contributionDays"][0]["date"][5:7]) if wi else None
        x = x0 + wi * sp
        if m != prev and x - last_x > 34:
            months.append(f'<text x="{f(x)}" y="{f(y0 + 6 * sp + 32)}">{MONTHS[m - 1]}</text>')
            last_x = x

    stat_svg = []
    for i, (num, label) in enumerate(reversed(stats)):
        x = xe - i * 150
        stat_svg.append(f'<text x="{f(x)}" y="86" text-anchor="end" font-family="{SANS}" font-size="24" font-weight="700" fill="#b4cdea">{num}</text>'
                        f'<text x="{f(x)}" y="106" text-anchor="end" font-family="{MONO}" font-size="12" fill="#6b7686">{label}</text>')

    ly = 322
    legend = [f'<text x="{f(xe)}" y="{ly + 4}" text-anchor="end">more</text>']
    for i in range(5):
        cx = xe - 52 - (4 - i) * 18
        legend.append(f'<circle cx="{f(cx)}" cy="{ly}" r="{RADII[i]}" fill="{COLORS[i]}"/>')
    legend.append(f'<text x="{f(xe - 52 - 4 * 18 - 14)}" y="{ly + 4}" text-anchor="end">less</text>')

    scan_w = 90
    total = cal["totalContributions"]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 350" width="1200" height="350" role="img" aria-label="{total:,} contributions in the last year">
<defs>
  <filter id="glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <linearGradient id="num" x1="0" x2="1"><stop offset="0" stop-color="#eef3fa"/><stop offset="1" stop-color="#6f97c4"/></linearGradient>
  <linearGradient id="scan" x1="0" x2="1"><stop offset="0" stop-color="#6f97c4" stop-opacity="0"/><stop offset="0.5" stop-color="#6f97c4" stop-opacity="0.16"/><stop offset="1" stop-color="#6f97c4" stop-opacity="0"/></linearGradient>
  <pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="#6f97c4" fill-opacity="0.06"/></pattern>
</defs>
<rect width="1200" height="350" rx="18" fill="{BG}"/>
<rect width="1200" height="350" rx="18" fill="url(#dots)"/>
<rect x="0.5" y="0.5" width="1199" height="349" rx="18" fill="none" stroke="#1d2533"/>
<text x="{f(x0 - 5)}" y="60" font-family="{MONO}" font-size="14" fill="#6b7686">contribution activity · last 12 months</text>
<text x="{f(x0 - 6)}" y="104" font-family="{SANS}"><tspan font-size="40" font-weight="700" fill="url(#num)">{total:,}</tspan><tspan dx="10" font-size="18" fill="#a9c2e0">contributions</tspan></text>
{"".join(stat_svg)}
<rect x="{f(x0 - scan_w / 2)}" y="{y0 - 22}" width="{scan_w}" height="{f(6 * sp + 44)}" fill="url(#scan)" opacity="0">
  <animate attributeName="x" dur="{T}s" repeatCount="indefinite" values="{f(x0 - scan_w / 2)};{f(x0 - scan_w / 2)};{f(xe - scan_w / 2)};{f(xe - scan_w / 2)}" keyTimes="0;0.04;0.84;1"/>
  <animate attributeName="opacity" dur="{T}s" repeatCount="indefinite" values="0;0;1;1;0;0" keyTimes="0;0.01;0.05;0.8;0.86;1"/>
</rect>
<g stroke="#6f97c4" stroke-width="0.8">{"".join(edges)}</g>
{"".join(nodes)}
<g font-family="{MONO}" font-size="12" fill="#6b7686">{"".join(months)}</g>
<text x="{f(x0 - 5)}" y="{ly + 4}" font-family="{MONO}" font-size="12" fill="#6b7686">{days[0]["date"]} → {days[-1]["date"]}</text>
<g font-family="{MONO}" font-size="12" fill="#6b7686">{"".join(legend)}</g>
</svg>
"""


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    cal = fetch(os.environ["GH_USER"], os.environ["GITHUB_TOKEN"])
    (out / "neural-contrib.svg").write_text(render(cal))
