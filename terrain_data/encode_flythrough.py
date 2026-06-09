from pathlib import Path
import shutil
import subprocess
import sys

FPS = 30


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    frames_dir = script_dir / "flythrough_frames"
    mp4_path = script_dir / "fairfax_flythrough.mp4"
    gif_path = script_dir / "fairfax_flythrough.gif"
    palette_path = script_dir / "flythrough_palette.png"

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("ffmpeg not found in PATH", file=sys.stderr)
        return 1

    if not mp4_path.exists():
        first_frame = frames_dir / "frame_0001.png"
        if not first_frame.exists():
            print(
                f"Missing inputs: expected {mp4_path} or {first_frame}",
                file=sys.stderr,
            )
            return 1

        run(
            [
                ffmpeg,
                "-y",
                "-framerate",
                str(FPS),
                "-i",
                str(frames_dir / "frame_%04d.png"),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(mp4_path),
            ]
        )

    run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(mp4_path),
            "-vf",
            "fps=15,scale=1280:-1:flags=lanczos,palettegen",
            str(palette_path),
        ]
    )

    run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(mp4_path),
            "-i",
            str(palette_path),
            "-lavfi",
            "fps=15,scale=1280:-1:flags=lanczos[x];[x][1:v]paletteuse",
            str(gif_path),
        ]
    )

    print(f"Wrote MP4: {mp4_path}")
    print(f"Wrote GIF: {gif_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
