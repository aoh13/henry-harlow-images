"""Render one room.

    python3 marketing/renders/render_room.py empress-green-bath --preview
    python3 marketing/renders/render_room.py empress-green-bath --out renders/
"""

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import assets  # noqa: E402
import kit  # noqa: E402
import products  # noqa: E402
import rooms  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("room", choices=sorted(rooms.ROOMS))
    ap.add_argument("--preview", action="store_true", help="small, fast and noisy")
    ap.add_argument("--samples", type=int, default=256)
    ap.add_argument("--out", type=Path, default=HERE / "build" / "out")
    ap.add_argument("--build", type=Path, default=HERE / "build")
    args = ap.parse_args(argv)

    spec = rooms.ROOMS[args.room]
    atlas_dir = args.build / "atlas"
    if not (atlas_dir / f"{spec['handle']}.png").exists():
        products.atlas(spec["handle"], atlas_dir)
    asset_dir = args.build / "assets"
    if not (asset_dir / "garden.png").exists():
        assets.build(asset_dir)

    kit.reset()
    if args.preview:
        kit.setup_render(400, 600, samples=24)
    else:
        kit.setup_render(1000, 1500, samples=args.samples)
    used = spec["build"](atlas_dir, asset_dir)
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / f"{args.room}{'-preview' if args.preview else ''}.png"
    t = time.time()
    kit.render(path)
    info = {"room": args.room, "title": spec["title"], "handle": spec["handle"], "surfaces": spec["surfaces"],
            "tiles": used, "seconds": round(time.time() - t)}
    (args.out / f"{args.room}.json").write_text(json.dumps(info, indent=2))
    print(json.dumps(info))


if __name__ == "__main__":
    main()
