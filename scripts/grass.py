"""Draw the last year of GitHub contributions as a red grid (assets/grass.svg, grass-light.svg).

Runs daily from .github/workflows/grass.yml. Locally: `python3 scripts/grass.py` (uses `gh auth token`).
"""
import json
import math
import os
import subprocess
import urllib.request
from datetime import date

USER = os.environ.get("GRASS_USER", "sjm-L")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
RED = "#e63b1f"
FONT = "'Space Grotesk','Pretendard','Apple SD Gothic Neo','Helvetica Neue',Helvetica,Arial,sans-serif"
THEMES = {
    "": {"text": "#f0f4f5", "muted": "#9aa1a4", "empty": "#21262d"},
    "-light": {"text": "#0e0e0e", "muted": "#6d7477", "empty": "#ebeef0"},
}
LEVELS = [0, 0.3, 0.55, 0.8, 1.0]  # red fill-opacity per level
W, CELL, GAP = 1200, 18, 4
STEP = CELL + GAP
TOP = 28


def token():
    t = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if t:
        return t
    return subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()


def fetch():
    query = """query($login: String!) { user(login: $login) { contributionsCollection {
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } } } } }"""
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {token()}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as res:
        data = json.load(res)
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def level(count, top):
    if count == 0:
        return 0
    return max(1, min(4, math.ceil(count / top * 4)))


def draw(cal, c):
    weeks = cal["weeks"]
    top = max([d["contributionCount"] for w in weeks for d in w["contributionDays"]] + [1])
    left = W - (len(weeks) * STEP - GAP)
    rows = []

    for label, row in (("MON", 1), ("WED", 3), ("FRI", 5)):
        rows.append(f'  <text class="t" x="0" y="{TOP + row * STEP + 13}" font-size="10" font-weight="700" '
                    f'fill="{c["muted"]}" letter-spacing="1.5">{label}</text>')

    last_label = -9
    for i, w in enumerate(weeks):
        first = date.fromisoformat(w["contributionDays"][0]["date"])
        if first.day <= 7 and i - last_label >= 3:
            rows.append(f'  <text class="t" x="{left + i * STEP}" y="16" font-size="10" font-weight="700" '
                        f'fill="{c["muted"]}" letter-spacing="1.5">{first.strftime("%b").upper()}</text>')
            last_label = i

    for i, w in enumerate(weeks):
        cells = []
        for d in w["contributionDays"]:
            row = (date.fromisoformat(d["date"]).weekday() + 1) % 7  # Sunday on top, like GitHub
            lv = level(d["contributionCount"], top)
            fill = f'fill="{c["empty"]}"' if lv == 0 else f'fill="{RED}" fill-opacity="{LEVELS[lv]}"'
            cells.append(f'<rect x="{left + i * STEP}" y="{TOP + row * STEP}" width="{CELL}" height="{CELL}" rx="2" {fill}>'
                         f'<title>{d["date"]}: {d["contributionCount"]}</title></rect>')
        rows.append(f'  <g class="in" style="animation-delay: {0.15 + i * 0.012:.3f}s">{"".join(cells)}</g>')

    base = TOP + 7 * STEP + 30
    total = cal["totalContributions"]
    rows.append(f'  <text class="t in" style="animation-delay: .8s" x="{left}" y="{base}" font-size="13" font-weight="700" '
                f'fill="{c["muted"]}" letter-spacing="2"><tspan font-size="22" fill="{RED}" letter-spacing="0">{total}</tspan>'
                f'  CONTRIBUTIONS IN THE LAST YEAR</text>')
    x = W - 5 * 18 - 48
    rows.append(f'  <text class="t" x="{x - 10}" y="{base - 2}" font-size="10" font-weight="700" fill="{c["muted"]}" '
                f'letter-spacing="1.5" text-anchor="end">LESS</text>')
    for lv in range(5):
        fill = f'fill="{c["empty"]}"' if lv == 0 else f'fill="{RED}" fill-opacity="{LEVELS[lv]}"'
        rows.append(f'  <rect x="{x + lv * 18}" y="{base - 14}" width="14" height="14" rx="2" {fill}/>')
    rows.append(f'  <text class="t" x="{W}" y="{base - 2}" font-size="10" font-weight="700" fill="{c["muted"]}" '
                f'letter-spacing="1.5" text-anchor="end">MORE</text>')

    h = base + 8
    style = (f".t {{ font-family: {FONT}; }} "
             ".in { animation: in .6s ease-out both; } @keyframes in { from { opacity: 0; } }")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" '
            f'aria-label="{total} contributions in the last year">\n  <style>{style}</style>\n'
            + "\n".join(rows) + "\n</svg>\n")


if __name__ == "__main__":
    cal = fetch()
    for suffix, c in THEMES.items():
        with open(os.path.join(OUT, f"grass{suffix}.svg"), "w") as fh:
            fh.write(draw(cal, c))
    print(f"{cal['totalContributions']} contributions, {len(cal['weeks'])} weeks")
