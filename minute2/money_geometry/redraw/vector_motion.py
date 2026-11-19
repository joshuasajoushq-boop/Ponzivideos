"""Reusable frame tracks and clean, font-outline captions."""
from functools import lru_cache
from pathlib import Path
import json
import math

from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT = Path('/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf')
TRACKS = json.loads(Path(__file__).with_name('image2_motion.json').read_text())


def sample(keys, time):
    """Interpolate any numeric channel tuple on a shared timeline."""
    for (start, *a), (end, *b) in zip(keys, keys[1:]):
        if time <= end:
            weight = max(0, (time - start) / (end - start))
            return tuple(x + (y - x) * weight for x, y in zip(a, b))
    return tuple(keys[-1][1:])


def warp(layer, angle, pivot, offset=(0, 0), zoom=1):
    """Rotate counterclockwise about an on-screen anchor, then translate."""
    x, y = pivot
    dx, dy = offset
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    c, s = c / zoom, s / zoom
    return layer.transform(layer.size, Image.Transform.AFFINE,
                           (c, -s, x-c*(x+dx)+s*(y+dy),
                            s, c, y-s*(x+dx)-c*(y+dy)),
                           Image.Resampling.BICUBIC)


@lru_cache(maxsize=16)
def line_art(text, width, height, fill, accent=None):
    font = ImageFont.truetype(str(FONT), 180)
    box = font.getbbox(text, stroke_width=2)
    art = Image.new('RGBA', (box[2]-box[0]+4, box[3]-box[1]+4))
    draw = ImageDraw.Draw(art)
    origin = (2-box[0], 2-box[1])
    draw.text(origin, text, font=font, fill=fill, stroke_width=2,
              stroke_fill='#523300' if fill == '#f3cb29' else '#362c29')
    if accent:
        start = text.index(accent)
        x = origin[0] + font.getlength(text[:start])
        draw.text((x, origin[1]), accent, font=font, fill='#7662df')
    return art.resize((width*3, height*3), Image.Resampling.LANCZOS)


def draw_caption(canvas, time, caption):
    x, y, scale, angle = sample(caption['pose'], time)
    pad = 256
    x, y = x + pad, y + pad
    size = (canvas.width+2*pad, canvas.height+2*pad)
    group = Image.new('RGBA', size)
    for line in caption['lines']:
        start, end = line['reveal']
        if time <= start:
            continue
        progress = min(1, (time-start)/(end-start))
        w, h = (max(1, round(value*scale)) for value in line['size'])
        art = line_art(line['text'], *line['size'], line['fill'], line.get('accent'))
        art = art.resize((w, h), Image.Resampling.LANCZOS)
        if progress < 1:
            if line.get('direction') == 'down':
                art = art.crop((0, 0, w, round(h*progress)))
            else:
                art = art.crop((0, 0, round(w*progress), h))
        lx, ly = line.get('offset', (0, 0))
        if 'offset_track' in line:
            dx, dy = sample(line['offset_track'], time)
            lx, ly = lx+dx, ly+dy
        group.alpha_composite(art, (round(x+lx*scale), round(y+ly*scale)))
    for mark in caption.get('brushes', []):
        start, end = mark['reveal']
        if time <= start:
            continue
        progress = min(1, (time-start)/(end-start))
        brush = Image.new('RGBA', size)
        px, py, width = mark['geometry']
        if 'brush_offset_track' in caption:
            dx, dy = sample(caption['brush_offset_track'], time)
            px, py = px+dx, py+dy
        points = [(0, 4), (8, 0), (width-8, 2), (width, 8), (width-4, 22),
                  (width-19, 27), (18, 26), (0, 20), (4, 12)]
        ImageDraw.Draw(brush).polygon([(x+(px+u)*scale, y+(py+v)*scale)
                                       for u,v in points], fill='#ffe224')
        edge = max(0, min(group.width, round(x+(px+width*progress)*scale)))
        group.alpha_composite(brush.crop((0, 0, edge, group.height)))
    posed = warp(group, angle, (x, y))
    if caption.get('camera') == 'question':
        posed = question_camera(posed, time, pad)
    canvas.alpha_composite(posed.crop((pad, pad, pad+canvas.width, pad+canvas.height)))


def question_camera(layer, time, pad):
    """Apply the same camera move to the question and portrait."""
    dx, dy, zoom, blur = sample(TRACKS['question_camera'], time)
    layer = warp(layer, 0, (pad, pad), (dx, dy), zoom)
    if blur:
        trail = layer.filter(ImageFilter.GaussianBlur(blur * .35))
        for offset in (-2, -1, 1, 2):
            smear = warp(layer, 0, (pad, pad), (offset*blur, 0))
            smear.putalpha(smear.getchannel('A').point(lambda alpha: alpha//5))
            trail.alpha_composite(smear)
        layer = trail
    return layer
