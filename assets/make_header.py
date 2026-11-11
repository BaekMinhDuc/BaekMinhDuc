"""Animated name header for a GitHub profile README.

Glyphs are converted to SVG paths (no font loading in the viewer), so it renders the same inside
<img> everywhere. The name draws its outline letter by letter, then fills with a gradient that keeps
sliding slowly; an accent bar grows and the subtitle fades in. Respects prefers-reduced-motion.

usage: make_header.py FONT.ttf OUT.svg [--text ...] [--sub ...]
"""
import argparse
import html

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ap = argparse.ArgumentParser()
ap.add_argument("font")
ap.add_argument("out")
ap.add_argument("--text", default="Ngo Pham Minh Duc")
ap.add_argument("--sub", default="AI Engineer & AI Researcher")
ap.add_argument("--weight", type=float, default=700)
ap.add_argument("--sub-weight", type=float, default=400)
ap.add_argument("--size", type=float, default=96)
ap.add_argument("--sub-size", type=float, default=26)
ap.add_argument("--tracking", type=float, default=-0.02, help="letter spacing of the name, in em")
ap.add_argument("--sub-tracking", type=float, default=0.01)
ap.add_argument("--sub-color", default="#7d8590")  # readable on GitHub light (#fff) and dark (#0d1117)
a = ap.parse_args()


def load(weight):
    f = TTFont(a.font)
    return instantiateVariableFont(f, {"wght": weight}) if "fvar" in f else f


def pair_kern(font, left, right):
    """X-advance adjustment for (left, right) from the GPOS 'kern' PairPos lookups."""
    if "GPOS" not in font:
        return 0
    gpos = font["GPOS"].table
    idx = {i for fr in gpos.FeatureList.FeatureRecord if fr.FeatureTag == "kern"
           for i in fr.Feature.LookupListIndex}
    for li in sorted(idx):
        lk = gpos.LookupList.Lookup[li]
        subs = [st.ExtSubTable for st in lk.SubTable] if lk.LookupType == 9 else lk.SubTable
        for st in subs:
            if getattr(st, "LookupType", 2) != 2 or left not in st.Coverage.glyphs:
                continue
            if st.Format == 1:
                for pvr in st.PairSet[st.Coverage.glyphs.index(left)].PairValueRecord:
                    if pvr.SecondGlyph == right and pvr.Value1 is not None:
                        return getattr(pvr.Value1, "XAdvance", 0) or 0
            elif st.Format == 2:
                v = st.Class1Record[st.ClassDef1.classDefs.get(left, 0)].Class2Record[
                    st.ClassDef2.classDefs.get(right, 0)].Value1
                if v is not None and getattr(v, "XAdvance", 0):
                    return v.XAdvance
    return 0


def run(font, text, size, tracking):
    """Lay out `text` at x=0, baseline=0. Returns (glyph path list, advance width, (ymin, ymax))."""
    s = size / font["head"].unitsPerEm
    cmap, gs, hmtx = font.getBestCmap(), font.getGlyphSet(), font["hmtx"]
    names = [cmap[ord(ch)] for ch in text]
    out, x, lo, hi = [], 0.0, 1e9, -1e9
    for i, (g, ch) in enumerate(zip(names, text)):
        if ch != " ":
            t = (s, 0, 0, -s, x, 0)
            pen, bp = SVGPathPen(gs), BoundsPen(gs)
            gs[g].draw(TransformPen(pen, t))
            gs[g].draw(TransformPen(bp, t))
            if bp.bounds:
                lo, hi = min(lo, bp.bounds[1]), max(hi, bp.bounds[3])
            out.append(pen.getCommands())
        kern = pair_kern(font, g, names[i + 1]) if i + 1 < len(names) else 0
        x += (hmtx[g][0] + kern) * s + tracking * size
    return out, x - tracking * size, (lo, hi)


name_paths, name_w, (n_lo, n_hi) = run(load(a.weight), a.text, a.size, a.tracking)
sub_paths, sub_w, (s_lo, s_hi) = run(load(a.sub_weight), a.sub, a.sub_size, a.sub_tracking)

PAD_X, PAD_TOP, GLOW = 28, 22, 14
W = round(max(name_w, sub_w) + 2 * PAD_X)
name_x = (W - name_w) / 2
name_base = PAD_TOP - n_lo                      # n_lo is negative (cap height above baseline)
bar_y = name_base + n_hi + 20
sub_base = bar_y + 24 - s_lo
H = round(sub_base + s_hi + 18)

n = len(name_paths)
t_fill = 0.9 + 0.08 * (n - 1) + 0.9             # when the last letter has finished filling
name_g = "".join(
    f'<path class="l" pathLength="1" style="animation-delay:{0.08 * i:.2f}s,{0.9 + 0.08 * i:.2f}s" d="{d}"/>'
    for i, d in enumerate(name_paths))
glow_g = "".join(f'<path d="{d}"/>' for d in name_paths)
sub_g = "".join(f'<path d="{d}"/>' for d in sub_paths)
esc = html.escape

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{esc(a.text)}, {esc(a.sub)}">
<title>{esc(a.text)} · {esc(a.sub)}</title>
<defs>
  <linearGradient id="g" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{W}" y2="0" spreadMethod="repeat">
    <stop offset="0" stop-color="#38bdf8"/>
    <stop offset="0.33" stop-color="#818cf8"/>
    <stop offset="0.66" stop-color="#e879f9"/>
    <stop offset="1" stop-color="#38bdf8"/>
    <animateTransform attributeName="gradientTransform" type="translate" from="0 0" to="{W} 0" dur="8s" repeatCount="indefinite"/>
  </linearGradient>
  <filter id="glow" x="-10%" y="-50%" width="120%" height="200%"><feGaussianBlur stdDeviation="{GLOW}"/></filter>
</defs>
<style>
  .l {{ fill: url(#g); fill-opacity: 0; stroke: url(#g); stroke-width: 1.6; stroke-linejoin: round;
        stroke-dasharray: 1; stroke-dashoffset: 1;
        animation: draw 1.4s cubic-bezier(.65,0,.35,1) forwards, fill .9s ease-out forwards; }}
  @keyframes draw {{ to {{ stroke-dashoffset: 0; }} }}
  @keyframes fill {{ to {{ fill-opacity: 1; stroke-opacity: 0; }} }}
  .glow {{ opacity: 0; animation: glow 1.2s ease-out {t_fill - 0.6:.2f}s forwards; }}
  @keyframes glow {{ to {{ opacity: .3; }} }}
  .bar {{ transform-box: fill-box; transform-origin: center; transform: scaleX(0);
          animation: bar .9s cubic-bezier(.65,0,.35,1) {t_fill - 0.8:.2f}s forwards; }}
  @keyframes bar {{ to {{ transform: scaleX(1); }} }}
  .sub {{ opacity: 0; animation: sub 1s ease-out {t_fill - 0.4:.2f}s forwards; }}
  @keyframes sub {{ to {{ opacity: 1; }} }}
  @media (prefers-reduced-motion: reduce) {{
    .l {{ animation: none; fill-opacity: 1; stroke-opacity: 0; }}
    .glow {{ animation: none; opacity: .3; }}
    .bar {{ animation: none; transform: none; }}
    .sub {{ animation: none; opacity: 1; }}
  }}
</style>
<g transform="translate({name_x:.2f} {name_base:.2f})">
  <g class="glow" filter="url(#glow)" fill="url(#g)">{glow_g}</g>
  <g>{name_g}</g>
</g>
<rect class="bar" x="{W / 2 - 60:.1f}" y="{bar_y:.1f}" width="120" height="4" rx="2" fill="url(#g)"/>
<g class="sub" fill="{a.sub_color}" transform="translate({(W - sub_w) / 2:.2f} {sub_base:.2f})">{sub_g}</g>
</svg>
'''
open(a.out, "w", encoding="utf-8").write(svg)
print(f"{a.out}: {W}x{H}, {n} glyphs, {len(svg) / 1024:.1f} KB, intro {t_fill + 0.6:.1f}s")
