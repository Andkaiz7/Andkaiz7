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


def arc(cx, cy, r1, r2, a0, a1):
    p = lambda r, a: f"{f(cx + r * math.sin(a))} {f(cy - r * math.cos(a))}"
    return f"M{p(r2, a0)} A{f(r2)} {f(r2)} 0 0 1 {p(r2, a1)} L{p(r1, a1)} A{f(r1)} {f(r1)} 0 0 0 {p(r1, a0)} Z"


def ring(weeks, cx, cy):
    r_in, band, gap_r = 50, 9, 1.6
    gap_deg = 14
    n = len(weeks)
    span = math.radians(360 - gap_deg)
    start = math.radians(gap_deg / 2)
    step = span / n
    cells = []
    for wi, w in enumerate(weeks):
        a0 = start + wi * step + 0.006
        a1 = start + (wi + 1) * step - 0.006
        a = (a0 + a1) / 2 / (2 * math.pi)
        for d in w["contributionDays"]:
            r1 = r_in + d["weekday"] * (band + gap_r)
            path = arc(cx, cy, r1, r1 + band, a0, a1)
            lvl = LEVELS.get(d["contributionLevel"], 0) if d["contributionCount"] else 0
            if not lvl:
                cells.append(f'<path d="{path}" fill="{COLORS[0]}"/>')
                continue
            c = COLORS[lvl]
            pre, post = max(0.001, a - 0.006), min(0.999, a + 0.05)
            cells.append(f'<path d="{path}" fill="{c}"><animate attributeName="fill" dur="{T}s" repeatCount="indefinite" '
                         f'values="{c};{c};#eef3fa;{c};{c}" keyTimes="0;{f(pre)};{f(min(a + 0.003, 0.998))};{f(post)};1"/></path>')
    r_out = r_in + 7 * band + 6 * gap_r
    rs = r_out + 5
    sweep = (f'<g><animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" to="360 {cx} {cy}" dur="{T}s" repeatCount="indefinite"/>'
             f'<path d="{arc(cx, cy, r_in - 5, rs, -math.radians(26), 0)}" fill="url(#sweep)"/>'
             f'<line x1="{cx}" y1="{cy - r_in + 5}" x2="{cx}" y2="{cy - rs}" stroke="#8fb4e0" stroke-opacity="0.55"/></g>')
    days = [d for w in weeks for d in w["contributionDays"]]
    active = sum(1 for d in days if d["contributionCount"])
    return (f'{"".join(cells)}{sweep}'
            f'<text x="{cx}" y="{cy + 4}" text-anchor="middle" font-family="{SANS}" font-size="24" font-weight="700" fill="url(#num)">{active:,}</text>'
            f'<text x="{cx}" y="{cy + 20}" text-anchor="middle" font-family="{MONO}" font-size="10" fill="{MUTED}">active days</text>')


def render(cal):
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    counts = [d["contributionCount"] for d in days]
    total = cal["totalContributions"]
    cur, best = current_streak(counts), longest_streak(counts)

    h, ly = 300, 200
    sx, sy, sr = 405, 118, 44
    circ = 2 * math.pi * sr
    gap = 30
    flame = (f'<g transform="translate({sx} {sy - sr})"><path d="M0 -13 C7 -6 9 -1 7 5 C5 10 -5 10 -7 5 C-9 0 -4 -4 0 -13 Z" fill="{HI}"/>'
             f'<path d="M0 -3 C3 0 4 3 2 6 C1 8 -2 8 -3 6 C-4 3 -2 1 0 -3 Z" fill="{BG}"/></g>')

    def stat(x, num, label):
        return (f'<text x="{x}" y="133" text-anchor="middle" font-family="{SANS}" font-size="42" font-weight="700" fill="url(#num)">{num}</text>'
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
<g stroke="{BORDER}">{"".join(f'<line x1="{x}" y1="66" x2="{x}" y2="234"/>' for x in (270, 540, 810))}</g>
{stat(135, f"{total:,}", "Total Contributions")}
<text x="135" y="222" text-anchor="middle" font-family="{MONO}" font-size="11" fill="{MUTED}">last 12 months</text>
<circle cx="{sx}" cy="{sy}" r="{sr}" fill="none" stroke="#6f97c4" stroke-width="5" stroke-linecap="round" transform="rotate(-90 {sx} {sy})"
  stroke-dasharray="{f(circ - gap)} {gap}" stroke-dashoffset="{f(circ - gap / 2)}"/>
{flame}
<text x="{sx}" y="{sy + 11}" text-anchor="middle" font-family="{SANS}" font-size="32" font-weight="700" fill="#eef3fa">{cur:,}</text>
<text x="{sx}" y="{ly}" text-anchor="middle" font-family="{SANS}" font-size="15" font-weight="700" fill="{SUB}">Current Streak</text>
{stat(675, f"{best:,}", "Longest Streak")}
{ring(cal["weeks"], 1005, h / 2)}
</svg>
"""


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    cal = fetch(os.environ["GH_USER"], os.environ["GITHUB_TOKEN"])
    (out / "activity.svg").write_text(render(cal))
