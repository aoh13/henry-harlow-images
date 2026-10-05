"""Scene kit for the room renders: render settings, daylight, materials,
primitives, the room shell and the tiler.

Units are metres; tile sizes come in inches and go through INCH. Runs inside
Blender's Python (`pip install bpy`).
"""

import json
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector

INCH = 0.0254


# --- scene ----------------------------------------------------------------

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()  # cached materials belonged to the scene just discarded


def setup_render(width=1000, height=1500, samples=192, exposure=0.0, look="AgX - Medium High Contrast"):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.015
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = 10
    sc.cycles.diffuse_bounces = 5
    sc.cycles.glossy_bounces = 5
    sc.cycles.transmission_bounces = 10
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.sample_clamp_indirect = 8
    sc.cycles.blur_glossy = 1.0
    sc.render.resolution_x, sc.render.resolution_y = width, height
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = look
    sc.view_settings.exposure = exposure
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_depth = "8"
    return sc


def daylight(sun_elevation=35, sun_azimuth=210, sky_strength=0.35, sun_strength=4.0, sun_angle=1.2):
    """Physical sky plus a matching sun lamp (cleaner than the sky's own disc).

    Azimuth is measured from +X towards +Y, in degrees: light travels from
    that direction into the scene."""
    world = bpy.data.worlds.new("sky")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_disc = False
    sky.sun_elevation = math.radians(sun_elevation)
    sky.sun_rotation = math.radians(sun_azimuth - 90)
    sky.air_density, sky.dust_density = 1.0, 1.5
    bg = nt.nodes["Background"]
    bg.inputs["Strength"].default_value = sky_strength
    nt.links.new(sky.outputs[0], bg.inputs[0])

    data = bpy.data.lights.new("sun", "SUN")
    data.energy = sun_strength
    data.angle = math.radians(sun_angle)
    data.color = (1.0, 0.95, 0.88)
    sun = bpy.data.objects.new("sun", data)
    bpy.context.collection.objects.link(sun)
    el, az = math.radians(sun_elevation), math.radians(sun_azimuth)
    towards = Vector((-math.cos(el) * math.cos(az), -math.cos(el) * math.sin(az), -math.sin(el)))
    sun.rotation_euler = towards.to_track_quat("-Z", "Y").to_euler()
    return sun


def area_light(name, loc, size, energy, aim_at, color=(1, 0.97, 0.92), portal=False, visible=False):
    data = bpy.data.lights.new(name, "AREA")
    data.shape = "RECTANGLE"
    data.size, data.size_y = size
    data.energy = energy
    data.color = color
    data.cycles.is_portal = portal
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = (Vector(aim_at) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    obj.visible_camera = visible
    obj.visible_glossy = visible  # fill lights must not show up in mirrors and polished stone
    return obj


def point_light(name, loc, energy, radius=0.03, color=(1.0, 0.82, 0.6)):
    data = bpy.data.lights.new(name, "POINT")
    data.energy = energy
    data.shadow_soft_size = radius
    data.color = color
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    return obj


def camera(loc, look_at, lens=26, shift_x=0.0, shift_y=0.0, level=True):
    """A camera at eye level; `level` keeps verticals straight by aiming
    horizontally and framing with lens shift, as architectural cameras do."""
    data = bpy.data.cameras.new("cam")
    data.lens = lens
    data.sensor_width = 36
    data.sensor_fit = "AUTO"
    data.shift_x, data.shift_y = shift_x, shift_y
    data.clip_start = 0.05
    obj = bpy.data.objects.new("cam", data)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    target = Vector(look_at)
    if level:
        target.z = obj.location.z
    obj.rotation_euler = (target - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = obj
    return obj


def render(path):
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


# --- materials ------------------------------------------------------------

_mats = {}


def _principled(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m, m.node_tree, m.node_tree.nodes["Principled BSDF"]


def srgb(rgb):
    """0-255 sRGB to linear RGBA."""
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (lin(rgb[0]), lin(rgb[1]), lin(rgb[2]), 1.0)


def mat(name, rgb, rough=0.5, metal=0.0, coat=0.0, sheen=0.0, bump=0.0, bump_scale=60.0,
        transmission=0.0, ior=1.45, emission=0.0, alpha=1.0, subsurface=0.0):
    key = (name, rgb, rough, metal, coat, sheen, bump, transmission, emission)
    if key in _mats:
        return _mats[key]
    m, nt, p = _principled(name)
    p.inputs["Base Color"].default_value = srgb(rgb)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["Coat Weight"].default_value = coat
    p.inputs["Sheen Weight"].default_value = sheen
    p.inputs["Transmission Weight"].default_value = transmission
    p.inputs["IOR"].default_value = ior
    p.inputs["Subsurface Weight"].default_value = subsurface
    if emission:
        p.inputs["Emission Color"].default_value = srgb(rgb)
        p.inputs["Emission Strength"].default_value = emission
    if alpha < 1:
        p.inputs["Alpha"].default_value = alpha
    if bump:
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = bump_scale
        noise.inputs["Detail"].default_value = 8
        b = nt.nodes.new("ShaderNodeBump")
        b.inputs["Strength"].default_value = bump
        b.inputs["Distance"].default_value = 0.002
        nt.links.new(noise.outputs["Fac"], b.inputs["Height"])
        nt.links.new(b.outputs["Normal"], p.inputs["Normal"])
    _mats[key] = m
    return m


def plaster(rgb, rough=0.85, variation=0.05, name="plaster"):
    """Limewash-style wall: soft tonal clouds and a fine trowelled bump."""
    m, nt, p = _principled(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1.6
    noise.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    lo = tuple(max(0, c - c * variation) for c in rgb)
    hi = tuple(min(255, c + (255 - c) * variation * 0.6) for c in rgb)
    ramp.color_ramp.elements[0].color = srgb(lo)
    ramp.color_ramp.elements[1].color = srgb(hi)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = rough
    fine = nt.nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 35
    fine.inputs["Detail"].default_value = 10
    nt.links.new(tc.outputs["Object"], fine.inputs["Vector"])
    b = nt.nodes.new("ShaderNodeBump")
    b.inputs["Strength"].default_value = 0.08
    nt.links.new(fine.outputs["Fac"], b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], p.inputs["Normal"])
    return m


def wood(light=(196, 152, 104), dark=(132, 92, 58), rough=0.5, name="wood"):
    """Rift-cut timber with its grain along the object's X axis: fine streaks
    of irregular spacing, stretched along the grain, over broad tone shifts."""
    m, nt, p = _principled(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")

    def stretched(sx, syz):
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (sx, syz, syz)
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
        return mp

    grain = nt.nodes.new("ShaderNodeTexNoise")
    grain.inputs["Scale"].default_value = 1.0
    grain.inputs["Detail"].default_value = 10
    grain.inputs["Roughness"].default_value = 0.62
    nt.links.new(stretched(0.6, 90.0).outputs["Vector"], grain.inputs["Vector"])
    tone = nt.nodes.new("ShaderNodeTexNoise")
    tone.inputs["Scale"].default_value = 1.0
    tone.inputs["Detail"].default_value = 3
    nt.links.new(stretched(0.8, 6.0).outputs["Vector"], tone.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "FLOAT"
    mix.inputs["Factor"].default_value = 0.4
    nt.links.new(grain.outputs["Fac"], mix.inputs["A"])
    nt.links.new(tone.outputs["Fac"], mix.inputs["B"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = srgb(dark)
    ramp.color_ramp.elements[1].color = srgb(light)
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[1].position = 0.62
    nt.links.new(mix.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = rough
    b = nt.nodes.new("ShaderNodeBump")
    b.inputs["Strength"].default_value = 0.03
    nt.links.new(grain.outputs["Fac"], b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], p.inputs["Normal"])
    return m


def image_mat(name, path, rough=0.6, emission=0.0):
    m, nt, p = _principled(name)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(path))
    tex.interpolation = "Cubic"
    nt.links.new(tex.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = rough
    if emission:
        nt.links.new(tex.outputs["Color"], p.inputs["Emission Color"])
        p.inputs["Emission Strength"].default_value = emission
    return m


FINISH = {  # roughness, bump strength, sheen of the stone face
    "polished": (0.06, 0.02),
    "honed": (0.32, 0.04),
    "brushed": (0.55, 0.12),
    "tumbled": (0.5, 0.1),
    "cleft": (0.6, 0.22),
}


def tile_mat(meta, atlas_path):
    """The stone: the product photo as colour, its own detail as relief."""
    rough, bump = FINISH[meta["finish"]]
    m, nt, p = _principled("tile-" + meta["handle"][:40])
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(atlas_path))
    tex.interpolation = "Cubic"
    tex.extension = "EXTEND"
    nt.links.new(tex.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = rough
    if meta["finish"] in ("polished", "honed"):
        p.inputs["Coat Weight"].default_value = 0.35 if meta["finish"] == "polished" else 0.0
        p.inputs["Coat Roughness"].default_value = 0.04
    else:  # rough stone: sheen varies with the stone's own tone
        rr = nt.nodes.new("ShaderNodeMapRange")
        rr.inputs["To Min"].default_value = rough - 0.15
        rr.inputs["To Max"].default_value = rough + 0.15
        nt.links.new(tex.outputs["Color"], rr.inputs["Value"])
        nt.links.new(rr.outputs["Result"], p.inputs["Roughness"])
    b = nt.nodes.new("ShaderNodeBump")
    b.inputs["Strength"].default_value = bump
    b.inputs["Distance"].default_value = 0.0015
    nt.links.new(tex.outputs["Color"], b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], p.inputs["Normal"])
    return m


# --- primitives -----------------------------------------------------------

def _link(obj):
    bpy.context.collection.objects.link(obj)
    return obj


def mesh_obj(name, verts, faces, material=None, smooth=False, uvs=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    if uvs is not None:
        layer = me.uv_layers.new(name="UVMap")
        i = 0
        for poly in me.polygons:
            for li in poly.loop_indices:
                layer.data[li].uv = uvs[i]
                i += 1
    me.validate()
    if smooth:
        me.shade_smooth()
    obj = _link(bpy.data.objects.new(name, me))
    if material:
        obj.data.materials.append(material)
    return obj


def bevel(obj, width, segments=3, angle=40, harden=True):
    mod = obj.modifiers.new("bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(angle)
    mod.harden_normals = harden
    if harden:
        obj.data.shade_smooth()
    return obj


def subsurf(obj, levels=2):
    mod = obj.modifiers.new("subd", "SUBSURF")
    mod.levels = mod.render_levels = levels
    obj.data.shade_smooth()
    return obj


def box(name, size, loc, material=None, rot_z=0.0, round_=0.002, segments=3):
    """A box of true size (x, y, z), centred on loc in x/y, sitting on loc.z."""
    sx, sy, sz = size
    v = [(x * sx / 2, y * sy / 2, z * sz) for z in (0, 1) for y in (-1, 1) for x in (-1, 1)]
    f = [(2, 3, 1, 0), (5, 7, 6, 4), (1, 5, 4, 0), (6, 7, 3, 2), (4, 6, 2, 0), (3, 7, 5, 1)]  # outward
    obj = mesh_obj(name, v, f, material)
    obj.location = loc
    obj.rotation_euler.z = rot_z
    if round_:
        bevel(obj, round_, segments)
    return obj


def lathe(name, profile, loc, material=None, steps=72, smooth=True, sub=1):
    """Spin a (radius, height) profile around Z: vases, bowls, sinks, lamps."""
    verts = [(r, 0, z) for r, z in profile]
    edges = [(i, i + 1) for i in range(len(verts) - 1)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, edges, [])
    obj = _link(bpy.data.objects.new(name, me))
    mod = obj.modifiers.new("screw", "SCREW")
    mod.angle = 2 * math.pi
    mod.steps = mod.render_steps = steps
    mod.axis = "Z"
    mod.use_merge_vertices = True
    mod.use_smooth_shade = smooth
    mod.use_normal_calculate = True
    if sub:
        subsurf(obj, sub)
    obj.location = loc
    if material:
        obj.data.materials.append(material)
    return obj


def tube(name, points, radius, material=None, resolution=6, bezier=True, caps=True):
    """A rod along points: pipes, faucets, rails, stems, legs."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = resolution
    cu.use_fill_caps = caps
    if bezier:
        sp = cu.splines.new("BEZIER")
        sp.bezier_points.add(len(points) - 1)
        for bp, p in zip(sp.bezier_points, points):
            bp.co = p
            bp.handle_left_type = bp.handle_right_type = "AUTO"
    else:
        sp = cu.splines.new("POLY")
        sp.points.add(len(points) - 1)
        for pt, p in zip(sp.points, points):
            pt.co = (*p, 1)
    obj = _link(bpy.data.objects.new(name, cu))
    if material:
        obj.data.materials.append(material)
    return obj


def cylinder(name, radius, height, loc, material=None, steps=64, round_=0.001, rot=(0, 0, 0)):
    v, f = [], []
    for z in (0, height):
        for i in range(steps):
            a = 2 * math.pi * i / steps
            v.append((radius * math.cos(a), radius * math.sin(a), z))
    f.append(tuple(range(steps))[::-1])
    f.append(tuple(range(steps, 2 * steps)))
    for i in range(steps):
        j = (i + 1) % steps
        f.append((i, j, steps + j, steps + i))
    obj = mesh_obj(name, v, f, material)
    obj.location = loc
    obj.rotation_euler = rot
    if round_:
        bevel(obj, round_, 2, angle=60)
    else:
        obj.data.shade_smooth()
    return obj



def quad(name, centre, u, v, w, h, material=None):
    """A flat rectangle spanning u (width) and v (height) around centre."""
    c = Vector(centre)
    pts = [c - u * (w / 2) - v * (h / 2), c + u * (w / 2) - v * (h / 2),
           c + u * (w / 2) + v * (h / 2), c - u * (w / 2) + v * (h / 2)]
    return mesh_obj(name, pts, [(0, 1, 2, 3)], material, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])


def boolean_cut(target, cutter):
    mod = target.modifiers.new("cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.solver = "EXACT"
    cutter.hide_render = True
    cutter.hide_viewport = True
    return target


# --- room shell -----------------------------------------------------------

class Room:
    """A rectangular room: interior x in [0, w], y in [0, d], z in [0, h].

    Walls are named by where they stand: back (y = d), left (x = 0),
    right (x = w), front (y = 0, behind the camera)."""

    T = 0.15  # wall thickness

    def __init__(self, w, d, h):
        self.w, self.d, self.h = w, d, h
        self.walls = {}
        self.openings = []

    def frame(self, wall):
        """(origin, u, v): u runs along the wall seen from inside, v is up."""
        w, d = self.w, self.d
        up = Vector((0, 0, 1))
        return {
            "back": (Vector((0, d, 0)), Vector((1, 0, 0)), up),
            "left": (Vector((0, 0, 0)), Vector((0, 1, 0)), up),
            "right": (Vector((w, d, 0)), Vector((0, -1, 0)), up),
            "front": (Vector((w, 0, 0)), Vector((-1, 0, 0)), up),
            "floor": (Vector((0, 0, 0)), Vector((1, 0, 0)), Vector((0, 1, 0))),
        }[wall]

    def length(self, wall):
        return self.w if wall in ("back", "front") else self.d

    def point(self, wall, s, t, out=0.0):
        o, u, v = self.frame(wall)
        n = u.cross(v)
        return o + u * s + v * t + n * out

    def build(self, wall_mats, floor_mat=None, ceiling_mat=None):
        T, w, d, h = self.T, self.w, self.d, self.h
        specs = {
            "back": ((w + 2 * T, T, h + 2 * T), (w / 2, d + T / 2, -T)),
            "front": ((w + 2 * T, T, h + 2 * T), (w / 2, -T / 2, -T)),
            "left": ((T, d, h + 2 * T), (-T / 2, d / 2, -T)),
            "right": ((T, d, h + 2 * T), (w + T / 2, d / 2, -T)),
        }
        for name, (size, loc) in specs.items():
            m = wall_mats.get(name, wall_mats.get("default"))
            self.walls[name] = box("wall-" + name, size, loc, m, round_=0)
        if floor_mat:
            box("floor", (w + 2 * T, d + 2 * T, T), (w / 2, d / 2, -T), floor_mat, round_=0)
        box("ceiling", (w + 2 * T, d + 2 * T, T), (w / 2, d / 2, h), ceiling_mat or wall_mats.get("default"),
            round_=0)

    def window(self, wall, s0, s1, z0, z1, frame_mat, mullions=(1, 1), sill_mat=None, frame_w=0.05,
               backdrop=None, backdrop_strength=1.0, portal=True):
        """An opening with frame, glazing bars, glass, a portal light and,
        optionally, a blurred garden outside."""
        o, u, v = self.frame(wall)
        n = u.cross(v)
        T = self.T
        centre = o + u * ((s0 + s1) / 2) + v * ((z0 + z1) / 2) - n * (T / 2)
        ww, hh = s1 - s0, z1 - z0
        cutter = box("cut", (ww, 1.0, hh), (0, 0, 0), round_=0)
        cutter.location = centre - v * (hh / 2)
        cutter.rotation_euler = n.to_track_quat("Y", "Z").to_euler()
        boolean_cut(self.walls[wall], cutter)
        rot = n.to_track_quat("Y", "Z").to_euler()
        depth = 0.06
        pos = centre - n * (T / 2 - depth)

        def bar(name, size, offset_u, offset_v):
            b = box(name, size, (0, 0, 0), frame_mat, round_=0.002)
            b.rotation_euler = rot
            b.location = pos + u * offset_u + v * (offset_v - size[2] / 2)
            return b

        bar("frame-l", (frame_w, depth, hh), -ww / 2 + frame_w / 2, 0)
        bar("frame-r", (frame_w, depth, hh), ww / 2 - frame_w / 2, 0)
        bar("frame-t", (ww, depth, frame_w), 0, hh / 2 - frame_w / 2)
        bar("frame-b", (ww, depth, frame_w), 0, -hh / 2 + frame_w / 2)
        cols, rows = mullions
        for i in range(1, cols):
            bar(f"mull-v{i}", (frame_w * 0.45, depth * 0.8, hh), -ww / 2 + ww * i / cols, 0)
        for j in range(1, rows):
            bar(f"mull-h{j}", (ww, depth * 0.8, frame_w * 0.45), 0, -hh / 2 + hh * j / rows)
        pane = quad("glass", pos, u, v, ww, hh, mat("glass", (255, 255, 255), rough=0.0, transmission=1.0, ior=1.45))
        pane.visible_shadow = False  # thin glazing: let the sun through without caustics
        if sill_mat:
            sill = box("sill", (ww + 0.08, T * 0.5 + 0.03, 0.03), (0, 0, 0), sill_mat, round_=0.003)
            sill.rotation_euler = rot
            sill.location = o + u * ((s0 + s1) / 2) + v * (z0 - 0.03) + n * 0.015
        if portal:
            area_light("portal", tuple(centre - n * (T / 2 + 0.01)), (ww, hh), 1.0,
                       tuple(centre + n * 2), portal=True)
        if backdrop:
            bd = quad("garden", centre - n * 6.0, u, v, ww * 5, hh * 4,
                      image_mat("garden", backdrop, emission=backdrop_strength))
            bd.visible_shadow = False
            bd.visible_diffuse = False
        self.openings.append((wall, s0, s1, z0, z1))

    def baseboard(self, walls, height, material, depth=0.015):
        for wall in walls:
            L = self.length(wall)
            b = box("base-" + wall, (L, depth, height), (0, 0, 0), material, round_=0.002)
            o, u, v = self.frame(wall)
            n = u.cross(v)
            b.rotation_euler = n.to_track_quat("Y", "Z").to_euler()
            b.location = o + u * (L / 2) + n * (depth / 2)


# --- tiler ----------------------------------------------------------------

def _clip(poly, x0, y0, x1, y1):
    """Sutherland-Hodgman clip of a convex polygon to a rectangle."""
    def clip_edge(pts, inside, cross):
        out = []
        for i, p in enumerate(pts):
            q = pts[i - 1]
            if inside(p):
                if not inside(q):
                    out.append(cross(q, p))
                out.append(p)
            elif inside(q):
                out.append(cross(q, p))
        return out

    def at_x(x):
        return lambda a, b: (x, a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]))

    def at_y(y):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]), y)

    for inside, cross in ((lambda p: p[0] >= x0, at_x(x0)), (lambda p: p[0] <= x1, at_x(x1)),
                          (lambda p: p[1] >= y0, at_y(y0)), (lambda p: p[1] <= y1, at_y(y1))):
        poly = clip_edge(poly, inside, cross)
        if not poly:
            return []
    return poly


def layout(width, height, tw, th, joint, pattern="grid", angle=0.0, offset=(0.0, 0.0)):
    """Tile rectangles covering [0, width] x [0, height].

    Yields (origin, ax, ay, w, h): a tile's corner and its unit axes in the
    region plane. Patterns: grid (stacked), running (half bond), third
    (one-third offset), herringbone (90 degree)."""
    ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))

    def rot(p):
        return (p[0] * ca - p[1] * sa, p[0] * sa + p[1] * ca)

    def place(x, y, w, h, vertical=False):
        """(x, y) is the tile's lower-left corner before rotation. A vertical
        tile keeps its long axis as its own x so the photo turns with it."""
        if vertical:
            origin, ax, ay = (x + h, y), (0.0, 1.0), (-1.0, 0.0)
        else:
            origin, ax, ay = (x, y), (1.0, 0.0), (0.0, 1.0)
        return rot((origin[0] + offset[0], origin[1] + offset[1])), rot(ax), rot(ay), w, h

    reach = math.hypot(width, height) + 2 * (tw + th)
    if pattern == "herringbone":
        s = th + joint
        L = tw + joint
        n = int(reach / s) + 4
        m = int(reach / L) + 4
        for k in range(-m, m + 1):
            bx, by = k * L, -k * L
            for i in range(-n, n + 1):
                x, y = bx + i * s, by + i * s
                yield place(x, y, tw, th)
                yield place(x, y + s, tw, th, vertical=True)
        return
    stepx, stepy = tw + joint, th + joint
    nx, ny = int(reach / stepx) + 2, int(reach / stepy) + 2
    for j in range(-ny, ny + 1):
        shift = {"grid": 0, "running": 0.5, "third": 1 / 3}[pattern] * (j % (2 if pattern == "running" else 3))
        for i in range(-nx, nx + 1):
            yield place((i + shift) * stepx, j * stepy, tw, th)


def tile_surface(name, room, wall, s0, s1, t0, t1, meta, atlas_path, pattern="grid", angle=0.0,
                 offset=(0.0, 0.0), seed=1, thickness=0.375 * INCH, lift=0.0, grout_recess=0.0025,
                 edge=None, lippage=None, material=None):
    """Lay real-size tiles over a rectangle of a wall or the floor.

    Every tile is its own slab, cut where it meets the edge of the area, with
    a joint of the product's grout width. Each tile takes one stone piece from
    the atlas and is turned, never flipped, as a real installer would lay it."""
    rnd = random.Random(seed)
    o, u, v = room.frame(wall)
    n = u.cross(v)
    base = o + u * s0 + v * t0 + n * lift
    W, H = s1 - s0, t1 - t0
    tw, th = meta["chip"][0] * INCH, meta["chip"][1] * INCH
    joint = meta["grout"] * INCH
    cells = meta["uv_cells"]
    square = abs(tw - th) < 1e-6
    rough_stone = meta["finish"] in ("cleft", "tumbled", "brushed")
    if edge is None:
        edge = (1 / 16 if rough_stone else 1 / 64) * INCH
    if lippage is None:
        lippage = 0.0006 if rough_stone else 0.00015

    verts, faces, uvs = [], [], []
    count = 0
    for (px, py), ax, ay, w, h in layout(W, H, tw, th, joint, pattern, angle, offset):
        corners = [(px, py), (px + ax[0] * w, py + ax[1] * w),
                   (px + ax[0] * w + ay[0] * h, py + ax[1] * w + ay[1] * h), (px + ay[0] * h, py + ay[1] * h)]
        poly = _clip(corners, 0, 0, W, H)
        if len(poly) < 3:
            continue
        area = 0.5 * abs(sum(poly[i][0] * poly[i - 1][1] - poly[i - 1][0] * poly[i][1] for i in range(len(poly))))
        if area < 1e-6:
            continue
        count += 1
        cx, cy, cw, ch = cells[rnd.randrange(len(cells))]
        if len(cells) > 1:  # several photographed pieces: any piece, any way up
            turn = rnd.choice((0, 2) if not square else (0, 1, 2, 3))
        else:
            # one photo: turn neighbours a quarter (squares) or by row (oblongs),
            # so no tile sits next to its own copy or its own half-turn
            mx = px + ax[0] * w / 2 + ay[0] * h / 2
            my = py + ax[1] * w / 2 + ay[1] * h / 2
            i = math.floor((mx * ax[0] + my * ax[1]) / (w + joint) + 1e-6)
            j = math.floor((mx * ay[0] + my * ay[1]) / (h + joint) + 1e-6)
            turn = (i + j) % 4 if square else 2 * (j % 2)
        top = thickness + rnd.uniform(-lippage, lippage)
        tilt = (rnd.uniform(-1, 1) * lippage / w, rnd.uniform(-1, 1) * lippage / h)

        def tile_uv(x, y):
            a = ((x - px) * ax[0] + (y - py) * ax[1]) / w
            b = ((x - px) * ay[0] + (y - py) * ay[1]) / h
            for _ in range(turn):  # tiles are turned, never flipped: the face only goes one way up
                a, b = b, 1 - a
            return (cx + min(max(a, 0), 1) * cw, cy + min(max(b, 0), 1) * ch)

        k = len(verts)
        m = len(poly)
        for x, y in poly:
            a = ((x - px) * ax[0] + (y - py) * ax[1]) - w / 2
            b = ((x - px) * ay[0] + (y - py) * ay[1]) - h / 2
            z = top + a * tilt[0] + b * tilt[1]
            verts.append(base + u * x + v * y + n * z)
        for x, y in poly:
            verts.append(base + u * x + v * y)
        faces.append(tuple(range(k, k + m)))
        uvs += [tile_uv(x, y) for x, y in poly]
        for i in range(m):
            j = (i + 1) % m
            faces.append((k + j, k + i, k + m + i, k + m + j))
            uvs += [tile_uv(*poly[j]), tile_uv(*poly[i]), tile_uv(*poly[i]), tile_uv(*poly[j])]

    obj = mesh_obj(name, verts, faces, material or tile_mat(meta, atlas_path), uvs=uvs)
    # flat shading: harden_normals on thousands of small tilted n-gons smears dark streaks
    bevel(obj, edge, segments=2 if edge < 0.001 else 3, angle=50, harden=False)
    obj.data.shade_flat()
    grout = mat("grout-" + meta["handle"][:20], tuple(meta["grout_rgb"]), rough=0.92, bump=0.3, bump_scale=900)
    g = mesh_obj(name + "-grout",
                 [base + n * (thickness - grout_recess), base + u * W + n * (thickness - grout_recess),
                  base + u * W + v * H + n * (thickness - grout_recess), base + v * H + n * (thickness - grout_recess)],
                 [(0, 1, 2, 3)], grout)
    obj["tiles"] = count
    return obj


def load_atlas(atlas_dir, handle):
    meta = json.loads((Path(atlas_dir) / f"{handle}.json").read_text())
    return meta, Path(atlas_dir) / f"{handle}.png"
