"""TieRZ 0.18.1 - native reroute bundles for unmodified Blender.

Single-file build. The original modules (i18n, data, clipboard, geometry,
sockets, selection, transforms, routing, rendering, preferences,
interaction, ui) live here; every top-level name carries its module
name as a prefix so the merged namespace stays unambiguous.
"""



# ==========================================================================
# module: i18n
# ==========================================================================

"""Small, file-based translation loader for the TieRZ interface."""
import json
import os

import bpy


i18n_DOMAIN = "TieRZ"
i18n_I18N_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "i18n")
i18n_LANGUAGE_NAMES = {"en_US": "English", "ko_KR": "한국어"}
i18n_LOCALE_CODES = {
    "en_US", "en", "ko_KR", "ko", "ja_JP", "ja", "zh_CN", "zh",
    "zh_TW", "es_ES", "es", "fr_FR", "fr", "de_DE", "de", "ru_RU",
    "ru", "vi_VN", "vi", "pt_BR", "pt_PT", "it_IT", "nl_NL", "pl_PL",
    "DEFAULT",
}


def i18n_language_items():
    items = [('AUTO', "Auto (Follow Blender)", "Use Korean when Blender is in Korean; otherwise use English")]
    if os.path.isdir(i18n_I18N_DIR):
        for filename in sorted(os.listdir(i18n_I18N_DIR)):
            if filename.endswith('.json'):
                code = filename[:-5]
                items.append((code, i18n_LANGUAGE_NAMES.get(code, code), f"Use {i18n_LANGUAGE_NAMES.get(code, code)}"))
    return items


def i18n__available_languages():
    if not os.path.isdir(i18n_I18N_DIR):
        return {}
    languages = {}
    for filename in sorted(os.listdir(i18n_I18N_DIR)):
        if filename.endswith('.json'):
            code = filename[:-5]
            languages[code] = i18n__read_language(code)
    return languages


def i18n__read_language(code):
    path = os.path.join(i18n_I18N_DIR, code + '.json')
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            table = json.load(handle)
        return table if isinstance(table, dict) else {}
    except (OSError, ValueError) as exc:
        print(f"[TieRZ] Could not load translation file {path}: {exc}")
        return {}


def i18n__as_context_table(entries):
    return {
        (context, source): translated
        for source, translated in entries.items()
        for context in (i18n_DOMAIN, '*', '')
    }


def i18n__system_language():
    try:
        language = bpy.context.preferences.view.language
    except Exception:
        language = 'en_US'
    return language


def i18n__matching_language(locale, available):
    if locale in available:
        return locale
    short_code = locale.split('_', 1)[0]
    return next((code for code in available if code.split('_', 1)[0] == short_code), 'en_US')


def i18n_tr(source):
    """Translate a dynamic UI string using TieRZ's registered context."""
    try:
        return bpy.app.translations.pgettext(source, i18n_DOMAIN)
    except Exception:
        return source


def i18n_register(language_mode='AUTO'):
    i18n_unregister()
    available = i18n__available_languages()
    english = available.get('en_US', {})
    if not english and not available:
        return

    current_locale = i18n__system_language()
    locales = set(i18n_LOCALE_CODES)
    locales.update({current_locale, current_locale.split('_', 1)[0]})

    if language_mode == 'AUTO':
        # Keep per-locale mappings so Auto follows Blender if the UI language
        # changes while the add-on remains enabled. New JSON files are picked
        # up automatically by locale code.
        translations = {}
        for locale in locales:
            code = i18n__matching_language(locale, available)
            target = {**english, **available.get(code, {})}
            if target:
                translations[locale] = i18n__as_context_table(target)
    else:
        code = language_mode
        if code not in available:
            short_code = code.split('_', 1)[0]
            code = next((item for item in available if item.split('_', 1)[0] == short_code), 'en_US')
        target = {**english, **available.get(code, {})}
        table = i18n__as_context_table(target or english)
        # An explicit choice overrides Blender's current interface language.
        locales.update({code, code.split('_', 1)[0]})
        translations = {locale: table for locale in locales}

    try:
        bpy.app.translations.register(__name__, translations)
    except Exception as exc:
        print(f"[TieRZ] Could not register translations: {exc}")


def i18n_unregister():
    try:
        bpy.app.translations.unregister(__name__)
    except Exception:
        pass


def i18n_update_language(_self, context):
    language_mode = getattr(_self, 'language_mode', 'AUTO')
    i18n_register(language_mode)
    wm = getattr(context, 'window_manager', None)
    for window in getattr(wm, 'windows', ()):
        for area in window.screen.areas:
            area.tag_redraw()


# ==========================================================================
# module: data
# ==========================================================================

"""Versioned tie storage, with stable logical connections through managed reroutes."""
import json
import math
import uuid

data_KEY = '_TieRZ_v1'
data_NODE_ID = '_TieRZ_uuid'


def data_color_srgb_to_linear(color):
    """Tie colors are stored/rendered as display sRGB; COLOR properties are scene-linear."""
    def channel(value):
        value = max(0.0, min(1.0, float(value)))
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
    return (channel(color[0]), channel(color[1]), channel(color[2]),
            max(0.0, min(1.0, float(color[3]))))


def data_color_linear_to_srgb(color):
    """Convert a scene-linear COLOR property back to the display sRGB tie color."""
    def channel(value):
        value = max(0.0, min(1.0, float(value)))
        return value * 12.92 if value <= 0.0031308 else 1.055 * value ** (1.0 / 2.4) - 0.055
    return (channel(color[0]), channel(color[1]), channel(color[2]),
            max(0.0, min(1.0, float(color[3]))))


def data_uid(node, create=False):
    value = node.get(data_NODE_ID, '')
    if not value and create:
        value = uuid.uuid4().hex
        node[data_NODE_ID] = value
    return value


def data_physical_key(link, create=False):
    # JSON encoding prevents collisions for custom socket identifiers with punctuation.
    return json.dumps([data_uid(link.from_node, create), link.from_socket.identifier,
                       data_uid(link.to_node, create), link.to_socket.identifier], separators=(',', ':'))


def data_link_key(link, create=False):
    if create:
        data_uid(link.from_node, True)
        data_uid(link.to_node, True)
    return routing_connection_key(link)


def data_read(tree):
    try:
        raw = json.loads(tree.get(data_KEY, '{}'))
        if raw.get('version') != 1:
            return []
        result = []
        seen = set()
        for t in raw.get('ties', []):
            if (not isinstance(t, dict) or not isinstance(t.get('id'), str) or t['id'] in seen or
                len(t.get('pos', [])) != 2 or not all(isinstance(v, (int,float)) and math.isfinite(v) for v in t['pos']) or
                not isinstance(t.get('angle'), (float,int)) or not math.isfinite(t['angle']) or
                not isinstance(t.get('members'), list) or not t['members'] or
                not all(isinstance(k, str) for k in t['members'])):
                continue
            color = t.get('color', [.55,.55,.58,1])
            if (not isinstance(color,(list,tuple)) or len(color) != 4 or
                    not all(isinstance(v,(int,float)) and math.isfinite(v) for v in color)):
                color = [.55,.55,.58,1]
            t['color'] = [max(0.0, min(1.0, float(v))) for v in color]
            if 'name' in t:
                if isinstance(t['name'],str):
                    t['name'] = ' '.join(t['name'].split())[:128]
                else:
                    t.pop('name')
            if 'scale' in t:
                value = t['scale']
                t['scale'] = max(.1,min(20,value)) if isinstance(value,(int,float)) and math.isfinite(value) and value>0 else 1.0
            if 'spacing' in t:
                value = t['spacing']
                if isinstance(value,(int,float)) and math.isfinite(value) and value>0:
                    t['spacing'] = max(4.0,min(50.0,float(value)))
                else:
                    t.pop('spacing')
            t['members'] = list(dict.fromkeys(t['members']))
            seen.add(t['id'])
            result.append(t)
        return result
    except (ValueError, TypeError, AttributeError):
        return []


def data_write(tree, ties):
    spacing,width = routing_settings()
    routing_sync(tree,ties,spacing,width)
    tree[data_KEY] = json.dumps({'version': 1, 'ties': ties}, separators=(',', ':'), allow_nan=False)


def data_new_tie(pos, angle, keys, ties, color):
    twin = next((t for t in ties if set(keys) <= set(t['members'])), None)
    if twin:
        keys = sorted(keys, key=twin['members'].index)
    return dict(id=uuid.uuid4().hex, pos=list(pos), angle=angle, members=keys, color=list(color))


def data_prune(tree, ties):
    live = routing_live_keys(tree)
    for t in ties:
        t['members'] = [k for k in t['members'] if k in live]
    return [t for t in ties if t['members']]


def data_repair_duplicate_ids(tree):
    """Run only in explicit edits, never draw callbacks. Preserve original identity."""
    seen = set()
    for n in tree.nodes:
        value = data_uid(n, True)
        if value in seen:
            n[data_NODE_ID] = uuid.uuid4().hex
        seen.add(data_uid(n))


# ==========================================================================
# module: clipboard
# ==========================================================================

"""Explicit clipboard commands preserve ties in the same undo operation as nodes.

Uses Blender's clipboard for nodes. Tie metadata is session-local, and only applied
when pasted UUIDs match the corresponding copy. Ordinary Ctrl-C/V are untouched.
"""
import copy
import json
import uuid
import bpy

clipboard_payload = None


class TRZ_OT_copy(bpy.types.Operator):
    bl_idname = 'tie.rz_copy'
    bl_label = 'Copy Nodes with Ties'
    bl_description = 'Copy selected nodes and their associated tie routes; use Paste here to restore the ties'

    @classmethod
    def poll(cls,context):
        tree = rendering_tree_of(context)
        return bool(tree and tree.is_editable and any(n.select and not routing_managed(n) for n in tree.nodes))

    def execute(self,context):
        global clipboard_payload
        tree = rendering_tree_of(context)
        if not tree.is_editable:
            return {'CANCELLED'}
        data_repair_duplicate_ids(tree)
        chosen = {data_uid(n):tuple(n.location_absolute) for n in tree.nodes if n.select and not routing_managed(n)}
        ties = []
        for tie in data_read(tree):
            if all(json.loads(k)[0] in chosen and json.loads(k)[2] in chosen for k in tie['members']):
                ties.append(tie)
        original_selection = [(n,n.select) for n in tree.nodes]
        try:
            for n in tree.nodes:
                if routing_managed(n):
                    src,_,dst,_ = json.loads(n[routing_OWNER])
                    n.select = src in chosen and dst in chosen
            result = bpy.ops.node.clipboard_copy()
        finally:
            for node,selected in original_selection:
                node.select = selected
        if result == {'FINISHED'}:
            clipboard_payload = dict(nodes=chosen,ties=copy.deepcopy(ties))
        return result


class TRZ_OT_paste(bpy.types.Operator):
    bl_idname = 'tie.rz_paste'
    bl_label = 'Paste Nodes with Ties'
    bl_options = {'UNDO'}
    bl_description = 'Paste the nodes copied with this add-on, including their associated ties'

    @classmethod
    def poll(cls,context):
        tree = rendering_tree_of(context)
        return bool(tree and tree.is_editable and clipboard_payload)

    def execute(self,context):
        tree = rendering_tree_of(context)
        before = {n.as_pointer() for n in tree.nodes}
        result = bpy.ops.node.clipboard_paste()
        if result != {'FINISHED'}:
            return result
        pasted = [n for n in tree.nodes if n.as_pointer() not in before]
        mapping = {}
        offsets = []
        for n in pasted:
            old = data_uid(n)
            new = uuid.uuid4().hex
            n[data_NODE_ID] = new
            if clipboard_payload and old in clipboard_payload['nodes']:
                mapping[old] = new
                offsets.append(tuple(n.location_absolute[k]-clipboard_payload['nodes'][old][k] for k in (0,1)))
        if not clipboard_payload or not offsets:
            return result
        delta = offsets[0]
        if any(any(abs(o[k]-delta[k])>.01 for k in (0,1)) for o in offsets):
            return result
        tie_ids = {t['id']:uuid.uuid4().hex for t in clipboard_payload['ties']}
        for node in pasted:
            if not routing_managed(node):
                continue
            src,out,dst,inp = json.loads(node[routing_OWNER])
            if src in mapping and dst in mapping and node.get(routing_TIE) in tie_ids:
                node[routing_OWNER] = json.dumps([mapping[src],out,mapping[dst],inp],separators=(',',':'))
                node[routing_TIE] = tie_ids[node[routing_TIE]]
            else:
                for attr in (routing_OWNER,routing_TIE,routing_SLOT):
                    if attr in node:
                        del node[attr]
        ties = data_read(tree)
        live = routing_live_keys(tree)
        selected = selection_of(tree)
        selected.clear()
        for original in clipboard_payload['ties']:
            tie = copy.deepcopy(original)
            keys = []
            for key in tie['members']:
                src,out,dst,inp = json.loads(key)
                if src not in mapping or dst not in mapping:
                    break
                keys.append(json.dumps([mapping[src],out,mapping[dst],inp],separators=(',',':')))
            if len(keys) == len(tie['members']) and set(keys) <= live:
                tie['members'] = keys
                tie['id'] = tie_ids[original['id']]
                tie['pos'] = [tie['pos'][k]+delta[k] for k in (0,1)]
                ties.append(tie)
                selected.add(tie['id'])
        data_write(tree,ties)
        return result


clipboard_classes = [TRZ_OT_copy,TRZ_OT_paste]


# ==========================================================================
# module: geometry
# ==========================================================================

"""Pure geometry; coordinates are node-editor units, angles counterclockwise.

Routing and lane ordering adapted from comfyui-zip-ties (MIT), Safzan Pirani.
"""
from math import cos, sin, hypot, isfinite

geometry_MUSIC_NOTE_ASPECTS = (167/297,135/350,103/297,299/330,298/327)
geometry_MAX_STRAND_SPACING = 50.0
geometry_MIN_STRAND_SPACING = 4.0


def geometry_effective_spacing(tie, spacing):
    """Absolute noodle gap for one tie, in node-editor units.

    Cached `spacing` wins. Legacy ties store only a `scale` multiplier, so it is
    resolved against the global spacing and never mutates the stored data.
    """
    value = tie.get('spacing')
    if isinstance(value, (int, float)) and isfinite(value) and value > 0:
        return max(geometry_MIN_STRAND_SPACING, min(geometry_MAX_STRAND_SPACING, float(value)))
    legacy = max(.1, min(20.0, tie.get('scale', 1.0)))
    return max(geometry_MIN_STRAND_SPACING, min(geometry_MAX_STRAND_SPACING, max(float(spacing), 1e-6) * legacy))


def geometry_effective_scale(tie, spacing):
    """Gap ratio against the global spacing, kept for geometry that scales with it."""
    return geometry_effective_spacing(tie, spacing) / max(float(spacing), 1e-6)


def geometry_music_note_index(tie):
    value = tie.get('music_note')
    if isinstance(value,int) and 0 <= value < len(geometry_MUSIC_NOTE_ASPECTS):
        return value
    return sum((index+1)*ord(char) for index,char in enumerate(tie['id'])) % len(geometry_MUSIC_NOTE_ASPECTS)


def geometry_add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def geometry_sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def geometry_mul(a, n):
    return (a[0] * n, a[1] * n)


def geometry_dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def geometry_axes(angle):
    return (cos(angle), sin(angle)), (-sin(angle), cos(angle))


def geometry_lane(tie, key, spacing):
    tangent, normal = geometry_axes(tie['angle'])
    gap = geometry_effective_spacing(tie, spacing)
    offset = (tie['members'].index(key) - (len(tie['members']) - 1) / 2) * gap
    return geometry_add(tie['pos'], geometry_mul(normal, offset)), tangent


def geometry_sample(curve, count=48):
    a, b, c, d = curve
    result = []
    for i in range(count + 1):
        t = i / count
        u = 1 - t
        result.append(tuple(u**3*a[k] + 3*u*u*t*b[k] + 3*u*t*t*c[k] + t**3*d[k] for k in (0, 1)))
    return result


def geometry_intersection(p, q, r, s):
    u, v, w = geometry_sub(q, p), geometry_sub(s, r), geometry_sub(r, p)
    cross = lambda a, b: a[0]*b[1] - a[1]*b[0]
    den = cross(u, v)
    if abs(den) < 1e-10:
        return None
    t, j = cross(w, v)/den, cross(w, u)/den
    return t if 0 <= t <= 1 and 0 <= j <= 1 else None


def geometry__segment_distance_squared(p, q, a, b):
    """Squared distance between two finite segments."""
    if geometry_intersection(p, q, a, b) is not None:
        return 0.0
    def point_distance_squared(point, start, end):
        edge = geometry_sub(end, start)
        length = geometry_dot(edge, edge)
        t = max(0, min(1, geometry_dot(geometry_sub(point, start), edge) / length)) if length else 0
        delta = geometry_sub(point, geometry_add(start, geometry_mul(edge, t)))
        return geometry_dot(delta, delta)
    return min(point_distance_squared(p, a, b), point_distance_squared(q, a, b),
               point_distance_squared(a, p, q), point_distance_squared(b, p, q))


def geometry_curve_hit(p, q, curves, tolerance=0):
    hits = []
    for curve in curves:
        points = geometry_sample(curve)
        for a, b in zip(points, points[1:]):
            t = geometry_intersection(p, q, a, b)
            distance_squared = geometry__segment_distance_squared(p, q, a, b)
            if t is not None or (tolerance > 0 and distance_squared <= tolerance*tolerance):
                if t is None:
                    # Project the closest point on the sampled noodle onto the stroke
                    # so multiple crossed wires still retain a stable ordering.
                    edge = geometry_sub(q, p)
                    length = geometry_dot(edge, edge)
                    candidates = []
                    for point in (a, b):
                        u = max(0, min(1, geometry_dot(geometry_sub(point, p), edge)/length)) if length else 0
                        closest = geometry_add(p, geometry_mul(edge, u))
                        candidates.append((geometry_dot(geometry_sub(point, closest), geometry_sub(point, closest)), u))
                    t = min(candidates)[1]
                delta = geometry_sub(b, a)
                length = hypot(*delta) or 1
                hits.append((t, geometry_mul(delta, 1 / length)))
    return min(hits, key=lambda h: h[0]) if hits else None


def geometry_half_length(tie, spacing):
    gap = geometry_effective_spacing(tie, spacing)
    return (len(tie['members']) - 1) * gap / 2 + 3 * geometry_effective_scale(tie, spacing)


def geometry_marker(tie, spacing=4.5, width=5, style='ORIGINAL'):
    tangent, normal = geometry_axes(tie['angle'])
    h = geometry_half_length(tie, spacing)
    def transform(x, y):
        return geometry_add(tie['pos'], geometry_add(geometry_mul(tangent, x), geometry_mul(normal, y)))
    if style in {'MINIMAL','MACHOCAT'}:
        body = [transform(x,y) for x,y in [(-width*.34,-h),(width*.34,-h),
                (width*.34,h),(-width*.34,h)]]
        if style == 'MINIMAL':
            return [body]
        # Include the full image quad in hit/box/lasso selection.
        side = width*2.7
        center_y = h+width*.65
        face = [transform(x,y) for x,y in [
            (-side/2,center_y-side/2),(side/2,center_y-side/2),
            (side/2,center_y+side/2),(-side/2,center_y+side/2)]]
        return [body,face]
    if style == 'MUSIC':
        note_height = max(2*h+width*2.0,width*4.0)
        note_width = note_height*geometry_MUSIC_NOTE_ASPECTS[geometry_music_note_index(tie)]
        half_w,half_h = note_width/2,note_height/2
        return [[transform(x,y) for x,y in [(-half_w,-half_h),(half_w,-half_h),
                (half_w,half_h),(-half_w,half_h)]]]
    strap = [transform(x, y) for x, y in [(-width/2,-h),(width/2,-h),(width/2,h),(-width/2,h)]]
    collar = [transform(x,y) for x,y in [(-.67*width,h-.1*width),(.67*width,h-.1*width),
                                        (.67*width,h+.9*width),(-.67*width,h+.9*width)]]
    # Convex rounded-top flap. Positive normal is the locking-head end.
    left,right = -.47*width,.47*width
    bottom,top,radius = h+.05*width,h+1.7*width,.16*width
    tip = [(left,bottom),(right,bottom),(right,top-radius)]
    for i in range(1,7):
        angle = i/6*1.5707963267948966
        tip.append((right-radius+radius*cos(angle),top-radius+radius*sin(angle)))
    tip.append((left+radius,top))
    for i in range(1,7):
        angle = 1.5707963267948966+i/6*1.5707963267948966
        tip.append((left+radius+radius*cos(angle),top-radius+radius*sin(angle)))
    front = [(left,bottom),(right,bottom),(right,h+.55*width),(left,h+.55*width)]
    return strap,collar,[transform(x,y) for x,y in tip],[transform(x,y) for x,y in front]


def geometry_marker_hit(tie, p, spacing=4.5, width=5, pad=0, style='ORIGINAL'):
    for poly in geometry_marker(tie,spacing,width,style):
        signs = []
        for a,b in zip(poly,poly[1:]+poly[:1]):
            edge,d = geometry_sub(b,a),geometry_sub(p,a)
            signs.append(edge[0]*d[1]-edge[1]*d[0])
            if pad>0:
                length = geometry_dot(edge,edge)
                t = max(0,min(1,geometry_dot(d,edge)/length)) if length else 0
                closest = geometry_sub(p,geometry_add(a,geometry_mul(edge,t)))
                if geometry_dot(closest,closest)<=pad*pad:
                    return True
        if all(s>=-1e-8 for s in signs) or all(s<=1e-8 for s in signs):
            return True
    return False


def geometry_marker_cut(tie, p, q, spacing=4.5, width=5, style='ORIGINAL'):
    if geometry_marker_hit(tie, p, spacing, width, style=style) or geometry_marker_hit(tie, q, spacing, width, style=style):
        return True
    return any(geometry_intersection(p, q, a, b) is not None for poly in geometry_marker(tie, spacing, width, style)
               for a, b in zip(poly, poly[1:]+poly[:1]))


def geometry__point_in_polygon(point, polygon):
    x,y = point
    inside = False
    previous = polygon[-1]
    for current in polygon:
        x0,y0 = previous
        x1,y1 = current
        if (y0 > y) != (y1 > y) and x < (x1-x0)*(y-y0)/(y1-y0)+x0:
            inside = not inside
        previous = current
    return inside


def geometry_marker_overlaps_rect(tie,lo,hi,spacing=4.5,width=5,style='ORIGINAL'):
    """Return true for any overlap, including a box fully inside a marker."""
    corners = [tuple(lo),(hi[0],lo[1]),tuple(hi),(lo[0],hi[1])]
    rect_edges = list(zip(corners,corners[1:]+corners[:1]))
    for poly in geometry_marker(tie,spacing,width,style):
        if any(lo[0]<=p[0]<=hi[0] and lo[1]<=p[1]<=hi[1] for p in poly):
            return True
        if any(geometry__point_in_polygon(corner,poly) for corner in corners):
            return True
        if any(geometry_intersection(a,b,c,d) is not None
               for a,b in zip(poly,poly[1:]+poly[:1]) for c,d in rect_edges):
            return True
    return False


# ==========================================================================
# module: sockets
# ==========================================================================

"""Socket estimates and View2D conversion for standard Blender node editors."""


def sockets_socket_position(node, socket):
    p = node.location_absolute
    if node.bl_idname == 'NodeReroute':
        return tuple(p)
    if node.hide:
        return (p.x + (node.width if socket.is_output else 0), p.y - 15)
    visible = [s for s in (node.outputs if socket.is_output else node.inputs)
               if not s.hide and s.enabled and not s.is_unavailable]
    index = next((i for i,s in enumerate(visible) if s == socket), 0)
    # Custom node layouts, expanded values and panels invalidate this estimate.
    return (p.x + (node.width if socket.is_output else 0), p.y - 35 - 22*index)


def sockets_controls(link, context):
    a = sockets_socket_position(link.from_node, link.from_socket)
    b = sockets_socket_position(link.to_node, link.to_socket)
    curve = context.preferences.themes[0].node_editor.noodle_curving
    dx, dy = abs(b[0]-a[0]), abs(b[1]-a[1])
    offset = curve*.1*dx*min(1,dy/dx*(4.5-.25*curve)) if dx else 0
    if not curve:
        return [a, tuple(a[k]+(b[k]-a[k])/3 for k in (0,1)), tuple(a[k]+2*(b[k]-a[k])/3 for k in (0,1)), b]
    return [a,(a[0]+offset,a[1]),(b[0]-offset,b[1]),b]


def sockets_color(link, context):
    try:
        return tuple(link.from_socket.draw_color(context, link.from_node))
    except (AttributeError, TypeError):
        return (.65,.65,.65,1)


def sockets_to_view(context, point):
    scale = context.preferences.system.ui_scale
    return tuple(v / scale for v in sockets_window_region(context).view2d.region_to_view(*point))


def sockets_window_region(context):
    return next(r for r in context.area.regions if r.type == 'WINDOW')


def sockets_to_region(context, point):
    scale = context.preferences.system.ui_scale
    return sockets_window_region(context).view2d.view_to_region(point[0]*scale,point[1]*scale,clip=False)


# ==========================================================================
# module: selection
# ==========================================================================

"""Ephemeral selection is scoped to a node tree, independent of stored tie data."""
selection_selected = {}
selection_hovered = {}
selection_preview = {}  # area pointer -> (stroke start, end, cut IDs)
selection_boxes = {}
selection_sync_pending = set()
selection_circle_active = {}  # area pointer -> node tree pointer


def selection_of(tree):
    return selection_selected.setdefault(tree.as_pointer(), set())


def selection_clear():
    selection_selected.clear()
    selection_hovered.clear()
    selection_preview.clear()
    selection_boxes.clear()
    selection_sync_pending.clear()
    selection_circle_active.clear()


# ==========================================================================
# module: transforms
# ==========================================================================

"""Frozen guide geometry for tie sliding between immediate neighbours."""
from bisect import bisect_right
from math import hypot


def transforms_lengths(points):
    result = [0.0]
    for a,b in zip(points,points[1:]):
        result.append(result[-1]+hypot(*geometry_sub(b,a)))
    return result


def transforms_at_distance(points,cumulative,distance):
    distance = max(0,min(cumulative[-1],distance))
    i = min(len(points)-2,max(0,bisect_right(cumulative,distance)-1))
    span = cumulative[i+1]-cumulative[i]
    factor = (distance-cumulative[i])/span if span else 0
    return geometry_add(points[i],geometry_mul(geometry_sub(points[i+1],points[i]),factor))


def transforms_project(points,position):
    """Closest point on a frozen polyline; never extend past its endpoints."""
    best = None
    for a,b in zip(points,points[1:]):
        delta = geometry_sub(b,a)
        denom = geometry_dot(delta,delta)
        factor = max(0,min(1,geometry_dot(geometry_sub(position,a),delta)/denom)) if denom else 0
        point = geometry_add(a,geometry_mul(delta,factor))
        offset = geometry_sub(point,position)
        score = geometry_dot(offset,offset)
        if best is None or score < best[0]:
            best = score,point
    return best[1] if best else tuple(position)


def transforms_slide_guide(tree,tie,context):
    """Sample only links between the surrounding ties or endpoint sockets.

    The current incoming link, three helper centres, and outgoing link form
    each member's local span. Average member positions at signed arc distance
    from the centre. Freeze the guide before any movement to avoid feedback.
    """
    strands = []
    for key in tie['members']:
        chain = routing_path(tree,key)
        indices = [i for i,l in enumerate(chain)
                   if l.to_node.get(routing_TIE)==tie['id'] and routing_managed(l.to_node)]
        if not indices:
            continue
        span = chain[min(indices):max(indices)+2]
        points = []
        center = None
        for link in span:
            samples = geometry_sample(sockets_controls(link,context))
            points.extend(samples if not points else samples[1:])
            if link.to_node.get(routing_TIE)==tie['id'] and link.to_node.get(routing_SLOT)==1:
                center = len(points)-1
        if center is None or len(points)<2:
            continue
        cumulative = transforms_lengths(points)
        strands.append((points,cumulative,cumulative[center]))
    if not strands:
        return [tuple(tie['pos']),tuple(tie['pos'])]
    clearance = max(12,preferences_prefs(context).width)+4
    lo = min(0,-min(s[2] for s in strands)+clearance)
    hi = max(0,min(s[1][-1]-s[2] for s in strands)-clearance)
    distances = [lo*(1-i/96) for i in range(96)]+[0]+[hi*i/96 for i in range(1,97)]
    guide = []
    for distance in distances:
        points = [transforms_at_distance(p,c,c0+distance) for p,c,c0 in strands]
        guide.append(tuple(sum(p[k] for p in points)/len(points) for k in (0,1)))
    offset = geometry_sub(tie['pos'],guide[96])
    return [geometry_add(p,offset) for p in guide]


# ==========================================================================
# module: routing
# ==========================================================================

"""Managed native reroutes. Blender draws every noodle; overlays draw only straps.

The user approved reroutes on 2026-10-27. Routing nodes persist and continue to
evaluate in vanilla Blender with this extension disabled.
"""
import json

routing_OWNER = '_TRZ_connection'
routing_TIE = '_TRZ_tie'
routing_SLOT = '_TRZ_slot'
routing_LAYOUT_KEY = '_TRZ_layout_version'
routing_LAYOUT_VERSION = 2


def routing_managed(node):
    return node.bl_idname == 'NodeReroute' and bool(node.get(routing_OWNER))


def routing_connection_key(link):
    a = link.from_node.get(routing_OWNER) if routing_managed(link.from_node) else None
    b = link.to_node.get(routing_OWNER) if routing_managed(link.to_node) else None
    if a and b and a != b:
        return data_physical_key(link)
    return a or b or data_physical_key(link)


def routing_endpoints(tree, key):
    try:
        source, output, target, input_ = json.loads(key)
        nodes = {data_uid(n): n for n in tree.nodes if not routing_managed(n)}
        a, b = nodes.get(source), nodes.get(target)
        if not a or not b:
            return None
        out = next((s for s in a.outputs if s.identifier == output), None)
        inp = next((s for s in b.inputs if s.identifier == input_), None)
        return (out, inp) if out and inp else None
    except (ValueError, TypeError):
        return None


def routing_path(tree, key):
    """Only count complete paths through this connection's own managed helpers."""
    pair = routing_endpoints(tree, key)
    if not pair:
        return []
    source, target = pair
    outgoing = {}
    for link in tree.links:
        outgoing.setdefault(link.from_socket.as_pointer(), []).append(link)
    stack = [(source, [])]
    visited = set()
    while stack:
        socket, chain = stack.pop()
        ptr = socket.as_pointer()
        if ptr in visited:
            continue
        visited.add(ptr)
        for link in outgoing.get(ptr, []):
            if link.to_socket == target:
                return chain + [link]
            node = link.to_node
            if routing_managed(node) and node.get(routing_OWNER) == key:
                stack.append((node.outputs[0], chain + [link]))
    return []


def routing_live_keys(tree):
    candidates = {routing_connection_key(l) for l in tree.links}
    return {k for k in candidates if routing_path(tree, k)}


def routing__center(node, point):
    # Blender 5.2 reroute_node_prepare_for_draw places both socket centres
    # directly at node_to_view(node.location), with bounds around that point.
    # A reroute is not positioned by the top-left corner of its drawing box.
    node.location_absolute = point


def routing_ordered_ties(applicable, old_path, source, target):
    """Keep native chain order fixed during transforms, including after reload.

    Only a newly added tie is inserted, at the nearest existing route span.
    Re-sorting by the source/destination chord on every drag can swap ties at
    different heights, separately for each strand, causing sudden rewiring.
    """
    by_id = {t['id']:t for t in applicable}
    seen = set()
    ordered = []
    for link in old_path:
        identity = link.to_node.get(routing_TIE) if routing_managed(link.to_node) else None
        if identity in by_id and identity not in seen:
            ordered.append(by_id[identity])
            seen.add(identity)

    def distance_squared(p,a,b):
        d = geometry_sub(b,a)
        length = geometry_dot(d,d)
        t = max(0,min(1,geometry_dot(geometry_sub(p,a),d)/length)) if length else 0
        delta = geometry_sub(p,geometry_add(a,geometry_mul(d,t)))
        return geometry_dot(delta,delta)

    for tie in applicable:
        if tie['id'] in seen:
            continue
        anchors = [sockets_socket_position(source.node,source)] + [t['pos'] for t in ordered] + [sockets_socket_position(target.node,target)]
        index = min(range(len(anchors)-1),
                    key=lambda i:distance_squared(tie['pos'],anchors[i],anchors[i+1]))
        ordered.insert(index,tie)
        seen.add(tie['id'])
    return ordered


def routing__orphan_helper_plan(tree,key,ties,spacing):
    """Match untagged reroutes on this restored endpoint path back to ties."""
    pair = routing_endpoints(tree,key)
    if not pair or not ties:
        return []
    source,target = pair
    outgoing = {}
    for link in tree.links:
        outgoing.setdefault(link.from_socket.as_pointer(),[]).append(link)
    expected = {tie['id']:tie for tie in ties}
    stack = [(source,[],set())]
    while stack:
        socket,chain,visited = stack.pop()
        for link in outgoing.get(socket.as_pointer(),[]):
            if link.to_socket == target:
                full = chain+[link]
                nodes = []
                for item in full:
                    node = item.to_node
                    if node.bl_idname == 'NodeReroute' and (not nodes or nodes[-1] != node):
                        nodes.append(node)
                if len(nodes) != len(expected) or not any(not routing_managed(n) for n in nodes):
                    continue
                if any(routing_managed(n) and n.get(routing_OWNER) != key for n in nodes):
                    continue
                assigned = {n.get(routing_TIE):n for n in nodes
                            if routing_managed(n) and n.get(routing_TIE) in expected}
                assigned_nodes = {n.as_pointer() for n in assigned.values()}
                free_nodes = [n for n in nodes if n.as_pointer() not in assigned_nodes]
                free_ties = [tie_id for tie_id in expected if tie_id not in assigned]
                if len(free_nodes) != len(free_ties):
                    continue
                centers = {tie_id:geometry_lane(tie,key,spacing)[0] for tie_id,tie in expected.items()}
                pairs = []
                for node in free_nodes:
                    pos = tuple(node.location_absolute)
                    for tie_id in free_ties:
                        delta = geometry_sub(pos,centers[tie_id])
                        pairs.append((geometry_dot(delta,delta),node,tie_id))
                plan = []
                used_nodes,set_ties = set(),set()
                for _,node,tie_id in sorted(pairs,key=lambda item:item[0]):
                    pointer = node.as_pointer()
                    if pointer in used_nodes or tie_id in set_ties:
                        continue
                    used_nodes.add(pointer)
                    set_ties.add(tie_id)
                    plan.append((node,tie_id))
                if len(plan) == len(free_nodes):
                    return plan
                continue
            node = link.to_node
            if node.bl_idname != 'NodeReroute':
                continue
            if routing_managed(node) and node.get(routing_OWNER) != key:
                continue
            pointer = node.as_pointer()
            if pointer in visited or not node.outputs:
                continue
            stack.append((node.outputs[0],chain+[link],visited|{pointer}))
    return []


def routing_has_recoverable_helpers(tree,key,ties,spacing=4.5):
    return bool(routing__orphan_helper_plan(tree,key,ties,spacing))


def routing_sync(tree, ties, spacing=4.5, width=5):
    """Reconcile routes in the caller's undo step. Moving ties reuses all nodes.

    Broken paths are never resurrected. Helpers that a user manually rewired
    remain ordinary reroutes rather than destroying those edits.
    """
    by_key = {}
    for tie in ties:
        for key in tie['members']:
            by_key.setdefault(key, []).append(tie)
    for key,applicable in by_key.items():
        if not routing_path(tree,key):
            for node,tie_id in routing__orphan_helper_plan(tree,key,applicable,spacing):
                node[routing_OWNER],node[routing_TIE],node[routing_SLOT] = key,tie_id,0
    helpers = {}
    for node in tree.nodes:
        if routing_managed(node):
            helpers.setdefault(node[routing_OWNER], []).append(node)
    for key in set(by_key) | set(helpers):
        old_nodes = helpers.get(key, [])
        old_path = routing_path(tree, key)
        if not old_path:
            # Keep surviving helpers managed while their tie references remain.
            # The path may be temporarily disconnected and reconnect to these
            # exact reroutes later. Explicitly deleted/pruned ties are released.
            retained_ties = {tie['id']:tie for tie in by_key.get(key, [])}
            for node in old_nodes:
                tie = retained_ties.get(node.get(routing_TIE))
                if tie is not None:
                    # Even while the endpoint path is broken, keep the proxy
                    # reroute attached to its tie's lane so they never drift.
                    centre,_ = geometry_lane(tie,key,spacing)
                    routing__center(node,centre)
                else:
                    for attr in (routing_OWNER,routing_TIE,routing_SLOT):
                        if attr in node:
                            del node[attr]
            continue
        source, target = routing_endpoints(tree, key)
        applicable = by_key.get(key, [])
        applicable = routing_ordered_ties(applicable,old_path,source,target)
        existing = {(n.get(routing_TIE), n.get(routing_SLOT)): n for n in old_nodes}
        desired_nodes = []
        # One reroute per strand keeps vanilla Blender graphs compact.
        for tie in applicable:
            centre, tangent = geometry_lane(tie, key, spacing)
            identity = (tie['id'], 0)
            node = existing.get(identity)
            if node is None:
                node = tree.nodes.new('NodeReroute')
                node[routing_OWNER], node[routing_TIE], node[routing_SLOT] = key, tie['id'], 0
                node.select = False
                data_uid(node, True)
            routing__center(node, centre)
            desired_nodes.append(node)
        edges = {(l.from_socket.as_pointer(),l.to_socket.as_pointer()):l for l in old_path}
        old_terminal = old_path[-1]
        mute = any(l.is_muted for l in old_path)
        kept = set()
        for index in range(len(desired_nodes)+1):
            # A reroute's sockets can be rebuilt when Blender infers its type
            # from the preceding link. Never retain those socket RNA objects
            # across tree.links.new calls.
            out = source if index == 0 else desired_nodes[index-1].outputs[0]
            inp = target if index == len(desired_nodes) else desired_nodes[index].inputs[0]
            edge = (out.as_pointer(),inp.as_pointer())
            link = edges.get(edge)
            if link is None:
                # Do not let single-input auto-replacement invalidate references
                # to old_path while we are constructing the new chain.
                link = tree.links.new(out,inp,verify_limits=False)
                if link is None:
                    raise RuntimeError('Blender could not connect a zip-tie reroute')
                if inp == target and target.is_multi_input:
                    link.swap_multi_input_sort_id(old_terminal)
                link.is_muted = mute
            kept.add(link.as_pointer())
        live = {l.as_pointer(): l for l in tree.links}
        for link in old_path:
            ptr = link.as_pointer()
            if ptr not in kept and ptr in live:
                tree.links.remove(link)
        wanted = {n.as_pointer() for n in desired_nodes}
        for node in old_nodes:
            if node.as_pointer() not in wanted:
                # Preserve unexpected user branches attached to a helper.
                if any(l.from_node == node or l.to_node == node for l in tree.links):
                    for attr in (routing_OWNER,routing_TIE,routing_SLOT):
                        if attr in node:
                            del node[attr]
                else:
                    tree.nodes.remove(node)
    tree[routing_LAYOUT_KEY] = routing_LAYOUT_VERSION


def routing_settings():
    import bpy
    options = preferences_prefs(bpy.context)
    return options.spacing, options.width


# ==========================================================================
# module: rendering
# ==========================================================================

import bpy
import gpu
import blf
import math
import os
import hashlib
from gpu_extras.batch import batch_for_shader

rendering_handles = []
rendering_last_error = ''
rendering_macho_images = {}
rendering_route_repair_pending = set()
rendering_MACHO_ICONS = (
    '1_macho_hoe.png',
    '2_macho_smile.png',
    '3_macho_cry.png',
    '4_macho_angry.png',
    '5_macho_oh.png',
    '6_macho_yawn.png',
    '7_macho_shy.png',
    '8_macho_love.png',
    '9_macho_tear.png',
    '10_macho_ddabong.png',
    '11_macho_sleep.png',
    '12_macho_question.png',
)
rendering_MUSIC_ICONS = tuple(f'music_note_{index:02}.png' for index in range(1,6))


def rendering_tree_of(context):
    space = context.space_data
    tree = space.edit_tree if space and space.type == 'NODE_EDITOR' else None
    return tree or getattr(context, 'node_tree', None)


def rendering__sync_selected_helpers(tree,tree_pointer):
    if tree_pointer in selection_circle_active.values():
        return 0.01
    selection_sync_pending.discard(tree_pointer)
    rendering_sync_selected_helpers_now(tree)
    return None


def rendering_sync_selected_helpers_now(tree,redraw_areas=True):
    try:
        if not tree or not tree.is_editable:
            return
        helpers = [n for n in tree.nodes if n.select and routing_managed(n)]
        tie_ids = {n.get(routing_TIE) for n in helpers if n.get(routing_TIE)}
        if not tie_ids:
            return
        selection_of(tree).update(tie_ids)
        for node in helpers:
            node.select = False
        if redraw_areas:
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'NODE_EDITOR':
                        space = area.spaces.active
                        if space.edit_tree == tree:
                            area.tag_redraw()
    except (ReferenceError,RuntimeError):
        pass


def rendering_sync_selected_helpers_later(tree):
    """Transfer native selection of a managed reroute to its visible tie."""
    try:
        context = bpy.context
        area_key = context.area.as_pointer() if context.area else None
        if area_key in selection_circle_active:
            return
        if not any(n.select and routing_managed(n) for n in tree.nodes):
            return
        pointer = tree.as_pointer()
        if pointer in selection_sync_pending:
            return
        selection_sync_pending.add(pointer)
        bpy.app.timers.register(lambda: rendering__sync_selected_helpers(tree,pointer),
                                first_interval=0.01)
    except (ReferenceError,RuntimeError,ValueError):
        selection_sync_pending.discard(tree.as_pointer())


def rendering_routes_need_repair(tree,ties):
    expected = {}
    for tie in ties:
        for key in tie['members']:
            expected.setdefault(key,[]).append(tie['id'])
    for key,tie_ids in expected.items():
        chain = routing_path(tree,key)
        if not chain:
            if routing_has_recoverable_helpers(tree,key,
                    [tie for tie in ties if key in tie['members']],preferences_prefs(bpy.context).spacing):
                return True
            continue
        actual = [link.to_node.get(routing_TIE) for link in chain
                  if routing_managed(link.to_node) and link.to_node.get(routing_TIE)]
        if sorted(actual) != sorted(tie_ids):
            return True
    return False


def rendering_schedule_route_repair(tree):
    try:
        if not tree or not tree.is_editable:
            return
        pointer = tree.as_pointer()
        if pointer in rendering_route_repair_pending:
            return
        ties = data_read(tree)
        if not ties or not rendering_routes_need_repair(tree,ties):
            return
        rendering_route_repair_pending.add(pointer)

        def repair():
            rendering_route_repair_pending.discard(pointer)
            try:
                if tree.as_pointer() != pointer or not tree.is_editable:
                    return None
                current = data_read(tree)
                if rendering_routes_need_repair(tree,current):
                    data_write(tree,current)
                    for window in bpy.context.window_manager.windows:
                        for area in window.screen.areas:
                            if area.type == 'NODE_EDITOR' and area.spaces.active.edit_tree == tree:
                                area.tag_redraw()
            except (ReferenceError,RuntimeError,ValueError):
                pass
            return None

        bpy.app.timers.register(repair,first_interval=.1)
    except (ReferenceError,RuntimeError,ValueError):
        try:
            rendering_route_repair_pending.discard(tree.as_pointer())
        except (ReferenceError,RuntimeError):
            pass


def rendering_shown(tree, ties):
    live = {data_link_key(l) for l in tree.links if not l.is_hidden}
    return [t for t in ties if any(k in live for k in t['members'])]


def rendering_display_ties(context,tree,ties):
    """Apply a tiny screen-space visual nudge without changing stored routes."""
    origin = sockets_to_view(context,(0,0))
    shifted = sockets_to_view(context,(1,0))
    offset = (shifted[0]-origin[0],shifted[1]-origin[1])
    result = []
    for tie in ties:
        display = dict(tie)
        display['pos'] = [tie['pos'][0]+offset[0],tie['pos'][1]+offset[1]]
        result.append(display)
    return result


def rendering_line(points, color, width=2):
    if len(points) < 2:
        return
    shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
    shader.bind()
    shader.uniform_float('viewportSize', gpu.state.viewport_get()[2:])
    shader.uniform_float('lineWidth', width)
    shader.uniform_float('color', color)
    batch_for_shader(shader,'LINE_STRIP',{'pos':points}).draw(shader)


def rendering_polygon(points,color,shades=None):
    shader = gpu.shader.from_builtin('SMOOTH_COLOR' if shades else 'UNIFORM_COLOR')
    shader.bind()
    attributes = {'pos':points}
    if shades:
        attributes['color'] = [tuple(c*shade for c in color[:3])+(color[3],) for shade in shades]
    else:
        shader.uniform_float('color', color)
    indices = [(0,i,i+1) for i in range(1,len(points)-1)]
    batch_for_shader(shader,'TRIS',attributes,indices=indices).draw(shader)


def rendering__macho_texture(icon_name):
    cached = rendering_macho_images.get(icon_name)
    if cached:
        return cached[1]
    path = os.path.join(os.path.dirname(__file__),'assets',icon_name)
    image = bpy.data.images.load(path,check_existing=True)
    # Blender may keep an older datablock for the same extension asset path
    # across add-on updates; refresh it so new icon pixels are actually used.
    image.reload()
    image.colorspace_settings.name = 'sRGB'
    image['_TRZ_asset'] = True
    texture = gpu.texture.from_image(image)
    rendering_macho_images[icon_name] = (image,texture)
    return texture


def rendering_draw_image_quad(texture,vertices):
    shader = gpu.shader.from_builtin('IMAGE_SCENE_LINEAR_TO_REC709_SRGB')
    shader.bind()
    shader.uniform_sampler('image',texture)
    coords = [(p[0],p[1],0) for p in vertices]
    batch = batch_for_shader(shader,'TRI_STRIP',{'pos':coords,
        'texCoord':[(0,1),(1,1),(0,0),(1,0)]})
    batch.draw(shader)


def rendering_macho_icon_name(tie):
    stored = tie.get('macho_icon')
    if stored in rendering_MACHO_ICONS:
        return stored
    digest = hashlib.blake2b(tie['id'].encode('utf8'),digest_size=4).digest()
    return rendering_MACHO_ICONS[int.from_bytes(digest,'big') % len(rendering_MACHO_ICONS)]


def rendering_music_note_name(tie):
    return rendering_MUSIC_ICONS[geometry_music_note_index(tie)]


def rendering__styled_points(tie, transform, local_points):
    tangent, normal = geometry_axes(tie['angle'])
    return [transform(geometry_add(tie['pos'], geometry_add(geometry_mul(tangent, x), geometry_mul(normal, y))))
            for x, y in local_points]


def rendering__styled_round_rect(tie, transform, x0, y0, x1, y1, radius):
    return rendering__styled_points(tie, transform, rendering_rounded_rect(x0, y0, x1, y1, radius))


def rendering__shade(color, factor):
    return tuple(max(0.0, min(1.0, channel * factor)) for channel in color[:3]) + (color[3],)


def rendering_draw_styled_tie(tie,spacing,width,transform,border,active,style):
    tangent, normal = geometry_axes(tie['angle'])
    h = geometry_half_length(tie,spacing)
    scale = max(0.35, min(1.0, width / 8.0))
    if style == 'INDUSTRIAL':
        # Broad, softly rounded strap with a compact, layered locking head.
        body = rendering__styled_round_rect(tie,transform,-width*.48,-h,width*.48,h,width*.30)
        rendering_polygon(body,rendering__shade(tie['color'],.88))
        rendering_line(body+[body[0]],border,2 if active else 1.3)
        head = rendering__styled_round_rect(tie,transform,-width*.67,h-width*.08,width*.67,h+width*.82,width*.18)
        rendering_polygon(head,rendering__shade(tie['color'],1.12))
        rendering_line(head+[head[0]],border,2 if active else 1.3)
        slot = rendering__styled_round_rect(tie,transform,-width*.34,h+width*.18,width*.34,h+width*.34,width*.08)
        rendering_polygon(slot,rendering__shade(tie['color'],.48))
        rendering_line(slot+[slot[0]],rendering__shade(border,.8),max(.8,scale))
    elif style == 'MINIMAL':
        # The entire design is one flat strap box: no buckle, slot, or trim.
        body = rendering__styled_round_rect(tie,transform,-width*.34,-h,width*.34,h,min(1.0,width*.34,h))
        rendering_polygon(body,tie['color'])
        rendering_line(body+[body[0]],border,2 if active else 1.0)
    else:  # TECH
        # Armored ratchet strap: bilateral serrations, inset spine and angular lock head.
        inset = width*.14
        teeth = max(3,min(12,int((2*h)/(width*.72))))
        step = (2*h)/teeth
        body = rendering__styled_round_rect(tie,transform,-width*.44,-h,width*.44,h,width*.12)
        rendering_polygon(body,rendering__shade(tie['color'],.82))
        rendering_line(body+[body[0]],border,2 if active else 1.3)
        # Cut-looking ratchet notches are drawn on both long edges.
        tooth_color = rendering__shade(tie['color'],.46)
        for side in (-1,1):
            serration = [(side*width*.40,-h+width*.18)]
            for index in range(teeth):
                y0 = -h+width*.18+index*step
                y1 = min(h-width*.12,y0+step)
                if y1 <= y0:
                    continue
                serration.extend([(side*(width*.40-inset),y0+(y1-y0)*.5),(side*width*.40,y1)])
            rendering_line(rendering__styled_points(tie,transform,serration),tooth_color,max(1.0,width*.09))
        rail = rendering__styled_round_rect(tie,transform,-width*.24,-h+width*.18,width*.20,h-width*.10,width*.08)
        rendering_polygon(rail,rendering__shade(tie['color'],1.22))
        rendering_line(rail+[rail[0]],rendering__shade(tie['color'],.54),max(.8,width*.07))
        # Chunky faceted buckle, with a dark ratchet socket and a small latch.
        head = rendering__styled_points(tie,transform,[(-width*.66,h-width*.10),(-width*.66,h+width*.48),
            (-width*.48,h+width*.76),(width*.48,h+width*.76),(width*.66,h+width*.48),(width*.66,h-width*.10)])
        rendering_polygon(head,rendering__shade(tie['color'],.94))
        rendering_line(head+[head[0]],border,2 if active else 1.3)
        socket = rendering__styled_round_rect(tie,transform,-width*.35,h+width*.08,width*.35,h+width*.40,width*.05)
        rendering_polygon(socket,rendering__shade(tie['color'],.30))
        rendering_line(socket+[socket[0]],rendering__shade(tie['color'],1.30),max(.8,scale))
        latch = rendering__styled_points(tie,transform,[(-width*.15,h+width*.52),(width*.15,h+width*.52),
                                               (width*.10,h+width*.64),(-width*.10,h+width*.64)])
        rendering_polygon(latch,rendering__shade(tie['color'],1.28))


def rendering_draw_tie(tie,spacing,width,transform,border,active,style='ORIGINAL'):
    if style == 'MUSIC':
        tangent,normal = geometry_axes(tie['angle'])
        height = max(2*geometry_half_length(tie,spacing)+width*2.0,width*4.0)
        image_width = height*geometry_MUSIC_NOTE_ASPECTS[geometry_music_note_index(tie)]
        local = [(-image_width/2,height/2),(image_width/2,height/2),
                 (-image_width/2,-height/2),(image_width/2,-height/2)]
        vertices = [transform(geometry_add(tie['pos'],geometry_add(geometry_mul(tangent,x),geometry_mul(normal,y))))
                    for x,y in local]
        rendering_draw_image_quad(rendering__macho_texture(rendering_music_note_name(tie)),vertices)
        return
    if style == 'MACHOCAT':
        h = geometry_half_length(tie,spacing)
        body = rendering__styled_round_rect(tie,transform,-width*.34,-h,width*.34,h,
                                  min(1.0,width*.34,h))
        rendering_polygon(body,tie['color'])
        rendering_line(body+[body[0]],border,2 if active else 1.0)
        side = width*2.7
        center_y = h+width*.65
        local = [(-side/2,center_y+side/2),(side/2,center_y+side/2),
                 (-side/2,center_y-side/2),(side/2,center_y-side/2)]
        rendering_draw_image_quad(rendering__macho_texture(rendering_macho_icon_name(tie)),rendering__styled_points(tie,transform,local))
        return
    if style not in {'ORIGINAL','MACHOCAT'}:
        rendering_draw_styled_tie(tie,spacing,width,transform,border,active,style)
        return
    strap,collar,tip,front = geometry_marker(tie,spacing,width)
    tangent,normal = geometry_axes(tie['angle'])
    h = geometry_half_length(tie,spacing)
    # Smooth body shadows at the lower end and immediately below the collar.
    stops = [(0,.48),(.2,1),(.78,1),(1,.55)]
    for (u,shade),(v,next_shade) in zip(stops,stops[1:]):
        a,b = -h+2*h*u,-h+2*h*v
        local = [(-width/2,a),(width/2,a),(width/2,b),(-width/2,b)]
        points = [transform(geometry_add(tie['pos'],geometry_add(geometry_mul(tangent,x),geometry_mul(normal,y)))) for x,y in local]
        rendering_polygon(points,tie['color'],[shade,shade,next_shade,next_shade])
    rendering_line([transform(p) for p in strap+strap[:1]],border,2 if active else 1.3)
    for index,poly in enumerate((collar,tip,front)):
        points = [transform(p) for p in poly]
        shades = None
        if index==1:
            shades = [.48+.52*max(0,min(1,(geometry_dot(geometry_sub(p,tie['pos']),normal)-h-.05*width)/(1.65*width))) for p in poly]
        rendering_polygon(points,tie['color'],shades)
        rendering_line(points+points[:1],border,2 if active else 1.3)
def rendering_label_anchor(tie,spacing,width,transform,style='ORIGINAL'):
    """Top of the visible silhouette in screen space, independent of rotation."""
    points = [transform(p) for poly in geometry_marker(tie,spacing,width,style) for p in poly]
    return ((min(p[0] for p in points)+max(p[0] for p in points))/2,max(p[1] for p in points))


def rendering_rounded_rect(x0,y0,x1,y1,radius):
    points = []
    for cx,cy,start in ((x1-radius,y0+radius,-90),(x1-radius,y1-radius,0),
                        (x0+radius,y1-radius,90),(x0+radius,y0+radius,180)):
        for step in range(5):
            angle = math.radians(start+step*90/4)
            points.append((cx+radius*math.cos(angle),cy+radius*math.sin(angle)))
    return points


def rendering_node_view_scale(context):
    """Estimate pixels per node unit without View2D's per-pixel rounding noise."""
    sample = 256.0
    origin = sockets_to_region(context,(0,0))
    along_x = sockets_to_region(context,(sample,0))
    along_y = sockets_to_region(context,(0,sample))
    scale_x = math.dist(origin,along_x)/sample
    scale_y = math.dist(origin,along_y)/sample
    return math.sqrt(scale_x*scale_y)


def rendering_draw_name(context,tie,options,transform):
    name = tie.get('name','')
    if not name:
        return
    font = 0
    # Rasterize text at the current node-editor zoom. Scaling a pre-rasterized
    # glyph with the GPU makes it soft and unstable while zooming.
    scale = max(.001,rendering_node_view_scale(context))
    blf.size(font,11*scale)
    text_width,text_height = blf.dimensions(font,name)
    if options.tie_style == 'MINIMAL':
        h = geometry_half_length(tie,options.spacing)
        points = rendering__styled_points(tie,transform,[(-options.width*.34,-h),(options.width*.34,-h),
                                                (options.width*.34,h),(-options.width*.34,h)])
        x = (min(p[0] for p in points)+max(p[0] for p in points))/2
        y = max(p[1] for p in points)
    else:
        x,y = rendering_label_anchor(tie,options.spacing,options.width,transform,options.tie_style)
    pad_x,pad_y = 7*scale,4*scale
    box_width,box_height = text_width+2*pad_x,text_height+2*pad_y
    x0,x1 = x-box_width/2,x+box_width/2
    y0,y1 = y+4*scale,y+4*scale+box_height
    radius = 4*scale
    outline = rendering_rounded_rect(x0,y0,x1,y1,radius)
    bg = (.035,.045,.06,.94)
    accent = tuple(tie['color'][:3])+(1,)
    rendering_polygon(outline,bg)
    rendering_line(outline+[outline[0]],accent,1.2*scale)
    text_x = x
    # Snap glyph origin to a device pixel to avoid subpixel shimmer when panning.
    blf.position(font,round(text_x-text_width/2),round(y0+(box_height-text_height)/2),0)
    text = context.preferences.themes[0].node_editor.space.text
    blf.color(font,*(tuple(text[:3])+(1.0,)))
    blf.enable(font,blf.SHADOW)
    blf.shadow(font,3,0,0,0,.65)
    blf.shadow_offset(font,1,-1)
    try:
        blf.draw(font,name)
    finally:
        blf.disable(font,blf.SHADOW)


def rendering_draw():
    global rendering_last_error
    context = bpy.context
    tree = rendering_tree_of(context)
    if not tree or not preferences_prefs(context).enabled:
        return
    options = preferences_prefs(context)
    # Built-in box/lasso/circle tools select native nodes. Observe their
    # reroute proxies after the editor redraw, then transfer the selection to
    # the overlay tie from a main-thread timer (never inside the GPU callback).
    rendering_sync_selected_helpers_later(tree)
    stored_ties = data_read(tree)
    rendering_schedule_route_repair(tree)
    ties = rendering_display_ties(context,tree,rendering_shown(tree,stored_ties))
    transform = lambda p: sockets_to_region(context,p)
    stroke = selection_preview.get(context.area.as_pointer())
    cuts = stroke[2] if stroke else set()
    gpu.state.blend_set('ALPHA')
    try:
        for tie in ties:
            if rendering_tie_occluded(tree,tie,context):
                continue
            active = tie['id'] in selection_of(tree) or tie['id'] == selection_hovered.get(context.area.as_pointer())
            border = (1,.1,.1,1) if tie['id'] in cuts else (1,1,1,1) if active else (.05,.05,.05,1)
            rendering_draw_tie(tie,options.spacing,options.width,transform,border,active,options.tie_style)
        if options.show_names:
            for tie in ties:
                if not rendering_tie_occluded(tree,tie,context):
                    rendering_draw_name(context,tie,options,transform)
        if stroke:
            rendering_line([transform(stroke[0]),transform(stroke[1])],(1,.1,.1,1) if cuts else (1,1,1,1))
        box = selection_boxes.get(context.area.as_pointer())
        if box:
            a,b = box
            vertices = [a,(b[0],a[1]),b,(a[0],b[1]),a]
            rendering_line([transform(p) for p in vertices],(.65,.8,1,1),1)
        rendering_last_error = ''
    except Exception as exc:
        # Surface diagnostics once in UI, rather than flooding Blender's console every frame.
        rendering_last_error = f'{type(exc).__name__}: {exc}'
    finally:
        gpu.state.blend_set('NONE')


def rendering_pre_draw_sync():
    """Transfer helper selection before Blender draws node/link highlights."""
    try:
        tree = rendering_tree_of(bpy.context)
        if tree:
            rendering_sync_selected_helpers_now(tree,redraw_areas=False)
    except (ReferenceError,RuntimeError):
        pass


def rendering_tie_occluded(tree,tie,context):
    if preferences_prefs(context).show_ties_in_front:
        return False
    ui_scale = context.preferences.system.ui_scale or 1.0
    options = preferences_prefs(context)
    polygons = geometry_marker(tie,options.spacing,options.width,options.tie_style)
    for node in tree.nodes:
        if node.bl_idname == 'NodeReroute' or routing_managed(node):
            continue
        p = node.location_absolute
        rect = (p.x,p.y-node.dimensions.y/ui_scale,
                p.x+node.dimensions.x/ui_scale,p.y)
        if any(rendering__polygon_intersects_rect(poly,rect) for poly in polygons):
            return True
    return False


def rendering__point_in_polygon(point,verts):
    x,y = point
    inside = False
    previous = verts[-1]
    for current in verts:
        x0,y0 = previous
        x1,y1 = current
        if (y0 > y) != (y1 > y) and x < (x1-x0)*(y-y0)/(y1-y0)+x0:
            inside = not inside
        previous = current
    return inside


def rendering__polygon_intersects_rect(poly,rect):
    x0,y0,x1,y1 = rect
    if (max(p[0] for p in poly) < x0 or min(p[0] for p in poly) > x1 or
            max(p[1] for p in poly) < y0 or min(p[1] for p in poly) > y1):
        return False
    corners = [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
    if any(x0<=p[0]<=x1 and y0<=p[1]<=y1 for p in poly):
        return True
    if any(rendering__point_in_polygon(p,poly) for p in corners):
        return True
    edges = list(zip(corners,corners[1:]+corners[:1]))
    return any(geometry_intersection(a,b,c,d) is not None
               for a,b in zip(poly,poly[1:]+poly[:1]) for c,d in edges)


def rendering_register():
    try:
        rendering_handles.append(bpy.types.SpaceNodeEditor.draw_handler_add(
            rendering_pre_draw_sync,(), 'WINDOW','PRE_VIEW'))
    except (TypeError,ValueError,RuntimeError):
        pass
    rendering_handles.append(bpy.types.SpaceNodeEditor.draw_handler_add(rendering_draw,(), 'WINDOW','POST_PIXEL'))


def rendering_unregister():
    for handle in rendering_handles:
        bpy.types.SpaceNodeEditor.draw_handler_remove(handle,'WINDOW')
    rendering_handles.clear()


# ==========================================================================
# module: preferences
# ==========================================================================

import bpy
import json
from bpy.props import BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty, StringProperty


def preferences_update_selected_visual(self,context,field):
    if self.panel_syncing:
        return
    tree = rendering_tree_of(context)
    if not tree or not tree.is_editable:
        return
    chosen = selection_of(tree)
    if not chosen:
        return
    ties = data_read(tree)
    for tie in ties:
        if tie['id'] not in chosen:
            continue
        if field == 'name':
            name = ' '.join(self.selected_tie_name.split())[:128]
            if name:
                tie['name'] = name
            else:
                tie.pop('name',None)
        else:
            tie['color'] = list(data_color_linear_to_srgb(self.selected_tie_color))
    tree[data_KEY] = json.dumps({'version':1,'ties':ties},separators=(',',':'),allow_nan=False)
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'NODE_EDITOR':
                area.tag_redraw()


def preferences_update_selected_name(self,context):
    preferences_update_selected_visual(self,context,'name')


def preferences_update_selected_color(self,context):
    preferences_update_selected_visual(self,context,'color')


def preferences_update_selected_spacing(self,context):
    if self.panel_syncing:
        return
    tree = rendering_tree_of(context)
    if not tree or not tree.is_editable:
        return
    chosen = selection_of(tree)
    if not chosen:
        return
    ties = data_read(tree)
    value = max(4.0,min(50.0,float(self.selected_tie_spacing)))
    for tie in ties:
        if tie['id'] in chosen:
            tie['spacing'] = value
            tie.pop('scale',None)
    data_write(tree,ties)
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'NODE_EDITOR':
                area.tag_redraw()


def preferences_prefs(context):
    entry = context.preferences.addons.get(__name__)
    return entry.preferences if entry else preferences_DEFAULTS


class preferences_Defaults:
    enabled = True
    show_names = True
    spacing = 8.0
    width = 8.0
    color_mode = 'RANDOM'
    tie_style = 'ORIGINAL'
    gesture_key = 'Z'


preferences_DEFAULTS = preferences_Defaults()


def preferences_update_key(self, context):
    interaction_remove_keymaps()
    interaction_add_keymaps()


def preferences_update_visibility(self,context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'NODE_EDITOR':
                area.tag_redraw()


def preferences_update_routes(self,context):
    trees = list(bpy.data.node_groups)
    trees += [m.node_tree for m in bpy.data.materials if m.node_tree]
    trees += [w.node_tree for w in bpy.data.worlds if w.node_tree]
    for tree in trees:
        if tree.is_editable and data_KEY in tree:
            routing_sync(tree,data_read(tree),self.spacing,self.width)
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'NODE_EDITOR':
                area.tag_redraw()


class TRZ_Preferences(bpy.types.AddonPreferences):
    bl_idname = __name__
    language_mode: EnumProperty(name='Language', description='Choose the TieRZ interface language',
                                items=i18n_language_items(), default='AUTO', update=i18n_update_language,
                                translation_context=i18n_DOMAIN)
    enabled: BoolProperty(name='Show Ties', default=True,update=preferences_update_visibility,
        description='Show colored ties; native routed wires and editing remain available',
        translation_context=i18n_DOMAIN)
    show_ties_in_front: BoolProperty(name='Show Ties In Front of Nodes',default=False,
        update=preferences_update_visibility,
        description='Draw ties over node boxes instead of hiding ties covered by nodes',
        translation_context=i18n_DOMAIN)
    show_names: BoolProperty(name='Show Names',default=True,update=preferences_update_visibility,
        description='Show small upright labels above named ties',translation_context=i18n_DOMAIN)
    spacing: FloatProperty(name='Strand spacing', default=8, min=4, max=50,update=preferences_update_routes,
                           translation_context=i18n_DOMAIN)
    width: FloatProperty(name='Tie width', default=8, min=2, max=20,update=preferences_update_routes,
                         translation_context=i18n_DOMAIN)
    color_mode: EnumProperty(name='New tie color',
        items=[('RANDOM','Random',''),('GREY','Grayscale',''),('WIRES','Match wire colors','')],
        translation_context=i18n_DOMAIN)
    tie_style: EnumProperty(name='Tie Design',default='ORIGINAL',update=preferences_update_visibility,
        translation_context=i18n_DOMAIN,
        items=[
            ('ORIGINAL','Default','Current cable-tie design'),
            ('INDUSTRIAL','Industrial','Rounded body with subtle bevels and a compact lock'),
            ('MINIMAL','Minimal','Slim tie with a clean, low-detail lock'),
            ('TECH','Tech','Structured rails and small mechanical details'),
            ('MACHOCAT','MachoCAT','Minimal tie with a large Macho cat head'),
            ('MUSIC','Music Note','A musical note motif with a flowing flag'),
        ])
    panel_syncing: BoolProperty(options={'HIDDEN'})
    synced_selection: StringProperty(default='', options={'HIDDEN'})
    selected_tie_name: StringProperty(name='Name',update=preferences_update_selected_name,
                                      translation_context=i18n_DOMAIN)
    selected_tie_color: FloatVectorProperty(name='Color',subtype='COLOR',size=4,min=0,max=1,
        default=(.55,.55,.58,1),update=preferences_update_selected_color,translation_context=i18n_DOMAIN)
    selected_tie_spacing: FloatProperty(name='Spacing', default=8, min=4, max=50,
        update=preferences_update_selected_spacing,translation_context=i18n_DOMAIN,
        description='Gap between the wires of the selected ties')
    gesture_key: EnumProperty(name='Hold key', default='Z', update=preferences_update_key,
        items=[(k,k,'Hold then drag; bare key starts a modal gesture') for k in ['Z','X','C','T','Y']],
        translation_context=i18n_DOMAIN)

    def draw(self, context):
        layout = self.layout
        layout.label(text='Language', icon='WORLD')
        layout.prop(self, 'language_mode', text='')
        layout.separator()
        layout.label(text='GitHub: https://github.com/narznarz/TieRZ')
        row = layout.row()
        row.operator('wm.url_open', text='Open GitHub').url = 'https://github.com/narznarz/TieRZ'


# ==========================================================================
# module: interaction
# ==========================================================================

import copy
import json
import math
import os
import random
import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty, PointerProperty, StringProperty

interaction_keymaps = []

_random_color_used = {}


def interaction_redraw(context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'NODE_EDITOR':
                area.tag_redraw()


def interaction_point(context,event):
    region = sockets_window_region(context)
    return sockets_to_view(context,(event.mouse_x-region.x,event.mouse_y-region.y))


def interaction_select_tool_id(context):
    try:
        tool = context.workspace.tools.from_space_node(context.space_data.tree_type)
        return tool.idname if tool else ''
    except (AttributeError,TypeError,RuntimeError):
        return ''


def interaction_hit_at(context,p):
    tree = rendering_tree_of(context)
    options = preferences_prefs(context)
    if not options.enabled:
        return None  # Hidden straps must not intercept ordinary canvas clicks.
    # Screen-pixel tolerance remains constant during navigation.
    a = sockets_to_view(context,(0,0))
    b = sockets_to_view(context,(6,0))
    candidates = rendering_display_ties(context,tree,rendering_shown(tree,data_read(tree)))
    for visible_tie in reversed(candidates):
        if (not rendering_tie_occluded(tree,visible_tie,context) and
                geometry_marker_hit(visible_tie,p,options.spacing,options.width,abs(b[0]-a[0]),
                             options.tie_style)):
            return visible_tie
    return None


def interaction_tie_cuts_at(context,ties,a,b):
    tree = rendering_tree_of(context)
    options = preferences_prefs(context)
    return {t['id'] for t in rendering_display_ties(context,tree,rendering_shown(tree,ties))
            if geometry_marker_cut(t,a,b,
                            options.spacing,options.width,options.tie_style)}


def interaction__link_edge(link):
    return (link.from_node.as_pointer(),link.from_socket.identifier,
            link.to_node.as_pointer(),link.to_socket.identifier)


def interaction__logical_link_key(link):
    """Map any managed route segment back to its original connection key."""
    source = link.from_node.get(routing_OWNER) if routing_managed(link.from_node) else None
    target = link.to_node.get(routing_OWNER) if routing_managed(link.to_node) else None
    if source and target and source != target:
        return data_physical_key(link)
    return source or target or data_physical_key(link)


def interaction__parallel_stroke(points,offset):
    """Offset a drawn path by a subpixel amount, preserving its local direction."""
    result = []
    for index,pt in enumerate(points):
        before = points[max(0,index-1)]
        after = points[min(len(points)-1,index+1)]
        dx,dy = after[0]-before[0],after[1]-before[1]
        length = math.hypot(dx,dy)
        if length <= 1e-8:
            result.append(pt)
        else:
            result.append((pt[0]-dy/length*offset,pt[1]+dx/length*offset))
    return result


def interaction__resolve_socket(node,identifier,index,is_output):
    sock_list = node.outputs if is_output else node.inputs
    socket = next((s for s in sock_list
                   if s.identifier == identifier and s.is_output == is_output),None)
    if socket is not None:
        return socket
    if index < len(sock_list) and sock_list[index].is_output == is_output:
        return sock_list[index]
    return next((s for s in sock_list if s.is_output == is_output),None)


def interaction__restore_link(tree,record):
    source = interaction__resolve_socket(record['source_node'],record['source_id'],
                             record['source_index'],True)
    target = interaction__resolve_socket(record['target_node'],record['target_id'],
                             record['target_index'],False)
    if source is None or target is None:
        raise RuntimeError('Could not resolve the original input/output sockets after link cutting')
    link = tree.links.new(source,target,verify_limits=False)
    if link:
        link.is_muted = record['muted']
    return link


def interaction_native_link_hits(context, tree, screen_path):
    """Use Blender's own noodle intersection operator, then restore cut links."""
    if len(screen_path) < 2:
        return []
    for node in tree.nodes:
        if not node.hide:
            continue
        try:
            center = sockets_to_view(context, (node.location_absolute.x + node.dimensions.x / 2.0,
                                            node.location_absolute.y - node.dimensions.y / 2.0))
        except Exception:
            continue
        radius = max(node.dimensions.x, node.dimensions.y) + 20.0
        for point in screen_path:
            if math.hypot(point[0] - center[0], point[1] - center[1]) <= radius:
                return []
    if len(screen_path) > 256:
        step = (len(screen_path)-1) / 255
        screen_path = [screen_path[round(i*step)] for i in range(256)]
    records = []
    for link in tree.links:
        if link.from_socket.hide or link.to_socket.hide:
            continue
        if link.from_node.hide or link.to_node.hide:
            continue
        records.append(dict(
            key=interaction__logical_link_key(link),
            source_node=link.from_node,
            from_socket=link.from_socket,
            source_id=link.from_socket.identifier,
            source_index=list(link.from_node.outputs).index(link.from_socket),
            target_node=link.to_node,
            to_socket=link.to_socket,
            target_id=link.to_socket.identifier,
            target_index=list(link.to_node.inputs).index(link.to_socket),
            edge=interaction__link_edge(link),
            muted=link.is_muted,
            multi=link.multi_input_sort_id if link.to_socket.is_multi_input else None,
        ))
    # Save each connection's physical chain order before the native cut mutates it.
    path_order = {}
    for key in {record['key'] for record in records}:
        for index,link in enumerate(routing_path(tree,key)):
            path_order[interaction__link_edge(link)] = index
    for record in records:
        record['path_index'] = path_order.get(record['edge'],10**9)
    paths = [[{'name': str(i), 'loc': tuple(p), 'time': float(i)}
              for i,p in enumerate(interaction__parallel_stroke(screen_path,offset))]
             for offset in (0.0,)]
    undo_enabled = context.preferences.edit.use_global_undo
    try:
        context.preferences.edit.use_global_undo = False
        for path in paths:
            bpy.ops.node.links_cut(path=path)
    finally:
        context.preferences.edit.use_global_undo = undo_enabled
    live_edges = {interaction__link_edge(link) for link in tree.links}
    removed = sorted((record for record in records if record['edge'] not in live_edges),
                     key=lambda r:(r['key'],r['path_index']))
    try:
        for record in removed:
            interaction__restore_link(tree,record)
        sockets_to_order = {(record['target_node'].as_pointer(),record['target_id']):
                            record['target_node'] for record in records if record['multi'] is not None}
        for (node_pointer,socket_id),node in sockets_to_order.items():
            socket = interaction__resolve_socket(node,socket_id,0,False)
            if socket is None:
                continue
            wanted = sorted((r for r in records
                             if r['target_node'].as_pointer() == node_pointer and
                             r['target_id'] == socket_id and r['multi'] is not None),
                            key=lambda r:r['multi'])
            for index, record in enumerate(wanted):
                current = sorted((link for link in tree.links if link.to_socket == socket),
                                 key=lambda link:link.multi_input_sort_id)
                target_link = next((link for link in current if interaction__link_edge(link) == record['edge']),None)
                if target_link is not None and index < len(current) and current[index] != target_link:
                    target_link.swap_multi_input_sort_id(current[index])
    finally:
        live_edges = {interaction__link_edge(link) for link in tree.links}
        for record in removed:
            if record['edge'] not in live_edges:
                interaction__restore_link(tree,record)
                live_edges.add(record['edge'])

    def _collapsed(record):
        fs = record.get('from_socket')
        ts = record.get('to_socket')
        if fs is not None and getattr(fs, 'hide', False):
            return True
        if ts is not None and getattr(ts, 'hide', False):
            return True
        if getattr(record['source_node'], 'hide', False):
            return True
        if getattr(record['target_node'], 'hide', False):
            return True
        return False

    keys = {record['key'] for record in removed if not _collapsed(record)}
    view_path = [sockets_to_view(context,p) for p in screen_path]
    candidates = {}
    for link in tree.links:
        key = interaction__logical_link_key(link)
        if key not in keys or link.is_hidden:
            continue
        for index,(a,b) in enumerate(zip(view_path,view_path[1:])):
            hit = geometry_curve_hit(a,b,[sockets_controls(link,context)])
            if hit:
                hit_position = geometry_add(a,geometry_mul(geometry_sub(b,a),hit[0]))
                entry = ((index+hit[0])/max(1,len(view_path)-1),hit[1],hit_position,link)
                if key not in candidates or entry[0] < candidates[key][1][0]:
                    candidates[key] = (key,(entry[0],entry[1],entry[2]),link)
    for key in keys:
        if key not in candidates:
            link = next((link for link in tree.links if data_link_key(link)==key),None)
            if link:
                midpoint = view_path[len(view_path)//2]
                candidates[key] = (key,(.5,(1.0,0.0),midpoint),link)

    # Blender's native cut tool can occasionally skip a noodle on the outer
    # edge of a fast/short gesture. Recover only links whose displayed curve
    # actually meets the stroke, allowing a tiny 1.25 screen-pixel antialias
    # margin. This keeps the visible stroke, not the native operator's hit set,
    # as the final source of truth without broad neighbor-wire picking.
    visible_path = screen_path
    stroke_segments = list(zip(visible_path,visible_path[1:]))
    for link in tree.links:
        if link.is_hidden:
            continue
        key = interaction__logical_link_key(link)
        if key in candidates:
            continue
        try:
            curve = [sockets_to_region(context,p) for p in sockets_controls(link,context)]
        except (AttributeError,ReferenceError,RuntimeError,TypeError):
            continue
        for index,(a,b) in enumerate(stroke_segments):
            hit = geometry_curve_hit(a,b,[curve],tolerance=1.25)
            if not hit:
                continue
            position = geometry_add(a,geometry_mul(geometry_sub(b,a),hit[0]))
            progress = (index+hit[0])/max(1,len(stroke_segments))
            if key not in candidates or progress < candidates[key][1][0]:
                candidates[key] = (key,(progress,hit[1],position),link)
            break
    return list(candidates.values())


def interaction_new_color(context,links):
    mode = preferences_prefs(context).color_mode
    if mode == 'GREY':
        return (.55,.55,.58,1)
    if mode == 'WIRES':
        colors = [sockets_color(l,context) for l in links]
        return max(colors,key=colors.count)
    # DawnBringer 16 (DB16) — the classic 16-colour pixel-art palette.
    # The darkest entries are lifted to HSL lightness 0.30 so the tie
    # stays visible against the dark node editor background.
    palette = [
        (.300,.180,.420,1),(.392,.208,.300,1),(.188,.204,.427,1),(.308,.292,.308,1),
        (.522,.298,.188,1),(.228,.442,.158,1),(.816,.275,.282,1),(.459,.443,.380,1),
        (.349,.490,.808,1),(.824,.490,.173,1),(.522,.584,.631,1),(.427,.667,.173,1),
        (.824,.667,.600,1),(.427,.761,.792,1),(.855,.831,.369,1),(.871,.933,.839,1),
    ]
    tree = rendering_tree_of(context)
    key = tree.as_pointer() if tree is not None else 0
    used = _random_color_used.get(key, set())
    available = [i for i in range(len(palette)) if i not in used]
    if not available:
        used = set()
        available = list(range(len(palette)))
    idx = random.choice(available)
    used.add(idx)
    _random_color_used[key] = used
    return palette[idx]


class interaction_NodeOperator:
    @classmethod
    def poll(cls,context):
        tree = rendering_tree_of(context)
        return tree is not None and tree.is_editable


class TRZ_OT_hover(interaction_NodeOperator,bpy.types.Operator):
    bl_idname = 'tie.rz_hover'
    bl_label = 'Tie Hover'
    bl_options = {'INTERNAL'}

    def invoke(self,context,event):
        tie = interaction_hit_at(context,interaction_point(context,event))
        key = context.area.as_pointer()
        value = tie['id'] if tie else None
        if selection_hovered.get(key) != value:
            selection_hovered[key] = value
            interaction_redraw(context)
        return {'PASS_THROUGH'}


class TRZ_OT_gesture(interaction_NodeOperator,bpy.types.Operator):
    bl_idname = 'tie.rz_gesture'
    bl_label = 'Tie Wires'
    bl_description = 'Drag a line across at least two wires; crossing a tie cuts it'
    bl_options = {'REGISTER','UNDO','BLOCKING'}

    def invoke(self,context,event):
        self.tree = rendering_tree_of(context)
        self.node_ids = [(n,n.get(data_NODE_ID)) for n in self.tree.nodes]
        # Assign IDs before collecting keys, within this operator's undo step.
        data_repair_duplicate_ids(self.tree)
        # Keep ties whose wires are temporarily disconnected. If the user
        # reconnects the same sockets, their stable connection keys can revive.
        self.ties = data_read(self.tree)
        self.start = interaction_point(context,event) if event.type == 'LEFTMOUSE' else None
        self.screen_path = [(event.mouse_region_x,event.mouse_region_y)] if event.type == 'LEFTMOUSE' else []
        self.area_key = context.area.as_pointer()
        context.window_manager.modal_handler_add(self)
        context.workspace.status_text_set('Zip ties: drag across wires • Esc cancels')
        return {'RUNNING_MODAL'}

    def finish(self,context,cancel=False):
        if cancel:
            for node,original in self.node_ids:
                if original is None:
                    if data_NODE_ID in node:
                        del node[data_NODE_ID]
                else:
                    node[data_NODE_ID] = original
        selection_preview.pop(self.area_key,None)
        context.workspace.status_text_set(None)
        interaction_redraw(context)
        return {'CANCELLED'} if cancel else {'FINISHED'}

    def modal(self,context,event):
        if event.type in {'ESC','RIGHTMOUSE'} and event.value == 'PRESS':
            return self.finish(context,True)
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.start = interaction_point(context,event)
            self.screen_path = [(event.mouse_region_x,event.mouse_region_y)]
        if self.start is not None and event.type == 'MOUSEMOVE':
            p = interaction_point(context,event)
            screen = (event.mouse_region_x,event.mouse_region_y)
            if not self.screen_path or math.dist(screen,self.screen_path[-1]) >= 1.0:
                self.screen_path.append(screen)
            cuts = interaction_tie_cuts_at(context,self.ties,self.start,p)
            selection_preview[self.area_key] = (self.start,p,cuts)
            interaction_redraw(context)
        if self.start is not None and event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            p = interaction_point(context,event)
            screen = (event.mouse_region_x,event.mouse_region_y)
            if not self.screen_path or screen != self.screen_path[-1]:
                self.screen_path.append(screen)
            cuts = interaction_tie_cuts_at(context,self.ties,self.start,p)
            if cuts:
                self.ties = [t for t in self.ties if t['id'] not in cuts]
                selection_of(self.tree).difference_update(cuts)
            else:
                hits = interaction_native_link_hits(context,self.tree,self.screen_path)
            if not cuts and len(hits) >= 2:
                # Estimate the bundle's undirected axis. PCA avoids cancellation
                # when link directions oppose each other or include angled wires.
                tangents = [h[1][1] for h in hits]
                xx = sum(v[0]*v[0] for v in tangents)
                yy = sum(v[1]*v[1] for v in tangents)
                xy = sum(v[0]*v[1] for v in tangents)
                angle = .5*math.atan2(2*xy,xx-yy)
                # Canonicalize the axis so its normal, and therefore member
                # order, does not randomly flip with link direction.
                if math.cos(angle) < -1e-8 or (abs(math.cos(angle)) <= 1e-8 and math.sin(angle) < 0):
                    angle += math.pi
                _,normal = geometry_axes(angle)
                hit_position = lambda h:h[1][2]
                pos = [sum(hit_position(h)[k] for h in hits)/len(hits) for k in (0,1)]
                target_nodes = {h[2].to_node.as_pointer() for h in hits}
                source_nodes = {h[2].from_node.as_pointer() for h in hits}
                if len(target_nodes) == 1:
                    # For a bundle entering one node, keep strands in that
                    # node's socket order so the fan-in does not twist at the tie.
                    hits.sort(key=lambda h:(geometry_dot(sockets_socket_position(
                        h[2].to_node,h[2].to_socket),normal),
                        h[2].multi_input_sort_id if h[2].to_socket.is_multi_input else -1,
                        h[0]))
                elif len(source_nodes) == 1:
                    # The same rule applies to several links leaving one node.
                    hits.sort(key=lambda h:(geometry_dot(sockets_socket_position(
                        h[2].from_node,h[2].from_socket),normal),h[0]))
                else:
                    hits.sort(key=lambda h:(geometry_dot(hit_position(h),normal),h[0]))
                tie = data_new_tie(pos,angle,[h[0] for h in hits],self.ties,interaction_new_color(context,[h[2] for h in hits]))
                if preferences_prefs(context).tie_style == 'MACHOCAT':
                    tie['macho_icon'] = random.choice(rendering_MACHO_ICONS)
                elif preferences_prefs(context).tie_style == 'MUSIC':
                    tie['music_note'] = random.randrange(len(rendering_MUSIC_ICONS))
                self.ties.append(tie)
                selection_of(self.tree).clear()
                selection_of(self.tree).add(tie['id'])
            elif not cuts:
                return self.finish(context,True)
            data_write(self.tree,self.ties)
            return self.finish(context)
        return {'RUNNING_MODAL'}


class TRZ_OT_pick(interaction_NodeOperator,bpy.types.Operator):
    bl_idname = 'tie.rz_pick'
    bl_label = 'Select or Transform Tie'
    bl_options = {'UNDO','BLOCKING'}

    def invoke(self,context,event):
        self.tree = rendering_tree_of(context)
        self.start = interaction_point(context,event)
        hit = interaction_hit_at(context,self.start)
        tool = interaction_select_tool_id(context)
        if event.type == 'LEFTMOUSE' and any(tool.endswith(name) for name in
                ('select_box','select_circle','select_lasso')) and not hit:
            # Let Blender's native tool hit the managed reroute proxy. The
            # release synchronizer translates that node selection to its tie.
            if not hit and not event.shift and not event.ctrl:
                selection_of(self.tree).clear()
                interaction_redraw(context)
            return {'PASS_THROUGH'}
        if not hit:
            if not event.shift and not event.ctrl:
                selection_of(self.tree).clear()
                interaction_redraw(context)
            return {'PASS_THROUGH'}
        for node in self.tree.nodes:
            if routing_managed(node) and node.get(routing_TIE)==hit['id']:
                node.select = False
        selected = selection_of(self.tree)
        if event.type == 'RIGHTMOUSE':
            if hit['id'] not in selected:
                selected.clear()
                selected.add(hit['id'])
            bpy.ops.wm.call_menu(name='TRZ_MT_context')
            return {'FINISHED'}
        if event.ctrl:
            selected.symmetric_difference_update({hit['id']})
            interaction_redraw(context)
            return {'FINISHED'}
        if not event.shift and hit['id'] not in selected:
            selected.clear()
        selected.add(hit['id'])
        self.original = data_read(self.tree)
        self.hit = hit
        self.start_screen = (event.mouse_region_x,event.mouse_region_y)
        self.dragging = False
        self.rotate = event.shift
        self.offset = hit['angle'] - math.atan2(self.start[1]-hit['pos'][1],self.start[0]-hit['pos'][0])
        context.window_manager.modal_handler_add(self)
        interaction_redraw(context)
        return {'RUNNING_MODAL'}

    def modal(self,context,event):
        if event.type in {'ESC','RIGHTMOUSE'} and event.value == 'PRESS':
            data_write(self.tree,self.original)
            interaction_redraw(context)
            return {'CANCELLED'}
        if event.type == 'MOUSEMOVE':
            # A click can generate a tiny pointer jitter before release. Do not
            # rebuild native reroute chains unless the user actually drags.
            if not self.dragging:
                screen = (event.mouse_region_x,event.mouse_region_y)
                if math.dist(screen,self.start_screen) < 3.0:
                    return {'RUNNING_MODAL'}
                self.dragging = True
            p = interaction_point(context,event)
            delta = geometry_sub(p,self.start)
            ties = copy.deepcopy(self.original)
            angle = math.atan2(p[1]-self.hit['pos'][1],p[0]-self.hit['pos'][0])+self.offset
            if not event.alt:
                angle = round(angle/(math.pi/12))*(math.pi/12)
            for t in ties:
                if t['id'] in selection_of(self.tree):
                    if self.rotate:
                        t['angle'] += angle-self.hit['angle']
                    else:
                        t['pos'] = list(geometry_add(t['pos'],delta))
            data_write(self.tree,ties)
            interaction_redraw(context)
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            return {'FINISHED'}
        return {'RUNNING_MODAL'}


class TRZ_OT_circle_clear_ties(interaction_NodeOperator,bpy.types.Operator):
    bl_idname = 'tie.rz_circle_clear_ties'
    bl_label = 'Clear Tie Selection for Circle Select'
    bl_options = {'INTERNAL'}

    def invoke(self,context,event):
        tree = rendering_tree_of(context)
        # This operator is bound only inside the Circle Select tool keymap;
        # do not depend on WorkspaceTool.idname, which varies by Blender build.
        if not tree:
            return {'PASS_THROUGH'}
        area_key = context.area.as_pointer()
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            selection_circle_active[area_key] = tree.as_pointer()
            if not event.shift and not event.ctrl and not interaction_hit_at(context,interaction_point(context,event)):
                selection_of(tree).clear()
                interaction_redraw(context)
        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE' and area_key in selection_circle_active:
            rendering_sync_selected_helpers_now(tree)
            selection_circle_active.pop(area_key,None)
            context.area.tag_redraw()
        # Leave the native Circle Select operation in charge of node selection.
        return {'PASS_THROUGH'}


class TRZ_OT_move(interaction_NodeOperator,bpy.types.Operator):
    bl_idname = 'tie.rz_move'
    bl_label = 'Move Ties'
    bl_description = 'G moves selected ties; press G again to slide between neighbouring ties'
    bl_options = {'UNDO','BLOCKING'}

    def invoke(self,context,event):
        self.tree = rendering_tree_of(context)
        self.original = data_read(self.tree)
        chosen = selection_of(self.tree)
        self.ids = {t['id'] for t in self.original if t['id'] in chosen}
        self.start = interaction_point(context,event)
        if not self.ids:
            hit = interaction_hit_at(context,self.start)
            if not hit:
                return {'PASS_THROUGH'}
            chosen.clear()
            chosen.add(hit['id'])
            self.ids = {hit['id']}
        self.guides = {t['id']:transforms_slide_guide(self.tree,t,context)
                       for t in self.original if t['id'] in self.ids}
        self.cursor = self.start
        self.slide = False
        context.window_manager.modal_handler_add(self)
        self.status(context)
        return {'RUNNING_MODAL'}

    def status(self,context):
        text = 'Slide ties between neighbours' if self.slide else 'Move ties • G again to slide'
        context.workspace.status_text_set(text+' • Click/Enter confirm • Esc/right-click cancel')

    def update(self,context):
        delta = geometry_sub(self.cursor,self.start)
        ties = copy.deepcopy(self.original)
        for tie in ties:
            if tie['id'] in self.ids:
                position = geometry_add(tie['pos'],delta)
                tie['pos'] = list(transforms_project(self.guides[tie['id']],position) if self.slide else position)
        data_write(self.tree,ties)
        interaction_redraw(context)

    def finish(self,context,cancel=False):
        if cancel:
            data_write(self.tree,self.original)
        context.workspace.status_text_set(None)
        interaction_redraw(context)
        return {'CANCELLED'} if cancel else {'FINISHED'}

    def modal(self,context,event):
        if event.value == 'PRESS':
            if event.type in {'ESC','RIGHTMOUSE'}:
                return self.finish(context,True)
            if event.type in {'LEFTMOUSE','RET','NUMPAD_ENTER'}:
                return self.finish(context)
            if event.type == 'G' and not getattr(event,'is_repeat',False) and not self.slide:
                self.slide = True
                self.status(context)
                self.update(context)
        if event.type == 'MOUSEMOVE':
            self.cursor = interaction_point(context,event)
            self.update(context)
        return {'RUNNING_MODAL'}


class TRZ_OT_scale(interaction_NodeOperator,bpy.types.Operator):
    bl_idname = 'tie.rz_scale'
    bl_label = 'Scale Ties'
    bl_description = 'Scale selected tie lengths and noodle gaps; click/Enter confirms, Esc cancels'
    bl_options = {'UNDO','BLOCKING'}
    ui_hide_shortcut: BoolProperty(default=True, options={'HIDDEN'})

    def invoke(self,context,event):
        self.tree = rendering_tree_of(context)
        self.original = data_read(self.tree)
        chosen = selection_of(self.tree)
        self.ids = {t['id'] for t in self.original if t['id'] in chosen}
        self.start = interaction_point(context,event)
        if not self.ids:
            hit = interaction_hit_at(context,self.start)
            if not hit:
                return {'PASS_THROUGH'}
            chosen.clear()
            chosen.add(hit['id'])
            self.ids = {hit['id']}
        ties = [t for t in self.original if t['id'] in self.ids]
        self.pivot = tuple(sum(t['pos'][k] for t in ties)/len(ties) for k in (0,1))
        self.radius = math.hypot(*geometry_sub(self.start,self.pivot))
        if self.radius < 1:
            # At the exact centre, use a virtual reference so left/right motion
            # can still shrink/grow instead of dividing by zero or jumping.
            self.radius = max(32,max(geometry_half_length(t,preferences_prefs(context).spacing) for t in ties))
            self.pivot = (self.start[0]-self.radius,self.start[1])
        self.base = max(geometry_effective_spacing(t,preferences_prefs(context).spacing) for t in ties)
        self.factor = 1.0
        self.gap = self.base
        self.numeric = ''
        context.window_manager.modal_handler_add(self)
        self.status(context)
        return {'RUNNING_MODAL'}

    def status(self,context):
        current = self.numeric or format(self.gap,'.1f')
        context.workspace.status_text_set(f'Spacing: {current} • Type a value • Click/Enter confirm • Esc/right-click cancel')

    def update(self,context):
        ties = copy.deepcopy(self.original)
        gap = max(geometry_MIN_STRAND_SPACING,min(geometry_MAX_STRAND_SPACING,self.base*self.factor))
        for tie in ties:
            if tie['id'] in self.ids:
                tie['spacing'] = gap
                tie.pop('scale',None)
        self.gap = gap
        data_write(self.tree,ties)
        self.status(context)
        interaction_redraw(context)

    def finish(self,context,cancel=False):
        if cancel:
            data_write(self.tree,self.original)
        context.workspace.status_text_set(None)
        interaction_redraw(context)
        return {'CANCELLED'} if cancel else {'FINISHED'}

    def modal(self,context,event):
        if event.value == 'PRESS':
            if event.type in {'ESC','RIGHTMOUSE'}:
                return self.finish(context,True)
            if event.type in {'LEFTMOUSE','RET','NUMPAD_ENTER'}:
                return self.finish(context)
            digits = dict(zip(['ZERO','ONE','TWO','THREE','FOUR','FIVE','SIX','SEVEN','EIGHT','NINE'],'0123456789'))
            digits.update({f'NUMPAD_{i}':str(i) for i in range(10)})
            if event.type in digits and len(self.numeric)<16:
                self.numeric += digits[event.type]
            elif event.type in {'PERIOD','NUMPAD_PERIOD'} and '.' not in self.numeric:
                self.numeric += '.'
            elif event.type == 'BACK_SPACE':
                self.numeric = self.numeric[:-1]
            else:
                return {'RUNNING_MODAL'}
            try:
                target = float(self.numeric) if self.numeric else self.base
                self.factor = max(.01,min(200,target/max(self.base,1e-6)))
            except ValueError:
                self.factor = 1.0
            self.update(context)
        if event.type == 'MOUSEMOVE' and not self.numeric:
            self.factor = max(.01,min(200,math.hypot(*geometry_sub(interaction_point(context,event),self.pivot))/self.radius))
            self.update(context)
        return {'RUNNING_MODAL'}


class TRZ_OT_match_scale(interaction_NodeOperator,bpy.types.Operator):
    bl_idname = 'tie.rz_match_scale'
    bl_label = 'Match Selected Tie Sizes'
    bl_description = 'Give all selected ties the same average scale; Alt+S'
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls,context):
        tree = rendering_tree_of(context)
        if not tree or not tree.is_editable:
            return False
        chosen = selection_of(tree)
        return sum(tie['id'] in chosen for tie in data_read(tree)) >= 2

    def execute(self,context):
        tree = rendering_tree_of(context)
        chosen = selection_of(tree)
        ties = data_read(tree)
        selected = [tie for tie in ties if tie['id'] in chosen]
        if len(selected) < 2:
            return {'CANCELLED'}
        target = min(geometry_MAX_STRAND_SPACING,max(geometry_MIN_STRAND_SPACING,
                     sum(geometry_effective_spacing(tie,preferences_prefs(context).spacing) for tie in selected)/len(selected)))
        for tie in selected:
            tie['spacing'] = target
            tie.pop('scale',None)
        data_write(tree,ties)
        interaction_redraw(context)
        return {'FINISHED'}


class TRZ_OT_rotate(interaction_NodeOperator,bpy.types.Operator):
    bl_idname = 'tie.rz_rotate'
    bl_label = 'Rotate Ties Freely'
    bl_description = 'Rotate selected ties with the mouse; click or Enter confirms, Esc cancels'
    bl_options = {'UNDO','BLOCKING'}
    ui_hide_shortcut: BoolProperty(default=True, options={'HIDDEN'})

    def invoke(self,context,event):
        self.tree = rendering_tree_of(context)
        self.original = data_read(self.tree)
        chosen = selection_of(self.tree)
        self.ids = {t['id'] for t in self.original if t['id'] in chosen}
        if not self.ids:
            hit = interaction_hit_at(context,interaction_point(context,event))
            if not hit:
                return {'PASS_THROUGH'}
            chosen.clear()
            chosen.add(hit['id'])
            self.ids = {hit['id']}
        ties = [t for t in self.original if t['id'] in self.ids]
        self.pivot = tuple(sum(t['pos'][k] for t in ties)/len(ties) for k in (0,1))
        self.previous = None
        self.delta = 0.0
        self.track(interaction_point(context,event))
        context.window_manager.modal_handler_add(self)
        context.workspace.status_text_set('Rotate ties freely • Click/Enter confirm • Esc/right-click cancel')
        return {'RUNNING_MODAL'}

    def track(self,p):
        x,y = geometry_sub(p,self.pivot)
        if math.hypot(x,y) < 1e-4:
            return
        angle = math.atan2(y,x)
        if self.previous is not None:
            # Unwrap at +/-pi, supporting continuous turns without a jump.
            change = angle-self.previous
            self.delta += math.atan2(math.sin(change),math.cos(change))
        self.previous = angle

    def finish(self,context,cancel=False):
        if cancel:
            data_write(self.tree,self.original)
        context.workspace.status_text_set(None)
        interaction_redraw(context)
        return {'CANCELLED'} if cancel else {'FINISHED'}

    def modal(self,context,event):
        if event.value == 'PRESS':
            if event.type in {'ESC','RIGHTMOUSE'}:
                return self.finish(context,True)
            if event.type in {'LEFTMOUSE','RET','NUMPAD_ENTER'}:
                return self.finish(context)
        if event.type == 'MOUSEMOVE':
            self.track(interaction_point(context,event))
            ties = copy.deepcopy(self.original)
            for tie in ties:
                if tie['id'] in self.ids:
                    tie['angle'] += self.delta
            data_write(self.tree,ties)
            interaction_redraw(context)
        return {'RUNNING_MODAL'}


class TRZ_OT_delete(interaction_NodeOperator,bpy.types.Operator):
    bl_idname = 'tie.rz_delete'
    bl_label = 'Remove Selected Ties'
    bl_description = 'Remove selected ties; nodes and wires remain'
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls,context):
        tree = rendering_tree_of(context)
        return bool(tree and tree.is_editable and
                    any(t['id'] in selection_of(tree) for t in data_read(tree)))

    def execute(self,context):
        tree = rendering_tree_of(context)
        if not tree or not tree.is_editable:
            return {'CANCELLED'}
        selected = selection_of(tree)
        ties = [t for t in data_read(tree) if t['id'] not in selected]
        selected.clear()
        data_write(tree,ties)
        interaction_redraw(context)
        return {'FINISHED'}


class TRZ_OT_color(interaction_NodeOperator,bpy.types.Operator):
    bl_idname = 'tie.rz_color'
    bl_label = 'Tie Color'
    bl_description = 'Change the color of the selected ties'
    bl_options = {'REGISTER','UNDO'}
    color: FloatVectorProperty(name='Color',subtype='COLOR',size=4,min=0,max=1,default=(.55,.55,.58,1))
    # Store the tree by name: a NodeTree PointerProperty on an Operator fails to
    # register on newer Blender builds ("type doesn't support data-block properties").
    tree_name: StringProperty(options={'HIDDEN'})

    @classmethod
    def poll(cls,context):
        tree = rendering_tree_of(context)
        return bool(tree and tree.is_editable and
                    any(t['id'] in selection_of(tree) for t in data_read(tree)))

    def invoke(self,context,event):
        tree = rendering_tree_of(context)
        self.tree_name = tree.name if tree else ''
        self.color = data_color_srgb_to_linear(next(t['color'] for t in data_read(tree) if t['id'] in selection_of(tree)))
        return context.window_manager.invoke_props_dialog(self,width=190)

    def draw(self,context):
        self.layout.template_color_picker(self,'color',value_slider=True,cubic=False)
        self.layout.prop(self,'color',text='')

    def execute(self,context):
        tree = bpy.data.node_groups.get(self.tree_name) if self.tree_name else None
        tree = tree or rendering_tree_of(context)
        if not tree or not tree.is_editable:
            return {'CANCELLED'}
        ties = data_read(tree)
        for tie in ties:
            if tie['id'] in selection_of(tree):
                tie['color'] = list(data_color_linear_to_srgb(self.color))
        data_write(tree,ties)
        interaction_redraw(context)
        return {'FINISHED'}


class TRZ_OT_color_popup(interaction_NodeOperator,bpy.types.Operator):
    bl_idname = 'tie.rz_color_popup'
    bl_label = 'Tie Color'
    bl_description = 'Change the color of the selected ties'
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls,context):
        tree = rendering_tree_of(context)
        return bool(tree and tree.is_editable and
                    any(t['id'] in selection_of(tree) for t in data_read(tree)))

    def invoke(self,context,event):
        return bpy.ops.wm.call_panel('INVOKE_DEFAULT',name='TRZ_PT_color_popover')


class TRZ_OT_name(interaction_NodeOperator,bpy.types.Operator):
    bl_idname = 'tie.rz_name'
    bl_label = 'Name Tie'
    bl_description = 'Give the selected tie a label; leave empty to remove its name'
    bl_options = {'REGISTER','UNDO'}
    name: StringProperty(name='Name',maxlen=128)
    tie_id: StringProperty(options={'HIDDEN'})
    ui_hide_shortcut: BoolProperty(default=True, options={'HIDDEN'})

    @classmethod
    def poll(cls,context):
        tree = rendering_tree_of(context)
        return bool(tree and tree.is_editable and
                    sum(t['id'] in selection_of(tree) for t in data_read(tree))==1)

    def invoke(self,context,event):
        tree = rendering_tree_of(context)
        tie = next(t for t in data_read(tree) if t['id'] in selection_of(tree))
        self.tie_id = tie['id']
        self.name = tie.get('name','')
        return context.window_manager.invoke_props_dialog(self)

    def draw(self,context):
        self.layout.prop(self,'name',text='')
        self.layout.label(text=i18n_tr('Leave empty to hide the label.'))

    def execute(self,context):
        tree = rendering_tree_of(context)
        ties = data_read(tree)
        target = self.tie_id or next((t['id'] for t in ties if t['id'] in selection_of(tree)),None)
        tie = next((t for t in ties if t['id']==target),None)
        if tie is None:
            return {'CANCELLED'}
        name = ' '.join(self.name.split())[:128]
        if name:
            tie['name'] = name
        else:
            tie.pop('name',None)
        data_write(tree,ties)
        interaction_redraw(context)
        return {'FINISHED'}


class TRZ_OT_edit(interaction_NodeOperator,bpy.types.Operator):
    bl_idname = 'tie.rz_edit'
    bl_label = 'Edit Selected Ties'
    bl_options = {'REGISTER','UNDO'}
    action: EnumProperty(items=[('DELETE','Remove',''),('ROTATE','Rotate',''),
        ('PRUNE','Remove Missing Wire References','Remove missing connections from ties; does not delete disconnected nodes')],options={'HIDDEN'})
    angle: FloatProperty(default=math.pi/2)
    delete_nodes: BoolProperty(default=False,options={'HIDDEN'})

    def execute(self,context):
        tree = rendering_tree_of(context)
        selected = selection_of(tree)
        if not selected and self.action != 'PRUNE':
            return {'PASS_THROUGH'}
        ties = data_read(tree)
        if self.action == 'DELETE':
            ties = [t for t in ties if t['id'] not in selected]
            selected.clear()
            if self.delete_nodes:
                # Restore logical connections and remove owned helpers before
                # deleting their endpoints, within the same undo step.
                data_write(tree,ties)
                for node in list(tree.nodes):
                    if node.select:
                        tree.nodes.remove(node)
                ties = data_prune(tree,ties)
        elif self.action == 'PRUNE':
            ties = data_prune(tree,ties)
        else:
            for t in ties:
                if t['id'] in selected:
                    t['angle'] += self.angle
        data_write(tree,ties)
        interaction_redraw(context)
        return {'FINISHED'}


def interaction_addon_node_trees():
    candidates = list(bpy.data.node_groups)
    candidates += [item.node_tree for item in bpy.data.materials if item.node_tree]
    candidates += [item.node_tree for item in bpy.data.worlds if item.node_tree]
    candidates += [item.node_tree for item in bpy.data.lights if item.node_tree]
    candidates += [tree for scene in bpy.data.scenes
                   if getattr(scene,'use_nodes',False)
                   for tree in (getattr(scene,'node_tree',None),) if tree]
    result,seen = [],set()
    for tree in candidates:
        pointer = tree.as_pointer()
        if pointer not in seen:
            seen.add(pointer)
            result.append(tree)
    return result


def interaction_has_id_property(datablock,key):
    try:
        return key in datablock
    except (AttributeError,ReferenceError,RuntimeError,TypeError):
        return False


def interaction_addon_cleanup_scan():
    affected = []
    tie_count = helper_count = complete_count = broken_count = readonly_count = 0
    for tree in interaction_addon_node_trees():
        helpers = [node for node in tree.nodes
                  if node.bl_idname == 'NodeReroute' and
                  any(k in node for k in (routing_OWNER, routing_TIE, routing_SLOT, data_NODE_ID))]
        has_node_ids = any(interaction_has_id_property(node,data_NODE_ID) for node in tree.nodes)
        if not (data_KEY in tree or routing_LAYOUT_KEY in tree or helpers or has_node_ids):
            continue
        affected.append(tree)
        ties = data_read(tree)
        tie_count += len(ties)
        helper_count += len(helpers)
        readonly_count += not tree.is_editable
        owners = {node.get(routing_OWNER) for node in helpers if node.get(routing_OWNER)}
        for key in owners:
            if routing_path(tree,key):
                complete_count += 1
            else:
                owner_helpers = [node for node in helpers if node.get(routing_OWNER) == key]
                if any(link.from_node in owner_helpers or link.to_node in owner_helpers
                       for link in tree.links):
                    broken_count += 1
    cached_images = {image.as_pointer() for image,_texture in rendering_macho_images.values()}
    icons = set(rendering_MACHO_ICONS) | set(rendering_MUSIC_ICONS) | {'macho_smile.png','7_macho_shy.png'}
    image_candidates = []
    for image in bpy.data.images:
        marked = bool(image.get('_TRZ_asset',False))
        cached = image.as_pointer() in cached_images
        filepath = bpy.path.abspath(image.filepath)
        filename = os.path.basename(filepath)
        addon_asset = (filename in icons and
                       os.path.basename(os.path.dirname(filepath)).lower() == 'assets' and
                       'TieRZ' in filepath.lower())
        if marked or cached or addon_asset:
            image_candidates.append(image)
    removable_images = sum(image.users == 0 for image in image_candidates)
    preserved_images = len(image_candidates)-removable_images
    return dict(trees=affected,ties=tie_count,helpers=helper_count,
                complete=complete_count,broken=broken_count,readonly=readonly_count,
                removable_images=removable_images,preserved_images=preserved_images)


class TRZ_OT_cleanup_addon_data(bpy.types.Operator):
    bl_idname = 'tie.rz_cleanup_addon_data'
    bl_label = 'Clean Add-on Data'
    bl_description = 'Restore safe routes and remove TieRZ metadata before uninstalling'
    bl_options = {'REGISTER','UNDO'}

    def invoke(self,context,event):
        info = interaction_addon_cleanup_scan()
        if not info['trees'] and not (info['removable_images'] or info['preserved_images']):
            self.report({'INFO'},'No TieRZ data was found in this file')
            return {'CANCELLED'}
        return context.window_manager.invoke_props_dialog(self,width=440)

    def draw(self,context):
        layout = self.layout
        info = interaction_addon_cleanup_scan()
        layout.label(text='This cleanup affects every node tree in the current .blend file.',icon='INFO')
        layout.label(text=i18n_tr("Ties: {ties}   Managed reroutes: {helpers}   Node trees: {trees}").format(
            ties=info['ties'], helpers=info['helpers'], trees=len(info['trees'])))
        layout.label(text=i18n_tr("Complete routes to restore: {complete}").format(complete=info['complete']))
        if info['broken']:
            box = layout.box()
            box.alert = True
            box.label(text=i18n_tr("{broken} interrupted route chain(s) will be kept as native reroutes.").format(
                broken=info['broken']),icon='ERROR')
            box.label(text='Their existing links are preserved because they cannot be safely restored direct.')
        if info['preserved_images']:
            layout.label(text=i18n_tr("{images} icon image(s) used elsewhere will be packed and kept.").format(
                images=info['preserved_images']),icon='IMAGE_DATA')
        if info['readonly']:
            box = layout.box()
            box.alert = True
            box.label(text=i18n_tr("{readonly} affected node tree(s) are read-only; cleanup will stop.").format(
                readonly=info['readonly']),icon='LOCKED')
        layout.separator()
        layout.label(text='Tie records and add-on IDs will be removed. This cannot be undone after saving and uninstalling.')

    def execute(self,context):
        global clipboard_payload
        info = interaction_addon_cleanup_scan()
        if not info['trees'] and not (info['removable_images'] or info['preserved_images']):
            self.report({'INFO'},'No TieRZ data was found in this file')
            return {'CANCELLED'}
        if info['readonly']:
            self.report({'ERROR'},'Cleanup stopped: make linked node trees editable first')
            return {'CANCELLED'}
        spacing,width = routing_settings()
        helper_pointers = {
            tree.as_pointer():{node.as_pointer() for node in tree.nodes if routing_managed(node)}
            for tree in info['trees']
        }
        # First restore all complete routes. Do not clear any metadata unless
        # every tree reaches this safe stage successfully.
        try:
            for tree in info['trees']:
                routing_sync(tree,[],spacing,width)
        except Exception as exc:
            self.report({'ERROR'},f'Cleanup stopped before removing metadata: {type(exc).__name__}: {exc}')
            return {'CANCELLED'}

        for tree in info['trees']:
            for key in (data_KEY,routing_LAYOUT_KEY):
                if key in tree:
                    del tree[key]
            for node in tree.nodes:
                for key in (routing_OWNER,routing_TIE,routing_SLOT,data_NODE_ID):
                    try:
                        if key in node:
                            del node[key]
                    except (ReferenceError,RuntimeError,TypeError):
                        pass
            # Remove only isolated helpers created by the add-on. Keep any
            # reroute that still carries a user link.
            old_ids = helper_pointers.get(tree.as_pointer(),set())
            for node in list(tree.nodes):
                if node.as_pointer() in old_ids and not any(
                        link.from_node == node or link.to_node == node for link in tree.links):
                    tree.nodes.remove(node)

        cached_images = {image.as_pointer() for image,_texture in rendering_macho_images.values()}
        rendering_macho_images.clear()
        rendering_route_repair_pending.clear()
        icons = set(rendering_MACHO_ICONS) | set(rendering_MUSIC_ICONS) | {'macho_smile.png','7_macho_shy.png'}
        for image in list(bpy.data.images):
            marked = bool(image.get('_TRZ_asset',False))
            filepath = bpy.path.abspath(image.filepath)
            filename = os.path.basename(filepath)
            addon_asset = (filename in icons and
                           os.path.basename(os.path.dirname(filepath)).lower() == 'assets' and
                           'TieRZ' in filepath.lower())
            if not marked and image.as_pointer() not in cached_images and not addon_asset:
                continue
            if image.users == 0:
                bpy.data.images.remove(image)
            else:
                try:
                    image.pack()
                except (RuntimeError,TypeError):
                    pass
                if marked:
                    del image['_TRZ_asset']
        selection_clear()
        clipboard_payload = None
        interaction_redraw(context)
        self.report({'INFO'},'TieRZ data was cleaned from the current .blend file')
        return {'FINISHED'}


class TRZ_OT_box(interaction_NodeOperator,bpy.types.Operator):
    bl_idname = 'tie.rz_box'
    bl_label = 'Box Select Ties and Nodes'
    bl_options = {'UNDO','BLOCKING'}
    bl_description = 'Drag a box to select nodes and ties together; Shift adds to selection'

    def invoke(self,context,event):
        # B starts this operator before the drag begins. When invoked from the
        # toolbar's Select Box tool, Blender sends CLICK_DRAG as the invoke
        # event, so capture its initial mouse position immediately.
        self.start = None if event.type == 'B' else interaction_point(context,event)
        self.extend = event.shift
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self,context,event):
        if event.type in {'ESC','RIGHTMOUSE'}:
            selection_boxes.pop(context.area.as_pointer(),None)
            interaction_redraw(context)
            return {'CANCELLED'}
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.start = interaction_point(context,event)
        if self.start and event.type == 'MOUSEMOVE':
            p = interaction_point(context,event)
            selection_boxes[context.area.as_pointer()] = (self.start,p)
            interaction_redraw(context)
        if self.start and event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            tree = rendering_tree_of(context)
            p = interaction_point(context,event)
            lo = [min(self.start[k],p[k]) for k in (0,1)]
            hi = [max(self.start[k],p[k]) for k in (0,1)]
            chosen = selection_of(tree)
            if not self.extend:
                chosen.clear()
            options = preferences_prefs(context)
            box_ties = {t['id'] for t in rendering_display_ties(context,tree,data_read(tree))
                        if geometry_marker_overlaps_rect(t,lo,hi,options.spacing,options.width,options.tie_style)}
            chosen.update(box_ties)
            for n in tree.nodes:
                if routing_managed(n) and n.get(routing_TIE) in box_ties:
                    n.select = False
            for n in tree.nodes:
                if not self.extend:
                    n.select = False
                scale = context.preferences.system.ui_scale
                p = n.location_absolute
                width,height = n.dimensions.x/scale,n.dimensions.y/scale
                overlaps = p.x <= hi[0] and p.x+width >= lo[0] and p.y >= lo[1] and p.y-height <= hi[1]
                if overlaps and not routing_managed(n):
                    n.select = True
            interaction_redraw(context)
            selection_boxes.pop(context.area.as_pointer(),None)
            return {'FINISHED'}
        return {'RUNNING_MODAL'}


class TRZ_OT_move_nodes(interaction_NodeOperator,bpy.types.Operator):
    bl_idname = 'tie.rz_move_selection'
    bl_label = 'Move Selected Nodes and Ties'
    bl_options = {'UNDO','BLOCKING'}
    bl_description = 'Move selected nodes and ties together; click/Enter confirms, Esc cancels'

    @classmethod
    def poll(cls,context):
        tree = rendering_tree_of(context)
        return bool(tree and tree.is_editable and (
            any(n.select and not routing_managed(n) for n in tree.nodes) or
            any(t['id'] in selection_of(tree) for t in data_read(tree))))

    def invoke(self,context,event):
        self.tree = rendering_tree_of(context)
        self.nodes = [(n,tuple(n.location)) for n in self.tree.nodes if n.select and not routing_managed(n)]
        self.ties = data_read(self.tree)
        chosen_ties = selection_of(self.tree)
        selected_nodes = {data_uid(n) for n,_ in self.nodes}
        self.moving_ties = set()
        for tie in self.ties:
            endpoints = {v for key in tie['members']
                         for v in (json.loads(key)[0],json.loads(key)[2])}
            if tie['id'] in chosen_ties or (selected_nodes and endpoints <= selected_nodes):
                self.moving_ties.add(tie['id'])
        self.guides = ({tie['id']:transforms_slide_guide(self.tree,tie,context)
                        for tie in self.ties if tie['id'] in self.moving_ties}
                       if not self.nodes else {})
        self.slide = False
        self.start = interaction_point(context,event)
        context.window_manager.modal_handler_add(self)
        context.workspace.status_text_set('Move nodes and ties • Click/Enter confirm • Esc/right-click cancel')
        return {'RUNNING_MODAL'}

    def modal(self,context,event):
        cancel = event.type in {'ESC','RIGHTMOUSE'} and event.value == 'PRESS'
        if event.type == 'G' and event.value == 'PRESS' and not self.nodes and self.moving_ties and not self.slide:
            self.slide = True
            context.workspace.status_text_set('Slide selected ties between neighbours • Click/Enter confirm • Esc/right-click cancel')
            return {'RUNNING_MODAL'}
        if cancel:
            for node,pos in self.nodes:
                node.location = pos
            data_write(self.tree,self.ties)
            context.workspace.status_text_set(None)
            interaction_redraw(context)
            return {'CANCELLED'}
        if event.type == 'MOUSEMOVE':
            d = geometry_sub(interaction_point(context,event),self.start)
            for n,pos in self.nodes:
                # Children of selected frames already inherit their parent's movement.
                parent = n.parent
                ancestors_selected = False
                while parent:
                    ancestors_selected |= parent.select
                    parent = parent.parent
                if not ancestors_selected:
                    n.location = geometry_add(pos,d)
            ties = copy.deepcopy(self.ties)
            for t in ties:
                if t['id'] in self.moving_ties:
                    position = geometry_add(t['pos'],d)
                    if self.slide and t['id'] in self.guides:
                        position = transforms_project(self.guides[t['id']],position)
                    t['pos'] = list(position)
            data_write(self.tree,ties)
            interaction_redraw(context)
        if event.type in {'LEFTMOUSE','RET'} and event.value == 'PRESS':
            context.workspace.status_text_set(None)
            return {'FINISHED'}
        return {'RUNNING_MODAL'}


def interaction_add_keymaps():
    kc = bpy.context.window_manager.keyconfigs.addon
    if not kc:
        return
    km = kc.keymaps.new(name='Node Editor',space_type='NODE_EDITOR')
    # key_modifier preserves the bare Blender key command. Menu command also works without key.
    key = preferences_prefs(bpy.context).gesture_key
    entries = [('tie.rz_gesture','LEFTMOUSE','PRESS',dict(key_modifier=key)),
               ('tie.rz_pick','LEFTMOUSE','PRESS',dict(any=True)),
               ('tie.rz_pick','RIGHTMOUSE','PRESS',dict(any=True))]
    for op,kind,value,kw in entries:
        item = km.keymap_items.new(op,kind,value,**kw)
        interaction_keymaps.append((km,item))
    interaction_keymaps.append((km,km.keymap_items.new('tie.rz_hover','MOUSEMOVE','ANY',any=True)))
    # Circle Select clears tie selection at the beginning of an empty-canvas
    # stroke and transfers helper selection once, when that stroke ends.
    for name in ('Node Tool: Select Circle','Node Tool: Select Circle (fallback)'):
        try:
            circle_km = kc.keymaps.new(name=name,space_type='NODE_EDITOR',
                                       region_type='WINDOW',tool=True)
            for kind,value in [('LEFTMOUSE','PRESS'),('LEFTMOUSE','RELEASE')]:
                item = circle_km.keymap_items.new(
                    'tie.rz_circle_clear_ties',kind,value,any=True)
                interaction_keymaps.append((circle_km,item))
        except (TypeError,RuntimeError):
            continue
    interaction_keymaps.append((km,km.keymap_items.new('tie.rz_rotate','R','PRESS')))
    interaction_keymaps.append((km,km.keymap_items.new('tie.rz_move_selection','G','PRESS')))
    interaction_keymaps.append((km,km.keymap_items.new('tie.rz_scale','S','PRESS')))
    interaction_keymaps.append((km,km.keymap_items.new('tie.rz_match_scale','S','PRESS',alt=True)))
    interaction_keymaps.append((km,km.keymap_items.new('tie.rz_name','N','PRESS')))
    interaction_keymaps.append((km,km.keymap_items.new('tie.rz_color','C','PRESS')))
    item = km.keymap_items.new('tie.rz_edit','X','PRESS')
    item.properties.action = 'DELETE'
    item.properties.delete_nodes = False
    interaction_keymaps.append((km,item))
    for key in ['DEL','BACK_SPACE']:
        item = km.keymap_items.new('tie.rz_edit',key,'PRESS')
        item.properties.action = 'DELETE'
        item.properties.delete_nodes = True
        interaction_keymaps.append((km,item))


def interaction_remove_keymaps():
    for km,item in interaction_keymaps:
        km.keymap_items.remove(item)
    interaction_keymaps.clear()


interaction_classes = [TRZ_OT_hover,TRZ_OT_gesture,TRZ_OT_pick,TRZ_OT_circle_clear_ties,TRZ_OT_move,TRZ_OT_scale,TRZ_OT_match_scale,TRZ_OT_rotate,TRZ_OT_name,TRZ_OT_color,TRZ_OT_color_popup,TRZ_OT_delete,TRZ_OT_edit,TRZ_OT_cleanup_addon_data,TRZ_OT_box,TRZ_OT_move_nodes]


# ==========================================================================
# module: ui
# ==========================================================================

import os
import bpy
import bpy.utils.previews


def ui__addon_version():
    try:
        import tomllib
        path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'blender_manifest.toml')
        with open(path, 'rb') as handle:
            data = tomllib.load(handle)
        return str(data.get('version', ''))
    except Exception:
        return ''


ui__icon_collections = {}


def ui_register_icons():
    if 'main' in ui__icon_collections:
        return
    collection = bpy.utils.previews.new()
    icon_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'assets', '1_macho_hoe.png')
    if os.path.isfile(icon_path):
        preview = collection.load('TieRZ_machocat_tab', icon_path, 'IMAGE')
        TRZ_PT_panel.bl_icon_value = preview.icon_id
        ui__icon_collections['main'] = collection
    else:
        bpy.utils.previews.remove(collection)
        print(f"[TieRZ] MachoCAT tab icon not found: {icon_path}")


def ui_sync_panel_state(context,tree,ties):
    panel = preferences_prefs(context)
    signature = ','.join(t['id'] for t in ties)
    selection_changed = panel.synced_selection != signature
    panel.synced_selection = signature
    main = ties[0] if ties else None
    name = main.get('name','') if main else ''
    color = tuple(main['color']) if main else (.55,.55,.58,1)
    spacing = geometry_effective_spacing(main,panel.spacing) if main else panel.spacing
    # Only pull the color back when the selection changes; otherwise the color
    # picker would be reset mid-drag and live preview would stop.
    if (selection_changed
            or panel.selected_tie_name != name
            or abs(panel.selected_tie_spacing - spacing) > 1e-4):
        panel.panel_syncing = True
        panel.selected_tie_name = name
        if selection_changed:
            panel.selected_tie_color = data_color_srgb_to_linear(color)
        panel.selected_tie_spacing = spacing
        panel.panel_syncing = False


def ui_unregister_icons():
    for collection in ui__icon_collections.values():
        bpy.utils.previews.remove(collection)
    ui__icon_collections.clear()


def ui_state(context):
    tree = rendering_tree_of(context)
    chosen = selection_of(tree) if tree else set()
    return tree, [t for t in data_read(tree) if t['id'] in chosen] if tree else []


def ui_selected_actions(layout,context):
    tree,chosen = ui_state(context)
    if tree:
        layout.context_pointer_set('node_tree',tree)
    col = layout.column(align=True)
    col.enabled = bool(tree and tree.is_editable and chosen)
    rename = col.row()
    rename.enabled = bool(tree and tree.is_editable and len(chosen)==1)
    rename_op = rename.operator('tie.rz_name',text=i18n_tr('Name (N)'),translate=False)
    rename_op.ui_hide_shortcut = False
    col.operator('tie.rz_color_popup',text=i18n_tr('Color (C)'),translate=False)
    remove_row = col.row()
    remove_row.alert = True
    remove_text = i18n_tr('Remove Tie' if len(chosen)==1 else 'Remove Ties')
    remove_row.operator('tie.rz_delete',text=remove_text + ' (X)',translate=False)


class TRZ_PT_color_popover(bpy.types.Panel):
    bl_label = 'Tie Color'
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'HEADER'

    def draw(self,context):
        layout = self.layout
        layout.ui_units_x = 11
        options = preferences_prefs(context)
        tree,chosen = ui_state(context)
        ui_sync_panel_state(context,tree,chosen)
        col = layout.column()
        col.enabled = bool(tree and tree.is_editable and chosen)
        col.template_color_picker(options,'selected_tie_color',value_slider=True,cubic=False)
        col.prop(options,'selected_tie_color',text='')


class TRZ_MT_context(bpy.types.Menu):
    bl_label = 'TieRZ'

    def draw(self,context):
        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'
        tree,chosen = ui_state(context)
        ui_sync_panel_state(context,tree,chosen)
        key = preferences_prefs(context).gesture_key
        hints = layout.column(align=True)
        hints.enabled = False
        hints.label(text=i18n_tr('Hold {key} and drag across wires').format(key=key),icon='MOUSE_LMB')
        hints.label(text=i18n_tr('Match Sizes'),icon='MOD_LENGTH')
        layout.separator()
        col = layout.column()
        col.enabled = bool(tree and tree.is_editable and chosen)
        rotate_op = col.operator('tie.rz_rotate',text=i18n_tr('Rotate (R)'),translate=False)
        rotate_op.ui_hide_shortcut = False
        scale_op = col.operator('tie.rz_scale',text=i18n_tr('Spacing (S)'),translate=False)
        scale_op.ui_hide_shortcut = False
        ui_selected_actions(layout,context)


class TRZ_PT_panel(bpy.types.Panel):
    bl_label = 'TieRZ'
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'TieRZ'
    bl_icon_value = 0

    def draw(self,context):
        layout = self.layout
        options = preferences_prefs(context)
        tree,chosen = ui_state(context)
        ui_sync_panel_state(context,tree,chosen)
        layout.operator_context = 'INVOKE_DEFAULT'

        split = layout.split(factor=0.5)
        split.column().label(text='V ' + ui__addon_version())
        right = split.column()
        right.alignment = 'RIGHT'
        right.label(text='by NARZ')
        quick = layout.box()
        quick.label(text=i18n_tr('Quick Access'),icon='INFO',translate=False)
        key_split = quick.split(factor=0.5,align=True)
        key_split.label(text=i18n_tr('Hold key'),translate=False)
        key_split.prop(options,'gesture_key',text='')
        quick.label(text=i18n_tr('Hold {key} and drag across wires').format(key=options.gesture_key),
                    icon='MOUSE_LMB',translate=False)
        if not tree:
            quick.label(text=i18n_tr('Open a node tree to start.'),translate=False)
        elif not tree.is_editable:
            quick.label(text=i18n_tr('This node tree is read-only.'),icon='LOCKED',translate=False)

        box = layout.box()
        box.label(text=f"{i18n_tr('Selected Ties')} · {len(chosen)}",icon='LINKED',translate=False)
        if chosen:
            name_row = box.row()
            name_row.enabled = bool(tree and tree.is_editable and len(chosen)==1)
            name_row.prop(options,'selected_tie_name',text=i18n_tr('Name'),translate=False)
            color_row = box.row(align=True)
            color_row.enabled = bool(tree and tree.is_editable)
            color_row.prop(options,'selected_tie_color',text=i18n_tr('Color'),translate=False)
            remove_row = box.row()
            remove_row.alert = True
            op = remove_row.operator('tie.rz_edit',text=i18n_tr('Remove Selected Ties'),icon='X',translate=False)
            op.action = 'DELETE'
            match = box.row()
            match.enabled = len(chosen) > 1
            match.operator('tie.rz_match_scale',text=i18n_tr('Match Sizes'),icon='MOD_LENGTH',translate=False)
        else:
            box.label(text=i18n_tr('Select a tie to edit its name and color.'),translate=False)

        layout.separator()
        appearance = layout.box()
        appearance.label(text=i18n_tr('Appearance'),icon='PREFERENCES',translate=False)
        visibility = appearance.row(align=True)
        visibility.prop(options,'enabled',text=i18n_tr('Show Ties'),translate=False)
        visibility.prop(options,'show_names',text=i18n_tr('Names'),translate=False)
        appearance.prop(options,'show_ties_in_front',text=i18n_tr('Show Ties In Front of Nodes'),translate=False)
        design_split = appearance.split(factor=0.5,align=True)
        design_split.label(text=i18n_tr('Tie Design'),translate=False)
        design_split.prop(options,'tie_style',text='')
        dimensions = appearance.row(align=True)
        if chosen:
            dimensions.prop(options,'selected_tie_spacing',text=i18n_tr('Spacing'),translate=False)
        else:
            dimensions.prop(options,'spacing',text=i18n_tr('Spacing'),translate=False)
        dimensions.prop(options,'width',text=i18n_tr('Width'),translate=False)
        color = appearance.row(align=True)
        color.label(text=i18n_tr('New Tie Color'),translate=False)
        color.prop(options,'color_mode',text='')

        layout.separator()
        maintenance = layout.box()
        maintenance.label(text=i18n_tr('Maintenance'),icon='TOOL_SETTINGS',translate=False)
        prune = maintenance.row()
        prune.enabled = bool(tree and tree.is_editable and data_read(tree))
        prune.operator('tie.rz_edit',text=i18n_tr('Remove Missing Wire References'),
                       icon='BRUSH_DATA',translate=False).action = 'PRUNE'

        if rendering_last_error:
            layout.label(text=rendering_last_error,icon='ERROR')
        layout.separator()
        layout.label(text=i18n_tr('Before uninstall'),translate=False)
        cleanup_row = layout.row()
        cleanup_row.alert = True
        cleanup_row.operator('tie.rz_cleanup_addon_data',
                             text=i18n_tr('Clean Add-on Data'),icon='TRASH',translate=False)


def ui_context_menu(self,context):
    tree = rendering_tree_of(context)
    if tree and selection_of(tree):
        self.layout.separator()
        self.layout.menu('TRZ_MT_context',text='TieRZ')


ui_classes = [TRZ_MT_context,TRZ_PT_color_popover,TRZ_PT_panel]


# ==========================================================================
# module: __init__
# ==========================================================================

"""TieRZ: native reroute bundles for unmodified Blender."""
import bpy
from bpy.app.handlers import persistent

__init___classes = [TRZ_Preferences] + interaction_classes + clipboard_classes + ui_classes


@persistent
def __init___reset_runtime(*_):
    global clipboard_payload
    selection_clear()
    clipboard_payload = None


def __init___migrate_routes():
    """Upgrade old overlay-only ties once, outside any drawing callback."""
    trees = list(bpy.data.node_groups)
    trees += [m.node_tree for m in bpy.data.materials if m.node_tree]
    trees += [w.node_tree for w in bpy.data.worlds if w.node_tree]
    for tree in trees:
        if tree.is_editable and data_KEY in tree:
            ties = data_read(tree)
            needed = {(t['id'],k) for t in ties for k in t['members']}
            existing = {(n.get(routing_TIE),n.get(routing_OWNER)) for n in tree.nodes if routing_managed(n)}
            if needed - existing or (needed and tree.get(routing_LAYOUT_KEY) != routing_LAYOUT_VERSION):
                data_write(tree,ties)
    return None


@persistent
def __init___load_routes(*_):
    __init___migrate_routes()


def register():
    ui_register_icons()
    for cls in __init___classes:
        cls.bl_translation_context = i18n_DOMAIN
        bpy.utils.register_class(cls)
    language_mode = 'AUTO'
    try:
        addon = bpy.context.preferences.addons.get(__name__)
        if addon:
            language_mode = addon.preferences.language_mode
    except Exception:
        pass
    i18n_register(language_mode)
    bpy.types.NODE_MT_context_menu.append(ui_context_menu)
    interaction_add_keymaps()
    rendering_register()
    bpy.app.handlers.load_post.append(__init___load_routes)
    bpy.app.timers.register(__init___migrate_routes,first_interval=.1)
    for handlers in [bpy.app.handlers.load_post,bpy.app.handlers.undo_post,bpy.app.handlers.redo_post]:
        handlers.append(__init___reset_runtime)


def unregister():
    global clipboard_payload
    i18n_unregister()
    if bpy.app.timers.is_registered(__init___migrate_routes):
        bpy.app.timers.unregister(__init___migrate_routes)
    if __init___load_routes in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(__init___load_routes)
    rendering_unregister()
    interaction_remove_keymaps()
    bpy.types.NODE_MT_context_menu.remove(ui_context_menu)
    for handlers in [bpy.app.handlers.load_post,bpy.app.handlers.undo_post,bpy.app.handlers.redo_post]:
        if __init___reset_runtime in handlers:
            handlers.remove(__init___reset_runtime)
    selection_clear()
    clipboard_payload = None
    for cls in reversed(__init___classes):
        bpy.utils.unregister_class(cls)
    ui_unregister_icons()
