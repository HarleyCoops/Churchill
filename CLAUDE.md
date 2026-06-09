# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Historical research and documentation repository focused on a first edition set of Winston Churchill's "The Second World War" containing a personal note from Churchill to Colonel Bryan Charles Fairfax (dated 6 December 1946). Three strands of work live here:

1. A Python archive search tool for locating Fairfax's original letter to Churchill.
2. A Blender-based cinematic flythrough of the Somme battlefield, tied to the 89th Brigade's actions.
3. HTML deliverables — a research portal and a slide deck — built on a fact-only research ledger.

## Commands

```bash
# Install Python dependencies
pip install -r requirements.txt

# --- Archive search tool ---
python fairfax_letter_finder.py                       # basic search, no OCR
python fairfax_letter_finder.py --full                # full search with OCR
python fairfax_letter_finder.py --ocr-only <directory>  # OCR existing downloads
python fairfax_letter_finder.py --query "search terms"  # custom query

# --- Cinematic flythrough (requires Blender installed locally) ---
cd terrain_data
blender -b somme_battlefield.blend \
  --python build_cinematic_flythrough.py \
  --python render_flythrough.py          # build animation, render to MP4
python3 encode_flythrough.py             # MP4 -> GIF (needs ffmpeg on PATH)
```

No build, lint, or test commands — this is a documentation repository. The flythrough scripts run inside Blender's Python (`bpy`) and cannot be executed in this environment.

## Architecture

**fairfax_letter_finder.py** (sole code file) contains three classes:

- **ArchiveAPIClient** — HTTP client for querying archive APIs (Churchill Archives Centre, Library and Archives Canada, University of Toronto). Handles rate limiting (1s delay) and retry with backoff.
- **OCRProcessor** — Processes scanned document images via Tesseract OCR. Includes image preprocessing, keyword matching for Churchill/Fairfax references, and relevance scoring. Gracefully degrades when pytesseract is not installed.
- **FairfaxLetterAgent** — Orchestrator that coordinates searches across archives, downloads documents, runs OCR, and compiles results.

Data flow: Agent searches archives → downloads document images → OCR extracts text → relevance scoring → results compiled.

**research/** — fact-only research deliverables. `ground-truth-ledger.md` is the source of truth: every provable claim with source file, page/line, and verbatim quote. The HTML pages (`index.html` portal, `artifact-gallery.html`, `provenance-timeline.html`, `somme-battlefield-map.html`, `valuation-brief.html`) are self-contained — inline CSS, Google Fonts, no build step. `sales-visual-spec.md` (also in `visuals/`) gives production specs for sales visuals, each referencing ledger entries. **Any historical claim in HTML or the deck must trace back to a ledger entry.**

**terrain_data/** — Somme battlefield 3D visualization. The flythrough is a three-stage pipeline (see `CINEMATIC_FLYTHROUGH.md` and `cinematic_flythrough_plan.md`):

- **build_cinematic_flythrough.py** — runs inside an open `.blend`; data-driven. Edit the `WAYPOINTS` list (story beats, pacing, card text, orbit/zoom) to change the film. Each beat travels → settles → shows an info card → orbits → pushes in. Expects scene objects `FlythroughCam`, `CameraTarget`, and `PinHead_*` pins.
- **render_flythrough.py** — renders the animation straight to `fairfax_flythrough.mp4` via EEVEE Next; set `RENDER_IMAGE_SEQUENCE = True` for PNG frames instead.
- **encode_flythrough.py** — converts the MP4 to GIF (or builds an MP4 from PNG frames); requires `ffmpeg`.
- Most raw terrain assets (DEM GeoTIFF, elevation JSON, satellite mosaic, heightmap, trench tiles, the `.blend`) are gitignored. Only selected deliverables are tracked: `somme_dem_meta.json`, `trench_mosaic.png` (NLS sheet 62C.NW, 3 Sept 1916), `trench_render_wide.png`, and the flythrough MP4/GIF.

**presentations/fairfax-churchill-deck/** — HTML slide deck. `deck-stage.js` is a reusable `<deck-stage>` web component handling slide navigation, auto-scaling to a fixed 1920×1080 design canvas, speaker notes, and print-to-PDF. `Fairfax Churchill Deck.html` is the deck; `deck.css` and `assets/` support it.

## Code Style (Python)

- Type hints on function signatures
- Docstrings on classes and methods
- Module-level constants in UPPER_CASE
- Logging via `logging` module with both file (`fairfax_search.log`) and console handlers
- HTTP calls use 15-second timeouts and rate limiting
- Graceful degradation when optional dependencies (pytesseract, pdf2image, opencv) are missing

## Documentation Style

- ATX-style markdown headers, blank lines between blocks
- Reference-style links at document end when possible
- Academic tone with citations for historical claims
- Cross-reference related content between documents (Readme.md, Fairfax-Churchill.md, FirstEditionChecklist.md)
- Document provenance and sources for all historical assertions
