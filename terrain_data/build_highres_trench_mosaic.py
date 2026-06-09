#!/usr/bin/env python3
"""Build a maximum-resolution NLS trench-map mosaic for the Somme terrain texture.

Replaces the legacy ``trench_mosaic.png`` (1536x768, stitched from z14 tiles)
with a z17 (max zoom exposed by the NLS tileset) mosaic covering the exact
geographic bounds of the Blender terrain mesh, so the existing 0..1 UV layout
on ``SommeTerrain`` maps onto it with no realignment.

Sources (National Library of Scotland WWI trench-map tilesets, web mercator):
  - primary  : sheet 101465287 (Maricourt / Montauban / Briqueterie sector)
  - secondary: sheet 101464777 (adjacent northern sheet; fills any tiles the
               primary sheet is missing along its northern edge)

Pipeline:
  1. Derive the texture bounding box from ``somme_dem_meta.json`` (cell-centre
     bounds, i.e. the same SOUTH/NORTH/WEST/EAST used by rebuild_full_scene.py).
  2. Fetch all z17 tiles covering the box, max 4 concurrent requests, retry
     with exponential backoff, permanent cache in ``nls_tile_cache/`` (404s are
     cached as ``.missing`` markers so reruns make zero network calls).
  3. Stitch tiles into a web-mercator mosaic, flattening alpha onto paper
     white, preferring the primary sheet and falling back to the secondary.
  4. Resample rows from mercator to an equirectangular (linear-in-latitude)
     grid so that v in [0,1] maps linearly to latitude exactly like the
     terrain UVs. (At this latitude span the correction is < 1 px, but doing
     it makes the sidecar bounds exact rather than approximate.)
  5. Write the full PNG + JPEG + a geo sidecar JSON + a legibility crop.

Outputs (all in terrain_data/):
  - somme_trench_mosaic_z17.png        full-res terrain texture (lossless)
  - somme_trench_mosaic_z17.jpg        q92 JPEG convenience copy
  - somme_trench_mosaic_z17_geo.json   exact geo-bounds / UV mapping sidecar
  - somme_trench_mosaic_z17_crop_briqueterie.png  1:1 crop for legibility QA

Attribution: map imagery (c) National Library of Scotland trench-map
collection; retain the tile URL pattern + metadata URL in documentation.
"""
from __future__ import annotations

import json
import math
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

HERE = Path(__file__).resolve().parent

PRIMARY_SOURCE = "101465287"
SECONDARY_SOURCE = "101464777"
SOURCES = [PRIMARY_SOURCE, SECONDARY_SOURCE]
ZOOM = 17                      # maxzoom advertised by both sheets' metadata.json
TILE_SIZE = 256
BASE_URL = "https://mapseries-tilesets.s3.amazonaws.com/trench/{src}/{z}/{x}/{y}.png"
USER_AGENT = "Churchill-archive-highres-mosaic/1.0 (historical research)"
MAX_WORKERS = 4                # be polite to the NLS/S3 endpoint
TIMEOUT_S = 30
RETRIES = 4

CACHE_DIR = HERE / "nls_tile_cache"
DEM_META = HERE / "somme_dem_meta.json"

OUT_PNG = HERE / "somme_trench_mosaic_z17.png"
OUT_JPG = HERE / "somme_trench_mosaic_z17.jpg"
OUT_SIDECAR = HERE / "somme_trench_mosaic_z17_geo.json"
OUT_CROP = HERE / "somme_trench_mosaic_z17_crop_briqueterie.png"

PAPER_WHITE = (244, 240, 229)  # flatten alpha onto aged-paper tone

# QA crop centre: Montauban/Briqueterie label area (1 July objective).
CROP_CENTER = (50.0040, 2.7960)  # lat, lon
CROP_SIZE = (1800, 1200)         # px at native z17 resolution

_print_lock = threading.Lock()


def log(msg: str) -> None:
    with _print_lock:
        print(msg, flush=True)


# Texture bounds = the SOUTH/NORTH/WEST/EAST constants of rebuild_full_scene.py
# (cell-centre bounds of the 144x396 DEM grid in somme_dem_meta.json, i.e.
# meta bounds shifted by half a 0.0002777778-degree pixel). The terrain mesh
# UVs span exactly this box, so a texture cropped to it drops straight in.
REBUILD_BOUNDS = {"west": 2.749861, "east": 2.859861,
                  "south": 49.970139, "north": 50.010139}


def verify_bounds_against_dem_meta(bounds: dict) -> None:
    """Sanity-check the hard-coded bounds against somme_dem_meta.json."""
    meta = json.loads(DEM_META.read_text(encoding="utf-8"))
    half = meta["pixel_size_deg"] / 2.0
    for key, ref in (("west", meta["west"]), ("south", meta["south"]),
                     ("east", meta["east"]), ("north", meta["north"])):
        if abs(bounds[key] - ref) > half + 1e-6:
            raise RuntimeError(
                f"Texture bound {key}={bounds[key]} deviates from DEM meta "
                f"{ref} by more than half a pixel; check georeferencing.")


def lonlat_to_tile_float(lon: float, lat: float, z: int) -> tuple[float, float]:
    lat_rad = math.radians(lat)
    n = 2 ** z
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return x, y


def mercator_y_float(lat: float, z: int) -> float:
    return lonlat_to_tile_float(0.0, lat, z)[1]


def cache_path(src: str, x: int, y: int) -> Path:
    return CACHE_DIR / src / str(ZOOM) / str(x) / f"{y}.png"


DEADLINE: float | None = None  # time.monotonic() cutoff for new downloads


def fetch_tile(src: str, x: int, y: int) -> Path | None:
    """Return path to cached tile PNG, or None if the tile does not exist."""
    dest = cache_path(src, x, y)
    missing_marker = dest.with_suffix(".missing")
    if dest.exists() and dest.stat().st_size > 100:
        return dest
    if missing_marker.exists():
        return None
    if DEADLINE is not None and time.monotonic() > DEADLINE:
        return None  # budget exhausted: defer (no marker -> retried next run)
    url = BASE_URL.format(src=src, z=ZOOM, x=x, y=y)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
                data = r.read()
            with Image.open(BytesIO(data)) as im:
                im.verify()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return dest
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                missing_marker.parent.mkdir(parents=True, exist_ok=True)
                missing_marker.write_text("404", encoding="utf-8")
                return None
            log(f"WARN {src} {x},{y}: HTTP {e.code} (attempt {attempt + 1})")
        except Exception as e:  # noqa: BLE001 - network robustness
            log(f"WARN {src} {x},{y}: {e} (attempt {attempt + 1})")
        time.sleep(0.6 * (2 ** attempt))
    return None


def resolve_cached(tiles: list[tuple[int, int]]) -> dict[tuple[int, int], str]:
    """Resolve tiles already on disk (no network). Primary sheet wins."""
    found: dict[tuple[int, int], str] = {}
    for src in SOURCES:
        for xy in tiles:
            if xy in found:
                continue
            p = cache_path(src, *xy)
            if p.exists() and p.stat().st_size > 100:
                found[xy] = src
    return found


def fetch_all(tiles: list[tuple[int, int]],
              deadline: float | None = None) -> dict[tuple[int, int], str]:
    """Fetch every tile from primary, fall back to secondary. Returns
    {(x, y): source_id} for tiles found; missing tiles are simply absent.
    If ``deadline`` (time.monotonic value) is given, stop submitting new
    downloads once it passes — already-cached tiles still resolve."""
    global DEADLINE
    DEADLINE = deadline
    found = resolve_cached(tiles)
    for src in SOURCES:
        todo = [t for t in tiles if t not in found
                and not cache_path(src, *t).with_suffix(".missing").exists()]
        if not todo:
            continue
        log(f"Fetching up to {len(todo)} tiles from sheet {src} (z{ZOOM}, "
            f"{MAX_WORKERS} workers)...")
        done = 0
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(fetch_tile, src, x, y): (x, y) for x, y in todo}
            for fut in as_completed(futures):
                xy = futures[fut]
                if fut.result() is not None:
                    found[xy] = src
                done += 1
                if done % 100 == 0:
                    log(f"  {src}: {done}/{len(todo)} checked, "
                        f"{len(found)} total present")
        log(f"  sheet {src}: cumulative tiles present = {len(found)}")
    DEADLINE = None
    return found


def unresolved_tiles(tiles: list[tuple[int, int]],
                     found: dict[tuple[int, int], str]) -> int:
    """Tiles neither fetched nor confirmed missing on every sheet."""
    n = 0
    for xy in tiles:
        if xy in found:
            continue
        if all(cache_path(s, *xy).with_suffix(".missing").exists() for s in SOURCES):
            continue  # genuinely absent from both sheets
        n += 1
    return n


def build(budget_s: float | None = None, fetch_only: bool = False) -> None:
    bounds = REBUILD_BOUNDS
    verify_bounds_against_dem_meta(bounds)
    west, east = bounds["west"], bounds["east"]
    south, north = bounds["south"], bounds["north"]

    x0f, y0f = lonlat_to_tile_float(west, north, ZOOM)   # NW corner
    x1f, y1f = lonlat_to_tile_float(east, south, ZOOM)   # SE corner
    tx0, tx1 = math.floor(x0f), math.floor(x1f)
    ty0, ty1 = math.floor(y0f), math.floor(y1f)
    cols, rows = tx1 - tx0 + 1, ty1 - ty0 + 1
    tiles = [(x, y) for y in range(ty0, ty1 + 1) for x in range(tx0, tx1 + 1)]
    log(f"Bounds W{west} E{east} S{south} N{north}")
    log(f"Tile range x={tx0}..{tx1} y={ty0}..{ty1} -> {cols}x{rows} = {len(tiles)} tiles")

    deadline = time.monotonic() + budget_s if budget_s else None
    found = fetch_all(tiles, deadline=deadline)
    missing = len(tiles) - len(found)
    log(f"Tiles present: {len(found)}, missing: {missing}")

    pending = unresolved_tiles(tiles, found)
    if pending and (budget_s or fetch_only):
        log(f"INCOMPLETE: {pending} tiles still unresolved — rerun to resume "
            f"from cache (exit 3)")
        raise SystemExit(3)
    if fetch_only:
        log("Fetch complete (fetch-only mode); skipping stitch. DONE")
        return

    # ---- stitch into mercator canvas (flattened RGB on paper white) ----
    canvas_w, canvas_h = cols * TILE_SIZE, rows * TILE_SIZE
    canvas = np.empty((canvas_h, canvas_w, 3), dtype=np.uint8)
    canvas[:] = PAPER_WHITE
    paper = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), PAPER_WHITE + (255,))
    for (x, y), src in found.items():
        with Image.open(cache_path(src, x, y)) as tile:
            flat = Image.alpha_composite(paper, tile.convert("RGBA")).convert("RGB")
        px, py = (x - tx0) * TILE_SIZE, (y - ty0) * TILE_SIZE
        canvas[py:py + TILE_SIZE, px:px + TILE_SIZE] = np.asarray(flat)
    log(f"Stitched mercator canvas {canvas_w}x{canvas_h}")

    # ---- crop to exact bbox in mercator pixel space ----
    gpx0 = x0f * TILE_SIZE - tx0 * TILE_SIZE
    gpx1 = x1f * TILE_SIZE - tx0 * TILE_SIZE
    gpy0 = y0f * TILE_SIZE - ty0 * TILE_SIZE
    gpy1 = y1f * TILE_SIZE - ty0 * TILE_SIZE
    out_w = int(round(gpx1 - gpx0))
    out_h = int(round(gpy1 - gpy0))

    # ---- mercator -> equirectangular row resample (linear in latitude) ----
    # Output row i (top=north) corresponds to lat = north - (i+0.5)/out_h*(north-south).
    # Map that latitude back to a fractional mercator canvas row and gather
    # with linear interpolation between the two neighbouring rows.
    lats = north - (np.arange(out_h) + 0.5) / out_h * (north - south)
    n_tiles = 2 ** ZOOM
    merc_y = (1.0 - np.arcsinh(np.tan(np.radians(lats))) / math.pi) / 2.0 * n_tiles
    src_rows = merc_y * TILE_SIZE - ty0 * TILE_SIZE - 0.5
    r0 = np.clip(np.floor(src_rows).astype(np.int64), 0, canvas_h - 1)
    r1 = np.clip(r0 + 1, 0, canvas_h - 1)
    frac = (src_rows - r0).clip(0.0, 1.0)[:, None, None].astype(np.float32)

    x_lo = int(math.floor(gpx0))
    cols_slice = slice(x_lo, x_lo + out_w)
    upper = canvas[r0][:, cols_slice].astype(np.float32)
    lower = canvas[r1][:, cols_slice].astype(np.float32)
    equirect = (upper * (1.0 - frac) + lower * frac).round().astype(np.uint8)
    del canvas, upper, lower
    log(f"Equirectangular mosaic {equirect.shape[1]}x{equirect.shape[0]}")

    mosaic = Image.fromarray(equirect, "RGB")
    mosaic.save(OUT_PNG, optimize=False)
    mosaic.save(OUT_JPG, "JPEG", quality=92, optimize=True, progressive=True)
    log(f"Wrote {OUT_PNG.name} and {OUT_JPG.name}")

    # ---- QA legibility crop at native resolution ----
    clat, clon = CROP_CENTER
    cu = (clon - west) / (east - west)
    cv = (clat - south) / (north - south)
    ccx = int(cu * mosaic.width)
    ccy = int((1.0 - cv) * mosaic.height)
    cw, ch = CROP_SIZE
    left = max(0, min(mosaic.width - cw, ccx - cw // 2))
    top = max(0, min(mosaic.height - ch, ccy - ch // 2))
    mosaic.crop((left, top, left + cw, top + ch)).save(OUT_CROP)
    log(f"Wrote QA crop {OUT_CROP.name} centred on {CROP_CENTER}")

    # ---- geo sidecar ----
    deg_per_px_lon = (east - west) / mosaic.width
    deg_per_px_lat = (north - south) / mosaic.height
    m_per_px = deg_per_px_lon * 111320.0 * math.cos(math.radians((south + north) / 2))
    sidecar = {
        "image": OUT_PNG.name,
        "width": mosaic.width,
        "height": mosaic.height,
        "projection": "equirectangular (linear lon/lat), resampled from web-mercator z17 rows",
        "crs": "EPSG:4326",
        "bounds": {"west": west, "east": east, "south": south, "north": north},
        "row0_is_north": True,
        "uv_mapping": {
            "u": "(lon - west) / (east - west)",
            "v": "(lat - south) / (north - south)",
            "note": "Identical to the SommeTerrain UV layout from rebuild_full_scene.py; "
                    "apply the image directly to the existing UVMap with no offset.",
        },
        "deg_per_px": {"lon": deg_per_px_lon, "lat": deg_per_px_lat},
        "approx_m_per_px": round(m_per_px, 3),
        "zoom": ZOOM,
        "tile_size": TILE_SIZE,
        "tile_range": {"x0": tx0, "x1": tx1, "y0": ty0, "y1": ty1},
        "tiles_total": len(tiles),
        "tiles_present": len(found),
        "tiles_missing": missing,
        "tiles_by_source": {s: sum(1 for v in found.values() if v == s) for s in SOURCES},
        "sources": [
            {
                "source_id": s,
                "tile_url_pattern": BASE_URL.format(src=s, z="{z}", x="{x}", y="{y}"),
                "metadata_url": f"https://mapseries-tilesets.s3.amazonaws.com/trench/{s}/metadata.json",
            }
            for s in SOURCES
        ],
        "replaces": "trench_mosaic.png (1536x768, z14 tiles)",
        "rights_note": "National Library of Scotland trench-map imagery; archival/source "
                       "use with attribution. Keep this sidecar with the image.",
    }
    OUT_SIDECAR.write_text(json.dumps(sidecar, indent=2), encoding="utf-8")
    log(f"Wrote sidecar {OUT_SIDECAR.name}")
    log("DONE")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--budget", type=float, default=None, metavar="SECONDS",
                        help="stop starting new downloads after this many "
                             "seconds; exits 3 if tiles remain (rerun resumes "
                             "from nls_tile_cache/)")
    parser.add_argument("--fetch-only", action="store_true",
                        help="download/cache tiles but skip stitching")
    args = parser.parse_args()
    build(budget_s=args.budget, fetch_only=args.fetch_only)
# end of file
