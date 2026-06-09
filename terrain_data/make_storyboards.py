#!/usr/bin/env python3
"""Storyboard frames for flythrough v2 — map crops + info cards.

Reads somme_trench_mosaic_z17.png + its geo sidecar, crops each story
beat's location, overlays the documented route polyline and an info card
(title / subtitle / body / citation), and writes 1920x1080 PNGs to
storyboards/ plus a contact sheet. Pure PIL; no Blender required.
"""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

Image.MAX_IMAGE_PIXELS = None

HERE = Path(__file__).resolve().parent
OUT = HERE / "storyboards"
OUT.mkdir(exist_ok=True)

GEO = json.loads((HERE / "somme_trench_mosaic_z17_geo.json").read_text())
B = GEO["bounds"]
W_PX, H_PX = GEO["width"], GEO["height"]

LOC = {
    "brigade_hq": (49.9874, 2.7963),
    "maricourt_line": (49.9875, 2.7911),
    "no_mans_land": (49.9902, 2.7958),
    "dublin_trench": (49.9925, 2.8000),
    "glatz_area": (49.9955, 2.8060),
    "briqueterie": (49.9945, 2.8100),
    "guillemont_far": (50.0010, 2.8390),
}
ROUTE = [LOC[k] for k in ("brigade_hq", "maricourt_line", "no_mans_land",
                          "dublin_trench", "glatz_area", "briqueterie")]

# beat: slug, focus point(s), crop half-width in metres, texts
BEATS = [
    dict(slug="01_brigade_hq_predawn", focus=[LOC["brigade_hq"]], half_m=450,
         title="Brigade HQ — Maricourt", subtitle="Pre-dawn, 1 July 1916",
         body="Stanley's 89th Brigade HQ in a pit southwest of Maricourt. On the right of the "
              "entire British line, the 17th King's Liverpool under Lt-Col. Bryan Fairfax wait "
              "beside the French.",
         cite="89th Bde history, p.121"),
    dict(slug="02_bombardment_0625", focus=[LOC["maricourt_line"]], half_m=550,
         title="6:25 a.m. — The Bombardment", subtitle="Maricourt sector front line",
         body="“At 6-25 a.m. we started an 'intense' bombardment... after sixty-five "
              "minutes, we popped over the parapet.”",
         cite="89th Bde history, p.131 (ledger #12)"),
    dict(slug="03_zero_hour_arm_in_arm",
         focus=[LOC["maricourt_line"], LOC["dublin_trench"]], half_m=700,
         title="7:30 a.m. — Zero Hour", subtitle="Arm in arm at the Anglo-French boundary",
         body="Second wave: Lt-Col. Fairfax and Commandant Lepetit of the French 153e R.I. "
              "step off ARM IN ARM across no man's land — planned symbolism of the alliance, "
              "under fire.",
         cite="Ground-truth ledger #14"),
    dict(slug="04_briqueterie_falls", focus=[LOC["briqueterie"]], half_m=500,
         title="The Briqueterie Falls", subtitle="1 July 1916 — objective taken",
         body="The fortified brickworks east of Montauban is rushed and taken. The 89th "
              "Brigade's objectives on 1 July are secured while attacks further north founder.",
         cite="89th Bde history, p.131 (ledger #13)"),
    dict(slug="05_consolidation", focus=[LOC["glatz_area"]], half_m=600,
         title="Consolidation", subtitle="Dublin Trench — Glatz Redoubt area",
         body="The captured ground is wired, reversed and held. The 30th Division stands on "
              "all its objectives — one of the few unqualified successes of the day.",
         cite="89th Bde history, p.131"),
    dict(slug="06_the_days_gains",
         focus=[LOC["maricourt_line"], LOC["briqueterie"], LOC["guillemont_far"]], half_m=2300,
         title="The Day's Gains", subtitle="Maricourt to Montauban ridge — toward Guillemont",
         body="“...les relations si cordiales entretenues avec leur chef le Colonel "
              "Fairfax ont permis de remarquer ses hautes qualites militaires...” "
              "— Col. de Coutard, 11 July 1916",
         cite="89th Bde history, p.134 (ledger #15)"),
]

FW, FH = 1920, 1080
M_PER_PX = GEO["approx_m_per_px"]

SERIF_B = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def ll_to_px(lat, lon):
    x = (lon - B["west"]) / (B["east"] - B["west"]) * W_PX
    y = (B["north"] - lat) / (B["north"] - B["south"]) * H_PX
    return x, y


def wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_beat(mosaic, beat, idx):
    # crop window (16:9) around focus centroid
    lats = [p[0] for p in beat["focus"]]
    lons = [p[1] for p in beat["focus"]]
    cx, cy = ll_to_px(sum(lats) / len(lats), sum(lons) / len(lons))
    half_w = beat["half_m"] / M_PER_PX
    half_h = half_w * FH / FW
    x0, y0 = cx - half_w, cy - half_h
    x1, y1 = cx + half_w, cy + half_h
    # clamp inside mosaic, preserving size
    if x0 < 0:
        x1 -= x0; x0 = 0
    if y0 < 0:
        y1 -= y0; y0 = 0
    if x1 > W_PX:
        x0 -= (x1 - W_PX); x1 = W_PX
    if y1 > H_PX:
        y0 -= (y1 - H_PX); y1 = H_PX
    x0, y0 = max(0, x0), max(0, y0)

    crop = mosaic.crop((int(x0), int(y0), int(x1), int(y1))).resize((FW, FH), Image.LANCZOS)
    img = crop.convert("RGB")
    sx, sy = FW / (x1 - x0), FH / (y1 - y0)

    def to_frame(lat, lon):
        px, py = ll_to_px(lat, lon)
        return ((px - x0) * sx, (py - y0) * sy)

    ov = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    # route polyline with soft shadow
    pts = [to_frame(*p) for p in ROUTE]
    for off, col, w in (((3, 3), (0, 0, 0, 110), 11), ((0, 0), (178, 24, 43, 235), 7)):
        d.line([(x + off[0], y + off[1]) for x, y in pts], fill=col,
               width=w, joint="curve")
    # waypoint dots
    for x, y in pts:
        d.ellipse([x - 10, y - 10, x + 10, y + 10], fill=(255, 248, 231, 255),
                  outline=(120, 20, 20, 255), width=4)
    # focus marker(s)
    for p in beat["focus"]:
        if p == LOC["guillemont_far"] and beat["slug"] != "06_the_days_gains":
            continue
        x, y = to_frame(*p)
        r = 17
        d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 200, 60, 255), width=5)

    # bottom card: blurred dark band
    band_h = 295
    band = img.crop((0, FH - band_h, FW, FH)).filter(ImageFilter.GaussianBlur(9))
    img.paste(band, (0, FH - band_h))
    d2 = ImageDraw.Draw(ov)
    d2.rectangle([0, FH - band_h, FW, FH], fill=(12, 10, 8, 198))
    d2.rectangle([0, FH - band_h, FW, FH - band_h + 4], fill=(193, 142, 62, 255))

    f_title = ImageFont.truetype(SERIF_B, 56)
    f_sub = ImageFont.truetype(SERIF, 33)
    f_body = ImageFont.truetype(SANS, 29)
    f_cite = ImageFont.truetype(SANS, 23)
    f_num = ImageFont.truetype(SERIF_B, 120)

    pad = 70
    y = FH - band_h + 28
    d2.text((pad, y), beat["title"], font=f_title, fill=(245, 234, 210, 255))
    tw = d2.textlength(beat["title"], font=f_title)
    d2.text((pad + tw + 30, y + 22), beat["subtitle"], font=f_sub,
            fill=(193, 162, 110, 255))
    y += 78
    for line in wrap(d2, beat["body"], f_body, FW - 2 * pad - 170):
        d2.text((pad, y), line, font=f_body, fill=(222, 215, 202, 255))
        y += 40
    d2.text((pad, FH - 44), beat["cite"], font=f_cite, fill=(160, 140, 105, 255))
    # big beat number, right side
    d2.text((FW - 165, FH - band_h + 75), f"{idx}", font=f_num,
            fill=(193, 142, 62, 90))

    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    path = OUT / f"{beat['slug']}.png"
    img.save(path, optimize=True)
    return path


def main():
    mosaic = Image.open(HERE / "somme_trench_mosaic_z17.png")
    paths = []
    for i, b in enumerate(BEATS):
        p = OUT / f"{b['slug']}.png"
        paths.append(p if p.exists() else render_beat(mosaic, b, i + 1))

    # contact sheet 3x2 at half size
    cw, ch = FW // 2, FH // 2
    sheet = Image.new("RGB", (cw * 3 + 40, ch * 2 + 30), (16, 13, 10))
    for i, p in enumerate(paths):
        im = Image.open(p).resize((cw, ch), Image.LANCZOS)
        sheet.paste(im, ((i % 3) * (cw + 10) + 10, (i // 3) * (ch + 10) + 10))
    sheet_path = OUT / "storyboard_contact_sheet.png"
    sheet.save(sheet_path, optimize=True)
    for p i