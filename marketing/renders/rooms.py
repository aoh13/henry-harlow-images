"""The rooms. Each builds a full scene around one Henry Harlow tile and
returns what it used, so the pin copy can name the exact product.

Layout rules shared by every room, as a tile setter would do it:
- tiles are centred on a wall or floor so the cut pieces at both ends match;
- wall tiles start on top of the floor tile, floor tiles stop at the wall tile;
- joints are the product's own grout width (see products.py).
"""

import math

import kit
import props as P
from kit import INCH, Room, mat, plaster, tile_surface, wood

FLOOR_T = 0.375 * INCH + 0.003  # tile plus thinset, where a wall tile starts


def centred(length, tile, joint):
    """Offset that centres a run of tiles so both end cuts are equal.

    n tiles span n * tile + (n - 1) * joint; centre that span on the run."""
    pitch = tile + joint
    n = math.ceil(length / pitch)
    return (length - (n * pitch - joint)) / 2


def tile_wall(room, wall, s0, s1, t0, t1, meta, atlas, pattern="grid", angle=0.0, seed=1, centre_v=False,
              lift=0.0):
    tw, th = meta["chip"][0] * INCH, meta["chip"][1] * INCH
    j = meta["grout"] * INCH
    off = (centred(s1 - s0, tw, j), centred(t1 - t0, th, j) if centre_v else 0.0)
    return tile_surface(f"tile-{wall}", room, wall, s0, s1, t0, t1, meta, atlas, pattern=pattern, angle=angle,
                        offset=off, seed=seed, lift=lift)


ROOMS = {}


def room(slug, title, handle, surfaces):
    def deco(fn):
        ROOMS[slug] = dict(build=fn, title=title, handle=handle, surfaces=surfaces)
        return fn
    return deco


# --- 1. green marble bathroom -------------------------------------------------------

@room("empress-green-bath", "Green Marble Bathroom with Freestanding Tub",
      "empress-green-marble-tile",
      "Back wall floor to ceiling and the floor, straight stacked, 1/16\" joints")
def empress_green_bath(atlas_dir, assets):
    meta, atlas = kit.load_atlas(atlas_dir, "empress-green-marble-tile")
    r = Room(3.0, 3.6, 2.75)
    wall = plaster((236, 228, 216), name="limewash")
    r.build({"default": wall}, floor_mat=wall, ceiling_mat=mat("ceiling", (240, 236, 228), rough=0.9))
    r.window("left", 1.9, 3.15, 0.75, 2.35, P.black_metal(), mullions=(2, 2), backdrop=assets / "garden.png",
             backdrop_strength=1.6)
    floor = tile_surface("tile-floor", r, "floor", 0, r.w, 0, r.d - FLOOR_T, meta, atlas,
                         offset=(centred(r.w, 12 * INCH, meta["grout"] * INCH),
                                 centred(r.d, 12 * INCH, meta["grout"] * INCH)), seed=4)
    back = tile_wall(r, "back", 0, r.w, FLOOR_T, r.h, meta, atlas, seed=2)
    r.baseboard(["left", "right"], 0.1, plaster((236, 228, 216), name="base"))

    P.freestanding_tub((1.5, r.d - 0.62, 0), 0.0)
    P.wall_spout(r, "back", 1.5, 0.78, P.brass(), reach=0.2, spread=0.22)
    teak = wood((150, 104, 66), (104, 70, 44), name="teak")
    kit.box("tub-caddy", (0.2, 0.88, 0.022), (1.95, r.d - 0.62, 0.575), teak, round_=0.004)
    P.books((1.93, r.d - 0.72, 0.597), math.pi / 2, [(214, 200, 176), (120, 96, 72)], height=0.2, depth=0.14,
            lying=True)
    P.jar((1.95, r.d - 0.42, 0.597), 0.035, 0.07, (232, 226, 214), rough=0.4)
    for s in (0.55, 2.45):
        P.sconce(r, "back", s, 1.75, P.brass(), energy=4)
    oak = wood((176, 132, 92), (120, 84, 56), name="oak")
    P.stool((2.62, r.d - 1.05, 0), oak, height=0.46)
    P.towel_stack((2.62, r.d - 1.05, 0.46), 0.2, [(232, 224, 210), (214, 202, 182)])
    P.vase_branches((2.58, r.d - 1.0, 0.57), vase_rgb=(220, 206, 186), height=0.45, vase_h=0.18)
    P.bath_mat((1.45, r.d - 1.38, FLOOR_T), 0.02, size=(0.85, 0.52), rgb=(208, 196, 176))
    P.paddle_plant((0.42, r.d - 1.45, 0), height=1.35)
    for y in (1.6, 2.9):
        P.downlight((1.5, y, r.h), energy=6)
    kit.daylight(sun_elevation=30, sun_azimuth=192, sky_strength=0.3, sun_strength=14)
    kit.area_light("fill", (2.2, 0.3, 2.2), (2.0, 1.0), 40, (1.5, 2.0, 1.0))
    kit.camera((2.48, 0.32, 1.22), (0.95, r.d, 1.22), lens=24, shift_y=-0.08, focus=2.9)
    return dict(floor=floor["tiles"], wall=back["tiles"])


def planks(room, s0, s1, t0, t1, wood_mat, width_in=7.5, length_in=72, seed=9):
    """Engineered oak floor, through the same tiler as the stone."""
    meta = dict(handle="oak-planks", chip=(length_in, width_in), grout=0.03, uv_cells=[[0, 0, 1, 1]],
                finish="honed", grout_rgb=(58, 46, 36))
    return tile_surface("planks", room, "floor", s0, s1, t0, t1, meta, None, pattern="third", seed=seed,
                        thickness=0.012, material=wood_mat, edge=0.0008, lippage=0.0002)


def tile_floor(room, meta, atlas, s0=0.0, s1=None, t0=0.0, t1=None, pattern="grid", angle=0.0, seed=4):
    s1 = room.w if s1 is None else s1
    t1 = room.d - FLOOR_T if t1 is None else t1
    tw, th = meta["chip"][0] * INCH, meta["chip"][1] * INCH
    j = meta["grout"] * INCH
    off = (centred(s1 - s0, tw, j), centred(t1 - t0, th, j)) if not angle else (0.0, 0.0)
    return tile_surface("tile-floor", room, "floor", s0, s1, t0, t1, meta, atlas, pattern=pattern, angle=angle,
                        offset=off, seed=seed)


# --- 2. slate mosaic walk-in shower ----------------------------------------------

@room("golden-coast-shower", "Earthy Slate Mosaic Walk-In Shower",
      "golden-coast-slate-mosaic-wall-and-floor-tile",
      "Back and shower walls floor to ceiling and the whole floor; 2\" chips on 12\" sheets")
def golden_coast_shower(atlas_dir, assets):
    meta, atlas = kit.load_atlas(atlas_dir, "golden-coast-slate-mosaic-wall-and-floor-tile")
    r = Room(2.9, 3.2, 2.7)
    wall = plaster((232, 222, 206), name="limewash-warm")
    r.build({"default": wall}, floor_mat=wall, ceiling_mat=mat("ceiling", (238, 232, 222), rough=0.9))
    oak = wood((186, 146, 104), (128, 92, 62), name="oak")
    r.window("left", 0.85, 1.95, 1.2, 2.35, wood((120, 88, 60), (84, 60, 42), name="frame-wood"), mullions=(1, 1),
             backdrop=assets / "garden.png", backdrop_strength=1.5)
    floor = tile_floor(r, meta, atlas, seed=5)
    back = tile_wall(r, "back", 0, r.w, FLOOR_T, r.h, meta, atlas, seed=6)
    side = tile_wall(r, "right", FLOOR_T, 1.35, FLOOR_T, r.h, meta, atlas, seed=7)

    P.glass_panel((1.62, r.d - FLOOR_T - 0.01), (1.62, r.d - 1.1), FLOOR_T, 2.0, P.black_metal())
    P.rain_shower(r, "back", 2.3, 2.15, P.black_metal(), arm=0.42)
    P.linear_drain((1.78, r.d - 0.16, FLOOR_T), (2.72, r.d - 0.16, FLOOR_T), FLOOR_T)
    teak = wood((150, 104, 66), (104, 70, 44), name="teak")
    P.stool((2.45, r.d - 0.55, FLOOR_T), teak, height=0.44, radius=0.15)
    P.bottle((2.4, r.d - 0.55, FLOOR_T + 0.44), liquid_rgb=(226, 214, 190), h=0.2, r=0.03)
    P.bottle((2.5, r.d - 0.5, FLOOR_T + 0.44), liquid_rgb=(120, 140, 110), h=0.17, r=0.03)
    top = P.floating_vanity(r, "back", 0.18, 1.32, (226, 216, 200), oak, height=0.84, depth=0.48, sink="vessel",
                            basin_rgb=(236, 230, 220))
    P.wall_spout(r, "back", 0.75, 1.05, P.black_metal(), reach=0.17, handles=False)
    P.mirror(r, "back", 0.75, 1.62, "round", (0.68, 0.68), P.black_metal())
    P.vase_branches((1.12, top.y - 0.06, top.z), vase_rgb=(196, 168, 136), height=0.42, vase_h=0.16, seed=9)
    P.soap_pump((0.36, top.y - 0.08, top.z), tray_mat=teak)
    P.towel((0.22, r.d - 0.6, 1.15), math.pi / 2, size=(0.4, 0.6), rgb=(226, 214, 196))
    P.bath_mat((0.78, r.d - 0.95, FLOOR_T), 0.0, size=(0.75, 0.48), rgb=(196, 180, 158))
    P.paddle_plant((0.35, 0.85, 0), height=1.25, pot_rgb=(196, 170, 140))
    for x, y in ((0.75, r.d - 1.0), (2.25, r.d - 0.6)):
        P.downlight((x, y, r.h), energy=6)
    kit.daylight(sun_elevation=38, sun_azimuth=196, sky_strength=0.3, sun_strength=13)
    kit.area_light("fill", (1.45, 0.25, 2.1), (2.0, 1.0), 35, (1.45, 2.0, 1.0))
    kit.camera((1.22, 0.3, 1.24), (1.62, r.d, 1.24), lens=24, shift_y=-0.07, focus=2.9)
    return dict(floor=floor["tiles"], back=back["tiles"], side=side["tiles"])


# --- 3. rainbow slate kitchen backsplash ---------------------------------------

@room("rainbow-slate-kitchen", "Rainbow Slate Kitchen Backsplash with Plaster Hood",
      "rainbow-slate-wall-and-floor-tile",
      "Counter to ceiling, 3\" x 6\" laid horizontally in a half offset, 1/8\" joints")
def rainbow_kitchen(atlas_dir, assets):
    meta, atlas = kit.load_atlas(atlas_dir, "rainbow-slate-wall-and-floor-tile")
    r = Room(4.0, 3.4, 2.75)
    wall = plaster((238, 232, 222), name="limewash")
    r.build({"default": wall}, ceiling_mat=mat("ceiling", (240, 236, 228), rough=0.9))
    floor = planks(r, 0, r.w, 0, r.d, wood((190, 152, 112), (140, 104, 70), name="oak-floor"))
    r.window("right", 0.7, 1.9, 1.0, 2.3, P.black_metal(), mullions=(2, 2), backdrop=assets / "garden.png",
             backdrop_strength=1.5)
    counter_h = 0.91
    splash = tile_wall(r, "back", 0, r.w, counter_h, r.h, meta, atlas, pattern="running", seed=11)
    cream = mat("cabinet-cream", (230, 222, 206), rough=0.45, coat=0.15)
    counter = mat("counter", (232, 228, 220), rough=0.22, coat=0.2, bump=0.02, bump_scale=8)
    P.shaker_run(r, "back", 0.15, 3.85, cream, counter, height=counter_h, gaps=[(1.62, 2.38)])
    P.range_cooker(r, "back", 2.0, 0.76, mat("range-black", (30, 30, 32), rough=0.35, coat=0.4))
    P.dutch_oven(tuple(r.point("back", 1.82, counter_h + 0.015, 0.45)))
    P.plaster_hood(r, "back", 2.0, 0.98, 1.62, r.h, wall, ledge_mat=wood((120, 86, 60), (80, 56, 38), name="walnut"))
    walnut = wood((128, 92, 64), (84, 60, 42), name="walnut")
    for s0, s1 in ((0.3, 1.38), (2.62, 3.7)):
        for z in (1.5, 1.92):
            P.shelf(r, "back", s0, s1, z, 0.26, walnut, thickness=0.045)
    # styling: shelves left
    P.plate_stack(tuple(r.point("back", 0.55, 1.545, 0.13)), 0.12, 5, (238, 234, 226))
    P.bowl(tuple(r.point("back", 0.95, 1.545, 0.13)), 0.11, 0.08, (192, 140, 102))
    P.jar(tuple(r.point("back", 1.22, 1.545, 0.12)), 0.05, 0.16, (60, 58, 54))
    P.books(tuple(r.point("back", 0.45, 1.965, 0.12)), 0.0, [(150, 120, 92), (214, 200, 176), (92, 104, 84)],
            height=0.22, depth=0.16)
    P.bowl(tuple(r.point("back", 1.05, 1.965, 0.13)), 0.09, 0.07, (236, 232, 224))
    # shelves right
    P.jar(tuple(r.point("back", 2.85, 1.545, 0.12)), 0.06, 0.2, (224, 214, 196))
    P.jar(tuple(r.point("back", 3.05, 1.545, 0.12)), 0.045, 0.14, (186, 120, 82))
    P.plate_stack(tuple(r.point("back", 3.42, 1.545, 0.13)), 0.11, 4, (214, 206, 190))
    P.vase_branches(tuple(r.point("back", 3.3, 1.965, 0.13)), vase_rgb=(220, 206, 186), height=0.35, vase_h=0.16,
                    seed=4)
    # counter
    P.cutting_board(tuple(r.point("back", 0.62, counter_h, 0.05)), P.facing(r, "back"), (0.34, 0.48),
                    wood((176, 132, 90), (128, 90, 58), name="board"))
    P.cutting_board(tuple(r.point("back", 0.85, counter_h, 0.07)), P.facing(r, "back"), (0.28, 0.36),
                    wood((150, 108, 72), (100, 70, 46), name="board2"))
    P.bowl(tuple(r.point("back", 3.2, counter_h, 0.3)), 0.15, 0.09, (232, 226, 214), rough=0.6)
    P.lemons(tuple(r.point("back", 3.2, counter_h + 0.02, 0.3)), n=5)
    P.utensil_crock(tuple(r.point("back", 1.4, counter_h, 0.16)), rgb=(120, 128, 98))
    P.bottle(tuple(r.point("back", 2.55, counter_h, 0.14)), liquid_rgb=(156, 136, 44))
    for s_ in (0.98, 3.2):
        P.outlet(r, "back", s_, 1.12, out=0.0125)
    bar_z = 0.12 + 0.91 * 0.55 + 0.03
    P.towel(tuple(r.point("back", 2.12, bar_z + 0.01, 0.68)), P.facing(r, "back"), size=(0.24, 0.42),
            rgb=(196, 182, 156), folded_over=0.022, kind="linen", stripe_rgb=(150, 86, 60))
    for x in (0.9, 2.0, 3.1):
        P.downlight((x, r.d - 0.75, r.h), energy=7)
    kit.daylight(sun_elevation=34, sun_azimuth=-24, sky_strength=0.3, sun_strength=11)
    kit.area_light("fill", (2.0, 0.4, 2.2), (2.5, 1.0), 50, (2.0, 2.5, 1.2))
    kit.camera((1.72, 0.55, 1.34), (2.15, r.d, 1.34), lens=27, shift_y=0.03, focus=2.85)
    return dict(backsplash=splash["tiles"])


# --- 4. burgundy marble powder room ------------------------------------------------

@room("rosso-levanto-powder-room", "Burgundy Marble Powder Room with Brass Sconces",
      "rosso-levanto-12x12-modern-tumbled-square-tile",
      "Every wall floor to ceiling and the floor, 12\" x 12\" stacked, 1/8\" joints")
def rosso_powder(atlas_dir, assets):
    meta, atlas = kit.load_atlas(atlas_dir, "rosso-levanto-12x12-modern-tumbled-square-tile")
    r = Room(1.8, 2.1, 2.6)
    r.build({"default": plaster((210, 190, 176), name="plaster-rose")},
            ceiling_mat=mat("ceiling", (226, 212, 200), rough=0.9))
    floor = tile_floor(r, meta, atlas, seed=21)
    back = tile_wall(r, "back", 0, r.w, FLOOR_T, r.h, meta, atlas, seed=22)
    left = tile_wall(r, "left", 0, r.d - FLOOR_T, FLOOR_T, r.h, meta, atlas, seed=23)
    right = tile_wall(r, "right", FLOOR_T, r.d, FLOOR_T, r.h, meta, atlas, seed=24)
    walnut = wood((116, 80, 54), (74, 50, 34), name="walnut")
    out = 0.0125  # stand off the tiled wall
    top = P.floating_vanity(r, "back", 0.42, 1.38, (226, 214, 198), walnut, height=0.84, depth=0.46 + out,
                            sink="vessel", basin_rgb=(238, 232, 222))
    P.wall_spout(r, "back", 0.9, 1.1, P.brass(), reach=0.17 + out, handles=False)
    P.mirror(r, "back", 0.9, 1.62, "round", (0.58, 0.58), P.brass(), out=0.02 + out)
    for s in (0.32, 1.48):
        P.sconce(r, "back", s, 1.68, P.brass(), shade="linen", energy=12)
    P.vase_branches((top.x + 0.36, top.y - 0.05, top.z), vase_rgb=(214, 200, 180), height=0.3, vase_h=0.14, seed=31)
    P.soap_pump((top.x - 0.34, top.y - 0.06, top.z), glass_rgb=(60, 56, 52))
    ring = r.point("left", 1.15, 1.3, out + 0.04)
    kit.tube("towel-ring", [tuple(ring + kit.Vector((0, 0.08 * math.cos(t), 0.08 * math.sin(t))))
                            for t in [2 * math.pi * k / 32 for k in range(33)]], 0.005, P.brass(), bezier=False)
    P.towel((ring.x + 0.012, ring.y, ring.z - 0.06), math.pi / 2, size=(0.26, 0.42), rgb=(232, 222, 206),
            folded_over=0.024)
    casing = mat("casing", (236, 230, 220), rough=0.4, coat=0.1)
    r.door("front", 0.5, 1.3, 2.05, casing)
    # the hall the photo is taken from: oak floor, a lit wall behind the camera for the mirror to see
    hall_wall = plaster((226, 218, 206), name="hall-plaster")
    kit.box("hall-floor", (3.0, 2.0, 0.02), (0.9, -1.15, -0.02), wood((172, 132, 94), (124, 90, 60), name="hall-oak"),
            round_=0)
    kit.box("hall-back", (3.0, 0.1, 2.6), (0.9, -2.2, 0.0), hall_wall, round_=0)
    kit.box("hall-ceiling", (3.0, 2.2, 0.05), (0.9, -1.1, 2.6), mat("ceiling", (226, 212, 200), rough=0.9), round_=0)
    for x in (-0.65, 2.45):
        kit.box("hall-side", (0.1, 2.2, 2.6), (x, -1.1, 0.0), hall_wall, round_=0)
    P.downlight((0.9, 1.15, r.h), energy=18)
    kit.area_light("inside", (0.9, 1.2, 2.5), (0.8, 0.8), 30, (0.9, 1.2, 0.0), color=(1.0, 0.9, 0.8))
    kit.area_light("hall", (0.9, -1.4, 2.5), (1.2, 0.8), 70, (0.9, -1.4, 0.0), color=(1.0, 0.92, 0.84))
    bpy_world_dark()
    kit.camera((0.9, -1.0, 1.4), (0.9, r.d, 1.4), lens=26, shift_y=-0.03, focus=2.6, fstop=4.0)
    return dict(floor=floor["tiles"], back=back["tiles"], left=left["tiles"], right=right["tiles"])


def bpy_world_dark():
    import bpy
    w = bpy.data.worlds.new("dark")
    bpy.context.scene.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    return w


# --- 5. travertine living room ---------------------------------------------------

@room("walnut-travertine-living-room", "Warm Travertine Floor Living Room",
      "walnut-travertine-tile-cross-cut-18x18-1-2-unfilled-brushed-chiseled",
      "Whole floor, 18\" x 18\" straight lay, 1/8\" joints")
def travertine_living(atlas_dir, assets):
    meta, atlas = kit.load_atlas(atlas_dir, "walnut-travertine-tile-cross-cut-18x18-1-2-unfilled-brushed-chiseled")
    r = Room(5.0, 4.6, 2.9)
    wall = plaster((240, 234, 224), name="limewash")
    r.build({"default": wall}, ceiling_mat=mat("ceiling", (242, 238, 230), rough=0.9))
    floor = tile_floor(r, meta, atlas, t1=r.d, seed=41)
    frame = wood((150, 112, 78), (104, 74, 50), name="frame-oak")
    for s0, s1 in ((0.6, 1.9), (3.1, 4.4)):
        r.window("back", s0, s1, 0.45, 2.55, frame, mullions=(2, 3), backdrop=assets / "garden.png",
                 backdrop_strength=1.5)
        P.curtain(r, "back", s0 - 0.25, s0 + 0.05, 2.75, (236, 228, 214), folds=4)
        P.curtain(r, "back", s1 - 0.05, s1 + 0.25, 2.75, (236, 228, 214), folds=4)
    r.baseboard(["left", "right", "back"], 0.08, wall)
    fabric = P.boucle((234, 226, 212))
    P.sofa((2.5, 3.45, 0.0125), 0.0, fabric, length=2.5)
    P.cushion((1.74, 3.55, 0.47), (math.radians(-16), math.radians(6), 0.22), (0.5, 0.22, 0.5),
              P.linen((176, 118, 82)))
    P.cushion((3.26, 3.55, 0.47), (math.radians(-16), math.radians(-5), -0.18), (0.5, 0.22, 0.5),
              P.linen((196, 176, 140)))
    P.throw((3.05, 3.22, 0.43), 0.12, size=(0.5, 0.36, 0.05), rgb=(150, 120, 92))
    oak_dark = wood((122, 88, 60), (82, 58, 40), name="oak-dark")
    P.coffee_table((2.5, 2.35, 0.0125), 0.46, 0.36, oak_dark)
    P.books((2.35, 2.3, 0.375), 0.25, [(214, 200, 176), (120, 96, 72)], height=0.26, depth=0.2, lying=True)
    P.bowl((2.7, 2.45, 0.375), 0.13, 0.07, (60, 56, 52), rough=0.5)
    P.olive_tree((0.55, 3.95, 0.0125), height=1.9, pot_rgb=(200, 176, 146))
    P.floor_lamp((4.45, 3.7, 0.0125), P.brass(), P.linen((238, 230, 214)))
    P.art(r, "left", 2.3, 1.95, (0.75, 0.95), assets / "art-terracotta.png", oak_dark)
    kit.box("side-table", (0.45, 0.45, 0.5), (4.3, 3.05, 0.0125), oak_dark, round_=0.01)
    P.vase_branches((4.3, 3.05, 0.5125), vase_rgb=(176, 120, 86), height=0.4, vase_h=0.2, seed=44)
    P.outlet(r, "left", 1.2, 0.35, rgb=(238, 234, 226))
    kit.daylight(sun_elevation=30, sun_azimuth=62, sky_strength=0.32, sun_strength=6)
    kit.area_light("fill", (2.5, 0.3, 2.4), (3.0, 1.2), 60, (2.5, 2.5, 0.8))
    kit.camera((1.95, 0.25, 1.3), (2.75, r.d, 1.3), lens=24, shift_y=-0.15, focus=3.1)
    return dict(floor=floor["tiles"])


# --- 6. herringbone slate mudroom -----------------------------------------------

@room("chakra-slate-mudroom", "Herringbone Slate Mudroom with Sage Bench",
      "chakra-slate-tile",
      "Whole floor, 3\" x 6\" in a 45 degree herringbone, 1/8\" joints")
def chakra_mudroom(atlas_dir, assets):
    meta, atlas = kit.load_atlas(atlas_dir, "chakra-slate-tile")
    r = Room(2.6, 2.7, 2.7)
    wall = plaster((236, 230, 218), name="limewash")
    r.build({"default": wall}, ceiling_mat=mat("ceiling", (240, 236, 228), rough=0.9))
    floor = tile_floor(r, meta, atlas, t1=r.d, pattern="herringbone", angle=45, seed=51)
    r.window("right", 0.6, 1.6, 1.0, 2.25, P.black_metal(), mullions=(1, 2), backdrop=assets / "garden.png",
             backdrop_strength=1.5)
    r.baseboard(["left", "right"], 0.1, wall)
    sage = mat("sage-paint", (140, 152, 128), rough=0.5, coat=0.1)
    oak = wood((186, 146, 104), (128, 92, 62), name="oak")
    # built-in: side panels, bench with drawers, back panel, upper shelf
    s0, s1, depth = 0.35, 2.25, 0.45
    rot = P.facing(r, "back")
    for s in (s0 + 0.02, s1 - 0.02):
        kit.box("panel", (0.04, depth, 2.1), tuple(r.point("back", s, 0.0125, depth / 2)), sage, rot_z=rot,
                round_=0.003)
    kit.box("backboard", (s1 - s0, 0.02, 1.6), tuple(r.point("back", (s0 + s1) / 2, 0.5, 0.01)), sage, rot_z=rot,
            round_=0.002)
    P.shaker_run(r, "back", s0 + 0.04, s1 - 0.04, sage, oak, height=0.47, depth=depth, toe=0.08, doors=3)
    kit.box("upper-shelf", (s1 - s0, depth - 0.05, 0.035), tuple(r.point("back", (s0 + s1) / 2, 1.85, (depth - 0.05) / 2)),
            oak, rot_z=rot, round_=0.003)
    hooks = P.hooks(r, "back", [0.75, 1.3, 1.85], 1.42, P.brass())
    P.hat((hooks[0].x, hooks[0].y + 0.06, hooks[0].z - 0.22))
    P.tote((hooks[2].x, hooks[2].y - 0.03, hooks[2].z), 0.0)
    for s in (0.7, 1.3, 1.9):
        P.basket(tuple(r.point("back", s, 1.885, 0.2)), 0.15, 0.2)
    tick = P.ticking((226, 218, 202), (58, 72, 96))
    P.cushion(tuple(r.point("back", 0.85, 0.47, 0.25)), (0, 0, rot + 0.03), (0.62, 0.4, 0.07), tick)
    P.cushion(tuple(r.point("back", 1.75, 0.47, 0.25)), (0, 0, rot - 0.02), (0.62, 0.4, 0.07), tick)
    P.basket((0.35, 0.65, 0.0125), 0.17, 0.28, (170, 136, 96))
    P.vase_branches((2.38, 2.2, 0.0125), vase_rgb=(120, 104, 88), height=0.9, vase_h=0.45, seed=55,
                    leaf=(0.06, 0.04))
    P.downlight((1.3, 1.35, r.h), energy=8)
    kit.daylight(sun_elevation=32, sun_azimuth=-20, sky_strength=0.3, sun_strength=12)
    kit.area_light("fill", (1.3, 0.25, 2.2), (2.0, 1.0), 35, (1.3, 2.0, 0.6))
    kit.camera((1.08, 0.22, 1.32), (1.45, r.d, 1.32), lens=22, shift_y=-0.15, focus=2.3)
    return dict(floor=floor["tiles"])


# --- 7. red marble Mediterranean kitchen --------------------------------------------

@room("rojo-alicante-kitchen", "Mediterranean Kitchen with Red Marble Floor on the Diagonal",
      "rojo-alicante-marble-12x12-wall-floor-tile",
      "Whole floor, 12\" x 12\" polished, laid on the diagonal, 1/16\" joints")
def rojo_kitchen(atlas_dir, assets):
    meta, atlas = kit.load_atlas(atlas_dir, "rojo-alicante-marble-12x12-wall-floor-tile")
    r = Room(4.2, 4.6, 2.9)
    wall = plaster((242, 238, 230), name="limewash-white")
    r.build({"default": wall}, ceiling_mat=mat("ceiling", (244, 240, 234), rough=0.9))
    floor = tile_floor(r, meta, atlas, t1=r.d, angle=45, seed=61)
    r.window("back", 1.5, 2.7, 1.1, 2.45, wood((150, 112, 78), (104, 74, 50), name="frame-oak"), mullions=(2, 2),
             backdrop=assets / "garden.png", backdrop_strength=1.6)
    white = mat("cabinet-white", (236, 232, 222), rough=0.4, coat=0.15)
    oak = wood((186, 146, 104), (128, 92, 62), name="oak")
    counter = mat("counter-white", (236, 232, 224), rough=0.2, coat=0.3)
    P.shaker_run(r, "back", 0.15, 4.05, white, counter, height=0.91, handle_mat=P.brass())
    P.deck_faucet(tuple(r.point("back", 2.1, 0.91, 0.12)), P.facing(r, "back") + math.pi, P.brass())
    kit.box("sink", (0.7, 0.45, 0.005), tuple(r.point("back", 2.1, 0.912, 0.32)), mat("sink-shadow", (60, 58, 56),
                                                                                     rough=0.3),
            rot_z=P.facing(r, "back"), round_=0)
    P.shelf(r, "back", 0.25, 1.25, 1.65, 0.24, oak)
    P.plate_stack(tuple(r.point("back", 0.5, 1.69, 0.12)), 0.12, 5, (236, 232, 224))
    P.jar(tuple(r.point("back", 0.85, 1.69, 0.12)), 0.06, 0.2, (176, 120, 86))
    P.bowl(tuple(r.point("back", 1.1, 1.69, 0.12)), 0.09, 0.07, (232, 226, 214))
    P.shelf(r, "back", 2.95, 3.95, 1.65, 0.24, oak)
    P.vase_branches(tuple(r.point("back", 3.3, 1.69, 0.12)), vase_rgb=(236, 230, 220), height=0.35, vase_h=0.16, seed=64)
    P.books(tuple(r.point("back", 3.7, 1.69, 0.1)), 0.0, [(176, 120, 86), (226, 214, 190), (110, 96, 80)], height=0.22,
            depth=0.15)
    P.island((2.1, 2.75, 0.0125), (2.0, 0.95), white, mat("island-top", (232, 228, 220), rough=0.18, coat=0.3))
    for x in (1.45, 2.1, 2.75):
        P.stool((x, 2.05, 0.0125), oak, height=0.66, radius=0.17)
    P.bowl((1.7, 2.85, 0.9325), 0.16, 0.09, (60, 56, 52), rough=0.5)
    P.lemons((1.7, 2.85, 0.95), n=6, seed=6)
    P.vase_branches((2.6, 2.9, 0.9325), vase_rgb=(176, 120, 86), height=0.45, vase_h=0.22, seed=66)
    for x in (1.55, 2.65):
        P.pendant((x, 2.75, 2.9), 0.85, P.brass(), shade_rgb=(232, 224, 210), radius=0.2, energy=10)
    for s_ in (0.8, 3.45):
        P.outlet(r, "back", s_, 1.12)
    P.utensil_crock(tuple(r.point("back", 1.25, 0.91, 0.18)), rgb=(232, 226, 214))
    P.bottle(tuple(r.point("back", 2.85, 0.91, 0.14)), liquid_rgb=(156, 136, 44))
    P.towel((2.75, 2.75 - 0.49, 0.92), 0.0, size=(0.26, 0.4), rgb=(204, 188, 160), folded_over=0.022, kind="linen",
            stripe_rgb=(70, 86, 112))
    kit.daylight(sun_elevation=30, sun_azimuth=78, sky_strength=0.3, sun_strength=12)
    kit.area_light("fill", (2.1, 0.3, 2.4), (3.0, 1.0), 55, (2.1, 2.5, 0.8))
    kit.camera((1.72, 0.25, 1.45), (2.35, r.d, 1.45), lens=22, shift_y=-0.2, focus=2.6)
    return dict(floor=floor["tiles"])


# --- 8. grey slate Japandi bathroom ------------------------------------------------------

@room("amazon-slate-japandi-bath", "Japandi Bathroom in Large Grey Slate",
      "amazon-black-slate-wall-and-floor-tile-1",
      "Shower wall floor to ceiling and the floor, 12\" x 24\" in a one-third offset, 1/8\" joints")
def amazon_japandi(atlas_dir, assets):
    meta, atlas = kit.load_atlas(atlas_dir, "amazon-black-slate-wall-and-floor-tile-1")
    r = Room(3.0, 3.2, 2.7)
    wall = plaster((218, 210, 198), name="plaster-greige")
    r.build({"default": wall}, ceiling_mat=mat("ceiling", (236, 232, 224), rough=0.9))
    floor = tile_floor(r, meta, atlas, pattern="third", seed=71)
    back = tile_wall(r, "back", 0, r.w, FLOOR_T, r.h, meta, atlas, pattern="third", seed=72)
    r.window("left", 2.3, 3.0, 1.3, 2.35, P.black_metal(), mullions=(1, 1), backdrop=assets / "garden.png",
             backdrop_strength=1.5)
    r.baseboard(["left", "right"], 0.08, wall)
    oak = wood((196, 160, 118), (146, 112, 78), name="oak-light")
    top = P.floating_vanity(r, "left", 0.7, 1.9, (226, 220, 210), oak, height=0.84, depth=0.48, sink="vessel",
                            basin_rgb=(232, 228, 220), drawers=2)
    P.wall_spout(r, "left", 1.3, 1.06, P.black_metal(), reach=0.17, handles=False)
    P.mirror(r, "left", 1.3, 1.62, "rect", (0.75, 0.85), P.black_metal())
    P.sconce(r, "left", 0.6, 1.7, P.black_metal(), shade="globe", energy=5)
    P.glass_panel((1.75, r.d - FLOOR_T - 0.01), (1.75, r.d - 1.05), FLOOR_T, 2.0, P.black_metal())
    P.rain_shower(r, "back", 2.38, 2.15, P.black_metal(), arm=0.4)
    P.bench((1.95, r.d - 0.3, 0), (2.85, r.d - 0.3, 0), 0.3, 0.42, oak)
    P.towel_stack((2.62, r.d - 0.3, 0.42), 0.0, [(234, 228, 216), (210, 200, 186)])
    P.vase_branches((top.x - 0.05, top.y + 0.42, top.z), vase_rgb=(60, 58, 54), height=0.38, vase_h=0.16, seed=74)
    P.soap_pump((top.x - 0.05, top.y - 0.36, top.z), glass_rgb=(60, 56, 52))
    P.bath_mat((0.78, 1.3, FLOOR_T), math.pi / 2, size=(0.8, 0.5), rgb=(204, 196, 182))
    P.linear_drain((1.9, r.d - 0.12, FLOOR_T), (2.85, r.d - 0.12, FLOOR_T), FLOOR_T)
    P.paddle_plant((0.42, 2.72, 0), height=1.3, pot_rgb=(120, 112, 104))
    for x, y in ((1.3, 1.3), (2.35, r.d - 0.55)):
        P.downlight((x, y, r.h), energy=6)
    kit.daylight(sun_elevation=36, sun_azimuth=188, sky_strength=0.3, sun_strength=12)
    kit.area_light("fill", (2.4, 0.3, 2.2), (2.0, 1.0), 40, (1.5, 2.0, 1.0))
    kit.camera((2.55, 0.3, 1.25), (0.6, r.d - 0.6, 1.25), lens=24, shift_y=-0.07, focus=2.4)
    return dict(floor=floor["tiles"], back=back["tiles"])
