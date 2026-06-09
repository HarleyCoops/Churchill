# Cinematic Flythrough Workflow

This upgrades the Somme flythrough from a single glide into a multi-stop camera sequence:
- travel to waypoint
- settle into framing
- show an info card
- orbit the point
- push in for detail
- travel to the next stop

## Files

- `build_cinematic_flythrough.py` — builds the animation inside the existing `.blend`
- `render_flythrough.py` — renders directly to MP4 by default
- `encode_flythrough.py` — turns the MP4 into a GIF, or can still build an MP4 from frames if needed

## Current scene assumptions

The `.blend` already contains:
- `FlythroughCam`
- `CameraTarget`
- pin objects such as `PinHead_A`, `PinHead_B`, etc.

The script currently stages these story beats:
- Brigade HQ
- Maricourt sector
- Briqueterie
- Trones Wood
- Guillemont approach
- Guillemont

## Run it in Blender

Open `terrain_data/somme_battlefield.blend` in Blender, then run:

1. `terrain_data/build_cinematic_flythrough.py`
2. save the blend
3. `terrain_data/render_flythrough.py`

Or from the command line with Blender installed:

### Windows example

```powershell
cd C:\Users\chris\Churchill\terrain_data
blender -b somme_battlefield.blend --python build_cinematic_flythrough.py --python render_flythrough.py
```

### Linux / WSL example

```bash
cd /mnt/c/Users/chris/Churchill/terrain_data
blender -b somme_battlefield.blend --python build_cinematic_flythrough.py --python render_flythrough.py
```

Then make the GIF:

```bash
python3 encode_flythrough.py
```

## Output behavior

Default behavior now:
- Blender renders straight to `fairfax_flythrough.mp4`
- no PNG-per-frame dump is needed for normal runs

Optional debug behavior:
- set `RENDER_IMAGE_SEQUENCE = True` in `render_flythrough.py` if you explicitly want PNG frames for troubleshooting or re-encoding

## Notes

- Blender does not need to be visibly open if you run it headless with `-b`.
- Google Earth is not part of this workflow.
- `render_flythrough.py` respects whatever `scene.frame_end` the cinematic builder created.
- The cinematic builder is data-driven: edit `WAYPOINTS` in `build_cinematic_flythrough.py` to change stops, pacing, text, orbit size, or zoom intensity.

## Next tuning targets

- increase total runtime from the current default if you want a slower, more stately film
- add more direct quotations into the info card text
- add a final ending beat on Chartwell or on the letter itself in post
- replace camera-parented cards with compositor or VSE overlays if you want cleaner typography
