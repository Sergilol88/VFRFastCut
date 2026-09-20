# Contributing

Thanks for helping improve VFR FastCut.

## Bug reports

Please use the bug report issue template and include reproducible steps, VFR FastCut version, Windows version and a short description of the source media.

## Feature requests

VFR FastCut 0.2.x is intentionally focused on lossless stream-copy editing. Features that require video re-encoding (text overlays, filters, transitions, frame-exact video edits) are expected to belong to the 0.3.x line rather than expanding 0.2.x.

## Pull requests

- Keep changes focused.
- Preserve both English and Russian UI strings when adding user-visible text.
- Run `python -m py_compile vfr_fastcut.py` before submitting.
- Avoid introducing unnecessary dependencies.
- Do not commit sample VODs, `build/`, `dist/`, or bundled FFmpeg binaries.
