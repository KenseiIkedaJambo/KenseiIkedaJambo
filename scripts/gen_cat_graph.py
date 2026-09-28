"""GitHub の草を黒猫が食べていくアニメーション SVG を生成する。

標準入力に GraphQL の contributionCalendar の JSON を受け取り、SVG を書き出す。
既製の pacman-contribution-graph はスプライトを差し替えられないため自作している。
"""
import json, sys, random, io

# ---- レイアウト ----
CELL, GAP = 11, 3
PITCH = CELL + GAP
PAD_L, PAD_T, PAD_B, PAD_R = 14, 40, 26, 14
ROWS = 7

# ---- 宇宙パレット ----
VOID   = "#04050e"
LEVELS = ["#0b1026", "#312e81", "#5b21b6", "#7c3aed", "#c084fc"]
CYAN   = "#22d3ee"
STAR   = "#e8ecff"
FUR    = "#1c1940"
FUR_HI = "#2a2342"

# ---- タイミング（秒）----
PASS_DUR = 3.4     # 1 行を渡りきる時間
PASS_GAP = 0.25    # 行間の移動
EAT_FADE = 0.16    # 食べてから消えるまで
PAUSE    = 2.6     # 全部食べ終えてからリセットまで


def level_of(count, thresholds):
    if count <= 0:
        return 0
    for i, t in enumerate(thresholds, start=1):
        if count <= t:
            return i
    return 4


def build(cal):
    weeks = cal["weeks"]
    total = cal["totalContributions"]
    cols = len(weeks)

    counts = sorted(d["contributionCount"] for w in weeks for d in w["contributionDays"]
                    if d["contributionCount"] > 0)
    if counts:
        q = lambda p: counts[min(len(counts) - 1, int(len(counts) * p))]
        thresholds = [q(0.25), q(0.50), q(0.75)]
    else:
        thresholds = [1, 2, 3]

    # (col,row) -> level
    grid = {}
    for c, w in enumerate(weeks):
        for d in w["contributionDays"]:
            grid[(c, d["weekday"])] = level_of(d["contributionCount"], thresholds)

    W = PAD_L + cols * PITCH - GAP + PAD_R
    H = PAD_T + ROWS * PITCH - GAP + PAD_B

    x_of = lambda c: PAD_L + c * PITCH
    y_of = lambda r: PAD_T + r * PITCH

    active = ROWS * (PASS_DUR + PASS_GAP)
    LOOP = active + PAUSE
    k = lambda t: round(max(0.0, min(1.0, t / LOOP)), 5)

    def eat_time(c, r):
        """(c,r) のセルを猫が通過する時刻。奇数行は右→左。"""
        t0 = r * (PASS_DUR + PASS_GAP)
        frac = c / max(1, cols - 1)
        if r % 2 == 1:
            frac = 1.0 - frac
        return t0 + frac * PASS_DUR

    o = []
    A = o.append
    A(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" '
      f'role="img" aria-label="{total} contributions eaten by a black cat">')

    # ---- defs ----
    A('<defs>')
    A('<filter id="eyeGlow" x="-200%" y="-200%" width="500%" height="500%">'
      '<feGaussianBlur stdDeviation="1.6" result="b"/>'
      '<feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    A('<filter id="starGlow" x="-200%" y="-200%" width="500%" height="500%">'
      '<feGaussianBlur stdDeviation="0.9" result="b"/>'
      '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    A(f'<radialGradient id="neb" cx="50%" cy="50%" r="50%">'
      f'<stop offset="0%" stop-color="#7c3aed" stop-opacity="0.30"/>'
      f'<stop offset="100%" stop-color="#7c3aed" stop-opacity="0"/></radialGradient>')
    A(f'<filter id="catGlow" x="-80%" y="-80%" width="260%" height="260%">'
      f'<feDropShadow dx="0" dy="0" stdDeviation="2.6" flood-color="#8b5cf6" flood-opacity="0.95"/>'
      f'<feDropShadow dx="0" dy="0" stdDeviation="1.1" flood-color="#c4b5fd" flood-opacity="0.55"/>'
      f'</filter>')
    A('</defs>')
    A('<style>.tw{animation:tw ease-in-out infinite}'
      '@keyframes tw{0%,100%{opacity:.15}50%{opacity:.9}}</style>')

    # ---- 背景（星空）----
    A(f'<rect width="{W}" height="{H}" rx="8" fill="{VOID}"/>')
    A(f'<ellipse cx="{W*0.25:.0f}" cy="{H*0.4:.0f}" rx="{W*0.35:.0f}" ry="{H*0.6:.0f}" fill="url(#neb)"/>')
    A(f'<ellipse cx="{W*0.78:.0f}" cy="{H*0.6:.0f}" rx="{W*0.30:.0f}" ry="{H*0.55:.0f}" fill="url(#neb)"/>')
    rnd = random.Random(424242)
    for _ in range(90):
        sx, sy = round(rnd.uniform(0, W), 1), round(rnd.uniform(0, H), 1)
        sr = round(rnd.uniform(0.4, 1.3), 2)
        A(f'<circle class="tw" cx="{sx}" cy="{sy}" r="{sr}" fill="{STAR}" '
          f'opacity="{round(rnd.uniform(.2,.75),2)}" '
          f'style="animation-duration:{round(rnd.uniform(2.5,6),1)}s;'
          f'animation-delay:{round(rnd.uniform(0,6),1)}s"/>')

    # ---- 草 ----
    t_back = active + 1.0
    A('<g>')
    for (c, r), lv in sorted(grid.items()):
        x, y = x_of(c), y_of(r)
        base = f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" fill="{LEVELS[lv]}"'
        if lv == 0:
            A(base + '/>')
            continue
        te = eat_time(c, r)
        kt = ";".join(str(v) for v in [0, k(te), k(te + EAT_FADE), k(t_back), 1])
        A(base + '>'
          f'<animate attributeName="opacity" values="1;1;0;0;1" keyTimes="{kt}" '
          f'dur="{LOOP:.2f}s" repeatCount="indefinite" calcMode="linear"/>'
          f'<animate attributeName="fill" values="{LEVELS[lv]};{LEVELS[lv]};{STAR};{LEVELS[lv]};{LEVELS[lv]}" '
          f'keyTimes="{kt}" dur="{LOOP:.2f}s" repeatCount="indefinite"/>'
          '</rect>')
    A('</g>')

    # ---- 猫の移動経路 ----
    pts, times = [], []
    for r in range(ROWS):
        t0 = r * (PASS_DUR + PASS_GAP)
        y = y_of(r) + CELL / 2
        xa, xb = x_of(0) + CELL / 2, x_of(cols - 1) + CELL / 2
        if r % 2 == 1:
            xa, xb = xb, xa
        pts += [(xa, y), (xb, y)]
        times += [t0, t0 + PASS_DUR]
    pts.append(pts[-1]); times.append(LOOP)

    vals = ";".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    kts  = ";".join(str(k(t)) for t in times)

    # ---- 猫 ----
    A(f'<g opacity="1">')
    A(f'<animate attributeName="opacity" values="0;1;1;0;0" '
      f'keyTimes="0;0.02;{k(active)};{k(active+0.5)};1" dur="{LOOP:.2f}s" repeatCount="indefinite"/>')
    A(f'<animateTransform attributeName="transform" type="translate" values="{vals}" '
      f'keyTimes="{kts}" dur="{LOOP:.2f}s" repeatCount="indefinite" calcMode="linear"/>')
    # 上下に跳ねる（あわせて少し大きく見せる）
    A('<g transform="scale(1.28)">')
    A('<animateTransform attributeName="transform" type="translate" values="0,0;0,-3.2;0,0" '
      'dur="0.46s" repeatCount="indefinite" calcMode="spline" '
      'keySplines="0.4 0 0.6 1;0.4 0 0.6 1" keyTimes="0;0.5;1"/>')
    # 猫本体（線を使わず塗りだけで一体のシルエットにし、全体を紫に光らせる）
    A('<g filter="url(#catGlow)">')
    A(f'<path d="M 6.5 4 C 13 4.5, 15.5 0, 12.5 -5.5" stroke="{FUR}" stroke-width="2.2" '
      f'fill="none" stroke-linecap="round">'
      f'<animateTransform attributeName="transform" type="rotate" '
      f'values="-12 6.5 4;12 6.5 4;-12 6.5 4" dur="0.95s" repeatCount="indefinite"/></path>')
    A(f'<path d="M-6.6 -9.8 L-5.4 -16.6 L-1.0 -11.4 Z" fill="{FUR}"/>')
    A(f'<path d="M6.6 -9.8 L5.4 -16.6 L1.0 -11.4 Z" fill="{FUR}"/>')
    A(f'<ellipse cx="0" cy="3" rx="7.8" ry="7.0" fill="{FUR}"/>')
    A(f'<circle cx="0" cy="-6.2" r="7.2" fill="{FUR}"/>')
    A('</g>')
    # 目（アーモンド型・まばたきする）
    A('<g filter="url(#eyeGlow)">')
    for ex in (-2.9, 2.9):
        A(f'<ellipse cx="{ex}" cy="-6.9" rx="1.5" ry="2.1" fill="{CYAN}">'
          f'<animate attributeName="ry" values="2.1;2.1;0.22;2.1;2.1" '
          f'keyTimes="0;0.46;0.5;0.54;1" dur="4.2s" repeatCount="indefinite"/></ellipse>')
    A('</g>')
    A(f'<path d="M-1.1 -3.1 L1.1 -3.1 L0 -1.9 Z" fill="{CYAN}" opacity="0.7"/>')
    A('</g></g>')

    # ---- 見出し ----
    A(f'<text x="{PAD_L}" y="24" font-family="Segoe UI,Helvetica,Arial,sans-serif" '
      f'font-size="13" font-weight="600" fill="{STAR}" opacity="0.92">'
      f'{total:,} contributions</text>')
    A(f'<text x="{W-PAD_R}" y="24" text-anchor="end" font-family="Segoe UI,Helvetica,Arial,sans-serif" '
      f'font-size="11" fill="#6b7aa8">last 12 months</text>')
    # 凡例
    ly = H - 12
    A(f'<text x="{PAD_L}" y="{ly+4}" font-family="Segoe UI,Helvetica,Arial,sans-serif" '
      f'font-size="10" fill="#6b7aa8">Less</text>')
    for i, col in enumerate(LEVELS):
        A(f'<rect x="{PAD_L+30+i*13}" y="{ly-6}" width="9" height="9" rx="2" fill="{col}"/>')
    A(f'<text x="{PAD_L+30+len(LEVELS)*13+4}" y="{ly+4}" '
      f'font-family="Segoe UI,Helvetica,Arial,sans-serif" font-size="10" fill="#6b7aa8">More</text>')

    A('</svg>')
    return "\n".join(o)


if __name__ == "__main__":
    payload = json.load(sys.stdin)
    cal = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    svg = build(cal)
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/cat-contribution.svg"
    io.open(out, "w", encoding="utf-8").write(svg)
    print(f"{out}: {len(svg):,} bytes")
