# Map Flyover Pipeline

Turn any high-resolution scan of a historical map into a flyable, renderable
Blender artifact: a camera flies the map in story order, descending and
orbiting at each point of interest, under lighting that sweeps from warm
morning to amber evening across the flight.

First built for NWMP patrol file 344/90 (LAC e011863396) — Const. McMahon's
June 1890 watercolour route map, Calgary to Tail Creek and back.

## The method

1. **Extract the map at maximum resolution.** Close camera passes magnify the
   source, so 300–400 dpi is the difference between watercolour fibre and mush:

   ```bash
   pdftoppm -f 40 -l 40 -png -r 400 source.pdf map_hires
   ```

2. **Pick story waypoints.** Open the image, note pixel coordinates of each
   point of interest, convert to fractions: `u = x/width`, `v = 1 - y/height`.
   Order them as the narrative travels. Put a high-altitude `overview` stop at
   both ends so the flight opens and closes on the whole document. Write them
   to `stops.json`:

   ```json
   [
     {"name": "overview", "u": 0.50, "v": 0.50, "alt": 12.5},
     {"name": "calgary",  "u": 0.385,"v": 0.381,"alt": 2.2},
     {"name": "tailcreek","u": 0.800,"v": 0.727,"alt": 2.0}
   ]
   ```

   `alt` is closest-approach camera altitude; the map is normalized to
   10 units tall, so 1.5–3 is a close pass, 12+ frames the whole sheet.

3. **Build the scene headlessly:**

   ```bash
   blender --background --python map_flyover.py -- \
       --image map_hires-040.png --stops stops.json \
       --out flyover.blend --setup-render 1920x1080
   ```

4. **Fly it / render it.** Open the .blend and press Space (set the viewport
   to Material Preview or Rendered — Solid mode shows a blank plane), or:

   ```bash
   blender --background flyover.blend --render-anim
   ```

## Why it looks right

- **The map is a lit surface, not an emissive one.** A Principled BSDF with
  the scan as base color lets the animated sun rake across the paper, so the
  document reads as a physical object on a table, not a screenshot.
- **Camera grammar:** arrive high → descend while orbiting ~28° → climb out
  through ~55°. Approach bearings alternate per stop so consecutive moves
  never repeat. All keys are Bezier ease-in-out.
- **Lighting tells time.** Sun rotation/energy/color are keyframed
  morning → noon → evening over the full frame range, echoing the day-long
  patrols these maps record. A large dim area light keeps shadows from
  going muddy.
- **The texture is packed** (`bpy.ops.file.pack_all()`), so the .blend is a
  single self-contained artifact.

## Hard-won notes

- A multi-frame MP4 is unreadable until the render finishes — FFmpeg
  finalizes the container on the last frame. Not corruption; just wait.
- Never point two Blender processes at the same output file.
- Text overlays: parent FONT objects to the camera (z ≈ −2.2, |y| ≤ 0.40 for
  a 50 mm lens — further out is outside the frustum), fade with a
  Transparent/Emission Mix Shader keyframed on Fac, set the material's
  surface render method to Blended, **and connect the Mix Shader to the
  Material Output** — an unconnected output renders as opaque default
  material and will gaslight you for an hour.
- Frame budget: ~70 travel + ~110 hold frames per stop at 30 fps gives an
  unhurried documentary pace (12 stops ≈ 70 s).

## Files

- `map_flyover.py` — the pipeline (Blender 4.2+; EEVEE Next with fallback).
- `stops.example.json` — the NWMP McMahon patrol waypoints, as a template.
