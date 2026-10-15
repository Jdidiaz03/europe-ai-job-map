"""Inline the map outlines, the Indeed data and the employer counts into index.html.

Run from the project folder:  python3 build/build.py
"""
from pathlib import Path

root = Path(__file__).resolve().parent.parent
html = (root / "index.src.html").read_text()
topo = (root / "build" / "europe.topo.json").read_text()
data = (root / "build" / "data.json").read_text()
comp = (root / "build" / "companies.json").read_text()

html = html.replace("/*__TOPO__*/null", topo).replace("/*__DATA__*/null", data).replace("/*__COMP__*/null", comp)
# Full document so GitHub Pages renders it in standards mode (claude.ai adds this itself).
html = ('<!doctype html>\n<html lang="en">\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n' + html)
(root / "index.html").write_text(html)
print("wrote index.html,", len(html) // 1024, "KB")
