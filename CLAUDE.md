# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Historical research and documentation repository focused on a first edition set of Winston Churchill's "The Second World War" containing a personal note from Churchill to Colonel Bryan Charles Fairfax (dated 6 December 1946). Includes a Python archive search tool for locating Fairfax's original letter to Churchill.

## Commands

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run archive search (basic, no OCR)
python fairfax_letter_finder.py

# Full search with OCR processing
python fairfax_letter_finder.py --full

# OCR on existing downloaded documents
python fairfax_letter_finder.py --ocr-only <directory>

# Custom search query
python fairfax_letter_finder.py --query "search terms"
```

No build, lint, or test commands — this is a documentation repository with a single Python tool.

## Architecture

**fairfax_letter_finder.py** (sole code file) contains three classes:

- **ArchiveAPIClient** — HTTP client for querying archive APIs (Churchill Archives Centre, Library and Archives Canada, University of Toronto). Handles rate limiting (1s delay) and retry with backoff.
- **OCRProcessor** — Processes scanned document images via Tesseract OCR. Includes image preprocessing, keyword matching for Churchill/Fairfax references, and relevance scoring. Gracefully degrades when pytesseract is not installed.
- **FairfaxLetterAgent** — Orchestrator that coordinates searches across archives, downloads documents, runs OCR, and compiles results.

Data flow: Agent searches archives → downloads document images → OCR extracts text → relevance scoring → results compiled.

**research/** — fact-only research deliverables:

- **ground-truth-ledger.md** — every provable claim with source file, page/line, and verbatim quote
- **sales-visual-spec.md** — production specs for 3 sales visuals (timeline, map, artifact close-ups), each referencing ledger entries

**terrain_data/** — Somme battlefield 3D visualization assets:

- **somme_dem.tif** — Copernicus GLO-30 DEM GeoTIFF (30m resolution, bbox 49.97-50.01N, 2.75-2.86E)
- **somme_elevations.json** — 144x396 grid of raw elevation values in metres
- **somme_dem_meta.json** — DEM metadata (rows, cols, min/max elevation, bounding box)
- **somme_satellite.jpg** — ESRI World Imagery mosaic (1536x1024, zoom 14)
- **somme_heightmap.png** — 16-bit PNG heightmap converted from GeoTIFF
- **trench_mosaic.png** — Georeferenced NLS trench map mosaic, sheet 62C.NW, 3 Sept 1916 (1536x768)
- **trench_tiles/** — Raw NLS S3 tiles at zoom 14 from `mapseries-tilesets.s3.amazonaws.com`
- **trench_render_*.png** — Blender renders of the 3D terrain with trench map overlay

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
