# Cinematic multi-stop flythrough plan

Goal: replace the current single continuous glide with a reusable shot-based system that can pause at each waypoint, orbit, zoom, then travel to the next stop, while showing a title/info card for each location.

## Why the current approach is limited

The current scripts (`rebuild_full_scene.py`, `rebuild_cameras.py`, `fix_flythrough_v5.py`) animate either:
- one linear start/end glide, or
- a single camera path plus single target path with one offset factor from 0.0 to 1.0.

That structure is fine for a simple pass, but it is weak for cinematic beats because:
- pauses are awkward on a single follow-path offset animation
- orbits need camera motion around a local pivot, not just movement along a global spline
- zooms need focal length animation tied to the stop itself
- per-waypoint title cards need explicit timing windows
- changing route order or adding a new pin means rebuilding path logic by hand

## Recommended file strategy

Recommended new files:

1. `terrain_data/build_cinematic_flythrough.py`
   - new primary generator for the movie camera, timing, shots, and title-card hooks
   - should become the replacement for `fix_flythrough_v5.py`

2. `terrain_data/cinematic_flythrough_plan.md`
   - this design note

Recommended light-touch updates later:

3. `terrain_data/render_flythrough.py`
   - only update frame count/output naming once the new animation exists

4. Keep `terrain_data/rebuild_full_scene.py` focused on scene construction
   - terrain, pins, labels, collections, base cameras
   - do not bury the cinematic shot system inside the full scene rebuild unless you want every scene rebuild to also regenerate the movie timing

Best separation of concerns:
- `rebuild_full_scene.py`: build terrain and reference objects
- `build_cinematic_flythrough.py`: generate the animation from scene objects already in the blend file
- `render_flythrough.py`: render whatever the active cinematic script produced

## Core design recommendation

Do not drive the final cinematic camera from one global path curve.

Instead, use a shot-driven rig:
- `FlythroughCam`: actual render camera
- `CameraTarget`: empty the camera tracks to
- optional `CameraRigRoot`: parent empty for the camera during travel shots
- per-stop temporary or persistent orbit pivots created from waypoint positions

Animate explicit keyframes on:
- camera location
- target location
- camera lens
- optional camera parent / orbit pivot rotation
- title-card visibility or text content

This is more robust than a single `FOLLOW_PATH` constraint because pauses, local circles, and zoom-ins become natural keyframed beats rather than hacks in offset-factor timing.

## Shot model

Treat the movie as an ordered list of shot segments. Each waypoint can generate a bundle like:

1. travel_in
2. settle
3. hold_with_card
4. orbit
5. push_in_or_pull_back
6. exit / handoff to next waypoint

That means the movie is path-agnostic: the route is just data.

## Recommended waypoint data structure

Use a single declarative list of dictionaries or dataclasses.

Example:

```python
WAYPOINTS = [
    {
        "pin": "PinHead_A",
        "slug": "brigade_hq",
        "title": "Brigade HQ",
        "subtitle": "Pit southwest of Maricourt",
        "date": "June 1916",
        "citation": "89th Brigade, p.121",
        "card_body": "Brigade HQ before the July offensive.",
        "look_height": 0.30,
        "cam_height": 2.4,
        "travel_offset": (-2.8, -2.2, 2.2),
        "stop_offset": (-1.4, -1.1, 1.4),
        "orbit_radius": 1.7,
        "orbit_height": 1.3,
        "orbit_degrees": 120,
        "lens_hold": 42,
        "lens_detail": 58,
        "timing": {
            "travel": 42,
            "settle": 10,
            "card_in": 8,
            "hold": 28,
            "orbit": 36,
            "push": 20,
            "card_out": 8,
        },
    },
]
```

Notes:
- `pin` should reference existing scene objects like `PinHead_A`
- `travel_offset` is the default incoming camera offset from the point of interest
- `stop_offset` is the closer composition for the held beat
- `look_height` raises the target above terrain to avoid staring into the ground
- `lens_hold` and `lens_detail` allow a moderate zoom during the stop
- `timing` is per-stop and can be overridden for important waypoints

If you want stronger reuse, add global defaults and let each waypoint only override exceptions.

## Recommended scene-object lookup strategy

Never hard-code point coordinates if the scene already contains pins.

Preferred lookup order:
1. use `PinHead_<letter>` object location if it exists
2. otherwise use label or marker object fallback
3. otherwise fail loudly with a clear error

That makes the flythrough automatically adapt if pin placements change during terrain rebuilds.

## Animation strategy

### 1. Build a clean camera rig

At script start:
- find and clear animation data on `FlythroughCam` and `CameraTarget`
- ensure `FlythroughCam` has a `TRACK_TO` constraint aimed at `CameraTarget`
- optionally remove old helper empties from a `Cameras` child collection such as `CineRig_*`

### 2. Compute point-of-interest transforms from pins

For each waypoint:
- `poi = pin.location`
- `look_at = poi + Vector((0, 0, look_height))`
- `travel_cam = poi + Vector(travel_offset)`
- `stop_cam = poi + Vector(stop_offset)`

### 3. Animate in segments

For each waypoint, append frames in order:

Travel:
- camera moves from previous stop to this waypoint's `travel_cam`
- target moves toward current `look_at`
- interpolation: BEZIER with auto-clamped handles

Settle:
- camera eases from `travel_cam` to `stop_cam`
- lens eases from travel lens to `lens_hold`

Hold with card:
- camera and target remain fixed
- title card fades in and remains visible

Orbit:
- move camera around `look_at` on a circular arc while target stays on the same location
- easiest robust method: keyframe camera positions sampled along an arc rather than depending on a rotating parent with fragile parenting state

Push / zoom:
- either animate camera closer to target, lens longer, or both
- keep one of the two subtle; combining strong dolly + strong lens change can feel synthetic

Exit:
- hold final framing briefly, then next segment begins travel to next waypoint

### 4. Orbit implementation recommendation

Best practical choice for this repo: sampled orbit positions, not path constraints.

Pseudo-logic:

```python
for step in range(samples + 1):
    t = step / samples
    angle = math.radians(start_angle + orbit_degrees * t)
    cam.location = Vector((
        poi.x + math.cos(angle) * orbit_radius,
        poi.y + math.sin(angle) * orbit_radius,
        poi.z + orbit_height,
    ))
    cam.keyframe_insert("location", frame=f)
    target.location = look_at
    target.keyframe_insert("location", frame=f)
```

Why this is preferable here:
- works without curve bookkeeping
- easy to vary orbit angle per stop
- easy to skip on cramped points
- resilient if parents/constraints were left in odd states in prior blend versions

### 5. Title / info card strategy

Most feasible Blender-Python approach: 2D overlay scene in the Video Sequence Editor or compositor-backed text card.

Practical recommendation for this repo:
- create a dedicated text-card plane or text objects parented to a fixed overlay camera in a separate scene, then add it in the VSE as an overlay strip
- if you want a simpler first pass, generate title cards directly in the same scene as Text objects placed in front of the camera, but this is less robust

Preferred robust approach:

Option A: VSE text/color strips generated by Python
- enable `scene.sequence_editor_create()`
- for each waypoint, add:
  - semi-transparent color strip as card background
  - text strip for title/date/citation
- place each strip on channels above the render strip for the hold window

Pros:
- true screen-space overlay
- no need to manage camera-facing 3D card placement
- easy fade-in/out using strip blend alpha / opacity animation

Cons:
- Blender VSE text-strip API varies somewhat across versions

Option B: 3D card parented to camera
- create a plane and text objects in front of `FlythroughCam`
- parent them to camera so they stay screen-fixed
- animate material alpha / hide_render

Pros:
- easy to understand
- self-contained in one scene

Cons:
- transparency/material setup is fiddlier
- card can clip or scale oddly if camera settings change

For reliability without Blender installed, I recommend coding Option B first, with a later optional upgrade to VSE overlay if needed.

### 6. Recommended 3D title-card object bundle

Create once:
- `InfoCardRoot`
- `InfoCardBG` plane with transparent dark material
- `InfoCardTitle` text object
- `InfoCardSubtitle` text object
- `InfoCardMeta` text object

Parent all to `FlythroughCam` and place them a short distance in front of the camera, slightly lower-right or lower-left in frame. Keyframe:
- material alpha from 0.0 to 0.85
- text object `hide_render` if easier per card window
- text body updates at the first frame of each stop

Recommended card contents per stop:
- title
- date
- one-line caption
- short source citation

Keep copy short. Long body text will be unreadable during a flythrough.

## Suggested timing for a more cinematic cut

Current movie: 240 frames / 8 sec / 30 fps.
That is too short for multiple stops.

Recommendation:
- 720 to 1080 frames total at 30 fps
- target duration 24 to 36 seconds

Useful default per waypoint:
- travel: 30 to 50 frames
- settle: 8 to 14 frames
- hold/card: 24 to 36 frames
- orbit: 24 to 40 frames
- push/zoom: 14 to 24 frames

If 8 waypoints are kept, total runtime will likely be about 28 to 34 seconds.

## Concrete implementation outline for `build_cinematic_flythrough.py`

1. import `bpy`, `math`, and `Vector` from `mathutils`
2. define `DEFAULTS` and `WAYPOINTS`
3. helper: `get_obj(name)` with clear error
4. helper: `clear_animation(obj)`
5. helper: `ensure_track_to(camera, target)`
6. helper: `set_kf(obj, frame, location=None, lens=None, data_path_overrides=None)`
7. helper: `apply_bezier_smoothing(obj)`
8. helper: `ensure_info_card(camera)`
9. helper: `show_card(card, frame_start, frame_end, waypoint)`
10. helper: `animate_orbit(camera, target, poi, frame_start, frames, radius, height, degrees, lens=None)`
11. main builder:
    - find `FlythroughCam`, `CameraTarget`
    - for each waypoint:
      - resolve pin object
      - derive transforms
      - append travel, settle, hold, orbit, push frames
      - schedule card visibility and text
    - set `scene.frame_end`
    - smooth keyframes
    - save blend if desired

## Pitfalls and how to avoid them

1. Existing constraints may conflict
- old `FOLLOW_PATH` constraints on `FlythroughCam` or `CameraTarget` should be removed or muted
- otherwise explicit location keyframes will fight the constraint result

2. Lens animation can feel like a crash zoom
- keep focal changes small and pair with a subtle dolly
- e.g. 35mm to 50mm, not 28mm to 90mm unless deliberately dramatic

3. Orbit radius may collide with terrain or labels
- compute orbit center from pin and add a minimum camera height
- allow per-waypoint overrides for cramped areas

4. Text cards in 3D can flicker or alpha-sort badly in Eevee
- use Alpha Blend materials carefully
- keep card geometry close to camera but not so close that clipping occurs
- if alpha issues become annoying, move to VSE overlays

5. Camera may stare too low at the terrain
- always look at `poi.z + look_height`
- do not track to raw terrain elevation unless the shot truly needs ground focus

6. All waypoints should not receive identical treatment
- primary story points should get longer holds/orbits
- secondary transitions can be travel-only or very short holds

7. Interpolation must be tuned after keyframing
- use BEZIER/AUTO_CLAMPED for location and lens curves
- avoid global LINEAR except for specific mechanical movement

8. Re-running the script should be idempotent
- clear old animation data
- re-use or delete previously generated `InfoCard*` helpers
- do not duplicate constraints every run

## Recommended first-pass shot order for this project

Suggested emphasis using the existing battlefield route:
- A / Brigade HQ: establish context, longer title card
- B / Maricourt: short stop
- D / Briqueterie: moderate stop
- F / Trones Wood: strong orbit and hold
- G or I equivalent Guillemont point: strongest dramatic zoom/card

Not every pin needs a full stop. A hybrid approach is better:
- major stops: full pause + orbit + card
- minor stops: glide-through with only brief label or no card

## Bottom-line recommendation

Implement the new movie as a data-driven keyframed camera/target system, not as a single follow-path spline. Use existing pin objects as the authoritative waypoint anchors, add per-waypoint timing and framing data, and create title cards as camera-parented overlay objects for the first pass. This will be much easier to reuse, edit, and debug than the current one-curve glide.