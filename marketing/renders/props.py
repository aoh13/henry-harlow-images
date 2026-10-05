"""Furniture, fixtures and styling for the room renders, built from
primitives so every scene is self-contained and reproducible."""

import math
import random

import kit  # imports bpy, which provides mathutils
from kit import box, cylinder, lathe, mat, tube
from mathutils import Vector

# --- shared finishes --------------------------------------------------------

def brass():
    return mat("brass", (196, 150, 82), rough=0.28, metal=1.0)


def black_metal():
    return mat("black-metal", (28, 28, 28), rough=0.42, metal=0.6)



def porcelain(rgb=(244, 242, 236)):
    return mat("porcelain", rgb, rough=0.12, coat=0.6)


def linen(rgb):
    return mat("linen-%d-%d-%d" % rgb, rgb, rough=0.92, sheen=0.4, bump=0.25, bump_scale=420)


def boucle(rgb):
    return mat("boucle-%d-%d-%d" % rgb, rgb, rough=0.95, sheen=0.7, bump=0.6, bump_scale=160)


def glass_clear():
    return mat("glass", (255, 255, 255), rough=0.0, transmission=1.0, ior=1.45)


def mirror_mat():
    return mat("mirror", (240, 240, 240), rough=0.01, metal=1.0)


def ceramic(rgb, rough=0.35):
    return mat("ceramic-%d-%d-%d" % rgb, rgb, rough=rough, coat=0.3, bump=0.05, bump_scale=30)



def frosted():
    return mat("frosted", (250, 246, 240), rough=0.5, transmission=0.9, ior=1.45)


# --- placing things against walls -------------------------------------------


def facing(room, wall):
    """Rotation about Z so an object's -Y faces into the room off that wall."""
    o, u, v = room.frame(wall)
    return math.atan2(u.y, u.x)


# --- bathroom ------------------------------------------------------------------

def freestanding_tub(loc, rot_z=0.0, length=1.65, width=0.78, height=0.58, rgb=(246, 244, 239)):
    """Soft oval tub: a lathe-like shell stretched to length."""
    prof = [(0.0, 0.03), (0.30, 0.03), (0.40, 0.08), (0.47, 0.30), (0.5, height - 0.03),
            (0.5, height), (0.47, height), (0.45, height - 0.02), (0.43, 0.32), (0.36, 0.13), (0.0, 0.12)]
    tub = lathe("tub", prof, (0, 0, 0), porcelain(rgb), steps=96, sub=2)
    tub.scale = (length, width, 1)
    tub.location = loc
    tub.rotation_euler.z = rot_z
    water = cylinder("tub-water", 0.37, 0.001, (0, 0, height - 0.17), mat("water", (210, 225, 225), rough=0.0,
                                                                              transmission=1.0, ior=1.33),
                     round_=0)
    water.parent = tub  # inherits the tub's stretch; scaling it again would push it through the ends
    return tub



def wall_spout(room, wall, s, z, material, reach=0.18, handles=True, spread=0.2):
    o, u, v = room.frame(wall)
    n = u.cross(v)
    base = room.point(wall, s, z)
    end = base + n * reach
    tube("spout", [tuple(base), tuple(base + n * (reach * 0.6)), tuple(end - Vector((0, 0, 0.03)))], 0.011,
         material)
    cylinder("spout-rose", 0.028, 0.01, tuple(base), material, rot=_rot_towards(n))
    if handles:
        for side in (-1, 1):
            hp = base + u * (side * spread / 2) + Vector((0, 0, 0.02))
            cylinder("handle-rose", 0.026, 0.012, tuple(hp), material, rot=_rot_towards(n))
            tube("handle", [tuple(hp), tuple(hp + n * 0.06)], 0.009, material)


def _rot_towards(n):
    return Vector(n).to_track_quat("Z", "Y").to_euler()


def floating_vanity(room, wall, s0, s1, top_rgb_or_mat, body_mat, height=0.85, depth=0.5, body_h=0.42,
                    drawers=2, sink="undermount", basin_rgb=(244, 242, 236)):
    """A wall-hung cabinet with a slab top; returns the top's centre."""
    o, u, v = room.frame(wall)
    n = u.cross(v)
    rot = facing(room, wall)
    w = s1 - s0
    mid = room.point(wall, (s0 + s1) / 2, height - body_h, depth / 2)
    body = box("vanity", (w, depth, body_h - 0.03), tuple(mid), body_mat, rot_z=rot, round_=0.004)
    top_mat = top_rgb_or_mat if not isinstance(top_rgb_or_mat, tuple) else mat("vanity-top", top_rgb_or_mat,
                                                                               rough=0.25, coat=0.3)
    top_c = room.point(wall, (s0 + s1) / 2, height - 0.03, depth / 2 + 0.01)
    box("vanity-top", (w + 0.02, depth + 0.02, 0.03), tuple(top_c), top_mat, rot_z=rot, round_=0.003)
    # drawer reveals
    for i in range(1, drawers):
        g = room.point(wall, s0 + w * i / drawers, height - body_h + 0.01, depth + 0.001)
        box("reveal", (0.004, 0.004, body_h - 0.05), tuple(g), mat("shadow", (20, 18, 16), rough=0.9),
            rot_z=rot, round_=0)
    for i in range(drawers):
        pull = room.point(wall, s0 + w * (i + 0.5) / drawers, height - 0.09, depth + 0.012)
        box("pull", (0.16, 0.012, 0.012), tuple(pull), brass(), rot_z=rot, round_=0.004)
    top = room.point(wall, (s0 + s1) / 2, height, depth / 2 + 0.03)
    if sink == "vessel":
        lathe("vessel", [(0.0, 0.0), (0.12, 0.0), (0.2, 0.04), (0.22, 0.12), (0.21, 0.125), (0.19, 0.06),
                         (0.11, 0.02), (0.0, 0.02)], tuple(top), ceramic(basin_rgb, 0.2))
    return top


def mirror(room, wall, s, z, shape, size, frame_mat, out=0.02):
    """Round, arch or rectangle mirror with a thin metal frame; z is its centre."""
    o, u, v = room.frame(wall)
    n = u.cross(v)
    c = room.point(wall, s, z, out)
    w, h = size
    if shape == "round":
        r = w / 2
        pts = [c + u * (r * math.cos(a)) + v * (r * math.sin(a)) for a in
               [2 * math.pi * i / 96 for i in range(96)]]
    elif shape == "arch":
        r = w / 2
        pts = [c + u * (-r) + v * (-h / 2), c + u * r + v * (-h / 2)]
        pts += [c + u * (r * math.cos(a)) + v * (h / 2 - r + r * math.sin(a))
                for a in [math.pi * i / 48 for i in range(49)]]
    else:
        pts = [c + u * (-w / 2) + v * (-h / 2), c + u * (w / 2) + v * (-h / 2), c + u * (w / 2) + v * (h / 2),
               c + u * (-w / 2) + v * (h / 2)]
    kit.mesh_obj("mirror", pts, [tuple(range(len(pts)))], mirror_mat())
    ring = pts + [pts[0]]
    tube("mirror-frame", [tuple(p - n * 0.005) for p in ring], 0.008, frame_mat, bezier=False)
    return c


def sconce(room, wall, s, z, metal, shade="globe", lit=True, energy=6.0):
    o, u, v = room.frame(wall)
    n = u.cross(v)
    base = room.point(wall, s, z)
    cylinder("sconce-plate", 0.05, 0.015, tuple(base), metal, rot=_rot_towards(n))
    arm_end = base + n * 0.14
    tube("sconce-arm", [tuple(base), tuple(base + n * 0.08 + Vector((0, 0, 0.02))), tuple(arm_end)], 0.007, metal)
    if shade == "globe":
        lathe("sconce-globe", [(0.0, -0.06), (0.05, -0.05), (0.07, 0.0), (0.05, 0.05), (0.02, 0.065),
                               (0.0, 0.065)], tuple(arm_end + Vector((0, 0, 0.06))), frosted(), sub=1)
    else:
        lathe("sconce-shade", [(0.04, 0.0), (0.085, 0.0), (0.06, 0.14), (0.03, 0.14)],
              tuple(arm_end - Vector((0, 0, 0.02))), linen((236, 226, 208)), sub=0)
    if lit:
        kit.point_light("sconce-bulb", tuple(arm_end + Vector((0, 0, 0.06))), energy, radius=0.03)


def glass_panel(p0, p1, z0, height, frame_mat, frame=0.02):
    """A fixed shower screen between two floor points, with a slim frame."""
    p0, p1 = Vector(p0), Vector(p1)
    d = (p1 - p0)
    L = d.length
    d.normalize()
    rot = math.atan2(d.y, d.x)
    mid = (p0 + p1) / 2
    pane = box("shower-glass", (L, 0.008, height), (mid.x, mid.y, z0), glass_clear(), rot_z=rot, round_=0)
    pane.visible_shadow = False
    for t in (0.0, 1.0):
        q = p0 + (p1 - p0) * t
        box("glass-frame-v", (frame, 0.025, height), (q.x, q.y, z0), frame_mat, rot_z=rot, round_=0.002)
    for z in (z0, z0 + height - frame):
        box("glass-frame-h", (L, 0.025, frame), (mid.x, mid.y, z), frame_mat, rot_z=rot, round_=0.002)


def rain_shower(room, wall, s, z, material, arm=0.35, head_r=0.15):
    o, u, v = room.frame(wall)
    n = u.cross(v)
    base = room.point(wall, s, z)
    end = base + n * arm
    tube("shower-arm", [tuple(base), tuple(end)], 0.011, material, bezier=False)
    tube("shower-drop", [tuple(end), tuple(end - Vector((0, 0, 0.08)))], 0.011, material, bezier=False)
    cylinder("shower-head", head_r, 0.012, tuple(end - Vector((0, 0, 0.095))), material)
    valve = room.point(wall, s, 1.1)
    cylinder("valve-trim", 0.075, 0.012, tuple(valve), material, rot=_rot_towards(n))
    tube("valve-lever", [tuple(valve), tuple(valve + n * 0.04), tuple(valve + n * 0.05 + Vector((0, 0, -0.07)))],
         0.008, material)


def towel(loc, rot_z, size=(0.45, 0.7), rgb=(232, 224, 210), folded_over=0.03):
    """A towel hung over a bar at loc (its top edge)."""
    w, h = size
    t = box("towel", (w, folded_over, h), (loc[0], loc[1], loc[2] - h), linen(rgb), rot_z=rot_z, round_=0.012)
    return t


def towel_stack(loc, rot_z, rgbs, w=0.32, d=0.24, fold=0.055):
    x, y, z = loc
    for i, rgb in enumerate(rgbs):
        box("towel-fold", (w, d, fold), (x, y, z + i * fold), linen(rgb), rot_z=rot_z + random.uniform(-0.05, 0.05),
            round_=0.02)


def stool(loc, wood_mat, height=0.45, radius=0.16):
    x, y, z = loc
    cylinder("stool-seat", radius, 0.035, (x, y, z + height - 0.035), wood_mat, round_=0.006)
    for i in range(3):
        a = 2 * math.pi * i / 3 + 0.3
        top = (x + 0.6 * radius * math.cos(a), y + 0.6 * radius * math.sin(a), z + height - 0.035)
        foot = (x + 0.95 * radius * math.cos(a), y + 0.95 * radius * math.sin(a), z)
        tube("stool-leg", [foot, top], 0.014, wood_mat, bezier=False)


def bench(p0, p1, depth, height, wood_mat, slats=5):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    rot = math.atan2(d.y, d.x)
    mid = (p0 + p1) / 2
    perp = Vector((-d.y, d.x, 0)).normalized()
    gap = 0.012
    sw = (depth - gap * (slats - 1)) / slats
    for i in range(slats):
        off = -depth / 2 + sw / 2 + i * (sw + gap)
        c = mid + perp * off
        box("bench-slat", (d.length, sw, 0.028), (c.x, c.y, height - 0.028), wood_mat, rot_z=rot, round_=0.004)
    for t in (0.08, 0.92):
        c = p0 + d * t
        box("bench-leg", (0.05, depth, height - 0.028), (c.x, c.y, 0), wood_mat, rot_z=rot, round_=0.004)


# --- plants -------------------------------------------------------------------

def _leaf_mesh(length, width, fold=0.25, steps=7):
    """A pointed oval leaf along +X, its halves lifted slightly off the midrib."""
    verts, rows = [(0.0, 0.0, 0.0)], []
    for i in range(1, steps):
        t = i / steps
        hw = width / 2 * math.sin(math.pi * t) ** 0.8
        rows.append((len(verts), len(verts) + 1, len(verts) + 2))
        verts += [(length * t, hw, hw * fold), (length * t, 0.0, 0.0), (length * t, -hw, hw * fold)]
    verts.append((length, 0.0, 0.0))
    tip = len(verts) - 1
    l0, m0, r0 = rows[0]
    faces = [(0, m0, l0), (0, r0, m0)]
    for (l0, m0, r0), (l1, m1, r1) in zip(rows, rows[1:]):
        faces += [(l0, m0, m1, l1), (m0, r0, r1, m1)]
    l, m, r = rows[-1]
    faces += [(l, m, tip), (m, r, tip)]
    return verts, faces


def leaf_mat(rgb):
    return mat("leaf-%d-%d-%d" % rgb, rgb, rough=0.45, sheen=0.2, subsurface=0.15)


def leafy(name, stems, leaf_len, leaf_w, leaf_rgb_list, stem_mat, per_stem=14, seed=3, droop=0.3, fold=0.25):
    """Leaves along stems; stems is a list of point lists (world)."""
    rnd = random.Random(seed)
    lv, lf = _leaf_mesh(leaf_len, leaf_w, fold)
    verts, faces, mats_idx = [], [], []
    for stem in stems:
        tube(name + "-stem", stem, 0.004, stem_mat)
        pts = [Vector(p) for p in stem]
        for k in range(per_stem):
            t = 0.2 + 0.8 * k / max(1, per_stem - 1)
            seg = t * (len(pts) - 1)
            i = min(int(seg), len(pts) - 2)
            f = seg - i
            p = pts[i].lerp(pts[i + 1], f)
            yaw = rnd.uniform(0, 2 * math.pi)
            pitch = rnd.uniform(-droop, droop * 0.6) - 0.2
            scale = rnd.uniform(0.7, 1.1) * (1.0 - 0.35 * t)
            cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
            base = len(verts)
            for x, y, z in lv:
                x, y, z = x * scale, y * scale, z * scale
                x, z = x * cp - z * sp, x * sp + z * cp
                x, y = x * cy - y * sy, x * sy + y * cy
                verts.append((p.x + x, p.y + y, p.z + z))
            for face in lf:
                faces.append(tuple(base + q for q in face))
                mats_idx.append(rnd.randrange(len(leaf_rgb_list)))
    obj = kit.mesh_obj(name, verts, faces, None, smooth=True)
    for rgb in leaf_rgb_list:
        obj.data.materials.append(leaf_mat(rgb))
    for poly, mi in zip(obj.data.polygons, mats_idx):
        poly.material_index = mi
    return obj


def olive_tree(loc, height=1.7, pot_rgb=(196, 170, 140), seed=5):
    x, y, z = loc
    rnd = random.Random(seed)
    pot_h = 0.42
    lathe("pot", [(0.0, 0.0), (0.17, 0.0), (0.22, 0.05), (0.24, pot_h), (0.225, pot_h), (0.2, pot_h - 0.05),
                  (0.0, pot_h - 0.05)], (x, y, z), mat("terracotta-pot", pot_rgb, rough=0.85, bump=0.3, bump_scale=80))
    trunk_mat = mat("bark", (96, 84, 70), rough=0.9, bump=0.6, bump_scale=40)
    trunk = [(x, y, z + pot_h - 0.05), (x + 0.03, y + 0.02, z + pot_h + 0.4), (x - 0.02, y, z + height * 0.65)]
    tube("trunk", trunk, 0.025, trunk_mat)
    stems = []
    for i in range(9):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(0.18, 0.42)
        top = (x + r * math.cos(a), y + r * math.sin(a), z + height * rnd.uniform(0.82, 1.0))
        mid = (x + r * 0.4 * math.cos(a), y + r * 0.4 * math.sin(a), z + height * rnd.uniform(0.66, 0.75))
        stems.append([trunk[-1], mid, top])
    leafy("olive", stems, 0.07, 0.014, [(108, 124, 92), (128, 140, 108), (92, 108, 82)], trunk_mat,
          per_stem=60, seed=seed, droop=0.8, fold=0.1)


def vase_branches(loc, vase_rgb=(222, 210, 190), height=0.75, seed=7, leaf=(0.05, 0.035),
                  leaf_rgbs=((110, 128, 104), (128, 146, 120)), vase_h=0.3):
    """Eucalyptus-style branches in a stoneware vase."""
    x, y, z = loc
    rnd = random.Random(seed)
    lathe("vase", [(0.0, 0.0), (0.07, 0.0), (0.11, 0.06), (0.12, vase_h * 0.55), (0.06, vase_h * 0.92),
                   (0.055, vase_h), (0.045, vase_h), (0.045, vase_h * 0.9), (0.0, vase_h * 0.9)], (x, y, z),
          ceramic(vase_rgb, 0.6))
    stem_mat = mat("stem", (92, 98, 74), rough=0.7)
    stems = []
    for i in range(7):
        a = rnd.uniform(0, 2 * math.pi)
        lean = rnd.uniform(0.08, 0.3)
        top = (x + lean * math.cos(a), y + lean * math.sin(a), z + vase_h + height * rnd.uniform(0.6, 1.0))
        mid = (x + lean * 0.3 * math.cos(a), y + lean * 0.3 * math.sin(a), z + vase_h + height * 0.4)
        stems.append([(x, y, z + vase_h * 0.8), mid, top])
    leafy("branches", stems, leaf[0], leaf[1], list(leaf_rgbs), stem_mat, per_stem=16, seed=seed, droop=0.5)


def paddle_plant(loc, height=1.5, pot_rgb=(232, 226, 214), seed=11):
    """Large-leaf plant (bird of paradise / banana style) in a pot."""
    x, y, z = loc
    rnd = random.Random(seed)
    pot_h = 0.45
    lathe("pot", [(0.0, 0.0), (0.2, 0.0), (0.23, 0.04), (0.23, pot_h), (0.215, pot_h), (0.0, pot_h - 0.06)],
          (x, y, z), ceramic(pot_rgb, 0.7))
    stem_mat = mat("stem-green", (96, 112, 72), rough=0.6)
    verts, faces = [], []
    lv, lf = _leaf_mesh(0.55, 0.2, fold=0.18, steps=10)
    for i in range(8):
        a = 2 * math.pi * i / 8 + rnd.uniform(-0.3, 0.3)
        tilt = rnd.uniform(0.15, 0.55)
        stem_h = height * rnd.uniform(0.45, 0.75)
        top = Vector((x + math.cos(a) * tilt * 0.5, y + math.sin(a) * tilt * 0.5, z + pot_h + stem_h))
        tube("paddle-stem", [(x, y, z + pot_h - 0.05), tuple(top)], 0.007, stem_mat, bezier=False)
        pitch = rnd.uniform(0.5, 1.1)  # leaves rise and lean out from the stem tip
        base = len(verts)
        for vx, vy, vz in lv:
            px, pz = vx * math.cos(pitch) - vz * math.sin(pitch), vx * math.sin(pitch) + vz * math.cos(pitch)
            rx, ry = px * math.cos(a) - vy * math.sin(a), px * math.sin(a) + vy * math.cos(a)
            verts.append((top.x + rx, top.y + ry, top.z + pz))
        faces += [tuple(base + q for q in f) for f in lf]
    obj = kit.mesh_obj("paddles", verts, faces, leaf_mat((72, 110, 66)), smooth=True)
    return obj


# --- kitchen ----------------------------------------------------------------------

def shaker_run(room, wall, s0, s1, paint, top_mat, height=0.91, depth=0.62, toe=0.1, doors=None,
               handle_mat=None, gaps=()):
    """Base cabinets along a wall with shaker doors, top and toe kick.

    gaps: (s0, s1) spans to leave open (a range, a dishwasher)."""
    handle_mat = handle_mat or brass()
    rot = facing(room, wall)
    o, u, v = room.frame(wall)
    n = u.cross(v)
    spans = [(s0, s1)]
    for g0, g1 in gaps:
        new = []
        for a, b in spans:
            if g1 <= a or g0 >= b:
                new.append((a, b))
            else:
                if g0 > a:
                    new.append((a, g0))
                if g1 < b:
                    new.append((g1, b))
        spans = new
    for a, b in spans:
        w = b - a
        mid = room.point(wall, (a + b) / 2, toe, (depth - 0.02) / 2)
        box("cab", (w, depth - 0.02, height - toe - 0.03), tuple(mid), paint, rot_z=rot, round_=0.002)
        toe_c = room.point(wall, (a + b) / 2, 0, (depth - 0.08) / 2)
        box("toe", (w, depth - 0.08, toe), tuple(toe_c), mat("toe", (40, 36, 32), rough=0.8), rot_z=rot, round_=0)
        count = doors or max(1, round(w / 0.5))
        dw = w / count
        for i in range(count):
            dc = a + dw * (i + 0.5)
            _shaker_door(room, wall, dc, toe + 0.005, dw - 0.006, height - toe - 0.04, depth - 0.02, paint, rot)
            pull_z = height - 0.15
            p = room.point(wall, dc + (dw / 2 - 0.06) * (1 if i % 2 else -1), pull_z, depth + 0.012)
            box("pull", (0.012, 0.012, 0.12), tuple(p), handle_mat, rot_z=rot, round_=0.004)
    top = room.point(wall, (s0 + s1) / 2, height - 0.03, (depth + 0.02) / 2)
    box("counter", (s1 - s0, depth + 0.02, 0.03), tuple(top), top_mat, rot_z=rot, round_=0.002)


def _shaker_door(room, wall, s, z, w, h, depth, paint, rot, rail=0.065):
    face = room.point(wall, s, z, depth + 0.01)
    box("door-panel", (w, 0.012, h), tuple(face), paint, rot_z=rot, round_=0.0015)
    for side in (-1, 1):
        p = room.point(wall, s + side * (w / 2 - rail / 2), z, depth + 0.02)
        box("stile", (rail, 0.012, h), tuple(p), paint, rot_z=rot, round_=0.0015)
    for zz in (z, z + h - rail):
        p = room.point(wall, s, zz, depth + 0.02)
        box("rail", (w - 2 * rail, 0.012, rail), tuple(p), paint, rot_z=rot, round_=0.0015)


def range_cooker(room, wall, s, width, body_mat, depth=0.65, height=0.91, knob_mat=None):
    knob_mat = knob_mat or brass()
    rot = facing(room, wall)
    c = room.point(wall, s, 0, depth / 2)
    box("range", (width, depth, height - 0.02), tuple(c), body_mat, rot_z=rot, round_=0.006)
    oven = room.point(wall, s, 0.12, depth + 0.003)
    box("oven-door", (width * 0.86, 0.01, height * 0.55), tuple(oven), mat("oven-glass", (20, 20, 22), rough=0.1),
        rot_z=rot, round_=0.004)
    bar = room.point(wall, s, 0.12 + height * 0.55 + 0.03, depth + 0.04)
    tube("oven-bar", [tuple(bar + room.frame(wall)[1] * (-width * 0.35)), tuple(bar + room.frame(wall)[1] * (width * 0.35))],
         0.009, knob_mat, bezier=False)
    for i in range(5):
        k = room.point(wall, s - width * 0.36 + i * width * 0.18, height - 0.1, depth + 0.01)
        cylinder("knob", 0.022, 0.03, tuple(k), knob_mat, rot=_rot_towards(room.frame(wall)[1].cross(room.frame(wall)[2])))
    top = room.point(wall, s, height - 0.02, depth / 2)
    box("hob", (width, depth, 0.02), tuple(top), mat("hob", (24, 24, 24), rough=0.3), rot_z=rot, round_=0.002)
    for i, (dx, dy) in enumerate(((-0.2, 0.16), (0.2, 0.16), (-0.2, 0.42), (0.2, 0.42))):
        p = room.point(wall, s + dx * width / 0.9, height, dy)
        cylinder("burner", 0.05, 0.015, tuple(p), mat("cast-iron", (30, 30, 30), rough=0.7))


def plaster_hood(room, wall, s, width, z0, z1, plaster_mat, depth=0.5, top_depth=0.3, ledge_mat=None):
    """A tapered plaster range hood from z0 to the ceiling z1."""
    o, u, v = room.frame(wall)
    n = u.cross(v)
    hb = 0.12
    rot = facing(room, wall)
    c = room.point(wall, s, z0, depth / 2)
    box("hood-band", (width, depth, hb), tuple(c), plaster_mat, rot_z=rot, round_=0.01)
    pts = []
    for zz, dd, ww in ((z0 + hb, depth, width), (z1, top_depth, width * 0.75)):
        for su in (-1, 1):
            for dn in (0, 1):
                pts.append(room.point(wall, s + su * ww / 2, zz, dd * dn))
    faces = [(0, 2, 6, 4), (1, 5, 7, 3), (0, 1, 3, 2), (2, 3, 7, 6), (4, 6, 7, 5)]
    body = kit.mesh_obj("hood", pts, faces, plaster_mat)
    kit.bevel(body, 0.01, 3)
    if ledge_mat:
        lc = room.point(wall, s, z0 - 0.03, depth / 2 + 0.01)
        box("hood-ledge", (width + 0.04, depth + 0.02, 0.03), tuple(lc), ledge_mat, rot_z=rot, round_=0.004)


def shelf(room, wall, s0, s1, z, depth, material, thickness=0.04):
    c = room.point(wall, (s0 + s1) / 2, z, depth / 2)
    box("shelf", (s1 - s0, depth, thickness), tuple(c), material, rot_z=facing(room, wall), round_=0.003)
    return z + thickness


def bowl(loc, r, h, rgb, rough=0.4):
    return lathe("bowl", [(0.0, 0.0), (r * 0.45, 0.0), (r * 0.85, h * 0.4), (r, h), (r * 0.96, h),
                          (r * 0.8, h * 0.45), (0.0, h * 0.12)], loc, ceramic(rgb, rough))


def plate_stack(loc, r, n, rgb):
    x, y, z = loc
    for i in range(n):
        lathe("plate", [(0.0, 0.0), (r * 0.6, 0.0), (r, 0.015), (r * 0.97, 0.018), (r * 0.6, 0.006),
                        (0.0, 0.006)], (x, y, z + i * 0.012), ceramic(rgb, 0.3), sub=1)


def jar(loc, r, h, rgb, rough=0.5):
    return lathe("jar", [(0.0, 0.0), (r * 0.9, 0.0), (r, h * 0.1), (r, h * 0.85), (r * 0.7, h), (r * 0.65, h * 1.05),
                         (0.0, h * 1.05)], loc, ceramic(rgb, rough))


def cutting_board(loc, rot_z, size, wood_mat, lean=0.18):
    w, h = size
    b = box("board", (w, 0.02, h), loc, wood_mat, rot_z=rot_z, round_=0.006)
    b.rotation_euler.x = -lean
    return b


def books(loc, rot_z, colours, height=0.24, depth=0.17, lying=False):
    x, y, z = loc
    c, s = math.cos(rot_z), math.sin(rot_z)
    off = 0.0
    for i, rgb in enumerate(colours):
        t = 0.022 + 0.012 * ((i * 7) % 3)
        if lying:
            box("book", (height, depth, t), (x, y, z + off), mat("book-%d-%d-%d" % rgb, rgb, rough=0.7),
                rot_z=rot_z + 0.03 * ((i % 3) - 1), round_=0.002)
        else:
            box("book", (t, depth, height * (0.85 + 0.15 * ((i * 5) % 3) / 2)), (x + c * off, y + s * off, z),
                mat("book-%d-%d-%d" % rgb, rgb, rough=0.7), rot_z=rot_z, round_=0.002)
        off += t


def pendant(loc, drop, metal, shade_rgb=None, radius=0.18, lit=True, energy=12.0):
    x, y, z = loc
    tube("cord", [(x, y, z), (x, y, z - drop)], 0.003, mat("cord", (30, 30, 30), rough=0.6), bezier=False)
    if shade_rgb:
        lathe("pendant-shade", [(0.02, 0.0), (radius * 0.4, -0.04), (radius, -radius * 0.55), (radius * 0.98, -radius * 0.57),
                                (radius * 0.38, -0.05), (0.0, -0.045)], (x, y, z - drop), ceramic(shade_rgb, 0.6))
    else:
        lathe("pendant-dome", [(0.02, 0.0), (radius * 0.6, -0.05), (radius, -radius * 0.6), (radius * 0.98, -radius * 0.6),
                               (0.0, -0.01)], (x, y, z - drop), metal)
    if lit:
        kit.point_light("pendant-bulb", (x, y, z - drop - radius * 0.35), energy, radius=0.04)


# --- living -------------------------------------------------------------------------

def curved_sofa(loc, rot_z, fabric, length=2.4, depth=0.95, seat_h=0.42, back_h=0.75, curve=0.35):
    """A softly curved sofa: a bent seat block and back, rounded hard."""
    x, y, z = loc
    parts = []
    segs = 24
    for part, h0, h1, d0, d1 in (("seat", 0.12, seat_h, 0.0, depth), ("back", 0.12, back_h, depth - 0.24, depth)):
        verts, faces = [], []
        for i in range(segs + 1):
            t = i / segs - 0.5
            bend = curve * (2 * t) ** 2
            px = t * length
            for dd in (d0, d1):
                for hh in (h0, h1):
                    verts.append((px, dd + bend - depth / 2, hh))
        for i in range(segs):
            a = i * 4
            b = a + 4
            faces += [(a, b, b + 1, a + 1), (a + 2, a + 3, b + 3, b + 2), (a, a + 2, b + 2, b),
                      (a + 1, b + 1, b + 3, a + 3)]
        faces += [(0, 1, 3, 2), (segs * 4, segs * 4 + 2, segs * 4 + 3, segs * 4 + 1)]
        o = kit.mesh_obj("sofa-" + part, verts, faces, fabric)
        kit.bevel(o, 0.06, 5, angle=30, harden=False)
        o.data.shade_smooth()
        o.location = loc
        o.rotation_euler.z = rot_z
        parts.append(o)
    plinth = box("sofa-plinth", (length * 0.96, depth * 0.85, 0.12), (0, 0, 0), mat("plinth", (60, 50, 42), rough=0.7),
                 round_=0.01)
    plinth.location = (x, y, z)
    plinth.rotation_euler.z = rot_z
    return parts


def cushion(loc, rot, size, fabric):
    c = box("cushion", size, loc, fabric, round_=min(size) * 0.45, segments=6)
    c.rotation_euler = rot
    return c



def coffee_table(loc, r, h, material):
    x, y, z = loc
    cylinder("table-top", r, 0.05, (x, y, z + h - 0.05), material, round_=0.01)
    cylinder("table-base", r * 0.55, h - 0.05, (x, y, z), material, round_=0.01)


def floor_lamp(loc, metal, shade):
    x, y, z = loc
    cylinder("lamp-base", 0.14, 0.02, (x, y, z), metal)
    tube("lamp-pole", [(x, y, z), (x, y, z + 1.45)], 0.01, metal, bezier=False)
    lathe("lamp-shade", [(0.1, 0.0), (0.23, 0.0), (0.2, 0.3), (0.12, 0.3)], (x, y, z + 1.3), shade, sub=0)
    kit.point_light("lamp-bulb", (x, y, z + 1.42), 25, radius=0.06)


def art(room, wall, s, z, size, image_path, frame_mat, depth=0.035):
    rot = facing(room, wall)
    w, h = size
    c = room.point(wall, s, z - h / 2, depth / 2)
    box("art-frame", (w + 0.04, depth, h + 0.04), tuple(c - Vector((0, 0, 0.02))), frame_mat, rot_z=rot, round_=0.003)
    o, u, v = room.frame(wall)
    n = u.cross(v)
    kit.quad("art", room.point(wall, s, z, depth + 0.001), u, v, w, h, kit.image_mat("art", image_path, rough=0.8))


def curtain(room, wall, s0, s1, z_top, rgb, folds=10, depth=0.12):
    """A softly folded linen panel hanging from z_top to the floor."""
    o, u, v = room.frame(wall)
    n = u.cross(v)
    cols = folds * 6
    verts, faces = [], []
    for j in range(2):
        z = z_top if j else 0.01
        for i in range(cols + 1):
            t = i / cols
            wave = math.sin(t * folds * 2 * math.pi) * 0.04 + 0.06
            p = room.point(wall, s0 + (s1 - s0) * t, z, depth + wave)
            verts.append(p)
    for i in range(cols):
        faces.append((i, i + 1, cols + 2 + i, cols + 1 + i))
    obj = kit.mesh_obj("curtain", verts, faces, mat("sheer-%d" % sum(rgb), rgb, rough=0.9, sheen=0.5,
                                                    transmission=0.35, ior=1.2), smooth=True)
    sol = obj.modifiers.new("thick", "SOLIDIFY")
    sol.thickness = 0.004
    kit.subsurf(obj, 1)
    rod = room.point(wall, s0 - 0.1, z_top + 0.03, depth + 0.06)
    rod2 = room.point(wall, s1 + 0.1, z_top + 0.03, depth + 0.06)
    tube("curtain-rod", [tuple(rod), tuple(rod2)], 0.01, black_metal(), bezier=False)
    return obj


def basket(loc, r, h, rgb=(186, 152, 108)):
    return lathe("basket", [(0.0, 0.0), (r * 0.9, 0.0), (r, h), (r * 0.96, h), (r * 0.86, 0.02), (0.0, 0.02)], loc,
                 mat("woven-%d" % sum(rgb), rgb, rough=0.9, bump=1.0, bump_scale=140), sub=0)


def hat(loc, rgb=(214, 188, 140)):
    x, y, z = loc
    lathe("hat", [(0.0, 0.11), (0.08, 0.105), (0.095, 0.03), (0.2, 0.01), (0.2, 0.0), (0.09, 0.02), (0.075, 0.1),
                  (0.0, 0.1)], (x, y, z), mat("straw", rgb, rough=0.9, bump=1.0, bump_scale=200))


def lemons(loc, n=5, seed=2):
    rnd = random.Random(seed)
    x, y, z = loc
    m = mat("lemon", (226, 186, 60), rough=0.45, bump=0.3, bump_scale=300)
    for i in range(n):
        a = 2 * math.pi * i / n + rnd.uniform(-0.2, 0.2)
        r = 0.05 if i else 0.0
        o = kit.lathe("lemon", [(0.0, -0.035), (0.03, -0.03), (0.035, 0.0), (0.03, 0.03), (0.0, 0.037)],
                      (x + r * math.cos(a), y + r * math.sin(a), z + 0.035 + (0.03 if i == 0 else 0)), m, steps=24)
        o.rotation_euler = (rnd.uniform(0, 1), rnd.uniform(0, 1), 0)


def deck_faucet(loc, rot_z, material, height=0.36, reach=0.22):
    """A gooseneck faucet on a counter or sink deck."""
    x, y, z = loc
    c, s = math.cos(rot_z), math.sin(rot_z)

    def w(px, py, pz):
        return (x + px * c - py * s, y + px * s + py * c, z + pz)

    cylinder("faucet-base", 0.028, 0.03, (x, y, z), material)
    tube("gooseneck", [w(0, 0, 0.03), w(0, 0, height * 0.8), w(0, -reach * 0.3, height), w(0, -reach * 0.85, height * 0.92),
                       w(0, -reach, height * 0.72)], 0.012, material)
    tube("faucet-lever", [w(0.03, 0, height * 0.3), w(0.09, 0.0, height * 0.36)], 0.006, material, bezier=False)


def hooks(room, wall, s_list, z, material, items=()):
    """Wall hooks; items maps index -> callable(point) that hangs something."""
    o, u, v = room.frame(wall)
    n = u.cross(v)
    for i, s in enumerate(s_list):
        base = room.point(wall, s, z)
        tube("hook", [tuple(base), tuple(base + n * 0.06), tuple(base + n * 0.075 + Vector((0, 0, 0.03)))], 0.007,
             material)
    return [room.point(wall, s, z + 0.02, 0.07) for s in s_list]


def island(loc, size, body_mat, top_mat, height=0.92, overhang=0.25, rot_z=0.0):
    """Kitchen island: body, a top that overhangs one long side, toe kick."""
    x, y, z = loc
    w, d = size
    box("island-toe", (w - 0.1, d - overhang - 0.12, 0.1), (x, y + overhang / 2, z), mat("toe", (40, 36, 32), rough=0.8),
        rot_z=rot_z, round_=0)
    box("island-body", (w - 0.04, d - overhang, height - 0.13), (x, y + overhang / 2, z + 0.1), body_mat, rot_z=rot_z,
        round_=0.003)
    box("island-top", (w, d, 0.04), (x, y, z + height - 0.04), top_mat, rot_z=rot_z, round_=0.004)


def dutch_oven(loc, rgb=(184, 82, 54), r=0.13, h=0.13):
    """An enamelled cast-iron pot with its lid and knob."""
    x, y, z = loc
    enamel = ceramic(rgb, 0.25)
    lathe("pot-body", [(0.0, 0.0), (r * 0.92, 0.0), (r, h * 0.15), (r, h), (r * 0.96, h), (r * 0.94, h * 0.2),
                       (0.0, h * 0.18)], (x, y, z), enamel)
    lathe("pot-lid", [(0.0, h * 0.28), (r * 0.6, h * 0.24), (r * 1.01, h * 0.02), (r * 1.01, 0.0), (0.0, 0.0)],
          (x, y, z + h), enamel)
    cylinder("pot-knob", 0.022, 0.025, (x, y, z + h + h * 0.27), brass())
    for side in (-1, 1):
        cylinder("pot-handle", 0.018, 0.035, (x + side * (r + 0.012), y, z + h * 0.75), enamel,
                 rot=(0, math.pi / 2, 0))
