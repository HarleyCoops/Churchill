from pathlib import Path
import bpy

FPS = 30
WIDTH = 1920
HEIGHT = 1080
RENDER_IMAGE_SEQUENCE = False


def resolve_script_dir() -> Path:
    return Path(__file__).resolve().parent


def configure_video_render(scene: bpy.types.Scene, script_dir: Path) -> Path:
    mp4_path = script_dir / "fairfax_flythrough.mp4"
    scene.render.filepath = str(mp4_path)
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.ffmpeg.ffmpeg_preset = "GOOD"
    return mp4_path


def configure_image_sequence_render(scene: bpy.types.Scene, script_dir: Path) -> Path:
    output_dir = script_dir / "flythrough_frames"
    output_dir.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(output_dir / "frame_")
    scene.render.image_settings.file_format = "PNG"
    return output_dir


def main() -> None:
    scene = bpy.context.scene
    fly_cam = bpy.data.objects["FlythroughCam"]
    script_dir = resolve_script_dir()

    scene.camera = fly_cam
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.frame_start = 1

    if RENDER_IMAGE_SEQUENCE:
        render_target = configure_image_sequence_render(scene, script_dir)
        target_label = f"frames -> {render_target}"
    else:
        render_target = configure_video_render(scene, script_dir)
        target_label = f"mp4 -> {render_target}"

    bpy.ops.render.render(animation=True)

    done_file = script_dir / "render_done.txt"
    done_file.write_text(
        f"DONE\nframes={scene.frame_start}-{scene.frame_end}\nfps={scene.render.fps}\ntarget={render_target}\n",
        encoding="utf-8",
    )
    print(
        f"FLYTHROUGH RENDER COMPLETE: {scene.frame_end - scene.frame_start + 1} frames, {target_label}"
    )


if __name__ == "__main__":
    main()
