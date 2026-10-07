"""Generate assets/dino-hud.svg and dino-hud-dark.svg: a soft, animated pixel-dino banner with live GitHub stats.

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
ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")

W, H = 900, 310
GROUND = 278
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


BODY = [
    "..........########", ".........##.######", ".........#########", ".........##++#####",
    ".........#####....", ".........#######..", "#.......#####.....", "#.....#######.....",
    "##...##########...", "###.#########.#...", "##############....", ".############.....",
    "..##########......", "...########.......", "....######........",
]
LEG_A = ["....##...##.......", "....#.....#.......", "....##....##......"]
LEG_B = ["....##.##.........", "....#....#........", "....##...##......."]
PASTELS = ["#7a64c2", "#9f8bd6", "#b8a9e3", "#c9b8f0", "#ddd2f7", "#ebe5fa"]


def pixels(rows, y0, ch="#"):
    out = []
    for r, row in enumerate(rows):
        c = 0
        while c < len(row):
            if row[c] == ch:
                s = c
                while c < len(row) and row[c] == ch:
                    c += 1
                out.append(f'<rect x="{s*PX}" y="{(y0+r)*PX}" width="{(c-s)*PX}" height="{PX}"/>')
            else:
                c += 1
    return "".join(out)


def heart(x, y, s, fill):
    return (f'<path transform="translate({x},{y}) scale({s})" fill="{fill}" '
            f'd="M0,3 C0,-1 5,-1 5,3 C5,-1 10,-1 10,3 C10,7 5,9 5,11 C5,9 0,7 0,3Z"/>')


def tulip(x, color):
    g = GROUND
    return (f'<g transform="translate({x},0)">'
            f'<path d="M0,{g} Q1,{g-12} 0,{g-22}" stroke="#a99bd3" stroke-width="2.5" fill="none" stroke-linecap="round"/>'
            f'<path d="M0,{g-6} Q-9,{g-12} -10,{g-20} Q-2,{g-16} 0,{g-8}Z" fill="#c3b8e6"/>'
            f'<path d="M-7,{g-30} Q-7,{g-20} 0,{g-19} Q7,{g-20} 7,{g-30} L4,{g-26} L0,{g-32} L-4,{g-26}Z" fill="{color}"/>'
            f'</g>')


def jump_keyframes():
    # Tulips pass under the dino at 0.7s, 3.7s and 6.7s of the 9s loop.
    kf = []
    for c in (0.7, 3.7, 6.7):
        a, p, b = (c - .28) / 9 * 100, c / 9 * 100, (c + .28) / 9 * 100
        kf.append(f"{a-.01:.2f}%{{transform:translateY(0)}}"
                  f"{a:.2f}%{{transform:translateY(0);animation-timing-function:ease-out}}"
                  f"{p:.2f}%{{transform:translateY(-54px);animation-timing-function:ease-in}}"
                  f"{b:.2f}%{{transform:translateY(0)}}")
    return "@keyframes jump{0%{transform:translateY(0)}" + "".join(kf) + "100%{transform:translateY(0)}}"


def lang_block(langs, x, y, w):
    shown = langs[:4]
    rest = 100 - sum(p for _, p, _ in shown)
    items = [(n, p, PASTELS[i]) for i, (n, p, _) in enumerate(shown)]
    if rest >= 0.05:
        items.append(("Other", rest, PASTELS[5]))
    segs, off = [], x
    for i, (n, p, c) in enumerate(items):
        sw = w - (off - x) if i == len(items) - 1 else w * p / 100
        segs.append(f'<rect x="{off:.1f}" y="{y}" width="{max(sw, 0):.1f}" height="6" fill="{c}"/>')
        off += sw
    legend, lx = [], x
    for n, p, c in items:
        label = f"{escape(n)} {p:.0f}%"
        legend.append(f'<circle cx="{lx+3}" cy="{y+21}" r="3" fill="{c}"/>'
                      f'<text class="lg" x="{lx+10}" y="{y+25}">{label}</text>')
        lx += len(label) * 6.2 + 20
    return (f'<text class="lab" x="{x}" y="{y-10}">languages</text>'
            f'<clipPath id="bar"><rect x="{x}" y="{y}" width="{w}" height="6" rx="3"/></clipPath>'
            f'<g clip-path="url(#bar)">{"".join(segs)}</g>{"".join(legend)}')


def stat(x, y, value, label):
    return (f'<text class="num" x="{x}" y="{y}">{value}</text>'
            f'<text class="lab" x="{x}" y="{y+17}">{label}</text>')


def cloud(cx, cy, sc, cls, op):
    return (f'<g class="{cls}"><g transform="translate({cx},{cy}) scale({sc})" fill="#ffffff" opacity="{op}">'
            f'<ellipse cx="0" cy="0" rx="34" ry="12"/><ellipse cx="-12" cy="-8" rx="14" ry="11"/>'
            f'<ellipse cx="10" cy="-10" rx="18" ry="14"/></g></g>')


THEMES = {
    "light": {"sky": ("#faf8fe", "#efe9fb", "#e2d9f5"), "sun": ("#e6dcfa", "#c9b8f0"), "sunop": ".8",
              "ink": "#4a3b78", "soft": "#7d6eaa", "accent": "#8a74c9", "muted": "#9a8cc0",
              "legend": "#5b4b8a", "ground": "#c9b8f0", "cloud": ".8", "stars": 0},
    "dark": {"sky": ("#15122a", "#211b3d", "#2f2552"), "sun": ("#ece6fa", "#b8a9e3"), "sunop": ".3",
             "ink": "#ece6fa", "soft": "#b9addb", "accent": "#c9b8f0", "muted": "#9d90c8",
             "legend": "#ddd5f5", "ground": "#5b4b8a", "cloud": ".10", "stars": 14},
}
STAR_SPOTS = [(60, 30), (180, 160), (300, 22), (420, 150), (470, 34), (610, 186), (700, 30), (860, 110),
              (380, 196), (250, 200), (40, 196), (880, 190), (560, 20), (820, 24)]


def render(langs, s, t):
    today = s["today"]
    colors = ["#9f8bd6", "#c9b8f0", "#b8a9e3"]
    flowers = "".join(tulip(200 + 300 * i + 900 * k, colors[i]) for k in (0, 1) for i in range(3))
    sx = 520

    def days(n):
        return "day" if n == 1 else "days"

    best = f"best · {md(s['longest_start'], today)}" if s["longest_start"] else "best"
    stats = (lang_block(langs, sx, 58, 340)
             + stat(sx, 128, s["total"], f"contributions since {s['since'].year}")
             + stat(sx + 175, 128, s["current"], f"{days(s['current'])} streak")
             + stat(sx + 270, 128, s["longest"], best))
    stars = "".join(f'<circle class="star" cx="{x}" cy="{y}" r="{1 + (i % 3) * .4:.1f}" style="animation-delay:{i * .37 % 3:.2f}s"/>'
                    for i, (x, y) in enumerate(STAR_SPOTS[:t["stars"]]))
    dino_h = (len(BODY) + 3) * PX
    hearts = "".join(f'<g class="float" style="animation-delay:{d}s">{heart(x, GROUND - dino_h - 8, sc, c)}</g>'
                     for x, d, sc, c in [(160, 0, 1, "#b8a9e3"), (172, 1.5, .8, "#9f8bd6"), (150, 3, .9, "#c9b8f0")])

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t['sky'][0]}"/><stop offset=".6" stop-color="{t['sky'][1]}"/><stop offset="1" stop-color="{t['sky'][2]}"/></linearGradient>
<linearGradient id="sun" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t['sun'][0]}"/><stop offset="1" stop-color="{t['sun'][1]}"/></linearGradient>
<clipPath id="frame"><rect width="{W}" height="{H}" rx="20"/></clipPath>
<clipPath id="above"><rect width="{W}" height="{GROUND}"/></clipPath>
<style>
.name{{font-family:Georgia,"Times New Roman",serif;font-style:italic;font-size:36px;fill:{t['ink']}}}
.sub,.cap,.lab,.lg,.num,.small{{font-family:"Segoe UI",-apple-system,Helvetica,Arial,sans-serif}}
.sub{{font-size:13px;fill:{t['soft']};letter-spacing:3px}}
.cap{{font-size:13px;fill:{t['accent']}}}
.small{{font-size:12px;fill:{t['soft']}}}
.lab{{font-size:11px;fill:{t['muted']};letter-spacing:.5px}}
.lg{{font-size:11px;fill:{t['legend']}}}
.num{{font-size:26px;font-weight:600;fill:{t['ink']}}}
.dino{{fill:#9f8bd6}}
.blush{{fill:#f2b8d2}}
.star{{fill:#fff3f8;animation:tw 3.2s ease-in-out infinite}}
@keyframes tw{{0%,100%{{opacity:.25}}50%{{opacity:.95}}}}
.world{{animation:scroll 9s linear infinite}}
@keyframes scroll{{from{{transform:translateX(0)}}to{{transform:translateX(-900px)}}}}
.jumper{{animation:jump 9s linear infinite}}
{jump_keyframes()}
.legA{{animation:legA .3s steps(1) infinite}}
.legB{{animation:legB .3s steps(1) infinite}}
@keyframes legA{{0%{{opacity:1}}50%{{opacity:0}}}}
@keyframes legB{{0%{{opacity:0}}50%{{opacity:1}}}}
.float{{opacity:0;animation:float 4.5s ease-out infinite}}
@keyframes float{{0%{{opacity:0;transform:translate(0,0)}}15%{{opacity:1}}100%{{opacity:0;transform:translate(14px,-70px)}}}}
.drift1{{animation:drift 60s linear infinite}}
.drift2{{animation:drift 90s linear infinite;animation-delay:-40s}}
@keyframes drift{{from{{transform:translateX(0)}}to{{transform:translateX(-1100px)}}}}
.beat{{animation:beat 1.6s ease-in-out infinite}}
@keyframes beat{{0%,100%{{opacity:1}}15%{{opacity:.45}}30%{{opacity:1}}}}
</style>
</defs>
<g clip-path="url(#frame)">
<rect width="{W}" height="{H}" fill="url(#sky)"/>
<g clip-path="url(#above)"><circle cx="760" cy="{GROUND + 18}" r="78" fill="url(#sun)" opacity="{t['sunop']}"/></g>
{stars}
{cloud(1000, 46, 1, "drift1", t["cloud"])}{cloud(1150, 120, .7, "drift2", t["cloud"])}
<line x1="24" y1="{GROUND}" x2="{W - 24}" y2="{GROUND}" stroke="{t['ground']}" stroke-width="1.5" stroke-linecap="round"/>

<text class="name" x="40" y="58">Ayaz Ahmad</text>
<text class="sub" x="42" y="84">PYTHON BACKEND ENGINEER</text>
<text class="cap" x="42" y="108">building calm, reliable backends since 2022 <tspan class="beat" fill="#9f8bd6">&#9829;</tspan></text>
<text class="small" x="42" y="130">Toptal $50K+  ·  Upwork 100% job success</text>
{stats}

<g class="world">{flowers}</g>
{hearts}
<g transform="translate(96,{GROUND - dino_h})"><g class="jumper">
<g class="dino">{pixels(BODY, 0)}<g class="legA">{pixels(LEG_A, len(BODY))}</g><g class="legB">{pixels(LEG_B, len(BODY))}</g></g>
<g class="blush">{pixels(BODY, 0, "+")}</g>
</g></g>
</g>
</svg>
'''


if __name__ == "__main__":
    if "--sample" in sys.argv:
        langs, stats = SAMPLE
    else:
        langs, stats = fetch_stats(os.environ["GITHUB_TOKEN"])
    for name, suffix in (("light", ""), ("dark", "-dark")):
        out = os.path.join(ASSETS, f"dino-hud{suffix}.svg")
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(render(langs, stats, THEMES[name]))
        print(f"wrote {os.path.normpath(out)}: {len(langs)} languages, {stats['total']} contributions")
