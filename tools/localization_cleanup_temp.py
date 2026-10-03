from pathlib import Path

path = Path("vfr_fastcut.py")
text = path.read_text(encoding="utf-8")
old = "<li>Mouse wheel over the timeline — horizontal scroll.</li>"
new = "<li>Use the mouse wheel over the timeline for horizontal scrolling.</li>"
if old not in text:
    raise SystemExit(f"Expected text not found: {old}")
path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
