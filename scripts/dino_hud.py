"""Generate assets/dino-hud.svg: an animated pixel T-rex banner with live GitHub stats.

Run by .github/workflows/dino-hud.yml with GITHUB_TOKEN set. Use --sample to render
with placeholder numbers when no token is available.
"""
import datetime as dt
import json
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

USER = os.environ.get("GH_USER", "Ayaz-Ahmad1")
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "dino-hud.svg")

W, H = 900, 400
GROUND = 350
PX = 4


# ---------------------------------------------------------------- data

def gql(query, variables, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "dino-hud"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if body.get("errors"):
        raise RuntimeError(body["errors"])
    return body["data"]


def fetch_stats(token):
    base = gql(
        """query($login:String!){user(login:$login){
             contributionsCollection{contributionYears}
             repositories(ownerAffiliations:OWNER,isFork:false,first:100){nodes{
               languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}}}}}""",
        {"login": USER}, token)["user"]

    sizes, colors = {}, {}
    for repo in base["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            name = e["node"]["name"]
            sizes[name] = sizes.get(name, 0) + e["size"]
            colors[name] = e["node"]["color"] or "#8b9bb4"
    total = sum(sizes.values()) or 1
    langs = [(n, s * 100 / total, colors[n]) for n, s in sorted(sizes.items(), key=lambda kv: -kv[1])][:6]

    days = {}
    for year in base["contributionsCollection"]["contributionYears"]:
        cal = gql(
            """query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){
                 contributionsCollection(from:$from,to:$to){contributionCalendar{
                   weeks{contributionDays{date contributionCount}}}}}}""",
            {"login": USER, "from": f"{year}-01-01T00:00:00Z", "to": f"{year}-12-31T23:59:59Z"},
            token)["user"]["contributionsCollection"]["contributionCalendar"]
        for w in cal["weeks"]:
            for d in w["contributionDays"]:
                days[dt.date.fromisoformat(d["date"])] = d["contributionCount"]
    return langs, streaks(days)


def streaks(days):
    today = dt.datetime.now(dt.timezone.utc).date()
    ordered = sorted(d for d in days if d <= today)
    active = [d for d in ordered if days[d] > 0]
    total = sum(days[d] for d in ordered)
    first = active[0] if active else today

    run_start, run = None, 0
    longest = {"len": 0, "start": None, "end": None}
    for d in ordered:
        if days[d] > 0:
            run_start = run_start or d
            run += 1
            if run > longest["len"]:
                longest = {"len": run, "start": run_start, "end": d}
        else:
            run_start, run = None, 0

    # A streak stays alive through today until the day ends, like streak-stats.
    cur, d = 0, today if days.get(today, 0) > 0 else today - dt.timedelta(days=1)
    cur_end = d
    while days.get(d, 0) > 0:
        cur += 1
        d -= dt.timedelta(days=1)
    cur_start = d + dt.timedelta(days=1) if cur else today
    cur_end = cur_end if cur else today
    return {
        "total": total, "since": first,
        "current": cur, "current_start": cur_start, "current_end": cur_end,
        "longest": longest["len"], "longest_start": longest["start"], "longest_end": longest["end"],
        "today": today,
    }


SAMPLE = (
    [("Python", 80.99, "#3572A5"), ("HTML", 14.23, "#e34c26"), ("CSS", 2.53, "#663399"),
     ("JavaScript", 1.64, "#f1e05a"), ("Shell", 0.43, "#89e051"), ("PowerShell", 0.17, "#012456")],
    {"total": 243, "since": dt.date(2021, 6, 26), "current": 0,
     "current_start": None, "current_end": None, "longest": 5,
     "longest_start": dt.date(2026, 2, 27), "longest_end": dt.date(2026, 3, 3),
     "today": dt.date(2026, 10, 7)},
)


# ---------------------------------------------------------------- drawing

def md(d, today):
    s = f"{d:%b} {d.day}"
    return s if d.year == today.year else f"{s}, {d.year}"


def rng(a, b, today):
    if not a:
        return md(today, today)
    return md(a, today) if a == b else f"{md(a, today)} – {md(b, today)}"


BODY = [
    "..........########", ".........##.######", ".........#########", ".........#########",
    ".........#####....", ".........#######..", "#.......#####.....", "#.....#######.....",
    "##...##########...", "###.#########.#...", "##############....", ".############.....",
    "..##########......", "...########.......", "....######........",
]
LEG_A = ["....##...##.......", "....#.....#.......", "....##....##......"]
LEG_B = ["....##.##.........", "....#....#........", "....##...##......."]


def pixels(rows, y0):
    out = []
    for r, row in enumerate(rows):
        c = 0
        while c < len(row):
            if row[c] == "#":
                s = c
                while c < len(row) and row[c] == "#":
                    c += 1
                out.append(f'<rect x="{s*PX}" y="{(y0+r)*PX}" width="{(c-s)*PX}" height="{PX}"/>')
            else:
                c += 1
    return "".join(out)


def cactus(x, label, h):
    t = GROUND - h
    return (f'<g transform="translate({x},0)">'
            f'<rect class="cac" x="-7" y="{t}" width="14" height="{h}" rx="3"/>'
            f'<rect class="cac" x="-19" y="{t+14}" width="8" height="20" rx="3"/>'
            f'<rect class="cac" x="-19" y="{t+28}" width="14" height="7" rx="2"/>'
            f'<rect class="cac" x="11" y="{t+8}" width="8" height="18" rx="3"/>'
            f'<rect class="cac" x="5" y="{t+21}" width="14" height="7" rx="2"/>'
            f'<text class="bug" x="0" y="{t-10}" text-anchor="middle">{label}</text></g>')


def jump_keyframes():
    # Obstacles cross the dino at 0.7s, 3.7s and 6.7s of the 9s loop.
    kf = []
    for c in (0.7, 3.7, 6.7):
        a, p, b = (c - .28) / 9 * 100, c / 9 * 100, (c + .28) / 9 * 100
        kf.append(f"{a-.01:.2f}%{{transform:translateY(0)}}"
                  f"{a:.2f}%{{transform:translateY(0);animation-timing-function:ease-out}}"
                  f"{p:.2f}%{{transform:translateY(-72px);animation-timing-function:ease-in}}"
                  f"{b:.2f}%{{transform:translateY(0)}}")
    return "@keyframes jump{0%{transform:translateY(0)}" + "".join(kf) + "100%{transform:translateY(0)}}"


def lang_panel(langs, x, y, w, h):
    bx, bw = x + 16, w - 32
    segs, off = [], bx
    for i, (name, pct, color) in enumerate(langs):
        sw = bw - (off - bx) if i == len(langs) - 1 else bw * pct / 100
        segs.append(f'<rect x="{off:.1f}" y="{y+30}" width="{max(sw, 0):.1f}" height="8" fill="{color}"/>')
        off += sw
    legend = []
    for i, (name, pct, color) in enumerate(langs):
        lx, ly = x + 16 + (i % 3) * ((w - 32) / 3), y + 56 + (i // 3) * 17
        legend.append(f'<circle cx="{lx+4:.1f}" cy="{ly-4}" r="4" fill="{color}"/>'
                      f'<text class="lg" x="{lx+13:.1f}" y="{ly}">{escape(name)} {pct:.1f}%</text>')
    return (f'<rect class="chip" x="{x}" y="{y}" width="{w}" height="{h}" rx="10"/>'
            f'<text class="ck" x="{x+16}" y="{y+19}">// MOST USED LANGUAGES</text>'
            f'<clipPath id="bar"><rect x="{bx}" y="{y+30}" width="{bw}" height="8" rx="4"/></clipPath>'
            f'<g clip-path="url(#bar)">{"".join(segs)}</g>{"".join(legend)}')


def tile(x, y, w, h, label, value, sub, cls="cv2", flame=False):
    cx = x + w / 2
    f = ""
    if flame:
        f = (f'<g class="flame" transform="translate({cx+22:.1f},{y+24})">'
             f'<path d="M0,16 C-8,12 -7,3 -2,-4 C-1,2 2,3 3,0 C7,5 8,13 0,16Z" fill="#ffb627"/>'
             f'<path d="M0,15 C-3,13 -3,9 0,5 C3,9 3,13 0,15Z" fill="#ff2bd6"/></g>')
    return (f'<rect class="chip" x="{x}" y="{y}" width="{w}" height="{h}" rx="10"/>'
            f'<text class="ck" x="{cx:.1f}" y="{y+17}" text-anchor="middle">{label}</text>'
            f'<text class="{cls}" x="{cx-(8 if flame else 0):.1f}" y="{y+42}" text-anchor="middle">{value}</text>{f}'
            f'<text class="ds" x="{cx:.1f}" y="{y+58}" text-anchor="middle">{sub}</text>')


def render(langs, s):
    today = s["today"]
    cacti = "".join(cactus(200 + 300 * i + 900 * k, l, h) for k in (0, 1)
                    for i, (l, h) in enumerate([("504", 48), ("CORS", 42), ("BROKEN PIPE", 52)]))
    grid = "".join(f'<line x1="{450+i*14}" y1="{GROUND}" x2="{450+i*95}" y2="{H}"/>' for i in range(-12, 13))
    grid += "".join(f'<line x1="0" y1="{GROUND+o}" x2="{W}" y2="{GROUND+o}"/>' for o in (6, 14, 26, 44))
    stars = "".join(f'<circle class="star" cx="{x}" cy="{y}" r="{r}" style="animation-delay:{d}s"/>'
                    for x, y, r, d in [(40, 30, 1.2, 0), (130, 80, 1, 1.2), (260, 22, 1.4, .6), (380, 60, 1, 2),
                                       (470, 18, 1.2, 1.5), (420, 150, 1, .3), (610, 40, 1.3, 2.4),
                                       (870, 112, 1, .9), (330, 170, 1, 2.8), (240, 230, 1.2, .2),
                                       (60, 200, 1, 1.7), (400, 280, 1.1, 2.1)])
    chips, cx = "", 575
    for k, v in [("SINCE", "2022"), ("TOPTAL", "$50K+"), ("UPWORK JSS", "100%")]:
        w = max(len(k), len(v)) * 8.6 + 26
        chips += (f'<g transform="translate({cx:.0f},24)"><rect class="chip" width="{w:.0f}" height="44" rx="8"/>'
                  f'<text class="ck" x="13" y="18">{k}</text><text class="cv" x="13" y="36">{v}</text></g>')
        cx += w + 10

    px, pw = 470, 410
    tw = (pw - 20) / 3
    ty = 196
    tiles = (tile(px, ty, tw, 66, "CONTRIBUTIONS", s["total"], f"{md(s['since'], today)} – now")
             + tile(px + tw + 10, ty, tw, 66, "CURRENT STREAK", s["current"],
                    rng(s["current_start"], s["current_end"], today), "cv2 hot", flame=True)
             + tile(px + 2 * (tw + 10), ty, tw, 66, "LONGEST STREAK", s["longest"],
                    rng(s["longest_start"], s["longest_end"], today)))

    dino_h = (len(BODY) + 3) * PX
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#05060f"/><stop offset=".75" stop-color="#140a2e"/><stop offset="1" stop-color="#2a0d45"/></linearGradient>
<linearGradient id="sun" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ff2bd6"/><stop offset="1" stop-color="#ffb627"/></linearGradient>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<clipPath id="frame"><rect width="{W}" height="{H}" rx="18"/></clipPath>
<clipPath id="sunclip"><rect x="0" y="0" width="{W}" height="{GROUND}"/></clipPath>
<style>
text{{font-family:"JetBrains Mono","Fira Code",Consolas,"Courier New",monospace}}
.title{{font-size:24px;font-weight:700;fill:#e6f7ff;letter-spacing:2px}}
.subt{{font-size:13px;fill:#7dd3fc;letter-spacing:3px}}
.status{{font-size:12px;fill:#39ff9f;letter-spacing:2px}}
.chip{{fill:#0b1530;fill-opacity:.85;stroke:#22d3ee;stroke-opacity:.6}}
.ck{{font-size:10px;fill:#7dd3fc;letter-spacing:1.5px}}
.cv{{font-size:14px;font-weight:700;fill:#ffffff}}
.cv2{{font-size:24px;font-weight:700;fill:#e6f7ff}}
.hot{{fill:#ffb627}}
.ds{{font-size:10px;fill:#a5b4fc}}
.lg{{font-size:11px;fill:#dbe4f0}}
.dino{{fill:#39ff9f}}
.cac{{fill:#ff2bd6}}
.bug{{font-size:11px;font-weight:700;fill:#ffb627;letter-spacing:1px}}
.grid line{{stroke:#ff2bd6;stroke-opacity:.35;stroke-width:1}}
.ground{{stroke:#22d3ee;stroke-width:2}}
.cap{{font-size:11px;fill:#a5b4fc;letter-spacing:2px}}
.star{{fill:#fff;animation:tw 3s ease-in-out infinite}}
@keyframes tw{{0%,100%{{opacity:.2}}50%{{opacity:1}}}}
.world{{animation:scroll 9s linear infinite}}
@keyframes scroll{{from{{transform:translateX(0)}}to{{transform:translateX(-900px)}}}}
.jumper{{animation:jump 9s linear infinite}}
{jump_keyframes()}
.legA{{animation:legA .24s steps(1) infinite}}
.legB{{animation:legB .24s steps(1) infinite}}
@keyframes legA{{0%{{opacity:1}}50%{{opacity:0}}}}
@keyframes legB{{0%{{opacity:0}}50%{{opacity:1}}}}
.flame{{animation:fl .5s ease-in-out infinite alternate;transform-box:fill-box;transform-origin:center bottom}}
@keyframes fl{{from{{opacity:.75}}to{{opacity:1}}}}
.dash{{stroke:#22d3ee;stroke-width:2;stroke-dasharray:6 22;animation:dash .6s linear infinite}}
@keyframes dash{{to{{stroke-dashoffset:-28}}}}
.blink{{animation:bl 1.2s steps(1) infinite}}
@keyframes bl{{50%{{opacity:0}}}}
.scan{{fill:#22d3ee;opacity:.06;animation:scan 4s linear infinite}}
@keyframes scan{{from{{transform:translateY(-20px)}}to{{transform:translateY({H}px)}}}}
</style>
</defs>
<g clip-path="url(#frame)">
<rect width="{W}" height="{H}" fill="url(#sky)"/>
{stars}
<g clip-path="url(#sunclip)" opacity=".5"><circle cx="760" cy="{GROUND+10}" r="70" fill="url(#sun)"/>
<g fill="#140a2e"><rect x="680" y="{GROUND-34}" width="160" height="4"/><rect x="680" y="{GROUND-22}" width="160" height="6"/><rect x="680" y="{GROUND-10}" width="160" height="8"/></g></g>
<g class="grid">{grid}</g>
<line class="ground" x1="0" y1="{GROUND}" x2="{W}" y2="{GROUND}" filter="url(#glow)"/>
<line class="dash" x1="0" y1="{GROUND+6}" x2="{W}" y2="{GROUND+6}"/>

<text class="title" x="32" y="48" filter="url(#glow)">AYAZ.AHMAD<tspan fill="#ff2bd6">://</tspan>BACKEND</text>
<text class="subt" x="32" y="72">PYTHON BACKEND ENGINEER</text>
<text class="status" x="32" y="96"><tspan class="blink">●</tspan> SYSTEM ONLINE · APIs · QUEUES · INTEGRATIONS</text>
<text class="cap" x="32" y="122">&gt; jumping over production bugs since 2022<tspan class="blink">_</tspan></text>
{chips}
{lang_panel(langs, px, 96, pw, 90)}
{tiles}

<g class="world" filter="url(#glow)">{cacti}</g>
<g transform="translate(96,{GROUND-dino_h})" filter="url(#glow)"><g class="jumper"><g class="dino">
{pixels(BODY, 0)}<g class="legA">{pixels(LEG_A, len(BODY))}</g><g class="legB">{pixels(LEG_B, len(BODY))}</g>
</g></g></g>
<rect class="scan" x="0" y="0" width="{W}" height="14"/>
</g>
<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="17" fill="none" stroke="#22d3ee" stroke-opacity=".5" stroke-width="2"/>
</svg>
'''


if __name__ == "__main__":
    if "--sample" in sys.argv:
        langs, stats = SAMPLE
    else:
        langs, stats = fetch_stats(os.environ["GITHUB_TOKEN"])
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(render(langs, stats))
    print(f"wrote {os.path.normpath(OUT)}: {len(langs)} languages, {stats['total']} contributions")
