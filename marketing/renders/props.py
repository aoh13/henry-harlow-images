"""Furniture, fixtures and styling for the room renders, built from
primitives so every scene is self-contained and reproducible."""

import math
import random

import bpy

import kit
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


def soft_box(name, size, loc, material, rot=(0.0, 0.0, 0.0), round_=None, wrinkle=0.004, wrinkle_size=0.05,
             levels=2):
    """A cushion, towel or mat: a rounded box smoothed and lightly creased."""
    sx, sy, sz = size
    obj = box(name, size, loc, material, round_=0)
    obj.rotation_euler = rot
    bev = obj.modifiers.new("round", "BEVEL")
    bev.width = round_ if round_ is not None else min(size) * 0.45
    bev.segments = 3
    sub = obj.modifiers.new("smooth", "SUBSURF")
    sub.levels = sub.render_levels = levels
    if wrinkle:
        tex = bpy.data.textures.new(f"crease-{name}", "CLOUDS")
        tex.noise_scale = wrinkle_size
        tex.noise_depth = 2
        dis = obj.modifiers.new("creases", "DISPLACE")
        dis.texture = tex
        dis.texture_coords = "GLOBAL"
        dis.strength = wrinkle
    obj.data.shade_smooth()
    return obj


def _fabric(name, rgb, ribs=None, loop_scale=260.0, loop_bump=0.9, tone=0.06, stripe_rgb=None, stripe_period=0.07,
            stripe_axis="Z", stripe_share=0.18):
    """Cloth: tone mottling, a pile or weave you can see, optional ribs
    (bands along the object's X axis, every `ribs` metres) and optional woven
    stripes across its height (a tea towel's)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mottle = nt.nodes.new("ShaderNodeTexNoise")
    mottle.inputs["Scale"].default_value = 18.0
    nt.links.new(tc.outputs["Object"], mottle.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = kit.srgb(tuple(c * (1 - tone) for c in rgb))
    ramp.color_ramp.elements[1].color = kit.srgb(tuple(min(255, c * (1 + tone)) for c in rgb))
    nt.links.new(mottle.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = 0.96
    p.inputs["Sheen Weight"].default_value = 0.9
    p.inputs["Sheen Roughness"].default_value = 0.4
    pile = nt.nodes.new("ShaderNodeTexNoise")
    pile.inputs["Scale"].default_value = loop_scale
    pile.inputs["Detail"].default_value = 4
    nt.links.new(tc.outputs["Object"], pile.inputs["Vector"])
    height = pile.outputs["Fac"]
    if ribs:
        wave = nt.nodes.new("ShaderNodeTexWave")
        wave.wave_type = "BANDS"
        wave.bands_direction = "X"
        wave.wave_profile = "SIN"
        wave.inputs["Scale"].default_value = 2 * math.pi / (20 * ribs)  # Blender bands repeat every 2pi/(20 scale)
        nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "FLOAT"
        mix.inputs["Factor"].default_value = 0.35
        nt.links.new(wave.outputs["Fac"], mix.inputs["A"])
        nt.links.new(pile.outputs["Fac"], mix.inputs["B"])
        height = mix.outputs["Result"]
        shade = nt.nodes.new("ShaderNodeMix")  # the grooves read a touch darker
        shade.data_type = "RGBA"
        shade.blend_type = "MULTIPLY"
        shade.inputs["Factor"].default_value = 0.25
        nt.links.new(ramp.outputs["Color"], shade.inputs["A"])
        nt.links.new(wave.outputs["Color"], shade.inputs["B"])
        nt.links.new(shade.outputs["Result"], p.inputs["Base Color"])
    if stripe_rgb:
        bands = nt.nodes.new("ShaderNodeTexWave")
        bands.wave_type = "BANDS"
        bands.bands_direction = stripe_axis
        bands.wave_profile = "SAW"
        bands.inputs["Scale"].default_value = 2 * math.pi / (20 * stripe_period)
        nt.links.new(tc.outputs["Object"], bands.inputs["Vector"])
        step = nt.nodes.new("ShaderNodeValToRGB")
        step.color_ramp.interpolation = "CONSTANT"
        step.color_ramp.elements[1].position = 1 - stripe_share
        nt.links.new(bands.outputs["Fac"], step.inputs["Fac"])
        stripe = nt.nodes.new("ShaderNodeMix")
        stripe.data_type = "RGBA"
        stripe.inputs["B"].default_value = kit.srgb(stripe_rgb)
        nt.links.new(step.outputs["Color"], stripe.inputs["Factor"])
        nt.links.new(p.inputs["Base Color"].links[0].from_socket, stripe.inputs["A"])
        nt.links.new(stripe.outputs["Result"], p.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = loop_bump
    bump.inputs["Distance"].default_value = 0.003
    nt.links.new(height, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])
    return m


def terry(rgb):
    return _fabric("terry-%d-%d-%d" % rgb, rgb, loop_scale=420.0, loop_bump=1.0)


def ribbed_cotton(rgb):
    return _fabric("ribbed-%d-%d-%d" % rgb, rgb, ribs=0.009, loop_scale=500.0, loop_bump=0.8)


def ticking(rgb, stripe_rgb):
    """Cushion ticking: a cotton ground with thin stripes running its length."""
    return _fabric("ticking-%d-%d" % (sum(rgb), sum(stripe_rgb)), rgb, loop_scale=900.0, loop_bump=0.4,
                   stripe_rgb=stripe_rgb, stripe_period=0.022, stripe_axis="X", stripe_share=0.22)


def canvas_cloth(rgb):
    return _fabric("canvas-%d-%d-%d" % rgb, rgb, loop_scale=700.0, loop_bump=0.7, tone=0.1)


def woven(rgb):
    """Seagrass or rattan basketweave: crossing strands, darker in the gaps."""
    m = bpy.data.materials.new("woven-%d-%d-%d" % rgb)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    strands = []
    for axis in ("X", "Z"):
        w = nt.nodes.new("ShaderNodeTexWave")
        w.wave_type = "BANDS"
        w.bands_direction = axis
        w.inputs["Scale"].default_value = 2 * math.pi / (20 * 0.012)  # a strand every 12 mm
        w.inputs["Distortion"].default_value = 1.5
        nt.links.new(tc.outputs["Object"], w.inputs["Vector"])
        strands.append(w)
    weave = nt.nodes.new("ShaderNodeMath")
    weave.operation = "MULTIPLY"
    nt.links.new(strands[0].outputs["Fac"], weave.inputs[0])
    nt.links.new(strands[1].outputs["Fac"], weave.inputs[1])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = kit.srgb(tuple(c * 0.55 for c in rgb))
    ramp.color_ramp.elements[1].color = kit.srgb(tuple(min(255, c * 1.1) for c in rgb))
    ramp.color_ramp.elements[1].position = 0.45
    nt.links.new(weave.outputs["Value"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = 0.85
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 1.0
    bump.inputs["Distance"].default_value = 0.004
    nt.links.new(weave.outputs["Value"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])
    return m


def linen_weave(rgb, stripe_rgb=None):
    return _fabric("linen-weave-%d-%d-%d" % rgb, rgb, loop_scale=900.0, loop_bump=0.5, tone=0.08,
                   stripe_rgb=stripe_rgb)


def bath_mat(loc, rot_z, size=(0.8, 0.5), rgb=(204, 192, 172)):
    x, y, z = loc
    return soft_box("bath-mat", (size[0], size[1], 0.022), (x, y, z), ribbed_cotton(rgb), rot=(0, 0, rot_z),
                    round_=0.009, wrinkle=0.004, wrinkle_size=0.22)


def soap_pump(loc, glass_rgb=(150, 92, 40), tray_mat=None):
    """An amber glass pump bottle, on a little stone or wood tray."""
    x, y, z = loc
    if tray_mat:
        box("tray", (0.2, 0.12, 0.012), (x + 0.03, y, z), tray_mat, round_=0.004)
        z += 0.012
    lathe("soap-bottle", [(0.0, 0.0), (0.035, 0.0), (0.038, 0.01), (0.038, 0.13), (0.03, 0.15), (0.015, 0.16),
                          (0.015, 0.17), (0.0, 0.17)], (x, y, z),
          mat("amber-glass", glass_rgb, rough=0.05, transmission=0.85, ior=1.5))
    cylinder("pump-collar", 0.017, 0.02, (x, y, z + 0.168), black_metal())
    cylinder("pump-stem", 0.006, 0.03, (x, y, z + 0.188), black_metal())
    tube("pump-nozzle", [(x, y, z + 0.215), (x + 0.045, y, z + 0.21)], 0.006, black_metal(), bezier=False)


def outlet(room, wall, s, z, out=0.0, rgb=(240, 238, 232)):
    """A duplex outlet: a plate with two receptacles."""
    o, u, v = room.frame(wall)
    rot = facing(room, wall)
    box("outlet-plate", (0.07, 0.006, 0.115), tuple(room.point(wall, s, z - 0.0575, out + 0.003)),
        mat("outlet", rgb, rough=0.35), rot_z=rot, round_=0.002)
    for dz in (-0.022, 0.022):
        box("receptacle", (0.034, 0.003, 0.03), tuple(room.point(wall, s, z + dz - 0.015, out + 0.0065)),
            mat("receptacle", (226, 224, 218), rough=0.4), rot_z=rot, round_=0.003)


def downlight(loc, energy=12.0, lit=True):
    """A recessed ceiling light: white trim ring, warm lens, a soft cone."""
    x, y, z = loc
    cylinder("downlight-trim", 0.055, 0.004, (x, y, z - 0.004), mat("trim", (240, 238, 234), rough=0.4))
    cylinder("downlight-lens", 0.04, 0.001, (x, y, z - 0.0045),
             mat("lens-lit" if lit else "lens", (255, 226, 190), rough=0.3, emission=4.0 if lit else 0.0))
    if lit:
        data = bpy.data.lights.new("downlight", "SPOT")
        data.energy = energy
        data.spot_size = math.radians(70)
        data.spot_blend = 0.6
        data.shadow_soft_size = 0.03
        data.color = (1.0, 0.84, 0.66)
        obj = bpy.data.objects.new("downlight", data)
        bpy.context.collection.objects.link(obj)
        obj.location = (x, y, z - 0.01)


def linear_drain(p0, p1, z, width=0.06):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    mid = (p0 + p1) / 2
    rot = math.atan2(d.y, d.x)
    steel = mat("steel", (180, 180, 176), rough=0.3, metal=1.0)
    box("drain", (d.length, width, 0.003), (mid.x, mid.y, z), steel, rot_z=rot, round_=0.001)
    for off in (-width / 4, 0.0, width / 4):
        c = mid + Vector((-d.y, d.x, 0)).normalized() * off
        box("drain-slot", (d.length - 0.03, 0.004, 0.0035), (c.x, c.y, z), mat("slot", (30, 30, 30), rough=0.6),
            rot_z=rot, round_=0)


def bottle(loc, liquid_rgb=(150, 130, 40), h=0.28, r=0.035):
    """A glass bottle of oil, with a cork."""
    x, y, z = loc
    lathe("bottle", [(0.0, 0.0), (r * 0.95, 0.0), (r, h * 0.05), (r, h * 0.62), (r * 0.4, h * 0.82), (r * 0.32, h),
                     (0.0, h)], (x, y, z), mat("oil-%d" % sum(liquid_rgb), liquid_rgb, rough=0.03, transmission=0.9,
                                              ior=1.47))
    cylinder("cork", r * 0.3, 0.025, (x, y, z + h - 0.005), mat("cork", (176, 140, 100), rough=0.9, bump=0.6,
                                                                bump_scale=200))


def utensil_crock(loc, rgb=(222, 212, 196), wood_mat=None, seed=8):
    rnd = random.Random(seed)
    x, y, z = loc
    jar((x, y, z), 0.065, 0.16, rgb, rough=0.55)
    wood_mat = wood_mat or mat("spoon-wood", (176, 136, 92), rough=0.6)
    for i in range(5):
        a = 2 * math.pi * i / 5 + rnd.uniform(-0.3, 0.3)
        lean = rnd.uniform(0.04, 0.09)
        top = (x + lean * math.cos(a), y + lean * math.sin(a), z + 0.16 + rnd.uniform(0.12, 0.2))
        tube("utensil", [(x, y, z + 0.03), top], 0.006, wood_mat, bezier=False)
        head = lathe("spoon-head", [(0.0, -0.035), (0.022, -0.02), (0.024, 0.0), (0.02, 0.02), (0.0, 0.03)], top,
                     wood_mat, steps=24)
        head.scale = (1, 0.35, 1)
        head.rotation_euler = (0, 0, a)


def throw(loc, rot_z, size=(0.55, 0.4, 0.05), rgb=(150, 120, 92)):
    """A folded knit blanket."""
    return soft_box("throw", size, loc, _fabric("knit-%d" % sum(rgb), rgb, ribs=0.006, loop_scale=300.0,
                                                    loop_bump=1.0),
                    rot=(0, 0, rot_z), round_=size[2] * 0.45, wrinkle=0.009, wrinkle_size=0.06)


def tote(loc, rot_z, rgb=(214, 198, 168)):
    """A canvas tote hanging from a hook at loc."""
    x, y, z = loc
    canvas = canvas_cloth(rgb)
    soft_box("tote", (0.36, 0.08, 0.4), (x, y, z - 0.55), canvas, rot=(0.05, 0, rot_z), round_=0.03, wrinkle=0.006)
    c, s_ = math.cos(rot_z), math.sin(rot_z)
    for side in (-1, 1):
        tube("tote-handle", [(x + side * 0.12 * c, y + side * 0.12 * s_, z - 0.16), (x, y, z)], 0.006, canvas,
             bezier=False)


def soil(loc, r):
    """The top of the potting mix, a little below the pot's rim."""
    cylinder("soil", r, 0.01, loc, mat("soil", (62, 48, 38), rough=1.0, bump=1.0, bump_scale=120), round_=0)


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


def towel(loc, rot_z, size=(0.45, 0.7), rgb=(214, 202, 182), folded_over=0.035, kind="terry", stripe_rgb=None):
    """A towel hung over a bar or hook at loc (its top edge): soft and creased."""
    w, h = size
    cloth = terry(rgb) if kind == "terry" else linen_weave(rgb, stripe_rgb)
    return soft_box("towel", (w, folded_over, h), (loc[0], loc[1], loc[2] - h), cloth, rot=(0.04, 0, rot_z),
                    round_=folded_over * 0.48, wrinkle=0.011, wrinkle_size=0.09)


def towel_stack(loc, rot_z, rgbs, w=0.32, d=0.24, fold=0.055, seed=4):
    rnd = random.Random(seed)
    x, y, z = loc
    for i, rgb in enumerate(rgbs):
        soft_box("towel-fold", (w, d, fold), (x + rnd.uniform(-0.01, 0.01), y + rnd.uniform(-0.01, 0.01), z + i * fold),
                 terry(rgb), rot=(0, 0, rot_z + rnd.uniform(-0.06, 0.06)), round_=fold * 0.45, wrinkle=0.003)


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

def _leaf_mesh(length, width, fold=0.25, steps=7, curl=0.0, cup=0.0):
    """A pointed oval leaf along +X: halves lifted off the midrib (fold), the
    tip curling up or down (curl, share of length) and edges cupped (cup)."""
    def lift(t):
        return curl * length * t * t

    verts, rows = [(0.0, 0.0, 0.0)], []
    for i in range(1, steps):
        t = i / steps
        hw = width / 2 * math.sin(math.pi * t) ** 0.8
        z = lift(t)
        edge = z + hw * (fold + cup)
        rows.append((len(verts), len(verts) + 1, len(verts) + 2))
        verts += [(length * t, hw, edge), (length * t, 0.0, z), (length * t, -hw, edge)]
    verts.append((length, 0.0, lift(1.0)))
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
    soil((x, y, z + pot_h - 0.04), 0.205)
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


def paddle_plant(loc, height=1.5, pot_rgb=(232, 226, 214), seed=11, leaves=12):
    """Bird-of-paradise style: long stems, broad leaves that arch and droop."""
    x, y, z = loc
    rnd = random.Random(seed)
    pot_h, pot_r = 0.45, 0.23
    lathe("pot", [(0.0, 0.0), (pot_r - 0.03, 0.0), (pot_r, 0.04), (pot_r, pot_h), (pot_r - 0.015, pot_h),
                  (pot_r - 0.02, pot_h - 0.06), (0.0, pot_h - 0.06)], (x, y, z), ceramic(pot_rgb, 0.7))
    soil((x, y, z + pot_h - 0.045), pot_r - 0.022)
    stem_mat = mat("stem-green", (96, 112, 72), rough=0.6)
    greens = [(66, 104, 60), (78, 116, 66), (58, 92, 54)]
    verts, faces, mats_idx = [], [], []
    for i in range(leaves):
        a = 2 * math.pi * i / leaves + rnd.uniform(-0.35, 0.35)
        lean = rnd.uniform(0.08, 0.32)
        stem_h = height * rnd.uniform(0.35, 0.72)
        top = Vector((x + math.cos(a) * lean, y + math.sin(a) * lean, z + pot_h + stem_h))
        mid = Vector((x + math.cos(a) * lean * 0.35, y + math.sin(a) * lean * 0.35, z + pot_h + stem_h * 0.5))
        tube("paddle-stem", [(x, y, z + pot_h - 0.05), tuple(mid), tuple(top)], 0.0065, stem_mat)
        length = rnd.uniform(0.42, 0.62) * (height / 1.5)
        lv, lf = _leaf_mesh(length, length * rnd.uniform(0.3, 0.38), fold=0.12, steps=12,
                            curl=-rnd.uniform(0.15, 0.4), cup=0.05)
        pitch = rnd.uniform(0.7, 1.25)  # leaves rise from the stem tip, then droop
        roll = rnd.uniform(-0.5, 0.5)
        base = len(verts)
        for vx, vy, vz in lv:
            vy, vz = vy * math.cos(roll) - vz * math.sin(roll), vy * math.sin(roll) + vz * math.cos(roll)
            px, pz = vx * math.cos(pitch) - vz * math.sin(pitch), vx * math.sin(pitch) + vz * math.cos(pitch)
            rx, ry = px * math.cos(a) - vy * math.sin(a), px * math.sin(a) + vy * math.cos(a)
            verts.append((top.x + rx, top.y + ry, top.z + pz))
        faces += [tuple(base + q for q in f) for f in lf]
        mats_idx += [i % len(greens)] * len(lf)
    obj = kit.mesh_obj("paddles", verts, faces, None, smooth=True)
    for rgb in greens:
        obj.data.materials.append(leaf_mat(rgb))
    for poly, mi in zip(obj.data.polygons, mats_idx):
        poly.material_index = mi
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

def sofa(loc, rot_z, fabric, length=2.3, depth=0.98, seat_h=0.43, arm_w=0.2, arm_h=0.62, back_h=0.82, seats=3,
         plinth_mat=None, seed=6):
    """A deep modern sofa: recessed plinth, upholstered base, loose seat and
    back cushions, rounded arms. loc is the centre of its footprint; the back
    is on the +y side before rotation."""
    rnd = random.Random(seed)
    x, y, z = loc
    c, s_ = math.cos(rot_z), math.sin(rot_z)

    def at(dx, dy, dz):  # local (along, front-to-back, up) to world
        return (x + dx * c - dy * s_, y + dx * s_ + dy * c, z + dz)

    plinth_mat = plinth_mat or mat("plinth", (52, 44, 38), rough=0.6)
    box("sofa-plinth", (length - 0.12, depth - 0.12, 0.07), at(0, 0, 0), plinth_mat, rot_z=rot_z, round_=0.005)
    soft_box("sofa-base", (length, depth, 0.2), at(0, 0, 0.07), fabric, rot=(0, 0, rot_z), round_=0.05,
             wrinkle=0.002)
    inner = length - 2 * arm_w
    for side in (-1, 1):
        soft_box("sofa-arm", (arm_w, depth, arm_h - 0.07), at(side * (length - arm_w) / 2, 0, 0.07), fabric,
                 rot=(0, 0, rot_z), round_=0.07, wrinkle=0.003)
    soft_box("sofa-back", (inner, 0.18, back_h - 0.27), at(0, depth / 2 - 0.09, 0.27), fabric, rot=(0, 0, rot_z),
             round_=0.06, wrinkle=0.002)
    w = inner / seats
    for i in range(seats):
        cx = -inner / 2 + w * (i + 0.5)
        soft_box("seat-cushion", (w - 0.012, depth - 0.24, seat_h - 0.27), at(cx, -0.1, 0.27), fabric,
                 rot=(0, 0, rot_z + rnd.uniform(-0.01, 0.01)), round_=0.05, wrinkle=0.006, wrinkle_size=0.07)
        soft_box("back-cushion", (w - 0.02, 0.2, 0.48), at(cx, depth / 2 - 0.27, seat_h - 0.02), fabric,
                 rot=(math.radians(-12), 0, rot_z + rnd.uniform(-0.02, 0.02)), round_=0.07, wrinkle=0.007,
                 wrinkle_size=0.07)
    return at


def cushion(loc, rot, size, fabric):
    """A plump throw pillow: thick in the middle, pinched at the corners."""
    obj = soft_box("cushion", size, loc, fabric, rot=rot, round_=min(size) * 0.48, wrinkle=0.012,
                   wrinkle_size=0.07, levels=3)
    obj.scale = (1.0, 0.82, 1.0)  # the fill sags towards the seams
    return obj


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


def curtain(room, wall, s0, s1, z_top, rgb, folds=None, depth=0.12):
    """A linen panel hanging from a rod at z_top to the floor: folds about
    14 cm apart, gathered at the top and opening out towards the hem."""
    o, u, v = room.frame(wall)
    folds = folds or max(1, round((s1 - s0) / 0.14))
    cols = folds * 8
    rows = 6
    verts, faces = [], []
    for j in range(rows + 1):
        h = j / rows  # 0 at the hem, 1 at the rod
        z = 0.01 + (z_top - 0.01) * h
        amp = 0.028 * (1.25 - 0.45 * h)
        for i in range(cols + 1):
            t = i / cols
            p = room.point(wall, s0 + (s1 - s0) * t, z, depth + 0.05 + amp * math.sin(t * folds * 2 * math.pi))
            verts.append(p)
    for j in range(rows):
        for i in range(cols):
            a = j * (cols + 1) + i
            faces.append((a, a + 1, a + cols + 2, a + cols + 1))
    obj = kit.mesh_obj("curtain", verts, faces, linen_weave(rgb), smooth=True)
    sol = obj.modifiers.new("thick", "SOLIDIFY")
    sol.thickness = 0.004
    kit.subsurf(obj, 1)
    rod = room.point(wall, s0 - 0.1, z_top + 0.03, depth + 0.06)
    rod2 = room.point(wall, s1 + 0.1, z_top + 0.03, depth + 0.06)
    tube("curtain-rod", [tuple(rod), tuple(rod2)], 0.01, black_metal(), bezier=False)
    return obj


def basket(loc, r, h, rgb=(186, 152, 108)):
    x, y, z = loc
    weave = woven(rgb)
    obj = lathe("basket", [(0.0, 0.0), (r * 0.9, 0.0), (r, h), (r * 0.96, h), (r * 0.86, 0.02), (0.0, 0.02)], loc,
                weave, sub=0)
    tube("basket-rim", [(x + (r - 0.006) * math.cos(t), y + (r - 0.006) * math.sin(t), z + h)
                        for t in [2 * math.pi * k / 48 for k in range(49)]], 0.009, weave, bezier=False)
    return obj


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
