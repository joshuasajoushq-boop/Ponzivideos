"""Procedural room, drifting smoke and firelight for the Ponzi close-up."""
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


WIDTH, HEIGHT = 640, 360
SMOKE_DENSITY = .66
FIRELIGHT = 1.0


@lru_cache(maxsize=1)
def room_plate():
    room = Image.new('RGB', (WIDTH, HEIGHT), '#211813')
    draw = ImageDraw.Draw(room)
    draw.polygon([(0, 0), (265, 0), (242, 190), (0, 239)], fill='#48342c')
    draw.polygon([(320, 0), (640, 0), (640, 219), (359, 173)], fill='#332822')
    draw.polygon([(310, 0), (388, 145), (371, 208), (242, 73)], fill='#181614')
    draw.polygon([(0, 225), (250, 179), (455, 202), (640, 310),
                  (640, 360), (0, 360)], fill='#291b16')
    draw.line([(45, -15), (77, 147), (46, 260)], fill='#211815', width=27)
    draw.line([(18, 163), (289, 139), (530, 180)], fill='#654135', width=16)
    draw.rectangle((519, 32, 564, 107), fill='#65432c')
    return room.filter(ImageFilter.GaussianBlur(13))


@lru_cache(maxsize=2)
def noise_tile(seed):
    rng = np.random.default_rng(seed)
    side = 512
    signal = np.zeros((side, side), dtype=np.float32)
    for cells, weight in ((5, .49), (11, .27), (24, .15), (49, .09)):
        data = rng.integers(0, 256, (cells, cells), dtype=np.uint8)
        grid = Image.fromarray(np.tile(data, (3, 3)))
        extended = grid.resize((side*3, side*3), Image.Resampling.BICUBIC)
        signal += np.asarray(extended.crop((side, side, side*2, side*2))) * (weight/255)
    return signal


Y, X = np.mgrid[:HEIGHT:2, :WIDTH:2].astype(np.float32)


def plume(seed, time, drift, phase):
    x = X*.59 + phase + drift*time + 13*np.sin(Y*.018 + time*.61)
    y = Y*.76 + 120 + time*11 + 15*np.sin(X*.013 - time*.32)
    return noise_tile(seed)[y.astype(int) % 512, x.astype(int) % 512]


def render_smoky_room(seconds, camera, *, smoke=SMOKE_DENSITY, fire=FIRELIGHT,
                      smoke_delay=0, fire_delay=0, falloff=1, room_depth=.34):
    time = seconds - 18.68
    shift_x, shift_y, zoom, _ = camera
    # The room is farther behind the camera subject and responds less to its move.
    far_zoom = 1 + (zoom-1)*room_depth
    left = np.clip(48-shift_x*.22/far_zoom, 0, WIDTH*(1-1/far_zoom))
    top = np.clip(10-shift_y*.22/far_zoom, 0, HEIGHT*(1-1/far_zoom))
    plate = room_plate().transform((WIDTH, HEIGHT), Image.Transform.AFFINE,
        (1/far_zoom, 0, left,
         0, 1/far_zoom, top),
        Image.Resampling.BICUBIC, fillcolor='#211813')
    room = np.asarray(plate.resize((WIDTH//2, HEIGHT//2))).astype(np.float32)
    far = plume(12, time-smoke_delay, -11, 60)
    near = plume(82, time-smoke_delay, 17, 125)
    density = np.clip((far-.32)*1.45 + (near-.50)*.84, 0, 1) * smoke
    glow = np.exp(-((X-626)/(92*falloff))**2-((Y-325)/101)**2)
    glow += .43*np.exp(-((X-55)/123)**2-((Y-265)/106)**2)
    time -= fire_delay
    glow *= fire * (.92+.08*np.sin(time*5.7))
    haze_color = np.array([98, 79, 75]) + glow[..., None] * [103, 49, 6]
    scene = room*(1-density[..., None]) + haze_color*density[..., None]
    scene += glow[..., None] * [44, 15, 1]
    # Ragged flames show through the edge of the haze.
    for i, (base, height, width) in enumerate(((623, 99, 14), (637, 68, 16), (609, 40, 14))):
        h = height*(.86+.15*np.sin(time*5.3+i*2.2))
        rise = np.clip((357-Y)/h, 0, 1)
        center = base + rise * (8*np.sin(Y*.07+time*8+i) - i*2)
        shape = np.exp(-((X-center)/((1-rise*.85)*width))**2)
        flame = shape*np.maximum(0, 1-rise**1.7) * (Y >= 357-h)
        flame *= (.55+.45*near)*fire
        scene += flame[..., None] * [225, 132, 47]
    image = Image.fromarray(np.clip(scene, 0, 255).astype(np.uint8))
    return image.resize((WIDTH, HEIGHT), Image.Resampling.BICUBIC).convert('RGBA')
