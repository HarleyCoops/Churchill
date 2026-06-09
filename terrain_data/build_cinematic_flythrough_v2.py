#!/usr/bin/env python3
"""Epic catalogue flythrough of 1 July 1916 — Fairfax's documented route.

Version 2 of build_cinematic_flythrough.py (the original is untouched).
Run inside Blender with somme_battlefield.blend open, or headless:

    blender -b somme_battlefield.blend --python build_cinematic_flythrough_v2.py ^
            --python render_flythrough.py

What v2 adds over v1
--------------------
1. STORY   — six beats tracing the 17th Bn King's Liverpool Regiment
   (89th Brigade, 30th Division) on 1 July 1916: pre-dawn Maricourt HQ,
   the 6:25 a.m. bombardment, the 7:30 a.m. arm-in-arm advance with
   Commandant Lepetit of the French 153e RI (slow low tracking shot),
   the Briqueterie assault, Glatz Redoubt consolidation, and a pull-back
   finale over the day's gains. Card copy quotes the 89th Brigade history
   with page citations (see WAYPOINTS).
2. CAMERA  — at each key beat the camera ZOOMS OUT (altitude up + lens
   wider) while the info card fades in, holds for reading, then zooms
   back to the map surface and resumes tracing the route. All keys are
   BEZIER / AUTO_CLAMPED (slow-in/slow-out).
3. ROUTE   — the documented path is rebuilt as a ground-hugging polyline:
   every sample is dropped onto the terrain by bilinear interpolation of
   somme_elevations.json, so camera target and route tube follow the
   actual relief.
4. LIGHT   — the Sun object is animated across the film: pre-dawn
   blue-grey, low warm light at zero hour (1 July 1916 dawned clear),
   harsher higher sun by the Briqueterie beat. World background follows.
   Optional cheap EEVEE-Next volumetric mist (ENABLE_MIST).
5. TEXTURE — swaps the terrain texture to the z17 NLS mosaic built by
   build_highres_trench_mosaic.py, validating geo-alignment against the
   JSON sidecar (the mosaic spans exactly the terrain UV bounds, so no
   UV changes are needed; the script verifies this rather than assuming).

Source citations used on cards (all traceable to research/ground-truth-ledger.md):
  - Ledger #12 / 89th Bde p.131: "at 6-25 a.m. we started an 'intense'
    bombardment... after sixty-five minutes, we popped over the parapet."
  - Ledger #14 / Readme.md: Fairfax and Cdt Lepetit (3rd Bn, 153e RI)
    advanced arm in arm across no man's land in the second wave.
  - Ledger #13 / 89th Bde p.131: the Briqueterie objective taken on 1 July.
  - Ledger #15 / 89th Bde p.134: Colonel de Coutard's letter, 11 July 1916,
    naming Fairfax: "...ses hautes qualites militaires...".
  - Brigade HQ "pit southwest of Maricourt": 89th Bde p.121 (v1 citation).
  NOTE: "Glatz Redoubt" as a named strongpoint is standard 30th Division
  historiography but is NOT yet a ledger entry; its card therefore stays
  on ledgered ground (consolidation of captured objectives, p.131) and
  names the redoubt only in the subtitle as a map label.

The module imports cleanly WITHOUT bpy so geometry/easing helpers can be
unit-tested:  python3 build_cinematic_flythrough_v2.py --selftest
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

try:  # Blender runtime
    import bpy
    from mathutils import Vector
    IN_BLENDER = True
except ImportError:  # plain CPython: helpers + selftest only
    bpy = None
    Vector = None
    IN_BLENDER = False

HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------- constants
FPS = 30
TRAVEL_LENS = 32          # mm while moving between beats
ENABLE_MIST = True        # cheap EEVEE-Next volumetric ground haze
MIST_DENSITY = 0.015

# Geo frame — MUST match rebuild_full_scene.py and the mosaic sidecar.
SOUTH, NORTH = 49.970139, 50.010139
WEST, EAST = 2.749861, 2.859861
TERRAIN_X, TERRAIN_Y = 30.0, 11.0
MIN_ELEV, MAX_ELEV = 58.1, 171.4
Z_SCALE = 1.5 / (MAX_ELEV - MIN_ELEV)

ELEVATIONS_JSON = HERE / "somme_elevations.json"
MOSAIC_PNG = HERE / "somme_trench_mosaic_z17.png"
MOSAIC_SIDECAR = HERE / "somme_trench_mosaic_z17_geo.json"

# ------------------------------------------------------------------- story
# All positions are (lat, lon) inside the terrain/mosaic bounds above.
# The scene's pin geography (rebuild_full_scene.py waypoints A..H) is kept
# as the spatial reference so existing labels/pins stay coherent.
LOC = {
    "brigade_hq":     (49.9874, 2.7963),  # pin A — "pit SW of Maricourt", p.121
    "maricourt_line": (49.9875, 2.7911),  # pin B — Anglo-French boundary seam;
                                          # memorial at 49d59'15"N 2d47'28"E
    "no_mans_land":   (49.9902, 2.7958),  # mid-advance sample point
    "dublin_trench":  (49.9925, 2.8000),  # first objective belt (south of Montauban pin)
    "glatz_area":     (49.9955, 2.8060),  # consolidation area NW of Briqueterie pin
    "briqueterie":    (49.9945, 2.8100),  # pin D — objective taken 1 July, p.131
    "guillemont_far": (50.0010, 2.8390),  # pin G — finale gaze direction
}

# The documented route polyline (ground-hugging, in story order).
ROUTE_LATLON = [
    LOC["brigade_hq"],
    LOC["maricourt_line"],
    LOC["no_mans_land"],
    LOC["dublin_trench"],
    LOC["glatz_area"],
    LOC["briqueterie"],
]

DEFAULTS = {
    "stop_offset": (-1.3, -1.0, 1.1),   # camera offset from POI at the stop
    "look_height": 0.22,
    "lens_stop": 45,                    # mm when settled on the surface
    "lens_wide": 24,                    # mm at the top of the card zoom-out
    "card_rise": 3.2,                   # BU of altitude gained for the card
    "orbit_radius": 1.6,
    "orbit_height": 1.0,
    "orbit_degrees": 0,                 # default: no orbit
    "timing": {
        "travel": 84,    # frames moving to this beat
        "settle": 14,
        "zoom_out": 26,  # card fades in during this rise
        "hold": 78,      # reading time, wide framing
        "zoom_in": 26,   # card fades out during the descent
        "orbit": 0,
        "exit": 6,
    },
}

# Each waypoint: where, what the card says, and how the camera behaves.
# "kind": "stop" = settle/zoom-out/card/zoom-in; "tracking" = slow low dolly
# along a route segment with the card up (the zero-hour centrepiece);
# "finale" = continuous pull-back/zoom-out, card up, no return descent.
WAYPOINTS = [
    {
        "kind": "stop",
        "slug": "brigade_hq_predawn",
        "loc": "brigade_hq",
        "title": "Brigade HQ — Maricourt",
        "subtitle": "Pre-dawn, 1 July 1916",
        "card_body": "Stanley's 89th Brigade HQ in a pit southwest of Maricourt. "
                     "On the right of the entire British line, the 17th King's "
                     "Liverpool under Lt-Col. Bryan Fairfax wait beside the French.",
        "citation": "89th Bde history, p.121",
        "timing": {"travel": 60, "hold": 84},
        "orbit_degrees": 70,
        "sun": "predawn",
    },
    {
        "kind": "stop",
        "slug": "bombardment_0625",
        "loc": "maricourt_line",
        "title": "6:25 a.m. — The Bombardment",
        "subtitle": "Maricourt sector front line",
        "card_body": "“At 6-25 a.m. we started an 'intense' bombardment... "
                     "after sixty-five minutes, we popped over the parapet.”",
        "citation": "89th Bde history, p.131 (ledger #12)",
        "timing": {"travel": 78, "hold": 84},
        "sun": "first_light",
    },
    {
        # EMOTIONAL CENTREPIECE: slow, low tracking shot across no man's land
        # at the Anglo-French boundary seam.
        "kind": "tracking",
        "slug": "zero_hour_arm_in_arm",
        "track_from": "maricourt_line",
        "track_to": "dublin_trench",
        "title": "7:30 a.m. — Zero Hour",
        "subtitle": "Arm in arm at the Anglo-French boundary",
        "card_body": "Second wave: Lt-Col. Fairfax and Commandant Lepetit of the "
                     "French 153e R.I. step off ARM IN ARM across no man's land — "
                     "planned symbolism of the alliance, under fire.",
        "citation": "Ground-truth ledger #14; Readme.md (89th Bde narrative)",
        "track_height": 0.55,        # very low over the map surface
        "track_lateral": (-0.9, -0.7),  # camera rides SW of the route line
        "lens_stop": 50,
        "timing": {"travel": 64, "track": 260, "hold": 0},
        "sun": "zero_hour",
    },
    {
        "kind": "stop",
        "slug": "briqueterie_assault",
        "loc": "briqueterie",
        "title": "The Briqueterie Falls",
        "subtitle": "1 July 1916 — objective taken",
        "card_body": "The fortified brickworks east of Montauban is rushed and "
                     "taken. The 89th Brigade's objectives on 1 July are secured "
                     "while attacks further north founder.",
        "citation": "89th Bde history, p.131 (ledger #13)",
        "orbit_degrees": 120,
        "timing": {"travel": 96, "hold": 84, "orbit": 84},
        "sun": "mid_morning",
    },
    {
        "kind": "stop",
        "slug": "glatz_consolidation",
        "loc": "glatz_area",
        "title": "Consolidation",
        "subtitle": "Dublin Trench — Glatz Redoubt area",
        "card_body": "The captured ground is wired, reversed and held. The "
                     "30th Division stands on all its objectives — one of the "
                     "few unqualified successes of the day.",
        "citation": "89th Bde history, p.131; Glatz Redoubt named per 30th Div. accounts (not yet ledgered)",
        "orbit_degrees": 90,
        "timing": {"travel": 72, "hold": 78, "orbit": 72},
        "sun": "mid_morning",
    },
    {
        "kind": "finale",
        "slug": "finale_the_days_gains",
        "loc": "glatz_area",
        "gaze": "guillemont_far",
        "title": "The Day's Gains",
        "subtitle": "Maricourt to Montauban ridge — toward Guillemont",
        "card_body": "“...les relations si cordiales entretenues avec leur chef "
                     "le Colonel Fairfax ont permis de remarquer ses hautes "
                     "qualites militaires...” — Col. de Coutard, 11 July 1916",
        "citation": "89th Bde history, p.134 (ledger #15)",
        "finale_rise": 7.5,
        "finale_back": 6.0,
        "lens_wide": 21,
        "timing": {"travel": 60, "zoom_out": 150, "hold": 110},
        "sun": "late_morning",
    },
]

# Sun states: (elevation deg, azimuth deg from +Y/north CW, energy, color).
# 1 July 1916 over the Somme: sunrise ~04:00 BST in the NE, clear morning.
SUN_STATES = {
    "predawn":      (-2.0,  48.0, 0.45, (0.52, 0.60, 0.78)),
    "first_light":  ( 4.0,  55.0, 1.40, (1.00, 0.58, 0.34)),
    "zero_hour":    (11.0,  68.0, 2.60, (1.00, 0.74, 0.50)),
    "mid_morning":  (28.0,  95.0, 3.80, (1.00, 0.90, 0.78)),
    "late_morning": (40.0, 118.0, 4.40, (1.00, 0.96, 0.90)),
}
WORLD_STATES = {  # background colour + strength keyed alongside the sun
    "predawn":      ((0.045, 0.055, 0.090), 0.28),
    "first_light":  ((0.120, 0.090, 0.080), 0.35),
    "zero_hour":    ((0.180, 0.160, 0.140), 0.42),
    "mid_morning":  ((0.230, 0.250, 0.290), 0.50),
    "late_morning": ((0.260, 0.300, 0.360), 0.55),
}


# ======================================================== pure helpers
# (no bpy — unit-testable; see selftest())

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def smoothstep(t: float) -> float:
    """Cubic ease-in/ease-out on [0,1]."""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def load_elevations() -> list:
    with open(ELEVATIONS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def sample_elevation(elev: list, lat: float, lon: float) -> float:
    """Bilinear elevation (metres) at lat/lon from the DEM grid."""
    rows, cols = len(elev), len(elev[0])
    u = (lon - WEST) / (EAST - WEST)
    v = (lat - SOUTH) / (NORTH - SOUTH)
    col_f = max(0.0, min(1.0, u)) * (cols - 1)
    row_f = (1.0 - max(0.0, min(1.0, v))) * (rows - 1)  # row 0 = north
    r0 = min(int(row_f), rows - 2)
    c0 = min(int(col_f), cols - 2)
    fr, fc = row_f - r0, col_f - c0
    return (elev[r0][c0] * (1 - fr) * (1 - fc)
            + elev[r0][c0 + 1] * (1 - fr) * fc
            + elev[r0 + 1][c0] * fr * (1 - fc)
            + elev[r0 + 1][c0 + 1] * fr * fc)


def geo_to_blender(elev: list, lat: float, lon: float) -> tuple:
    """lat/lon -> Blender (x, y, z) on the terrain surface.
    Identical mapping to rebuild_full_scene.py."""
    u = (lon - WEST) / (EAST - WEST)
    v = (lat - SOUTH) / (NORTH - SOUTH)
    x = u * TERRAIN_X
    y = v * TERRAIN_Y
    z = (sample_elevation(elev, lat, lon) - MIN_ELEV) * Z_SCALE
    return (x, y, z)


def resample_route(elev: list, latlon_points: list, samples_per_leg: int = 24) -> list:
    """Densify the lat/lon polyline and drop every sample onto the terrain.
    Returns a list of (x, y, z) Blender coords hugging the ground."""
    out = []
    for i in range(len(latlon_points) - 1):
        (lat0, lon0), (lat1, lon1) = latlon_points[i], latlon_points[i + 1]
        n = samples_per_leg
        for s in range(n):
            t = s / n
            out.append(geo_to_blender(elev, lerp(lat0, lat1, t), lerp(lon0, lon1, t)))
    out.append(geo_to_blender(elev, *latlon_points[-1]))
    return out


def sun_rotation(elevation_deg: float, azimuth_deg: float) -> tuple:
    """Euler XYZ for a Blender SUN light so it shines FROM the given sky
    position (azimuth measured clockwise from north/+Y)."""
    el = math.radians(max(elevation_deg, 0.5))  # keep just above horizon
    az = math.radians(azimuth_deg)
    # Sun light points along its local -Z. Tilt from straight-down (0,0,0
    # shines -Z) by (90 - elevation) about X, then yaw about Z.
    return (math.radians(90.0) - el, 0.0, -az)


def waypoint_coords_in_bounds() -> list:
    """Return [(slug, lat, lon, ok)] bound-check for every story location."""
    res = []
    for slug, (lat, lon) in LOC.items():
        ok = (SOUTH < lat < NORTH) and (WEST < lon < EAST)
        res.append((slug, lat, lon, ok))
    return res


# ======================================================== Blender-side code

def get_obj(name):
    obj = bpy.data.objects.get(name)
    if not obj:
        raise RuntimeError(f"Required object not found: {name}")
    return obj


def clear_animation(obj):
    if obj.animation_data:
        obj.animation_data_clear()


def remove_constraint(obj, ctype):
    for c in list(obj.constraints):
        if c.type == ctype:
            obj.constraints.remove(c)


def ensure_track_to(camera, target):
    for c in camera.constraints:
        if c.type == "TRACK_TO":
            c.target = target
            c.track_axis = "TRACK_NEGATIVE_Z"
            c.up_axis = "UP_Y"
            return c
    c = camera.constraints.new("TRACK_TO")
    c.target = target
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    return c


def key_pose(camera, target, frame, cam_loc, tgt_loc, lens=None):
    camera.location = Vector(cam_loc)
    target.location = Vector(tgt_loc)
    camera.keyframe_insert(data_path="location", frame=frame)
    target.keyframe_insert(data_path="location", frame=frame)
    if lens is not None:
        camera.data.lens = lens
        camera.data.keyframe_insert(data_path="lens", frame=frame)


def smooth_action(obj):
    ad = getattr(obj, "animation_data", None)
    if not ad or not ad.action:
        return
    for fc in ad.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = "AUTO_CLAMPED"
            kp.handle_right_type = "AUTO_CLAMPED"
        fc.update()


# ---- high-res texture swap -------------------------------------------------

def swap_terrain_texture():
    """Point the terrain material at the z17 mosaic, after validating that the
    sidecar geo-bounds equal the scene's UV geo frame."""
    if not MOSAIC_PNG.exists():
        print(f"WARN: {MOSAIC_PNG.name} not found — keeping existing texture. "
              f"Run build_highres_trench_mosaic.py first.")
        return False
    if MOSAIC_SIDECAR.exists():
        sc = json.loads(MOSAIC_SIDECAR.read_text(encoding="utf-8"))
        b = sc["bounds"]
        for key, ref in (("west", WEST), ("east", EAST),
                         ("south", SOUTH), ("north", NORTH)):
            if abs(b[key] - ref) > 1e-4:
                raise RuntimeError(
                    f"Mosaic sidecar bound {key}={b[key]} != scene {ref}; "
                    f"UVs would be misaligned. Rebuild the mosaic.")
        print(f"Sidecar OK: {sc['width']}x{sc['height']} px, "
              f"~{sc.get('approx_m_per_px', '?')} m/px, bounds match scene UVs.")
    else:
        print("WARN: mosaic sidecar missing — applying texture unverified.")

    img = bpy.data.images.get(MOSAIC_PNG.name) or bpy.data.images.load(str(MOSAIC_PNG))
    swapped = 0
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image and \
                    node.image.name.startswith(("trench_mosaic", MOSAIC_PNG.stem)):
                node.image = img
                node.interpolation = "Cubic"   # crisper minification of fine linework
                swapped += 1
    if swapped == 0:
        # Fall back: assign on the terrain material's first image node.
        mat = bpy.data.materials.get("TrenchMapMaterial")
        if mat and mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == "TEX_IMAGE":
                    node.image = img
                    node.interpolation = "Cubic"
                    swapped += 1
                    break
    print(f"Terrain texture swapped on {swapped} node(s) -> {MOSAIC_PNG.name}")
    return swapped > 0


# ---- route tube -------------------------------------------------------------

def build_route_object(route_pts):
    """(Re)build the ground-hugging route polyline as a thin emissive tube."""
    old = bpy.data.objects.get("RouteLineV2")
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    curve = bpy.data.curves.get("RouteLineV2")
    if curve:
        bpy.data.curves.remove(curve)

    curve = bpy.data.curves.new("RouteLineV2", type="CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = 0.022
    curve.bevel_resolution = 4
    spline = curve.splines.new("POLY")
    spline.points.add(len(route_pts) - 1)
    for i, (x, y, z) in enumerate(route_pts):
        spline.points[i].co = (x, y, z + 0.06, 1.0)  # ride just above the relief

    mat = bpy.data.materials.get("RouteMat")
    if mat is None:
        mat = bpy.data.materials.new("RouteMat")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.9, 0.8, 0.2, 1.0)
            bsdf.inputs["Emission Color"].default_value = (0.9, 0.8, 0.2, 1.0)
            bsdf.inputs["Emission Strength"].default_value = 1.5
    obj = bpy.data.objects.new("RouteLineV2", curve)
    obj.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(obj)

    legacy = bpy.data.objects.get("RouteLine")
    if legacy:
        legacy.hide_render = True
        legacy.hide_viewport = True
    print(f"RouteLineV2 rebuilt with {len(route_pts)} ground-hugging samples")
    return obj


# ---- info card ---------------------------------------------------------------

def ensure_info_card(camera):
    root = bpy.data.objects.get("InfoCardRoot")
    if root:
        return root
    bpy.ops.object.empty_add(type="PLAIN_AXES")
    root = bpy.context.active_object
    root.name = "InfoCardRoot"
    root.parent = camera
    root.location = (0.0, -0.85, -0.42)

    bpy.ops.mesh.primitive_plane_add(size=0.45)
    bg = bpy.context.active_object
    bg.name = "InfoCardBG"
    bg.parent = root
    bg.scale = (1.75, 0.62, 1.0)
    mat = bpy.data.materials.get("InfoCardBGMat") or bpy.data.materials.new("InfoCardBGMat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.04, 0.04, 0.04, 1.0)
        bsdf.inputs["Alpha"].default_value = 0.0
    mat.blend_method = "BLEND"
    if not bg.data.materials:
        bg.data.materials.append(mat)
    else:
        bg.data.materials[0] = mat

    for name, size, loc in (("InfoCardTitle", 0.10, (0.0, 0.115, 0.01)),
                            ("InfoCardSubtitle", 0.06, (0.0, 0.030, 0.01)),
                            ("InfoCardMeta", 0.042, (0.0, -0.075, 0.01))):
        bpy.ops.object.text_add()
        txt = bpy.context.active_object
        txt.name = name
        txt.parent = root
        txt.location = loc
        txt.rotation_euler = (math.radians(90), 0.0, 0.0)
        txt.data.align_x = "CENTER"
        txt.data.align_y = "CENTER"
        txt.data.size = size
    return root


def card_objs():
    return {k: get_obj(n) for k, n in (("bg", "InfoCardBG"),
                                       ("title", "InfoCardTitle"),
                                       ("subtitle", "InfoCardSubtitle"),
                                       ("meta", "InfoCardMeta"))}


def set_card_alpha(bg, frame, alpha):
    mat = bg.data.materials[0]
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if not bsdf:
        return
    bsdf.inputs["Alpha"].default_value = alpha
    bsdf.inputs["Alpha"].keyframe_insert(data_path="default_value", frame=frame)


def show_card(frame_in, frame_out, wp, fade=10):
    """Card text + fade window. frame_in..frame_out is full visibility."""
    card = card_objs()
    card["title"].data.body = wp["title"]
    card["subtitle"].data.body = wp["subtitle"]
    body = wp["card_body"]
    if len(body) > 110:  # wrap long copy onto two lines
        cut = body.rfind(" ", 0, len(body) // 2 + 20)
        body = body[:cut] + "\n" + body[cut + 1:]
    card["meta"].data.body = f"{body}\nSource: {wp['citation']}"

    set_card_alpha(card["bg"], frame_in - fade, 0.0)
    set_card_alpha(card["bg"], frame_in, 0.85)
    set_card_alpha(card["bg"], frame_out, 0.85)
    set_card_alpha(card["bg"], frame_out + fade, 0.0)
    for key in ("title", "subtitle", "meta"):
        obj = card[key]
        obj.hide_render = True
        obj.keyframe_insert(data_path="hide_render", frame=frame_in - fade)
        obj.hide_render = False
        obj.keyframe_insert(data_path="hide_render", frame=frame_in - fade + 1)
        obj.keyframe_insert(data_path="hide_render", frame=frame_out + fade - 1)
        obj.hide_render = True
        obj.keyframe_insert(data_path="hide_render", frame=frame_out + fade)


# ---- lighting ------------------------------------------------------------------

def ensure_sun():
    sun = bpy.data.objects.get("Sun")
    if sun is None or sun.type != "LIGHT":
        light = bpy.data.lights.new("Sun", type="SUN")
        sun = bpy.data.objects.new("Sun", light)
        bpy.context.scene.collection.objects.link(sun)
    clear_animation(sun)
    clear_animation(sun.data)
    sun.data.angle = math.radians(1.2)  # slightly soft shadows
    fill = bpy.data.objects.get("FillLight")
    if fill:  # the animated sun owns the look now; keep fill very low
        fill.data.energy = 0.25
    return sun


def key_sun(sun, frame, state_name):
    el, az, energy, color = SUN_STATES[state_name]
    sun.rotation_euler = sun_rotation(el, az)
    sun.keyframe_insert(data_path="rotation_euler", frame=frame)
    sun.data.energy = energy
    sun.data.color = color
    sun.data.keyframe_insert(data_path="energy", frame=frame)
    sun.data.keyframe_insert(data_path="color", frame=frame)

    world = bpy.context.scene.world
    if world and world.use_nodes:
        bg = world.node_tree.nodes.get("Background")
        if bg:
            wc, ws = WORLD_STATES[state_name]
            bg.inputs["Color"].default_value = (*wc, 1.0)
            bg.inputs["Strength"].default_value = ws
            bg.inputs["Color"].keyframe_insert(data_path="default_value", frame=frame)
            bg.inputs["Strength"].keyframe_insert(data_path="default_value", frame=frame)


def setup_mist():
    if not ENABLE_MIST:
        return
    scene = bpy.context.scene
    try:  # EEVEE Next volumetrics, kept cheap
        scene.eevee.volumetric_tile_size = "16"
        scene.eevee.volumetric_samples = 32
        scene.eevee.volumetric_end = 80.0
    except AttributeError:
        pass
    if bpy.data.objects.get("MistVolume"):
        return
    bpy.ops.mesh.primitive_cube_add()
    cube = bpy.context.active_object
    cube.name = "MistVolume"
    cube.location = (TERRAIN_X / 2, TERRAIN_Y / 2, 0.55)
    cube.scale = (TERRAIN_X / 2 + 2, TERRAIN_Y / 2 + 2, 0.6)
    cube.hide_select = True
    cube.display_type = "WIRE"
    mat = bpy.data.materials.new("MistMat")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = MIST_DENSITY
    vol.inputs["Anisotropy"].default_value = 0.35
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])
    cube.data.materials.append(mat)
    print(f"MistVolume added (density {MIST_DENSITY})")


# ---- camera choreography ---------------------------------------------------------

def travel_along_route(camera, target, route_pts, frame, frames, idx_from, idx_to,
                       height=1.6, lateral=(-1.0, -0.8)):
    """Glide the camera above the ground-hugging route from sample idx_from to
    idx_to, target leading a few samples ahead on the ground."""
    if frames <= 0 or idx_to == idx_from:
        return frame
    steps = max(4, frames // 10)
    n = len(route_pts)
    for s in range(steps + 1):
        t = smoothstep(s / steps)
        fi = idx_from + (idx_to - idx_from) * t
        i = max(0, min(n - 1, int(fi)))
        px, py, pz = route_pts[i]
        lead = max(0, min(n - 1, i + (3 if idx_to > idx_from else -3)))
        tx, ty, tz = route_pts[lead]
        f = frame + round(frames * (s / steps))
        key_pose(camera, target,
                 f,
                 (px + lateral[0], py + lateral[1], pz + height),
                 (tx, ty, tz + 0.18),
                 TRAVEL_LENS)
    return frame + frames


def card_zoom_beat(camera, target, frame, wp, poi, look_at):
    """The signature v2 move: zoom OUT (rise + widen) while the card fades in,
    hold for reading, then zoom back IN to the surface. Returns end frame."""
    t = wp["timing"]
    stop_cam = (poi[0] + wp["stop_offset"][0],
                poi[1] + wp["stop_offset"][1],
                poi[2] + wp["stop_offset"][2])
    wide_cam = (stop_cam[0] - 0.6, stop_cam[1] - 0.8, stop_cam[2] + wp["card_rise"])

    # settle on the surface
    key_pose(camera, target, frame, stop_cam, look_at, wp["lens_stop"])
    frame += t["settle"]
    key_pose(camera, target, frame, stop_cam, look_at, wp["lens_stop"])

    # zoom OUT with card fade-in
    card_in = frame + t["zoom_out"]
    key_pose(camera, target, card_in, wide_cam, look_at, wp["lens_wide"])
    hold_end = card_in + t["hold"]
    key_pose(camera, target, hold_end, wide_cam, look_at, wp["lens_wide"])
    show_card(card_in, hold_end, wp)

    # zoom back IN, card gone
    frame = hold_end + t["zoom_in"]
    key_pose(camera, target, frame, stop_cam, look_at, wp["lens_stop"])
    return frame


def orbit_beat(camera, target, frame, wp, poi, look_at, start_angle_deg=-135):
    frames = wp["timing"].get("orbit", 0)
    deg = wp.get("orbit_degrees", 0)
    if frames <= 0 or deg <= 0:
        return frame
    samples = max(6, frames // 5)
    for s in range(samples + 1):
        t = smoothstep(s / samples)
        ang = math.radians(start_angle_deg + deg * t)
        cam = (poi[0] + math.cos(ang) * wp["orbit_radius"],
               poi[1] + math.sin(ang) * wp["orbit_radius"],
               poi[2] + wp["orbit_height"])
        key_pose(camera, target, frame + round(frames * (s / samples)),
                 cam, look_at, wp["lens_stop"])
    return frame + frames


def merged(spec):
    wp = dict(DEFAULTS)
    wp["timing"] = dict(DEFAULTS["timing"])
    for k, v in spec.items():
        if k == "timing":
            wp["timing"].update(v)
        else:
            wp[k] = v
    return wp


def nearest_route_index(route_pts, point):
    best, best_d = 0, float("inf")
    for i, (x, y, z) in enumerate(route_pts):
        d = (x - point[0]) ** 2 + (y - point[1]) ** 2
        if d < best_d:
            best, best_d = i, d
    return best


def build():
    scene = bpy.context.scene
    scene.render.fps = FPS

    camera = get_obj("FlythroughCam")
    target = get_obj("CameraTarget")
    for obj in (camera, target):
        clear_animation(obj)
        remove_constraint(obj, "FOLLOW_PATH")
    clear_animation(camera.data)
    ensure_track_to(camera, target)
    ensure_info_card(camera)
    setup_mist()
    sun = ensure_sun()
    swap_terrain_texture()

    elev = load_elevations()
    route_pts = resample_route(elev, ROUTE_LATLON, samples_per_leg=24)
    build_route_object(route_pts)

    frame = 1
    prev_idx = 0
    sun_prev = WAYPOINTS[0].get("sun", "predawn")
    key_sun(sun, 1, sun_prev)

    for spec in WAYPOINTS:
        wp = merged(spec)
        t = wp["timing"]

        if wp["kind"] == "tracking":
            a = geo_to_blender(elev, *LOC[wp["track_from"]])
            b = geo_to_blender(elev, *LOC[wp["track_to"]])
            ia, ib = nearest_route_index(route_pts, a), nearest_route_index(route_pts, b)
            # approach: drop to the start of the segment
            frame = travel_along_route(camera, target, route_pts, frame,
                                       t["travel"], prev_idx, ia)
            # sun eases to this beat's state across the approach
            key_sun(sun, frame, wp.get("sun", sun_prev))
            sun_prev = wp.get("sun", sun_prev)
            # the slow, low tracking shot with the card up for its middle 70%
            track_frames = t.get("track", 240)
            frame_end = travel_along_route(
                camera, target, route_pts, frame, track_frames, ia, ib,
                height=wp["track_height"], lateral=wp["track_lateral"])
            show_card(frame + int(track_frames * 0.15),
                      frame + int(track_frames * 0.85), wp)
            frame = frame_end
            prev_idx = ib

        elif wp["kind"] == "finale":
            poi = geo_to_blender(elev, *LOC[wp["loc"]])
            gaze = geo_to_blender(elev, *LOC[wp["gaze"]])
            ip = nearest_route_index(route_pts, poi)
            frame = travel_along_route(camera, target, route_pts, frame,
                                       t["travel"], prev_idx, ip)
            key_sun(sun, frame, wp.get("sun", sun_prev))
            start_cam = (poi[0] - 1.2, poi[1] - 1.0, poi[2] + 1.2)
            look_mid = ((poi[0] + gaze[0]) / 2, (poi[1] + gaze[1]) / 2,
                        (poi[2] + gaze[2]) / 2 + 0.2)
            key_pose(camera, target, frame, start_cam, look_mid, wp["lens_stop"])
            # continuous pull-back + rise + widen over the whole sector
            end_cam = (poi[0] - wp["finale_back"], poi[1] - wp["finale_back"] * 0.8,
                       poi[2] + wp["finale_rise"])
            frame_out = frame + t["zoom_out"]
            key_pose(camera, target, frame_out, end_cam, look_mid, wp["lens_wide"])
            show_card(frame + t["zoom_out"] // 3, frame_out + t["hold"] - 12, wp)
            frame = frame_out + t["hold"]
            key_pose(camera, target, frame, end_cam, look_mid, wp["lens_wide"])

        else:  # "stop"
            poi = geo_to_blender(elev, *LOC[wp["loc"]])
            look_at = (poi[0], poi[1], poi[2] + wp["look_height"])
            ip = nearest_route_index(route_pts, poi)
            frame = travel_along_route(camera, target, route_pts, frame,
                                       t["travel"], prev_idx, ip)
            key_sun(sun, frame, wp.get("sun", sun_prev))
            sun_prev = wp.get("sun", sun_prev)
            frame = card_zoom_beat(camera, target, frame, wp, poi, look_at)
            frame = orbit_beat(camera, target, frame, wp, poi, look_at)
            prev_idx = ip

        frame += wp["timing"]["exit"]

    scene.frame_start = 1
    scene.frame_end = frame + 18
    scene.camera = camera

    smooth_action(camera)
    smooth_action(target)
    smooth_action(camera.data)
    smooth_action(sun)
    smooth_action(sun.data)

    dur = scene.frame_end / FPS
    print(f"Epic flythrough v2 built: frames 1-{scene.frame_end} "
          f"({dur:.1f}s at {FPS}fps), {len(WAYPOINTS)} story beats")


# ======================================================== selftest (no bpy)

def selftest() -> int:
    failures = 0

    def check(name, cond, detail=""):
        nonlocal failures
        status = "ok" if cond else "FAIL"
        if not cond:
            failures += 1
        print(f"  [{status}] {name} {detail}")

    print("selftest: easing")
    check("smoothstep(0)=0", smoothstep(0.0) == 0.0)
    check("smoothstep(1)=1", smoothstep(1.0) == 1.0)
    check("smoothstep(0.5)=0.5", abs(smoothstep(0.5) - 0.5) < 1e-9)
    check("smoothstep clamps", smoothstep(-3) == 0.0 and smoothstep(9) == 1.0)
    mid_slope = (smoothstep(0.51) - smoothstep(0.49)) / 0.02
    edge_slope = (smoothstep(0.02) - smoothstep(0.0)) / 0.02
    check("ease slow-in", edge_slope < mid_slope, f"({edge_slope:.3f} < {mid_slope:.3f})")

    print("selftest: geo frame")
    for slug, lat, lon, ok in waypoint_coords_in_bounds():
        check(f"{slug} inside terrain/mosaic bounds", ok, f"({lat}, {lon})")
    if MOSAIC_SIDECAR.exists():
        sc = json.loads(MOSAIC_SIDECAR.read_text(encoding="utf-8"))
        b = sc["bounds"]
        same = all(abs(b[k] - v) < 1e-4 for k, v in
                   (("west", WEST), ("east", EAST), ("south", SOUTH), ("north", NORTH)))
        check("mosaic sidecar bounds == scene UV bounds", same, str(b))
    else:
        print("  [skip] mosaic sidecar not present yet")

    print("selftest: terrain sampling")
    if ELEVATIONS_JSON.exists():
        elev = load_elevations()
        e = sample_elevation(elev, 49.99, 2.80)
        check("elevation in DEM range", MIN_ELEV - 1 <= e <= MAX_ELEV + 1, f"({e:.1f} m)")
        x, y, z = geo_to_blender(elev, SOUTH + 1e-6, WEST + 1e-6)
        check("SW corner -> origin-ish", x < 0.01 and y < 0.01, f"({x:.4f},{y:.4f})")
        x, y, z = geo_to_blender(elev, NORTH - 1e-6, EAST - 1e-6)
        check("NE corner -> (30,11)-ish",
              abs(x - TERRAIN_X) < 0.01 and abs(y - TERRAIN_Y) < 0.01,
              f"({x:.3f},{y:.3f})")
        pts = resample_route(elev, ROUTE_LATLON, 24)
        check("route densified", len(pts) == 24 * (len(ROUTE_LATLON) - 1) + 1,
              f"({len(pts)} pts)")
        check("route z hugs ground", all(0.0 <= p[2] <= 1.6 for p in pts))
    else:
        print("  [skip] somme_elevations.json not present here")

    print("selftest: sun")
    rx, ry, rz = sun_rotation(90.0, 0.0)
    check("sun overhead -> no tilt", abs(rx) < 1e-6)
    rx, _, _ = sun_rotation(0.0, 90.0)
    check("sun at horizon -> ~90deg tilt", abs(rx - math.radians(89.5)) < 1e-6)
    for name in {w.get("sun") for w in WAYPOINTS if w.get("sun")}:
        check(f"sun state '{name}' defined", name in SUN_STATES and name in WORLD_STATES)

    print(f"selftest: {'PASS' if failures == 0 else f'{failures} FAILURE(S)'}")
    return failures


if __name__ == "__main__":
    if "--selftest" in sys.argv or not IN_BLENDER:
        raise SystemExit(selftest())
    build()
