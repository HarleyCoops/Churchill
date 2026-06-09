# Repository Guidelines

## Project Structure & Module Organization

This repository is a historical research and presentation package for the Churchill/Fairfax first-edition set. Core narrative documents live at the root, especially `Readme.md`, `Fairfax-Churchill.md`, `FirstEditionChecklist.md`, and `TextExtract.md`. Source evidence and public research pages live in `research/`. Book, letter, battlefield, and memorial images are organized under `Images/`, `MonumenImages/`, `visuals/`, and `presentations/fairfax-churchill-deck/assets/`.

Python tooling is intentionally small: `fairfax_letter_finder.py` handles archive searching/OCR, `blender_mcp_addon.py` contains the Blender MCP add-on, and `terrain_data/` contains Somme terrain assets plus flythrough build/encode scripts.

## Build, Test, and Development Commands

- `pip install -r requirements.txt` installs OCR/search dependencies.
- `python fairfax_letter_finder.py` runs the basic archive search workflow.
- `python fairfax_letter_finder.py --full` enables document download and OCR processing.
- `python fairfax_letter_finder.py --ocr-only downloaded_documents` OCRs already downloaded files.
- `python -m unittest test_blender_mcp_security.py` runs the current security regression tests.
- `python terrain_data/encode_flythrough.py` rebuilds the MP4/GIF outputs when `ffmpeg` is installed.
- `blender -b terrain_data/somme_battlefield.blend --python terrain_data/build_cinematic_flythrough.py` rebuilds the cinematic scene when Blender and the `.blend` file are available.

## Coding Style & Naming Conventions

Use Python 3 with 4-space indentation, type hints on public functions, class/method docstrings, and module-level constants in `UPPER_CASE`. Prefer `pathlib` for filesystem work in new scripts. Keep HTTP calls rate-limited and bounded by explicit timeouts. Generated image/video assets should use descriptive lowercase or existing project patterns such as `fairfax_flythrough.mp4`, `render_maricourt_closeup.png`, or `trench_mosaic.png`.

## Testing Guidelines

Tests use the standard `unittest` framework. Name root-level tests `test_*.py` and keep Blender-dependent code stubbed or guarded so tests can run outside Blender. Add focused regression tests for security-sensitive behavior, archive/OCR parsing, and command-line argument handling.

## Commit & Pull Request Guidelines

Recent history uses short imperative subjects, sometimes with conventional prefixes such as `feat:` and `chore:`. Keep commits scoped to one theme, for example `feat: add cinematic flythrough rendering pipeline`. Pull requests should summarize changed research claims, cite affected evidence files, note regenerated assets, and include screenshots or links for changes under `research/` or `presentations/`.

## Agent-Specific Instructions

Preserve provenance. Do not add historical claims without a source path, citation, or ledger entry. Avoid committing caches, logs, temporary downloads, or generated scratch frames unless they are intentional deliverables.
