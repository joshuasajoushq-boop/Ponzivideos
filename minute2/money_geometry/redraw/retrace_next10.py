"""Render frames 586–835 with editable cutouts, type, and stage layers."""
import base64
from functools import lru_cache
import json
from pathlib import Path
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from build_image2_html import get_video, reencode
from retrace_opening import ROOT, ASSETS, SIZE, FPS, rasterize, placed
from retrace_followup import calibrate, money
from smoky_room import render_smoky_room
from vector_motion import draw_caption, sample, warp

BASE = ROOT/'Ponzi_Minute2_Retraced_Through22.html'
OUT = ROOT/'Ponzi_Minute2_Retraced_Through33'
FIRST, LAST = 586, 836
TRACKS = {
    'closeup': [[23.44,-183,-5,1.05],[23.76,-134,-2,1],[24.54,-136,-2,1],
                [25.0,145,-5,1.06],[25.6,154,-4,1.06],[28.16,109,-4,1.08],
                [28.32,140,-5,1.1]],
    'teen': [[28.36,-185,-98,1.56],[28.64,-56,-44,1.19],[29.28,50,36,.8],
             [29.96,52,40,.79],[30.40,105,69,.63],[31.92,105,69,.63],
             [32.44,-32,-33,1.09],[33.40,-71,-44,1.21]]
}
LANDMARKS = [
    ('closeup',24.00,[(387,47),(388,169)],[(332,29),(333,191)]),
    ('closeup',26.00,[(387,47),(388,169)],[(594,47),(595,228)]),
    ('teen',29.44,[(320,96),(317,265)],[(320,113),(318,276)]),
    ('teen',32.44,[(320,96),(317,265)],[(317,87),(315,292)]),
    ('teen',33.12,[(320,96),(317,265)],[(319,75),(316,288)]),
]


@lru_cache(maxsize=1)
def corridor():
    """Build a red corridor with separate geometry and lighting."""
    canvas=Image.new('RGBA',SIZE,'#23080d')
    d=ImageDraw.Draw(canvas)
    d.polygon([(0,0),(250,102),(253,275),(0,359)],fill='#5a090e')
    d.polygon([(640,0),(395,102),(392,275),(640,360)],fill='#4f080b')
    d.polygon([(0,360),(255,249),(396,249),(640,360)], fill='#650b10')
    d.rectangle((255,105,395,256),fill='#391016')
    for x,w,top,bottom in [(14,48,22,307),(78,41,45,281),(135,36,66,268),(184,26,83,254),
                            (419,25,88,253),(461,32,66,266),(512,39,51,287),(570,48,23,313)]:
        d.polygon([(x,top),(x+w,top+8),(x+w,bottom-6),(x,bottom)],fill='#250810')
        d.line([(x,top),(x,bottom),(x+w,bottom-6)],fill='#88151a',width=5)
    for row in range(107,319,22):
        d.line([(0,row),(236,188+(row-170)*.32)],fill='#6e0a11',width=2)
        d.line([(640,row),(407,188+(row-170)*.32)],fill='#67090e',width=2)
    data=np.array(canvas.filter(ImageFilter.GaussianBlur(1.7))).astype(np.float32)
    yy,xx=np.mgrid[:360,:640]
    haze=np.exp(-((xx-320)/226)**2-((yy-148)/145)**2)
    shade=.58+.42*np.exp(-((xx-320)/263)**2-((yy-187)/191)**2)
    grain=np.random.default_rng(77).normal(0,1.5,xx.shape)
    data[:,:,:3]=data[:,:,:3]*shade[:,:,None]+haze[:,:,None]*[56,3,13]+grain[:,:,None]
    return Image.fromarray(np.clip(data,0,255).astype(np.uint8))


def words(frame,time,text,x,y,width,height,color,start,end):
    line={'text':text,'size':[width,height],'fill':color,'reveal':[start,end]}
    caption={'pose':[[time-1,x,y,1,0],[time+1,x,y,1,0]],'lines':[line]}
    draw_caption(frame,time,caption)


def draw_coins(frame,time):
    d=ImageDraw.Draw(frame)
    for x,y,r,count in [(179,340,37,2),(235,338,35,7),(294,343,39,9),
                         (324,333,37,13),(370,359,46,8),(417,347,37,7),
                         (465,352,40,4),(201,355,50,4)]:
        for i in range(count):
            cy=y-i*6
            d.rounded_rectangle((x-r,cy-4,x+r,cy+6),radius=3,fill='#8d694c',outline='#ae8865')
            d.ellipse((x-r,cy-8,x+r,cy+2),fill='#d0a779',outline='#f1cf9e')
            d.arc((x-r+4,cy-6,x+r-4,cy+1),0,180,fill='#a1815d',width=1)
            for gx in range(x-r+4,x+r-2,5):
                d.line((gx,cy+3,gx,cy+5),fill='#71513f')
    y=206+min(30,max(0,(time-30.30)*50))
    d.ellipse((270,y,353,y+12),fill='#dab482',outline='#f3ce99',width=2)


def composite(frame,layers,track,time,fade=1):
    x,y,scale=sample(track,time)
    for layer in layers.values():
        if fade < 1:
            layer=layer.copy()
            layer.putalpha(layer.getchannel('A').point(lambda value:round(value*fade)))
        placed(frame,layer,x,y,scale)


def render(time,assets,tracks):
    if time<28.36:
        frame=render_smoky_room(time,(0,0,1,0),smoke=.6,fire=.92)
        money(frame,time-22.8,False)
        composite(frame,assets['closeup'],tracks['closeup'],time)
        if time<24.96:
            words(frame,time,'born rich',216,206,349,56,'#fff7e8',23.44,23.72)
            words(frame,time,'?',358,143,75,96,'#fff033',23.49,23.70)
        else:
            words(frame,time,'Enjoy a life of leisure without having',74,162,355,27,
                  '#fff8e8',24.96,25.96)
            words(frame,time,'to worry about a job or money?',74,190,319,27,
                  '#fff8e8',25.60,26.86)
            if time>=27.10:
                words(frame,time,'$',208,87,92,165,'#ffe430',27.10,27.28)
        money(frame,time-22.8,True)
        if time<23.64:
            frame=frame.filter(ImageFilter.GaussianBlur(5*max(0,(23.64-time)/.20)))
    else:
        frame=corridor().copy()
        label='TEENAGER' if time<33 else 'COLLEGE'
        width=506 if time<28.76 or time>32.22 else 362
        words(frame,time,label,(640-width)//2,67,width,69,'#ffe532',28.27,28.42)
        composite(frame,assets['teen'],tracks['teen'],time)
        if 30.16<=time<32.24:
            fade=max(0,min(1,(time-30.16)/.20,(32.24-time)/.16))
            # Hold the room behind the hand; only the fingers drift vertically.
            coins=Image.new('RGBA',SIZE)
            draw_coins(coins,time)
            coins.alpha_composite(assets['fingers']['hand'],(0,round(-95*(1-fade))))
            coins.putalpha(coins.getchannel('A').point(lambda a:round(a*fade)))
            frame.alpha_composite(coins)
            for i,line in enumerate(('following',"his father’s",'death')):
                words(frame,time,line,42,133+37*i,154 if i<2 else 94,32,'#e9dbce',
                      30.54+i*.23,30.81+i*.23)
        if time<28.76:
            angle=12*max(0,(28.76-time)/.40)
            padded=Image.new('RGBA',(920,640),'#30080d')
            padded.alpha_composite(frame,(140,140))
            frame=warp(padded,-angle,(460,320),zoom=1+angle*.010).crop((140,140,780,500))
    return frame.convert('RGB')


def main():
    html=BASE.read_text()
    match,model=get_video('clipB',html)
    tracks,passes=calibrate(TRACKS,LANDMARKS)
    with tempfile.TemporaryDirectory() as directory:
        work=Path(directory)
        old=work/'before.mp4'
        old.write_bytes(model)
        assets={'closeup':rasterize(ROOT/'upload/Ponzi_Anime_Closeup.svg',work),
                'teen':rasterize(ASSETS/'teen_suitcase.svg',work),
                'fingers':rasterize(ASSETS/'coin_fingers.svg',work)}
        replacements={n:render(n/FPS,assets,tracks).tobytes() for n in range(FIRST,LAST)}
        reencode(old,OUT.with_suffix('.mp4'),replacements)
    payload=base64.b64encode(OUT.with_suffix('.mp4').read_bytes()).decode()
    tag=f'<script id="clipB" type="application/octet-stream">{payload}</script>'
    result=(html[:match.start()]+tag+html[match.end():]).replace(
        'Retraced through the close-up','Retraced through 33.44s')
    OUT.with_suffix('.html').write_text(result)
    (ASSETS/'next10_tracks.json').write_text(json.dumps(tracks,indent=2))
    Path(f'{OUT}_Passes.json').write_text(json.dumps({
        'new_frames':[FIRST,LAST-1], 'passes':passes,
        'metric':'Residual in pixels against manually marked source anchors, not visual fidelity.'},indent=2))
    print(passes)


if __name__=='__main__':
    main()
