"""Cut world-atlas countries-50m down to Europe and write a compact TopoJSON.

Keeps every country whose bounding box touches the Europe frame, then keeps
only the arcs those countries use and renumbers them.
"""
import json
import sys

FRAME = (-26, 33, 45, 72)  # lon_min, lat_min, lon_max, lat_max

src, dst = sys.argv[1], sys.argv[2]
topo = json.load(open(src))
sx, sy = topo["transform"]["scale"]
tx, ty = topo["transform"]["translate"]

# Decode delta-encoded arcs to lon/lat for the bounding-box test.
decoded = []
for arc in topo["arcs"]:
    x = y = 0
    pts = []
    for dx, dy in arc:
        x += dx
        y += dy
        pts.append((x * sx + tx, y * sy + ty))
    decoded.append(pts)


def arc_ids(geom):
    rings = geom["arcs"]
    if geom["type"] == "Polygon":
        rings = [rings]
    return [a for poly in rings for ring in poly for a in ring]


def real(i):
    return i if i >= 0 else ~i


kept, used = [], set()
for g in topo["objects"]["countries"]["geometries"]:
    if "arcs" not in g:
        continue
    ids = [real(a) for a in arc_ids(g)]
    pts = [p for i in ids for p in decoded[i]]
    lons = [p[0] for p in pts]
    lats = [p[1] for p in pts]
    if max(lons) < FRAME[0] or min(lons) > FRAME[2] or max(lats) < FRAME[1] or min(lats) > FRAME[3]:
        continue
    kept.append(g)
    used.update(ids)

remap = {old: new for new, old in enumerate(sorted(used))}


def renumber(geom):
    def r(a):
        return remap[a] if a >= 0 else ~remap[~a]

    if geom["type"] == "Polygon":
        geom["arcs"] = [[r(a) for a in ring] for ring in geom["arcs"]]
    else:
        geom["arcs"] = [[[r(a) for a in ring] for ring in poly] for poly in geom["arcs"]]
    return geom


out = {
    "type": "Topology",
    "transform": topo["transform"],
    "objects": {"countries": {"type": "GeometryCollection", "geometries": [renumber(g) for g in kept]}},
    "arcs": [topo["arcs"][i] for i in sorted(used)],
}
json.dump(out, open(dst, "w"), separators=(",", ":"))
print(len(kept), "countries,", len(used), "arcs")
