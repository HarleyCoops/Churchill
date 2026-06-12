#!/usr/bin/env python3
"""
map_flyover.py — turn any high-resolution map scan into a flyable Blender artifact.

A camera flies a sequence of "stops" over the map: it travels to each point,
descends while orbiting (zoom in), climbs out (zoom out), and moves on.
An animated sun sweeps warm-morning -> noon -> amber-evening across the flight.

Usage (headless):
    blender --background --python map_flyover.py -- \
        --image path/to/map.png \
        --stops path/to/stops.json \
        --out   path/to/scene.blend \
        [--fps 30] [--travel 70] [--hold 110] [--res 3840x2160] [--lens 50]

stops.json — ordered list of waypoints. u = fraction from left edge,
v = fraction from bottom edge, alt = camera altitude at closest approach
(map height is normalized to 10 Blender units; alt 1.5-3 is a close pass,
12+ is a full overview):

    [
      {"name": "overview", "u": 0.50, "v": 0.50, "alt": 12.5},
      {"name": "fort",     "u": 0.38, "v": 0.38, "alt": 2.2},
      {"name": "crossing", "u": 0.71, "v": 0.64, "alt": 1.7}
    ]

To render the result:
    blender --background scene.blend --render-anim
(Configure Output Properties first, or pass --setup-render 1920x1080 here
and the .blend is saved ready to render H.264 MP4 beside itself.)

Tips
----
* Scan resolution is everything: extract map pages at 300-400 dpi
  (e.g. `pdftoppm -png -r 400 source.pdf out`) so close passes stay sharp.
* Pick u/v by opening the image and reading pixel coords:
  u = x_px / width_px, v = 1 - y_px / height_px.
* Text overlays: parent FONT objects to the camera at z ~ -2.2,
  y within +/-0.40 (the 50mm frustum is narrow), and fade them with a
  Transparent/Emission Mix Shader whose Fac is keyframed — and remember
  to LINK THE MIX SHADER TO MATERIAL OUTPUT (ask us how we know).
"""
import bpy, os, sys, math, json, argparse


def parse_args():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument('--image', required=True)
    p.add_argument('--stops', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--fps', type=int, default=30)
    p.add_argument('--travel', type=int, default=70, help='frames between stops')
    p.add_argument('--hold', type=int, default=110, help='frames spent at each stop')
    p.add_argument('--res', default='3840x2160')
    p.add_argument('--lens', type=float, default=50)
    p.add_argument('--setup-render', default=None, metavar='WxH',
                   help='also configure H.264 MP4 output at this resolution')
    return p.parse_args(argv)


def build(args):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    try:
        scn.render.engine = 'BLENDER_EEVEE_NEXT'
    except TypeError:
        scn.render.engine = 'BLENDER_EEVEE'
    rx, ry = (int(n) for n in args.res.split('x'))
    scn.render.resolution_x, scn.render.resolution_y = rx, ry
    scn.render.fps = args.fps

    world = bpy.data.worlds.new('World'); scn.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes['Background']
    bg.inputs[0].default_value = (0.02, 0.018, 0.015, 1)
    bg.inputs[1].default_value = 0.35

    # --- map plane (lit surface so animated lighting reads on the paper) ---
    img = bpy.data.images.load(os.path.abspath(args.image))
    W = 10.0 * img.size[0] / img.size[1]
    H = 10.0
    mesh = bpy.data.meshes.new('MapMesh')
    mesh.from_pydata([(-W/2,-H/2,0),(W/2,-H/2,0),(W/2,H/2,0),(-W/2,H/2,0)], [], [(0,1,2,3)])
    uvl = mesh.uv_layers.new()
    for i, uv in enumerate([(0,0),(1,0),(1,1),(0,1)]):
        uvl.data[i].uv = uv
    plane = bpy.data.objects.new('Map', mesh)
    scn.collection.objects.link(plane)

    mat = bpy.data.materials.new('MapMat'); mat.use_nodes = True
    nt = mat.node_tree
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img
    bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Roughness'].default_value = 0.85
    nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    plane.data.materials.append(mat)

    def P(u, v):
        return ((u-0.5)*W, (v-0.5)*H, 0.0)

    stops = json.load(open(args.stops))

    # --- camera rig ---
    target = bpy.data.objects.new('Target', None); scn.collection.objects.link(target)
    cam_data = bpy.data.cameras.new('Cam'); cam_data.lens = args.lens
    cam = bpy.data.objects.new('Camera', cam_data); scn.collection.objects.link(cam)
    scn.camera = cam
    con = cam.constraints.new('TRACK_TO'); con.target = target
    con.track_axis = 'TRACK_NEGATIVE_Z'; con.up_axis = 'UP_Y'

    def cam_pos(x, y, alt, azim_deg):
        a = math.radians(azim_deg)
        r = alt * 0.62
        return (x + r*math.sin(a), y - r*math.cos(a), alt)

    frame = 1
    for i, s in enumerate(stops):
        x, y, _ = P(s['u'], s['v'])
        alt = s['alt']
        azim = (-30 + 60*((i % 3) - 1))         # vary approach bearing
        arrive = frame if i == 0 else frame + args.travel
        mid = arrive + args.hold // 2
        leave = arrive + args.hold
        for f in (arrive, leave):
            target.location = (x, y, 0)
            target.keyframe_insert('location', frame=f)
        cam.location = cam_pos(x, y, alt*1.55, azim)        # arrive high
        cam.keyframe_insert('location', frame=arrive)
        cam.location = cam_pos(x, y, alt, azim + 28)        # sink + orbit
        cam.keyframe_insert('location', frame=mid)
        cam.location = cam_pos(x, y, alt*1.25, azim + 55)   # climb out
        cam.keyframe_insert('location', frame=leave)
        frame = leave
    scn.frame_start, scn.frame_end = 1, frame + 20

    for ob in (target, cam):
        for fc in ob.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'; kp.easing = 'EASE_IN_OUT'

    # --- animated sun: morning -> noon -> evening over the whole flight ---
    sun_data = bpy.data.lights.new('Sun', 'SUN')
    sun_data.angle = math.radians(5)
    sun = bpy.data.objects.new('Sun', sun_data)
    scn.collection.objects.link(sun); sun.location = (0, 0, 12)
    END = scn.frame_end
    for f, rotx, roty, energy, color in [
        (1,      55, -50, 2.0, (1.0, 0.80, 0.62)),
        (END//2, 12,   0, 3.2, (1.0, 0.98, 0.92)),
        (END,    58,  50, 1.8, (1.0, 0.72, 0.48)),
    ]:
        sun.rotation_euler = (math.radians(rotx), math.radians(roty), 0)
        sun.keyframe_insert('rotation_euler', frame=f)
        sun_data.energy = energy
        sun_data.keyframe_insert('energy', frame=f)
        sun_data.color = color
        sun_data.keyframe_insert('color', frame=f)

    fill_data = bpy.data.lights.new('Fill', 'AREA')
    fill_data.energy = 220; fill_data.size = 14
    fill = bpy.data.objects.new('Fill', fill_data)
    fill.location = (0, -4, 10)
    scn.collection.objects.link(fill)

    if args.setup_render:
        rx, ry = (int(n) for n in args.setup_render.split('x'))
        scn.render.resolution_x, scn.render.resolution_y = rx, ry
        scn.render.image_settings.file_format = 'FFMPEG'
        scn.render.ffmpeg.format = 'MPEG4'
        scn.render.ffmpeg.codec = 'H264'
        scn.render.ffmpeg.constant_rate_factor = 'HIGH'
        scn.render.filepath = os.path.splitext(os.path.abspath(args.out))[0] + '.mp4'

    bpy.ops.file.pack_all()                       # texture travels inside the .blend
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.out))
    print('Saved', args.out, 'frames:', scn.frame_end)


if __name__ == '__main__':
    build(parse_args())
