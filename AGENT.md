# Churchill Repository Agent Guidelines

## Build/Lint/Test Commands
- No build/lint commands - this is a historical documentation repository
- Python OCR tool: `python fairfax_letter_finder.py` (see fairfax_letter_finder.py for usage)
- Python dependencies: `pip install -r requirements.txt`
- To preview markdown: use any markdown previewer (VS Code, GitHub, etc.)

## Architecture & Structure
- **Core docs**: Readme.md (main), Fairfax-Churchill.md (detailed history), FirstEditionChecklist.md
- **Images**: Images/ (Churchill/book photos), MonumenImages/ (memorial photos)
- **Python tool**: fairfax_letter_finder.py - archive search agent for finding Fairfax's original letter to Churchill
- **Dependencies**: pytesseract, Pillow, requests (see requirements.txt)
- **Downloaded content**: downloaded_documents/, ocr_results/
- **Historical PDF**: 89thBrigadeStanley.pdf (contemporary WWI account)

## Code Style (Python)
- Use logging module with file handler (fairfax_search.log)
- Type hints for function signatures
- Docstrings for classes and methods
- Constants in UPPER_CASE at module level
- HTTP timeout handling and rate limiting for API calls
- Graceful degradation for missing dependencies (OCR)

## Documentation Style
- ATX-style headers (# symbols), blank lines between blocks
- Reference-style links at document end when possible
- Academic tone with citations for historical claims
- Images in Images/ or MonumenImages/ subdirectories
- Cross-reference related content between documents
- Document provenance and sources