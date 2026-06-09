# Flythrough v2 — Epic Catalogue of 1 July 1916

Upgrades the Somme flythrough into a six-beat film of Lt-Col. Bryan Fairfax's
documented route (17th Bn King's Liverpool, 89th Brigade, 30th Division):
pre-dawn Maricourt HQ → 6:25 a.m. bombardment → 7:30 a.m. zero hour and the
arm-in-arm advance with Commandant Lepetit (153e RI) → the Briqueterie →
Glatz Redoubt-area consolidation → pull-back finale over the day's gains.
Card copy quotes the 89th Brigade history with page citations; every claim
traces to `research/ground-truth-ledger.md` (entries #12–#15).

## What changed vs v1 (`build_cinematic_flythrough.py`, untouched)

1. **High-res map.** `build_highres_trench_mosaic.py` downloads NLS trench-map
   tiles at z17 (the tileset's maximum) and stitches
   `somme_trench_mosaic_z17.png` — **10,253 × 5,799 px (~0.77 m/px)** vs the
   old `trench_mosaic.png` at 1,536 × 768 (z14). Tiles are cached in
   `nls_tile_cache/` (reruns are free, max 4 concurrent requests). The
   sidecar `somme_trench_mosaic_z17_geo.json` records exact geo-bounds; they
   equal the terrain-mesh UV bounds, so the texture drops onto the existing
   `UVMap` with no offset. v2 swaps it in automatically and validates the
   sidecar before doing so.
2. **Card zoom choreography.** At each beat the camera zooms OUT (altitude up,
   lens 45 mm → 24 mm) while the info card fades in, holds for reading, then
   zooms back to the map surface and resumes the route. All keys are
   BEZIER/AUTO_CLAMPED.
3. **Ground-hugging route.** The route polyline (`RouteLineV2`) and camera
   target are sampled onto the terrain via bilinear interpolation of
   `somme_elevations.json`.
4. **Animated dawn.** A single Sun is keyed across the film: blue-grey
   pre-dawn → low warm light at zero hour (1 July 1916 dawned clear) →
   harsher mid-morning sun by the Briqueterie beat. World background follows.
   Optional cheap EEVEE-Next mist (`ENABLE_MIST` in the script).
5. **Zero-hour centrepiece.** A slow, low tracking shot across no man's land
   at the Anglo-French boundary seam (ledger #14).

## How to run (the one command)

Blender on Windows, from `C:\Users\chris\Churchill\terrain_data`:

```powershell
cd C:\Users\chris\Churchill\terrain_data
blender -b somme_battlefield.blend --python build_cinematic_flythrough_v2.py --python render_flythrough.py
```

Output: `fairfax_flythrough.mp4` (then `python3 encode_flythrough.py` for a GIF).

## Preflight checklist

- [ ] `somme_trench_mosaic_z17.png` + `_geo.json` exist (else run
      `python build_highres_trench_mosaic.py` — resumes from `nls_tile_cache/`)
- [ ] `somme_elevations.json` present (required for ground-hugging route)
- [ ] `.blend` contains `FlythroughCam`, `CameraTarget`, `SommeTerrain`,
      material `TrenchMapMaterial` (v2 finds the image node and swaps it)
- [ ] sanity check without Blender: `python build_cinematic_flythrough_v2.py --selftest`
      (easing, geo-bounds, route sampling, sun states — all must PASS)
- [ ] expect ~1,700+ frames (~60–90 s at 30 fps); EEVEE Next renders straight
      to MP4 per `render_flythrough.py`

## Editing the film

Everything is data-driven in `build_cinematic_flythrough_v2.py`:
- `WAYPOINTS` — beats, card copy, citations, timing, orbit/zoom amounts
- `LOC` / `ROUTE_LATLON` — lat/lon of the documented route (selftest verifies
  every point stays inside the mosaic geo-bounds)
- `SUN_STATES` / `WORLD_STATES` — the lighting timeline

## Note on live Blender control

The `blender_mcp_addon.py` socket (JSON over TCP, default `localhost:9876`)
binds to localhost on the Windows host and is not reachable from the Linux
sandbox, so v2 was validated via `--selftest` + `py_compile` instead of live
test-frame renders. With Blender open and the addon running, the same builds
can be driven live via `execute_code` (requires
`BLENDERMCP_ALLOW_UNSAFE_EXECUTE_CODE=1` and a token — see the addon header).

## Attribution

Trench-map imagery: National Library of Scotland tilesets `101465287`
(primary) and `101464777` (northern fill), z17, URL pattern
`https://mapseries-tilesets.s3.amazonaws.com/trench/{id}/{z}/{x}/{y}.png`.
A visible sheet seam crosses the northern third of the mosaic where the two
sheets meet; both are period sheets of the same series.
