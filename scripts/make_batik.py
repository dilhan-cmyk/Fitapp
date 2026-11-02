#!/usr/bin/env python3
"""Generate the batik artwork used by the app, drawn from the motifs on the
reference shirt (blue ground; rose paisley-form leaves with curved hatching;
cream ovals filled with a dot lattice; slim striped leaves; small rosettes;
pale vines with curled ends; and the centre panel of diamonds with
four-petal flowers between diagonally striped fields).

Writes www/batik-field.svg (the all-over pattern) and www/batik-band.svg
(the diamond panel as a horizontal border).
"""
import math, random, os, sys

OUT = sys.argv[1] if len(sys.argv) > 1 else 'www'
random.seed(11)
W = H = 240

# palette, read from the shirt
GROUND, GROUND_D, GROUND_L = '#4a98c6', '#3a85b5', '#6db3dc'
VINE, HALO = '#a9d6ee', '#c4e5f5'
ROSE, ROSE_L, MAUVE, MAUVE_L = '#c99aa5', '#dbb5be', '#8b5f73', '#a8707f'
CREAM, BLUE_DOT, BLUE_LINE, LAV = '#f0e6e3', '#3a7aa8', '#2f6f9f', '#7f88b4'

f = lambda v: ('%.2f' % v).rstrip('0').rstrip('.')


def spiral(step=0.6, k=0.011, smax=34):
    """A curl that starts heading along +x and winds tighter as it goes."""
    x = y = th = 0.0
    pts = [(0, 0)]
    s = 0.0
    while s < smax:
        th = k * s * s
        x += math.cos(th) * step
        y += math.sin(th) * step
        pts.append((x, y))
        s += step
    return 'M' + ' L'.join(f'{f(a)} {f(b)}' for a, b in pts)


def smooth(points):
    """Catmull-Rom -> cubic bezier through points."""
    d = f'M{f(points[0][0])} {f(points[0][1])}'
    for i in range(len(points) - 1):
        p0 = points[i - 1] if i > 0 else points[i]
        p1, p2 = points[i], points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f' C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(p2[0])} {f(p2[1])}'
    return d


def vine_h(y0, amp, phase, n=1):
    pts = [(x, y0 + amp * math.sin(2 * math.pi * n * x / W + phase)) for x in range(-30, W + 31, 10)]
    return smooth(pts)


def vine_v(x0, amp, phase, n=1):
    pts = [(x0 + amp * math.sin(2 * math.pi * n * y / H + phase), y) for y in range(-30, H + 31, 10)]
    return smooth(pts)


def vy(y0, amp, phase, x, n=1):
    return y0 + amp * math.sin(2 * math.pi * n * x / W + phase)


# ---------------------------------------------------------------- motifs
def bez(p0, p1, p2, p3, t):
    u = 1 - t
    return (u**3*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t**3*p3[0],
            u**3*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t**3*p3[1])


def edge(segs, n=26):
    """Sample a chain of cubics at even arc-length spacing."""
    raw = []
    for sg in segs:
        for i in range(31):
            raw.append(bez(*sg, i / 30))
    cum = [0.0]
    for a, b in zip(raw, raw[1:]):
        cum.append(cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    out = []
    for k in range(n):
        target = cum[-1] * k / (n - 1)
        j = max(i for i in range(len(cum)) if cum[i] <= target + 1e-9)
        j = min(j, len(raw) - 2)
        seg = cum[j + 1] - cum[j] or 1
        t = (target - cum[j]) / seg
        out.append((raw[j][0] + (raw[j + 1][0] - raw[j][0]) * t, raw[j][1] + (raw[j + 1][1] - raw[j][1]) * t))
    return out


# Large leaf: slender paisley form. Belly low on the left, tip drawn out and
# curling over to the right, as on the shirt.
TIP = (40, -102)
LEFT = edge([((0, 0), (-20, -4), (-25, -50), (-13, -73)), ((-13, -73), (-4, -87), (16, -95), TIP)])
RIGHT = edge([((0, 0), (20, -2), (28, -38), (20, -63)), ((20, -63), (17, -75), (28, -92), TIP)])
LEAF = smooth(LEFT) + ' ' + smooth(RIGHT[::-1]).replace('M', 'L', 1) + ' Z'

hatch = []
for i in range(15):
    u = 0.06 + 0.88 * i / 14
    pts = [((1 - u) * a[0] + u * b[0], (1 - u) * a[1] + u * b[1]) for a, b in zip(LEFT, RIGHT)]
    col = MAUVE if i % 4 == 0 else MAUVE_L
    dash = ['30 3 18 5 24 4', '20 4 32 3 13 6', '36 5 16 3 22 4'][i % 3]
    hatch.append(f'<path d="{smooth(pts)}" fill="none" stroke="{col}" stroke-width=".95" stroke-linecap="round" '
                 f'stroke-dasharray="{dash}" stroke-dashoffset="{(i * 11) % 29}"/>')
mid = [((1 - .55) * a[0] + .55 * b[0], (1 - .55) * a[1] + .55 * b[1]) for a, b in zip(LEFT, RIGHT)]
hatch.append(f'<path d="{smooth(mid)}" fill="none" stroke="{CREAM}" stroke-width="1.1" opacity=".55" stroke-linecap="round" stroke-dasharray="26 7 14 6"/>')
hatch = ''.join(hatch)

DEFS = f'''
<pattern id="lat" width="4.2" height="4.2" patternUnits="userSpaceOnUse" patternTransform="rotate(32)">
  <circle cx="1.05" cy="1.05" r=".78" fill="{BLUE_DOT}"/><circle cx="3.15" cy="3.15" r=".78" fill="{BLUE_DOT}"/>
</pattern>
<clipPath id="cl"><path d="{LEAF}"/></clipPath>
<path id="egg" d="M-1 -20 C9 -19 13 -4 10 8 C6 19 -5 21 -10 12 C-15 2 -12 -16 -1 -20Z"/>
<path id="lens" d="M0 -23 C8.5 -11 8.5 11 0 23 C-8.5 11 -8.5 -11 0 -23Z"/>
<clipPath id="cs"><path d="M0 -23 C8.5 -11 8.5 11 0 23 C-8.5 11 -8.5 -11 0 -23Z"/></clipPath>
<path id="curlp" d="{spiral()}"/>

<g id="leaf">
  <path d="{LEAF}" fill="{ROSE}" stroke="{HALO}" stroke-width="3" stroke-linejoin="round"/>
  <g clip-path="url(#cl)">{hatch}
    <path d="M26 -6 C33 -22 31 -38 24 -52" fill="none" stroke="{CREAM}" stroke-width="1" opacity=".55" stroke-linecap="round"/>
  </g>
  <path d="{LEAF}" fill="none" stroke="{MAUVE}" stroke-width=".9" opacity=".5" stroke-linejoin="round"/>
  <circle cx="14" cy="-18" r="1.5" fill="{CREAM}"/><circle cx="-8" cy="-34" r="1.2" fill="{CREAM}" opacity=".9"/>
</g>

<g id="leaf2">
  <use href="#leaf" xlink:href="#leaf" transform="translate(-4 2) rotate(-26) scale(.78)"/>
  <use href="#leaf" xlink:href="#leaf"/>
</g>

<g id="seed">
  <use href="#egg" xlink:href="#egg" fill="{HALO}" stroke="{HALO}" stroke-width="3" stroke-linejoin="round"/>
  <use href="#egg" xlink:href="#egg" fill="{CREAM}"/>
  <use href="#egg" xlink:href="#egg" fill="url(#lat)"/>
  <use href="#egg" xlink:href="#egg" fill="none" stroke="{BLUE_LINE}" stroke-width="1.2"/>
</g>

<g id="slim">
  <use href="#lens" xlink:href="#lens" fill="{ROSE_L}" stroke="{HALO}" stroke-width="2.8" stroke-linejoin="round"/>
  <g clip-path="url(#cs)" stroke="{CREAM}" stroke-width="1.15" stroke-linecap="butt" opacity=".95">
    {''.join(f'<path d="M-12 {f(y + 1.4)} L12 {f(y - 1.4)}"/>' for y in [v * 3.2 - 19 for v in range(0, 13)])}
  </g>
  <use href="#lens" xlink:href="#lens" fill="none" stroke="{LAV}" stroke-width=".9"/>
</g>

<g id="bud">
  <path d="M0 -12 C7 -5 7 6 0 12 C-7 6 -7 -5 0 -12Z" fill="{ROSE}" stroke="{HALO}" stroke-width="3" stroke-linejoin="round"/>
  <path d="M0 -8 L0 8 M-2.6 -2 L0 1 M2.6 -2 L0 1" stroke="{MAUVE}" stroke-width=".9" fill="none" opacity=".8" stroke-linecap="round"/>
  <circle cx="0" cy="-6.5" r="1.4" fill="{CREAM}"/>
</g>

<g id="ros">
  <circle r="4.6" fill="none" stroke="{CREAM}" stroke-width="1.1"/>
  <circle r="1.5" fill="{CREAM}"/>
  {''.join(f'<circle cx="{f(7.6 * math.cos(a * math.pi / 2.5))}" cy="{f(7.6 * math.sin(a * math.pi / 2.5))}" r=".85" fill="{CREAM}" opacity=".9"/>' for a in range(5))}
</g>

<g id="ros2">
  <circle r="4.6" fill="none" stroke="{CREAM}" stroke-width="1.2" stroke-dasharray="1.7 1.7"/>
  <circle r="1.5" fill="{CREAM}"/>
</g>

<g id="curl"><use href="#curlp" xlink:href="#curlp" fill="none" stroke="{VINE}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></g>
'''

# ---------------------------------------------------------------- layout
OCC = []
_OCC = {'leaf': (12, -50, 50), 'leaf2': (8, -48, 52), 'seed': (0, 0, 24), 'slim': (0, 0, 25),
        'bud': (0, 0, 14), 'ros': (0, 0, 11), 'ros2': (0, 0, 11)}


def put(i, x, y, r=0, s=1):
    if i in _OCC:
        lx, ly, rad = _OCC[i]
        a = math.radians(r)
        OCC.append((x + s * (lx * math.cos(a) - ly * math.sin(a)), y + s * (lx * math.sin(a) + ly * math.cos(a)), rad * s))
    return f'<use href="#{i}" xlink:href="#{i}" transform="translate({f(x)} {f(y)}) rotate({f(r)}) scale({f(s)})"/>'


body = []
# ground mottling (the cracked-wax texture of the dyed cloth)
for _ in range(150):
    x, y = random.uniform(0, W), random.uniform(0, H)
    body.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(random.uniform(.5, 1.2))}" fill="{random.choice([GROUND_L, GROUND_L, GROUND_D])}"/>')
for _ in range(26):
    x, y = random.uniform(0, W), random.uniform(0, H)
    a = random.uniform(0, 180)
    body.append(f'<path d="M{f(x)} {f(y)} l{f(math.cos(math.radians(a)) * 7)} {f(math.sin(math.radians(a)) * 7)}" stroke="{GROUND_D}" stroke-width=".8" stroke-linecap="round" opacity=".7"/>')

# vines first (they run behind the motifs)
VW = f'fill="none" stroke="{VINE}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"'
body += [f'<path d="{vine_h(60, 17, .5)}" {VW}/>',
         f'<path d="{vine_h(176, 15, 2.7)}" {VW}/>',
         f'<path d="{vine_v(122, 19, 1.1)}" {VW}/>']
# curls branching off the vines
for x, side, rot in [(36, -1, -75), (150, 1, 80), (214, -1, -70)]:
    y = vy(60, 17, .5, x)
    body.append(put('curl', x, y, rot, 1))
for x, side, rot in [(70, 1, 100), (190, -1, -95)]:
    y = vy(176, 15, 2.7, x)
    body.append(put('curl', x, y, rot, .95))
body.append(put('curl', 122 + 19 * math.sin(1.1 + 2 * math.pi * 30 / H), 30, 10, .9))
body.append(put('curl', 122 + 19 * math.sin(1.1 + 2 * math.pi * 200 / H), 200, 190, .9))

# main leaves, seeds, slim leaves, buds, rosettes
body += [
    # large paisley leaves, single and folded pairs
    put('leaf', 38, 156, -12, .8),
    put('leaf', 176, 236, 170, .76),
    put('leaf2', 140, 152, 22, .7),
    put('leaf', 222, 104, -6, .68),
    put('leaf2', 100, 46, 200, .6),
    # dot-lattice ovals
    put('seed', 118, 112, 38, .85),
    put('seed', 60, 70, -34, .8),
    put('seed', 206, 40, -22, .85),
    put('seed', 14, 98, 20, .75),
    put('seed', 82, 206, -58, .85),
    put('seed', 176, 176, 62, .78),
    put('seed', 232, 170, -14, .8),
    put('seed', 150, 22, 74, .72),
    put('seed', 34, 14, -50, .72),
    # slim striped leaves
    put('slim', 84, 100, -52, .9),
    put('slim', 166, 112, 40, .85),
    put('slim', 196, 72, 72, .8),
    put('slim', 52, 198, 28, .85),
    put('slim', 122, 200, -30, .8),
    put('slim', 8, 144, 10, .75),
    put('slim', 128, 70, 120, .75),
    put('slim', 234, 214, 150, .8),
    # small rose buds with a cream dot
    put('bud', 26, 52, 28, .8),
    put('bud', 100, 150, -22, .75),
    put('bud', 214, 192, 52, .75),
    put('bud', 66, 236, 160, .7),
    put('bud', 168, 52, -40, .7),
    put('bud', 238, 12, 10, .7),
    # rosettes
    put('ros', 70, 118, 0, .8), put('ros', 178, 84, 0, .75), put('ros', 148, 124, 0, .7),
    put('ros', 22, 128, 0, .7), put('ros', 112, 188, 0, .7), put('ros', 220, 140, 0, .72),
    put('ros2', 120, 84, 0, 1), put('ros2', 204, 114, 0, 1), put('ros2', 74, 172, 0, 1),
    put('ros2', 216, 230, 0, 1), put('ros2', 26, 214, 0, 1), put('ros2', 48, 28, 0, 1),
    put('ros2', 188, 10, 0, 1), put('ros2', 160, 196, 0, 1),
    # filler: small curls (sulur) in the gaps
    put('curl', 90, 134, 40, .55), put('curl', 196, 150, 200, .55), put('curl', 14, 176, -60, .55),
    put('curl', 140, 36, 150, .5), put('curl', 232, 66, 110, .5), put('curl', 106, 226, -100, .55),
    put('curl', 62, 14, 20, .5), put('curl', 184, 204, 60, .5),
]
# groups of three dots (cecek) and short "sawut" strokes in the gaps
for x, y, r in [(92, 70, 0), (30, 90, 40), (150, 96, 10), (206, 172, 70), (56, 154, 20), (128, 134, 60),
                (232, 98, 0), (180, 24, 30), (10, 36, 50), (104, 226, 0), (160, 232, 20), (68, 4, 0)]:
    body.append(f'<g transform="translate({x} {y}) rotate({r})" fill="{CREAM}"><circle cx="0" cy="0" r="1.15"/><circle cx="4.2" cy="1.2" r="1.15"/><circle cx="1.8" cy="4.4" r="1.15"/></g>')
for x, y, r in [(110, 98, 20), (28, 74, -30), (190, 130, 60), (86, 176, 10), (222, 80, 90), (150, 70, -10), (54, 232, 40)]:
    body.append(f'<g transform="translate({x} {y}) rotate({r})" stroke="{HALO}" stroke-width="1.3" stroke-linecap="round" fill="none"><path d="M0 0l5-3"/><path d="M1 3l5-3"/><path d="M2 6l5-3"/></g>')
# beads (cecek) strung along the vines
for x in (14, 54, 100, 142, 184, 232):
    y = vy(60, 17, .5, x)
    body.append(f'<circle cx="{x}" cy="{f(y + 4)}" r="1.1" fill="{CREAM}"/>')
for x in (30, 88, 130, 170, 224):
    y = vy(176, 15, 2.7, x)
    body.append(f'<circle cx="{x}" cy="{f(y - 4)}" r="1.1" fill="{CREAM}"/>')

# fine pale tendrils web the gaps, as on the cloth
def pd(a, b):
    dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
    return math.hypot(min(dx, W - dx), min(dy, H - dy))


rnd = random.Random(5)
placed = []
tries = 0
while len(placed) < 34 and tries < 6000:
    tries += 1
    pt = (rnd.uniform(0, W), rnd.uniform(0, H))
    if any(pd(pt, (cx, cy)) < r + 7 for cx, cy, r in OCC): continue
    if any(pd(pt, q) < 17 for q in placed): continue
    placed.append(pt)
    rot = rnd.uniform(0, 360)
    sc = rnd.uniform(.6, .95)
    flip = -1 if rnd.random() < .5 else 1
    body.append(f'<use href="#curl" xlink:href="#curl" transform="translate({f(pt[0])} {f(pt[1])}) rotate({f(rot)}) scale({f(sc * flip)} {f(sc)})"/>')
print('fillers placed:', len(placed))

content = ''.join(body)
copies = ''.join(f'<use href="#all" xlink:href="#all" x="{dx}" y="{dy}"/>'
                 for dx in (-W, 0, W) for dy in (-H, 0, H))

field = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>{DEFS}<g id="all">{content}</g></defs>
<rect width="{W}" height="{H}" fill="{GROUND}"/>
{copies}
</svg>'''

# ---------------------------------------------------------------- band
PL_G, PL_S, PL_D = '#a68f99', '#ecdade', '#54527f'
band = f'''<svg xmlns="http://www.w3.org/2000/svg" width="48" height="24" viewBox="0 0 48 24">
<defs>
<pattern id="sl" width="3.3941" height="3.3941" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
  <rect width="3.3941" height="3.3941" fill="{PL_G}"/><rect width="1.4" height="3.3941" fill="{PL_S}"/></pattern>
<pattern id="sr" width="3.3941" height="3.3941" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">
  <rect width="3.3941" height="3.3941" fill="{PL_G}"/><rect width="1.4" height="3.3941" fill="{PL_S}"/></pattern>
</defs>
<rect width="48" height="24" fill="url(#sl)"/>
<path d="M12 1.6L22.4 12L12 22.4L1.6 12Z" fill="{PL_D}" stroke="{CREAM}" stroke-width="1.3" stroke-linejoin="round"/>
<g fill="none" stroke="#b9b0d6" stroke-width="1.1">
  <circle cx="9" cy="12" r="2.7"/><circle cx="15" cy="12" r="2.7"/><circle cx="12" cy="9" r="2.7"/><circle cx="12" cy="15" r="2.7"/>
</g>
<circle cx="12" cy="12" r="1.2" fill="{CREAM}"/>
<path d="M36 1.6L46.4 12L36 22.4L25.6 12Z" fill="url(#sr)" stroke="{CREAM}" stroke-width="1.3" stroke-linejoin="round"/>
<rect width="48" height="1.1" fill="{CREAM}"/><rect y="22.9" width="48" height="1.1" fill="{CREAM}"/>
</svg>'''

os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, 'batik-field.svg'), 'w').write(field)
open(os.path.join(OUT, 'batik-band.svg'), 'w').write(band)
print('field', len(field), 'bytes; band', len(band), 'bytes')
