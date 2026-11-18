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


def current_streak(counts):
    cs = counts[:-1] if counts and not counts[-1] else counts
    n = 0
    for c in reversed(cs):
        if not c:
            break
        n += 1
    return n


def ring(days, cx, cy, r0, L):
    counts = [d["contributionCount"] for d in days]
    n, mx = len(days), max(counts, default=0) or 1
    bars = []
    for i, d in enumerate(days):
        ang = -math.pi / 2 + 2 * math.pi * i / n
        c = d["contributionCount"]
        ln = 4 + (L - 4) * math.sqrt(c / mx) if c else 2.5
        ca, sa = math.cos(ang), math.sin(ang)
        p = f'x1="{f(cx + r0 * ca)}" y1="{f(cy + r0 * sa)}" x2="{f(cx + (r0 + ln) * ca)}" y2="{f(cy + (r0 + ln) * sa)}"'
        if not c:
            bars.append(f'<line {p} stroke="{COLORS[0]}"/>')
            continue
        lvl = max(LEVELS.get(d["contributionLevel"], 0), 1)
        a = i / n
        pre, post = max(0.001, a - 0.004), min(0.999, a + 0.05)
        bars.append(f'<line {p} stroke="{COLORS[lvl]}"><animate attributeName="stroke" dur="{T}s" repeatCount="indefinite" '
                    f'values="{COLORS[lvl]};{COLORS[lvl]};#eef3fa;{COLORS[lvl]};{COLORS[lvl]}" keyTimes="0;{f(pre)};{f(min(a + 0.002, 0.998))};{f(post)};1"/></line>')
    rs = r0 + L + 4
    sweep = (f'<g><animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" to="360 {cx} {cy}" dur="{T}s" repeatCount="indefinite"/>'
             f'<path d="M{cx} {cy} L{cx} {cy - rs} A{rs} {rs} 0 0 0 {f(cx - rs * math.sin(math.radians(24)))} {f(cy - rs * math.cos(math.radians(24)))} Z" fill="url(#sweep)"/>'
             f'<line x1="{cx}" y1="{cy - r0 + 6}" x2="{cx}" y2="{cy - rs}" stroke="#8fb4e0" stroke-opacity="0.55"/></g>')
    active = sum(1 for c in counts if c)
    return (f'<circle cx="{cx}" cy="{cy}" r="{r0 - 8}" fill="none" stroke="{BORDER}"/>{sweep}'
            f'<g stroke-width="2" stroke-linecap="round">{"".join(bars)}</g>'
            f'<text x="{cx}" y="{cy + 4}" text-anchor="middle" font-family="{SANS}" font-size="24" font-weight="700" fill="url(#num)">{active:,}</text>'
            f'<text x="{cx}" y="{cy + 21}" text-anchor="middle" font-family="{MONO}" font-size="10" fill="{MUTED}">active days</text>')


def render(cal):
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    counts = [d["contributionCount"] for d in days]
    total = cal["totalContributions"]
    cur, best = current_streak(counts), longest_streak(counts)

    h, ly = 280, 190
    sx, sy, sr = 405, 108, 44
    circ = 2 * math.pi * sr
    gap = 30
    flame = (f'<g transform="translate({sx} {sy - sr})"><path d="M0 -13 C7 -6 9 -1 7 5 C5 10 -5 10 -7 5 C-9 0 -4 -4 0 -13 Z" fill="{HI}"/>'
             f'<path d="M0 -3 C3 0 4 3 2 6 C1 8 -2 8 -3 6 C-4 3 -2 1 0 -3 Z" fill="{BG}"/></g>')

    def stat(x, num, label):
        return (f'<text x="{x}" y="123" text-anchor="middle" font-family="{SANS}" font-size="42" font-weight="700" fill="url(#num)">{num}</text>'
                f'<text x="{x}" y="{ly}" text-anchor="middle" font-family="{SANS}" font-size="15" fill="{SUB}">{label}</text>')

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 {h}" width="1200" height="{h}" role="img" aria-label="{total:,} contributions, current streak {cur}, longest streak {best}">
<defs>
  <linearGradient id="num" x1="0" x2="1"><stop offset="0" stop-color="#eef3fa"/><stop offset="1" stop-color="#6f97c4"/></linearGradient>
  <linearGradient id="sweep" x1="1" y1="0" x2="0" y2="0.3"><stop offset="0" stop-color="#6f97c4" stop-opacity="0.16"/><stop offset="1" stop-color="#6f97c4" stop-opacity="0"/></linearGradient>
  <pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="#6f97c4" fill-opacity="0.05"/></pattern>
</defs>
<rect width="1200" height="{h}" rx="18" fill="{BG}"/>
<rect width="1200" height="{h}" rx="18" fill="url(#dots)"/>
<rect x="0.5" y="0.5" width="1199" height="{h - 1}" rx="18" fill="none" stroke="{BORDER}"/>
<g stroke="{BORDER}">{"".join(f'<line x1="{x}" y1="56" x2="{x}" y2="224"/>' for x in (270, 540, 810))}</g>
{stat(135, f"{total:,}", "Total Contributions")}
<text x="135" y="212" text-anchor="middle" font-family="{MONO}" font-size="11" fill="{MUTED}">last 12 months</text>
<circle cx="{sx}" cy="{sy}" r="{sr}" fill="none" stroke="#6f97c4" stroke-width="5" stroke-linecap="round" transform="rotate(-90 {sx} {sy})"
  stroke-dasharray="{f(circ - gap)} {gap}" stroke-dashoffset="{f(circ - gap / 2)}"/>
{flame}
<text x="{sx}" y="{sy + 11}" text-anchor="middle" font-family="{SANS}" font-size="32" font-weight="700" fill="#eef3fa">{cur:,}</text>
<text x="{sx}" y="{ly}" text-anchor="middle" font-family="{SANS}" font-size="15" font-weight="700" fill="{SUB}">Current Streak</text>
{stat(675, f"{best:,}", "Longest Streak")}
{ring(days, 1005, 140, 62, 50)}
</svg>
"""


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    cal = fetch(os.environ["GH_USER"], os.environ["GITHUB_TOKEN"])
    (out / "activity.svg").write_text(render(cal))
