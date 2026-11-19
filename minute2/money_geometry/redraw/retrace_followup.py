"""Retrace the merchant and official montage and the following hat portrait."""
import base64
from functools import lru_cache
import json
from pathlib import Path
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from build_image2_html import get_video, reencode
from retrace_opening import ROOT, ASSETS, SIZE, FPS, rasterize, room, placed, title
from smoky_room import render_smoky_room
from vector_motion import sample

BASE = ROOT/'Ponzi_Minute2_Retraced_Opening.html'
OUT = ROOT/'Ponzi_Minute2_Retraced_Through22'
FIRST, LAST = 323, 467
TRACKS = {
    # Scale and offsets in the SVG's 640 × 360 source coordinates.
    'merchant': [[12.92,-140,15,.91],[13.20,-62,6,.98],[13.44,0,0,1],
                 [13.92,161,-1,1.05],[14.24,238,1,1.03],[14.76,515,22,1.04]],
    'official': [[13.76,-353,9,.92],[14.2,-250,2,.96],[14.68,0,0,1],
                 [15.18,52,-5,1.10],[15.44,170,9,1.14]],
    'ancestors': [[12.92,218,-63,1.40],[13.44,425,-89,1.48],[13.92,590,-92,1.48]],
    'hat': [[15.40,68,38,.82],[15.70,0,24,.94],[16.20,-11,1,1.02],
            [16.80,0,0,1],[17.30,-23,-7,1.13],[17.92,-29,-22,1.17],
            [18.36,-22,-18,1.16],[18.64,-30,-18,1.17]],
}
# Manually measured reference points from the repaired source, including
# two points on each portrait to constrain both translation and size.
KEYS = [
    ('merchant',13.44,[(254,122),(322,191)],[(254,122),(322,191)]),
    ('official',14.68,[(421,114),(421,181)],[(421,114),(421,181)]),
    ('hat',16.80,[(245,187),(440,151)],[(245,187),(440,151)]),
    ('hat',17.32,[(245,187),(440,151)],[(255,197),(471,155)]),
]


def calibrate(source_tracks=TRACKS, landmarks=KEYS):
    tracks = {name:[row.copy() for row in keys] for name,keys in source_tracks.items()}
    candidates = []
    for name,time,local,ref in landmarks:
        local, ref = np.array(local), np.array(ref)
        x,y,z = sample(tracks[name],time)
        candidates.append([name,time,local,ref,np.array([x,y]),z])
    report = []
    for label in ('translate landmark centers','fit landmark spacing'):
        before, after = [], []
        for entry in candidates:
            _, _, local, ref, offset, scale = entry
            prior = local*scale+offset
            before.append(float(np.linalg.norm(prior-ref,axis=1).mean()))
            if label == 'translate landmark centers':
                entry[4] = offset + (ref-prior).mean(axis=0)
            else:
                baseline = np.linalg.norm(local[1]-local[0])
                entry[5] = np.linalg.norm(ref[1]-ref[0])/baseline
                entry[4] = ref.mean(axis=0) - local.mean(axis=0)*entry[5]
            after.append(float(np.linalg.norm(local*entry[5]+entry[4]-ref,axis=1).mean()))
        report.append({'pass':label,'before_px':round(float(np.mean(before)),3),
                       'after_px':round(float(np.mean(after)),3),'keyframes':len(landmarks)})
    for name,time,_,_,offset,scale in candidates:
        keys = [row for row in tracks[name] if row[0]!=time]
        tracks[name] = sorted(keys + [[time,*offset.tolist(),float(scale)]])
    return tracks, report


@lru_cache(maxsize=2)
def dark_room():
    canvas = Image.new('RGBA', SIZE,'#211411')
    draw = ImageDraw.Draw(canvas)
    draw.polygon([(0,0),(81,0),(55,285),(0,360)], fill='#675047')
    draw.polygon([(246,0),(337,0),(371,360),(283,360)], fill='#33221f')
    draw.polygon([(493,0),(639,0),(639,360),(548,360)], fill='#4c3128')
    draw.line([(0,227),(261,198),(640,264)],fill='#483021',width=17)
    return canvas.filter(ImageFilter.GaussianBlur(18))


@lru_cache(maxsize=1)
def banknote():
    tile = Image.new('RGBA',(78,39),'#b9a77a')
    d = ImageDraw.Draw(tile)
    d.rectangle((3,3,74,35),outline='#736747',width=2)
    d.rectangle((7,7,70,31),outline='#e1d0a1',width=1)
    d.ellipse((26,6,52,33),fill='#7b7252',outline='#e0cb93')
    d.ellipse((37,10,45,20),fill='#c1ad7c')
    d.arc((32,17,49,29),180,360,fill='#c1ad7c',width=3)
    for x in (10,61):
        d.rectangle((x,11,x+7,13),fill='#7a6f4d')
        d.line((x,25,x+6,25),fill='#786949',width=2)
    return tile


def money(frame,time,front):
    rng = np.random.default_rng(318 if front else 272)
    for _ in range(12 if front else 17):
        sx,sy,rate,size,angle = rng.uniform([0,0,25,.22,-160],[780,510,92,1.10,160])
        x = (sx-47*time)%780-70
        y = (sy+rate*time)%510-85
        z = size*(1 if front else .54)
        tile=banknote().resize((max(1,round(78*z)),max(1,round(39*z))),Image.Resampling.LANCZOS)
        tile=tile.rotate(angle+time*(46 if front else 27),Image.Resampling.BICUBIC,expand=True)
        if front:
            tile=tile.filter(ImageFilter.GaussianBlur(float(.8+z*.75)))
        frame.alpha_composite(tile,(round(x),round(y)))


def draw_asset(frame, assets, tracks, key,time):
    x,y,z = sample(tracks[key],time)
    for layer in assets[key].values():
        placed(frame,layer,x,y,z)


def transition(frame,time):
    # Horizontal stage motion accelerates into each source cut. Work on the
    # composed frame so money, people, and titles smear in the same direction.
    a = max(0,1-abs(time-15.40)/.17)
    b = max(0,min(1,(time-18.37)/.24))
    amount=max(a*.53,b)
    if amount <= 0:
        return frame
    w,h=SIZE
    band=frame.resize((max(1,round(w/(1+amount*30))),h),Image.Resampling.BOX)
    return Image.blend(frame,band.resize(SIZE,Image.Resampling.BICUBIC),amount*.9)


def render(time,assets,tracks):
    if time<15.44:
        back=room(12.5)
        boundary = 265 + (time-12.92)*340
        ramp = np.clip((boundary - np.arange(SIZE[0]))/140, 0, 1)
        mask = Image.fromarray(np.broadcast_to((ramp*255).astype(np.uint8), SIZE[::-1]).copy())
        frame=Image.composite(dark_room(),back,mask)
        money(frame,time-12.92,False)
        if time<14.0:
            draw_asset(frame,assets,tracks,'ancestors',time)
        if time>=13.76:
            draw_asset(frame,assets,tracks,'official',time)
        if time<14.78:
            draw_asset(frame,assets,tracks,'merchant',time)
        money(frame,time-12.92,True)
        merchant_alpha=min(1,max(0,(time-12.98)/.25),max(0,(14.28-time)/.28))
        title(frame,'Merchants',104+round((time-13.44)*185),194,62,(255,221,35),merchant_alpha)
        official_alpha=min(1,max(0,(time-14.24)/.29),max(0,(15.44-time)/.19))
        title(frame,'Public',134,107,76,(255,222,36),official_alpha)
        title(frame,'Officials',135,193,76,(255,222,36),official_alpha)
    else:
        frame=render_smoky_room(time,(0,0,1,0),smoke=.44,fire=1.24)
        warm=Image.new('RGBA',SIZE)
        d=ImageDraw.Draw(warm)
        d.polygon([(0,0),(194,0),(147,118),(224,277),(133,360),(0,360)],fill='#891f12aa')
        d.polygon([(490,9),(640,40),(640,334),(493,278),(464,197)],fill='#993816cc')
        frame.alpha_composite(warm.filter(ImageFilter.GaussianBlur(23)))
        draw_asset(frame,assets,tracks,'hat',time)
        d=ImageDraw.Draw(frame)
        alpha=min(1,max(0,(time-17.02)/.22),max(0,(18.66-time)/.23))
        if alpha:
            # Keep the text on its own layer so the exposure and timing are editable.
            title(frame,'Ponzi',25,173,55,(250,215,92),alpha)
            title(frame,'from a young age',25,226,49,(249,239,225),alpha)
        if 17.45<time<18.51:
            shift=round((time-17.45)*32)
            glow=Image.new('RGBA',SIZE)
            gd=ImageDraw.Draw(glow)
            gd.line([(343+shift,273),(402+shift,181),(458+shift,273),(343+shift,273)],
                    fill='#ffdf45cc',width=7,joint='curve')
            frame.alpha_composite(glow.filter(ImageFilter.GaussianBlur(6)))
            frame.alpha_composite(glow)
    return transition(frame,time).convert('RGB')


def main():
    html=BASE.read_text()
    match, model=get_video('clipB',html)
    tracks, passes=calibrate()
    with tempfile.TemporaryDirectory(prefix='ponzi-followup-') as td:
        work=Path(td)
        old=work/'prior.mp4'
        old.write_bytes(model)
        assets={name:rasterize(ASSETS/f'{name}.svg',work)
                for name in ('ancestors','merchant','official','hat') if name!='hat'}
        assets['hat']=rasterize(ASSETS/'older_hat.svg',work)
        replacements={n:render(n/FPS,assets,tracks).tobytes() for n in range(FIRST,LAST)}
        reencode(old,OUT.with_suffix('.mp4'),replacements)
    payload=base64.b64encode(OUT.with_suffix('.mp4').read_bytes()).decode()
    tag=f'<script id="clipB" type="application/octet-stream">{payload}</script>'
    output=(html[:match.start()]+tag+html[match.end():]).replace('Fresh opening traces','Retraced through the close-up')
    OUT.with_suffix('.html').write_text(output)
    (ASSETS/'followup_tracks.json').write_text(json.dumps(tracks,indent=2))
    Path(f'{OUT}_Passes.json').write_text(json.dumps({'passes':passes,
         'new_frames':[FIRST,LAST-1], 'prior_closeup':[467,585],
         'measurement':'Manually located source landmarks, not image fidelity.'},indent=2))
    print(passes,flush=True)


if __name__=='__main__':
    main()
