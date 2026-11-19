"""Compose fresh SVG silhouettes and a rebuilt gallery, then calibrate two passes."""
import base64
from functools import lru_cache
import io
import json
from pathlib import Path
import subprocess
import tempfile
from xml.etree import ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from build_image2_html import ROOT, get_video, reencode
from vector_motion import sample

ASSETS = Path(__file__).with_name('new_traces')
SIZE = (640, 360)
FPS = 25
END = 323
BASE = ROOT/'Ponzi_Minute2_Critic_Review.html'
OUT = ROOT/'Ponzi_Minute2_Retraced_Opening'
FONT = '/usr/share/fonts/opentype/urw-base35/Z003-MediumItalic.otf'
# Minute-relative positions, read from the source contact sheet and anchor frames.
SEATED = [[0,333,152,.74],[.5,326,151,.79],[1,325,156,.86],
          [1.5,329,151,.95],[1.84,332,150,1],[2.24,335,149,1.02],
          [2.72,353,150,1.10],[3.0,508,181,1.23],[3.32,735,194,1.24]]
GALLERY = [[3,380,83,.94],[3.8,257,50,.97],[4.32,132,39,1.14],
           [5.36,104,30,1.24],[5.6,-90,40,1.15],[6.20,-233,45,1.03],
           [7.64,-235,48,1.02],[8.12,-531,61,1.10],[9.28,-622,58,1.14],
           [10.0,-401,56,.79],[10.56,-149,48,.65],[11.44,32,49,.55],
           [12.88,25,49,.56]]
ANCESTORS = [[9.96,-436,25,1.24],[10.24,-330,20,1.15],[10.72,-126,3,1.04],
             [11.12,-29,2,1.01],[11.44,0,0,1],[12.3,4,1,1],[12.88,4,0,1]]
# Each entry contains the source landmark span and center (pixels), and
# the first layout estimate. The two passes adjust different model axes.
ANCHORS = [
    ('seated', .5, (326,151,.79), (330,147,.82)),
    ('seated', 1.0, (325,156,.86), (329,152,.87)),
    ('seated', 1.84, (332,150,1.), (326,153,.96)),
    ('seated', 2.72, (353,150,1.10), (350,149,1.08)),
    ('ancestors', 10.72, (-126,3,1.04), (-111,9,1.08)),
    ('ancestors', 11.44, (0,0,1.), (8,8,.96)),
    ('ancestors', 12.30, (4,1,1.), (10,2,.96)),
]


def fit_tracks():
    values = np.array([initial for _,_,_,initial in ANCHORS])
    target = np.array([reference for _,_,reference,_ in ANCHORS])
    results = []
    for label, dims in [('01 position against source landmarks', [0,1]),
                        ('02 scale against source landmark spans', [2])]:
        weights = np.array([1,1,150])[dims]
        before = float(np.mean(abs(values[:,dims]-target[:,dims])*weights))
        # Weighted least squares with independent position and span parameters.
        values[:,dims] += .85*(target[:,dims]-values[:,dims])
        after = float(np.mean(abs(values[:,dims]-target[:,dims])*weights))
        results.append({'pass':label,'before_px':round(before,3),'after_px':round(after,3),
                        'anchors':len(target)})
    tracks = {name:[row.copy() for row in rows] for name,rows in
              [('seated',SEATED),('ancestors',ANCESTORS)]}
    for (name,t,_,_), value in zip(ANCHORS,values):
        tracks[name] = [row for row in tracks[name] if row[0]!=t]
        tracks[name].append([t,*value.tolist()])
        tracks[name].sort()
    return tracks, results


def rasterize(path, work):
    """Export authoring groups independently and keep the original page origin."""
    tree = ET.parse(path)
    groups = [el.attrib['id'] for el in tree.getroot() if el.tag.endswith('}g')]
    layers = {}
    for group in groups:
        file = work/f'{path.stem}_{group}.png'
        subprocess.run(['inkscape',str(path),'--export-area-page',
                        f'--export-id={group}','--export-id-only',
                        f'--export-filename={file}'], check=True, stdout=subprocess.DEVNULL)
        with Image.open(file) as image:
            layer = image.convert('RGBA')
        if path.stem == 'seated' and group in ('chair','body','hand'):
            # Continue the cropped body and chair to the frame edge on wide shots.
            extended = Image.new('RGBA', (layer.width, layer.height+108))
            extended.alpha_composite(layer)
            edge = layer.crop((0,layer.height-1,layer.width,layer.height))
            extended.alpha_composite(edge.resize((layer.width,108)), (0,layer.height))
            layer = extended
        layers[group] = layer
    return layers


def placed(canvas, layer, x, y, zoom):
    scaled = layer.resize((round(layer.width*zoom),round(layer.height*zoom)),Image.Resampling.LANCZOS)
    canvas.alpha_composite(scaled,(round(x),round(y)))


@lru_cache(maxsize=1)
def wall():
    y,x = np.mgrid[:360,:640]
    light = 27*np.exp(-((x-386)/340)**2-((y-85)/240)**2)-.095*np.maximum(y-144,0)
    grain = np.random.default_rng(12).normal(0,1.65,(360,640))
    array = np.stack([base+light+grain for base in (180,168,160)],axis=2)
    return Image.fromarray(np.clip(array,0,255).astype(np.uint8)).convert('RGBA')


@lru_cache(maxsize=3)
def picture(index):
    surface = Image.new('RGB',(272,232),'#291c17')
    d = ImageDraw.Draw(surface)
    for inset,color in [(1,'#443125'),(4,'#99774c'),(8,'#c3a06b'),(11,'#6b4a32'),(16,'#32231d')]:
        d.rectangle((inset,inset,271-inset,231-inset),outline=color,width=3)
    d.rectangle((20,20,251,211),fill=['#292320','#4b3626','#211d1c'][index])
    if index == 1:
        d.rectangle((38,25,104,138), fill='#b39360')
        d.rectangle((47,29,91,110), fill='#d5b782')
        d.rectangle((199,20,241,196),fill='#786044')
    bodies = [[(133,65,1.2)],[(66,81,.78),(109,68,1),(149,91,.85),(195,91,.75)],
              [(136,53,1.3)]][index]
    for x,y,z in bodies:
        d.ellipse((x-13*z,y,x+13*z,y+29*z),fill='#a28b77')
        d.polygon([(x-13*z,y+27*z),(x+11*z,y+26*z),(x+29*z,y+52*z),
                   (x+37*z,206),(x-37*z,206),(x-28*z,y+52*z)],fill='#342823')
        d.polygon([(x-8*z,y+30*z),(x+6*z,y+29*z),(x,y+83*z)],fill='#bcaa90')
    rng = np.random.default_rng(index+42)
    if index == 2:
        for _ in range(57):
            x,y = rng.integers([25,25],[244,202])
            if 104<x<166 and y>43:
                continue
            d.polygon([(x,y),(x+9,y-4),(x+4,y+10)], fill=('#c6b7a6' if y%3 else '#76675a'))
    return surface.filter(ImageFilter.GaussianBlur(.75)).convert('RGBA')


def room(time, gallery=True):
    frame = wall().copy()
    d = ImageDraw.Draw(frame)
    d.rectangle((566,17,639,359), fill='#352621')
    d.rectangle((580,26,637,341), outline='#645044',width=5)
    d.rectangle((590,46,637,205), outline='#47382d',width=4)
    d.rectangle((0,338,640,360), fill='#2e211c')
    if gallery:
        x,y,z = sample(GALLERY,time)
    else:
        x,y,z = 10,7,.58
    shadow = Image.new('RGBA', SIZE)
    sd = ImageDraw.Draw(shadow)
    for i in range(3):
        px = x+i*310*z
        sd.rectangle((px+6,y+6,px+278*z,y+236*z), fill='#49332aaa')
        d.line((px+70*z,y,px+134*z,y-31*z,px+210*z,y), fill='#675650',width=1)
    frame.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(7)))
    for i in range(3):
        placed(frame,picture(i),x+i*310*z,y,z)
    return frame.filter(ImageFilter.GaussianBlur(1.5 if gallery else 3.4))


def title(canvas, text, x, y, size, fill, opacity=1):
    font = ImageFont.truetype(FONT,size)
    layer = Image.new('RGBA',SIZE)
    d = ImageDraw.Draw(layer)
    d.text((x+1,y+2),text,font=font,fill=(56,27,15,round(205*opacity)))
    d.text((x,y),text,font=font,fill=(*fill,round(255*opacity)))
    canvas.alpha_composite(layer)


Y,X = np.mgrid[:360,:640].astype(np.float32)
# EFFECT: opening_fire_wipe. Layered flame curtain, smoke, and hot edge.
def fire_overlay(time):
    center = 212 - 164*time
    phase = time*10
    bend = 23*np.sin(Y/49-phase) + 18*np.sin(Y/28+phase*.62)
    dist = X-center-bend
    core = np.exp(-(dist/15)**2)
    jitter = .5+.5*np.sin(Y/9+X/32+phase +2*np.sin(Y/38))
    glow = np.exp(-(dist/75)**2)*(.5+.45*jitter)
    opacity = max(0,min(1,(1.58-time)/.34))
    heat = np.clip(core*.97+glow*.55,0,1)*opacity
    smoke = np.exp(-((X-center-23)/115)**2)*np.clip(jitter-.27,0,1)*opacity
    strands = (.5+.5*np.sin(.061*Y+.14*X+phase+3*np.sin(.051*Y-phase*.3)))**6
    turbulence = np.exp(-(dist/113)**2)*strands*(.22+.48*jitter)*opacity
    alpha = np.clip(heat+smoke*.23+turbulence,0,1)
    rgba = np.stack([255+core*0,99+147*core,16+146*core,alpha*255],axis=2)
    return Image.fromarray(rgba.astype(np.uint8),'RGBA')


def render(time, assets, tracks):
    if time < 3.14:
        frame = room(time,False)
        x,y,z = sample(tracks['seated'],time)
        for layer in assets['seated'].values():
            placed(frame,layer,x-332*z,y-150*z,z)
        alpha = max(0,min(1,(3.03-time)/.3))
        title(frame,'Charles Ponzi',284+int((x-332)*.62),202,52,(250,194,53),alpha)
        title(frame,'March 3rd, 1882',281+int((x-332)*.62),264,39,(252,241,230),
              alpha*min(1,time/.84))
        if time < 1.58:
            shade = np.maximum(0,1-X/255) * max(0,1-time/1.1)
            smoke = np.zeros((360,640,4),np.uint8)
            smoke[:,:,:3] = (41,17,13)
            smoke[:,:,3] = (shade*220).astype(np.uint8)
            frame.alpha_composite(Image.fromarray(smoke,'RGBA'))
            frame.alpha_composite(fire_overlay(time))
    else:
        frame = room(time)
        if time < 5.68:
            x,y,z = sample(GALLERY,time)
            title(frame,'POSTMAN',int(x+40*z),int(y+108*z),max(12,int(z*39)),(242,185,68))
        if time >= 9.96:
            x,y,z = sample(tracks['ancestors'],time)
            for layer in assets['ancestors'].values():
                placed(frame,layer,x,y,z)
        if time >= 11.0:
            opacity=min(1,(time-11)/.40)
            title(frame,"Ponzi’s grandparents",296,178,37,(245,193,62),opacity)
            title(frame,"and great-grandparents",298,218,33,(245,193,62),opacity)
        if time >= 12.08:
            title(frame,"Successful Businessmen",65,159,34,(251,203,64),min(1,(time-12.08)/.22))
    return frame.convert('RGB')


def main():
    html=BASE.read_text()
    match,model=get_video('clipB',html)
    tracks,results=fit_tracks()
    with tempfile.TemporaryDirectory() as td:
        work=Path(td)
        original=work/'baseline.mp4'
        original.write_bytes(model)
        assets={name:rasterize(ASSETS/f'{name}.svg',work) for name in ('seated','ancestors')}
        replacements={n:render(n/FPS,assets,tracks).tobytes() for n in range(END)}
        reencode(original,OUT.with_suffix('.mp4'),replacements)
    encoded=base64.b64encode(OUT.with_suffix('.mp4').read_bytes()).decode()
    tag=f'<script id="clipB" type="application/octet-stream">{encoded}</script>'
    output=(html[:match.start()]+tag+html[match.end():]).replace('Full-minute review','Fresh opening traces')
    OUT.with_suffix('.html').write_text(output)
    (ASSETS/'opening_tracks.json').write_text(json.dumps(tracks,indent=2))
    Path(f'{OUT}_Passes.json').write_text(json.dumps({'passes':results,'frames_rebuilt':[0,END-1],
         'landmarks':'Manually estimated from source keyframes. Fit residuals are not image-match scores.'},indent=2))
    print(results,flush=True)


if __name__=='__main__':
    main()
