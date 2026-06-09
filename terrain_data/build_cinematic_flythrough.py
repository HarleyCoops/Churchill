import bpy
import math
from mathutils import Vector

# Cinematic flythrough scaffold
# Intended to replace the current single-path glide with explicit shot beats.
# This file is written to be repo-editable without Blender installed here.
# It has not been runtime-validated in this environment.

FPS = 30
TRAVEL_LENS = 35

DEFAULTS = {
    "look_height": 0.30,
    "travel_offset": (-2.8, -2.2, 2.2),
    "stop_offset": (-1.5, -1.0, 1.5),
    "orbit_radius": 1.8,
    "orbit_height": 1.2,
    "orbit_degrees": 110,
    "lens_hold": 42,
    "lens_detail": 52,
    "timing": {
        "travel": 38,
        "settle": 10,
        "card_in": 8,
        "hold": 26,
        "orbit": 32,
        "push": 18,
        "card_out": 8,
    },
}

WAYPOINTS = [
    {
        "pin": "PinHead_A",
        "title": "Brigade HQ",
        "subtitle": "Pit southwest of Maricourt",
        "date": "June 1916",
        "citation": "89th Brigade, p.121",
        "card_body": "Brigade HQ before the main assault.",
        "priority": "major",
        "timing": {"hold": 34, "orbit": 36},
    },
    {
        "pin": "PinHead_B",
        "title": "Maricourt sector",
        "subtitle": "Attack launch corridor",
        "date": "1 Jul 1916, 6:25am",
        "citation": "89th Brigade, p.131",
        "card_body": "Attack launched from the Maricourt sector.",
        "priority": "minor",
        "timing": {"hold": 18, "orbit": 0, "push": 0},
    },
    {
        "pin": "PinHead_D",
        "title": "Briqueterie",
        "subtitle": "Objective taken",
        "date": "1 Jul 1916",
        "citation": "89th Brigade, p.131",
        "card_body": "A successful intermediate objective on the July advance.",
        "priority": "medium",
    },
    {
        "pin": "PinHead_F",
        "title": "Trones Wood",
        "subtitle": "Holding under fire",
        "date": "Mid-Jul 1916",
        "citation": "89th Brigade, p.143",
        "card_body": "A key dramatic stop for a longer orbit and hold.",
        "priority": "major",
        "orbit_degrees": 150,
        "timing": {"hold": 34, "orbit": 44, "push": 22},
    },
    {
        "pin": "PinHead_G",
        "title": "Guillemont approach",
        "subtitle": "Gas exposure before the attack",
        "date": "Night of 29 Jul 1916",
        "citation": "TE line 29",
        "card_body": "Assembly area prior to the Guillemont attack.",
        "priority": "medium",
    },
    {
        "pin": "PinHead_H",
        "title": "Guillemont",
        "subtitle": "Attack despite gas poisoning",
        "date": "30 Jul 1916",
        "citation": "TE lines 31, 49",
        "card_body": "Final dramatic beat before evacuation from the line.",
        "priority": "major",
        "lens_hold": 46,
        "lens_detail": 58,
        "timing": {"hold": 38, "orbit": 28, "push": 26},
    },
]


def merged_waypoint(spec):
    merged = dict(DEFAULTS)
    merged["timing"] = dict(DEFAULTS["timing"])
    for key, value in spec.items():
        if key == "timing":
            merged["timing"].update(value)
        else:
            merged[key] = value
    return merged


def get_obj(name):
    obj = bpy.data.objects.get(name)
    if not obj:
        raise RuntimeError(f"Required object not found: {name}")
    return obj


def clear_animation(obj):
    if obj.animation_data:
        obj.animation_data_clear()


def remove_constraint_if_present(obj, constraint_type):
    for constraint in list(obj.constraints):
        if constraint.type == constraint_type:
            obj.constraints.remove(constraint)


def ensure_track_to(camera, target):
    for constraint in camera.constraints:
        if constraint.type == "TRACK_TO":
            constraint.target = target
            constraint.track_axis = "TRACK_NEGATIVE_Z"
            constraint.up_axis = "UP_Y"
            return constraint
    track = camera.constraints.new("TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"
    return track


def set_camera_pose(camera, target, frame, cam_loc, target_loc, lens=None):
    bpy.context.scene.frame_set(frame)
    camera.location = cam_loc
    target.location = target_loc
    camera.keyframe_insert(data_path="location", frame=frame)
    target.keyframe_insert(data_path="location", frame=frame)
    if lens is not None:
        camera.data.lens = lens
        camera.data.keyframe_insert(data_path="lens", frame=frame)


def smooth_action(obj):
    if not obj.animation_data or not obj.animation_data.action:
        return
    for fcurve in obj.animation_data.action.fcurves:
        for kp in fcurve.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = "AUTO_CLAMPED"
            kp.handle_right_type = "AUTO_CLAMPED"
        fcurve.update()


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
    bg.location = (0.0, 0.0, 0.0)
    bg.scale = (1.6, 0.55, 1.0)

    mat = bpy.data.materials.get("InfoCardBGMat") or bpy.data.materials.new("InfoCardBGMat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.04, 0.04, 0.04, 1.0)
        bsdf.inputs["Alpha"].default_value = 0.0
    mat.blend_method = "BLEND"
    if not bg.data.materials:
        bg.data.materials.append(mat)
    else:
        bg.data.materials[0] = mat

    text_specs = [
        ("InfoCardTitle", 0.105, (0.0, 0.09, 0.01)),
        ("InfoCardSubtitle", 0.065, (0.0, 0.0, 0.01)),
        ("InfoCardMeta", 0.05, (0.0, -0.1, 0.01)),
    ]
    for name, size, loc in text_specs:
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


def info_card_objects():
    return {
        "root": get_obj("InfoCardRoot"),
        "bg": get_obj("InfoCardBG"),
        "title": get_obj("InfoCardTitle"),
        "subtitle": get_obj("InfoCardSubtitle"),
        "meta": get_obj("InfoCardMeta"),
    }


def set_card_alpha(bg_obj, frame, alpha):
    bpy.context.scene.frame_set(frame)
    if not bg_obj.data.materials:
        return
    mat = bg_obj.data.materials[0]
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if not bsdf:
        return
    bsdf.inputs["Alpha"].default_value = alpha
    bsdf.inputs["Alpha"].keyframe_insert(data_path="default_value", frame=frame)


def show_card(frame_start, frame_end, waypoint):
    card = info_card_objects()
    card["title"].data.body = waypoint["title"]
    card["subtitle"].data.body = f"{waypoint['subtitle']} | {waypoint['date']}"
    card["meta"].data.body = f"{waypoint['card_body']}  Source: {waypoint['citation']}"

    set_card_alpha(card["bg"], frame_start - 1, 0.0)
    set_card_alpha(card["bg"], frame_start, 0.82)
    set_card_alpha(card["bg"], frame_end, 0.82)
    set_card_alpha(card["bg"], frame_end + 1, 0.0)

    for key in ("title", "subtitle", "meta"):
        obj = card[key]
        obj.hide_render = True
        obj.keyframe_insert(data_path="hide_render", frame=frame_start - 1)
        obj.hide_render = False
        obj.keyframe_insert(data_path="hide_render", frame=frame_start)
        obj.keyframe_insert(data_path="hide_render", frame=frame_end)
        obj.hide_render = True
        obj.keyframe_insert(data_path="hide_render", frame=frame_end + 1)


def animate_orbit(camera, target, frame_start, waypoint, poi, look_at, start_angle_deg=-135):
    samples = max(6, int(waypoint["timing"]["orbit"] / 4))
    orbit_frames = waypoint["timing"]["orbit"]
    if orbit_frames <= 0:
        return frame_start

    for step in range(samples + 1):
        t = step / samples
        frame = frame_start + round(orbit_frames * t)
        angle = math.radians(start_angle_deg + waypoint["orbit_degrees"] * t)
        cam_loc = Vector((
            poi.x + math.cos(angle) * waypoint["orbit_radius"],
            poi.y + math.sin(angle) * waypoint["orbit_radius"],
            poi.z + waypoint["orbit_height"],
        ))
        set_camera_pose(camera, target, frame, cam_loc, look_at, waypoint["lens_hold"])

    return frame_start + orbit_frames


def animate_push(camera, target, frame_start, waypoint, poi, look_at):
    push_frames = waypoint["timing"]["push"]
    if push_frames <= 0:
        return frame_start

    current = camera.location.copy()
    direction = (look_at - current).normalized()
    end_loc = current + (direction * 0.55)
    set_camera_pose(camera, target, frame_start, current, look_at, waypoint["lens_hold"])
    set_camera_pose(camera, target, frame_start + push_frames, end_loc, look_at, waypoint["lens_detail"])
    return frame_start + push_frames


def build_cinematic_flythrough():
    scene = bpy.context.scene
    scene.render.fps = FPS

    camera = get_obj("FlythroughCam")
    target = get_obj("CameraTarget")

    clear_animation(camera)
    clear_animation(target)
    clear_animation(camera.data)

    remove_constraint_if_present(camera, "FOLLOW_PATH")
    remove_constraint_if_present(target, "FOLLOW_PATH")
    ensure_track_to(camera, target)
    ensure_info_card(camera)

    frame = 1
    previous_stop = None

    for raw_waypoint in WAYPOINTS:
        waypoint = merged_waypoint(raw_waypoint)
        pin = get_obj(waypoint["pin"])
        poi = pin.location.copy()
        look_at = poi + Vector((0.0, 0.0, waypoint["look_height"]))
        travel_cam = poi + Vector(waypoint["travel_offset"])
        stop_cam = poi + Vector(waypoint["stop_offset"])

        if previous_stop is None:
            set_camera_pose(camera, target, frame, travel_cam, look_at, TRAVEL_LENS)
        else:
            set_camera_pose(camera, target, frame, previous_stop, target.location.copy(), TRAVEL_LENS)
            frame += waypoint["timing"]["travel"]
            set_camera_pose(camera, target, frame, travel_cam, look_at, TRAVEL_LENS)

        frame += waypoint["timing"]["settle"]
        set_camera_pose(camera, target, frame, stop_cam, look_at, waypoint["lens_hold"])

        hold_start = frame
        hold_end = hold_start + waypoint["timing"]["hold"]
        show_card(hold_start, hold_end, waypoint)
        set_camera_pose(camera, target, hold_end, stop_cam, look_at, waypoint["lens_hold"])
        frame = hold_end

        frame = animate_orbit(camera, target, frame, waypoint, poi, look_at)
        frame = animate_push(camera, target, frame, waypoint, poi, look_at)

        previous_stop = camera.location.copy()
        frame += waypoint["timing"]["card_out"]

    scene.frame_start = 1
    scene.frame_end = frame + 12
    scene.camera = camera

    smooth_action(camera)
    smooth_action(target)
    if camera.data.animation_data and camera.data.animation_data.action:
        smooth_action(camera.data)

    print(f"Cinematic flythrough built. Frame range: 1-{scene.frame_end}")


if __name__ == "__main__":
    build_cinematic_flythrough()
