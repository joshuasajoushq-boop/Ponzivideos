#!/usr/bin/env python3
"""Ponzi V33 procedural corrective renderer, source-video-specific.

Source *documentary* is NEVER imported into this renderer. Its video is read by
QA only. All output comes from the V32 independent procedural master and
programmatically constructed procedural sprites.

The timeline retains object identity for each active scene. No random per-frame
sprite regeneration. Camera and object transforms have independent trajectories.
"""
from __future__ import annotations
import argparse, functools, importlib.util, json, math, os, subprocess, sys
from pathlib import Path
from typing import Any
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

HERE=Path(__file__).resolve().parent
ROOT=Path('/mnt/data')
V32_FILE=HERE/'ponzi_v32_renderer.py'
V30_FILE=HERE/'ponzi_v30_renderer.py'
spec=importlib.util.spec_from_file_location('v32_underlay',str(V32_FILE))
v32=importlib.util.module_from_spec(spec);sys.modules[spec.name]=v32;spec.loader.exec_module(v32)
v30=v32.v30
W,H,FPS,N=1280,720,25,1500
DEFAULTS={
    'portrait_zoom':.28,'portrait_x':330,'title_y':150,
    'network_scale':1.18,'network_dolly':.10,
    'scheme_title_size':1.00,'scheme_reveal_delay':0.0,
    'storm_slide_range':1100,'storm_zoom':.14,
    'charles_stretch':1.52,'charles_gold':.92,
    'chapter_depth_scale':1.05,'chapter_portrait_delay':.16,'chapter_fire':.96,
    'pyramid_cam_speed':1.45,'pyramid_near_scale':1.12,
    'global_exposure':1.0,
}
BOUNDS={
    'portrait_zoom':(.10,.48),'portrait_x':(260,395),'title_y':(105,210),
    'network_scale':(.91,1.40),'network_dolly':(.04,.22),
    'scheme_title_size':(.85,1.14),'scheme_reveal_delay':(-.20,.20),
    'storm_slide_range':(920,1280),'storm_zoom':(.06,.22),
    'charles_stretch':(1.28,1.72),'charles_gold':(.78,1.04),
    'chapter_depth_scale':(.9,1.17),'chapter_portrait_delay':(-.05,.36),'chapter_fire':(.7,1.10),
    'pyramid_cam_speed':(1.12,1.85),'pyramid_near_scale':(.92,1.3),
    'global_exposure':(.98,1.02),
}
INTERVALS=[('S01_PONZI_CLOCK',3.60,5.28),('S11_NETWORK',27.13,29.55),('S13_PONZI_SCHEME',32.38,34.52),('S14_HAND_STORM',34.52,38.02),('S17_CHARLES_TITLE',42.48,47.05),('S19_CHAPTER',48.45,55.12),('S21_PYRAMID_FLYTHROUGH',57.40,60.0)]

def ease(t,a,b):return v32.ease(t,a,b)
def paste(dst,spr,x,y,a=1.):return v32.pste(dst,spr,x,y,a)

def cfade(a,b,q):return v32.crossfade(a,b,q)

def image_from_bgr(fr):return Image.fromarray(cv2.cvtColor(fr,cv2.COLOR_BGR2RGBA),'RGBA')

@functools.lru_cache(1)
def ponzi_clock_background():
    im=v32.atmosphere(48,(61,28,23)).copy();d=ImageDraw.Draw(im,'RGBA')
    for j in range(20):
        s=1-j/20
        x0=638-(492-j*11);x1=638+(492-j*11);y0=346-(496-j*11);y1=346+(496-j*11)
        d.ellipse((x0,y0,x1,y1),outline=(245,201,136,int(70*s+55)),width=max(1,int(6-j*.17)))
    d.ellipse((275,-90,1030,730),fill=(226,209,162,38),outline=(221,179,86,110),width=9)
    d.line((640,350,640,65),fill=(77,62,55,100),width=21)
    d.line((640,350,420,510),fill=(61,49,43,110),width=23)
    # layered warmth and smoky background; avoid hard crop-asset boundary
    wash=v32.atmosphere(6,(89,36,22)).copy()
    im=Image.blend(wash,im,.52)
    return im

@functools.lru_cache(1)
def ponzi_figure():
    # independent cutout rig, not source pixels. Lower body extends offscreen.
    im=v32.fedora_vintage().copy()
    return im

@functools.lru_cache(1)
def ponzi_glyphs():
    return v32.gold_text('PONZI',242,1.17,1.12,serif=True)

def clock_scene(t,p):
    im=ponzi_clock_background().copy()
    # Text on top of clock yet behind *foreground cutout*. This z-order
    # eliminates the crossing-text/figure error in V32.
    text=ponzi_glyphs().rotate(-7.0,expand=True,resample=Image.Resampling.BICUBIC)
    paste(im,text,14,int(p['title_y']),.96)
    man=ponzi_figure().resize((535,682),Image.Resampling.LANCZOS)
    paste(im,man,int(p['portrait_x'])-106,120,1.0)
    # camera dollies into Ponzi, using identical scale/pivot for all layers.
    q=ease(t,4.32,5.20)
    s=1+p['portrait_zoom']*q
    if abs(s-1)>1e-3:
        # use extended overscan background: bilinear clamp fills edges, never black
        center=(690,355)
        mat=cv2.getRotationMatrix2D(center,0,s)
        arr=np.array(im)
        out=cv2.warpAffine(arr,mat,(W,H),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
        im=Image.fromarray(out,'RGBA')
    # flash for following beat, preserves same frame until light reaches peak
    flash=ease(t,5.03,5.26)
    if flash:im=cfade(im,Image.new('RGBA',(W,H),(255,240,172,255)),flash*.94)
    return im

@functools.lru_cache(2)
def platform3d():
    # Truncated perspective pyramid with connected bevels, not separate slabs.
    out=Image.new('RGBA',(900,560),(0,0,0,0));d=ImageDraw.Draw(out,'RGBA')
    upper=[(340,80),(558,80),(615,115),(284,115)]
    tiers=[(284,130,615),(248,231,649),(195,340,695),(120,474,772)]
    # Continuous z-walls connecting tiers. Each tier front and its side face.
    for i,(lx,yy,rx) in enumerate(tiers):
        nxt=tiers[min(i+1,len(tiers)-1)]
        width=rx-lx
        top=[(lx+50,yy-42),(rx-50,yy-42),(rx,yy),(lx,yy)]
        d.polygon(top,fill=(138+12*i,218+5*i,46,232))
        d.polygon([(lx,yy),(rx,yy),(rx+3,yy+34),(lx-3,yy+34)],fill=(44,96,29,255))
        d.polygon([(rx-50,yy-42),(rx+3,yy+34),(rx+17,yy+24),(rx-35,yy-49)], fill=(55,105,18,190))
        d.line((lx,yy,rx,yy),fill=(249,255,127,245),width=7)
        d.line((lx+50,yy-42,rx-50,yy-42),fill=(236,255,151,230),width=4)
        if i+1<len(tiers):
            lo=nxt[0];hi=nxt[2];ny=nxt[1]-42
            d.polygon([(lx,yy+34),(rx,yy+34),(hi-50,ny),(lo+50,ny)],fill=(51,105,23,165))
            d.line((lx,yy+34,lo+50,ny),fill=(137,189,42,255),width=3)
            d.line((rx,yy+34,hi-50,ny),fill=(100,163,36,255),width=3)
        for cx in [lx+width*.24,lx+width*.51,lx+width*.76]:
            rr=5+i*2;d.ellipse((cx-rr,yy-rr*1.5,cx+rr,yy+rr*.5),fill=(255,255,222,235))
    gl=out.filter(ImageFilter.GaussianBlur(23))
    gl.putalpha(gl.getchannel('A').point(lambda z:int(z*.50)))
    gl.alpha_composite(out)
    return gl

@functools.lru_cache(1)
def line_network():
    return v32.network_base(31,False)


def network_scene(t,p,scheme=False):
    base=v32.network_base(17 if scheme else 31,red=scheme).copy()
    bq=ease(t,27.30,27.77) if not scheme else 1.0
    pp=platform3d()
    s=p['network_scale'] * (1+p['network_dolly']*ease(t,27.97,28.95))
    pp=pp.resize((int(pp.width*s),int(pp.height*s)),Image.Resampling.LANCZOS)
    # Big 3D object has a common stable track. Top tier fully connected.
    paste(base,pp,(W-pp.width)/2,230-(s-1)*25,bq*.94)
    if not scheme:
        fq=ease(t,28.02,28.43)
        if fq:
            face=v32.startled_portrait().resize((585,615),Image.Resampling.LANCZOS)
            s2=1+.14*ease(t,28.16,28.86)
            face=face.resize((int(face.width*s2),int(face.height*s2)),Image.Resampling.LANCZOS)
            paste(base,face,(W-face.width)/2,-80,fq*.50)
            # wire network remains in front as upper depth plane
            upper=line_network()
            base=Image.blend(base,upper,.12*fq).convert('RGBA')
        qflash=ease(t,29.14,29.47)
        if qflash:base=cfade(base,Image.new('RGBA',(W,H),(255,246,204,255)),qflash*.78)
    else:
        # Source includes numbers travelling OUT towards distant layer.
        for j in range(3):
            age=t-(32.34+j*.24)
            if age>=0 and age<1.95:
                label=v32.gold_text('100',150,.78,1.22)
                sc=max(.12,1.26-.51*age)
                label=label.resize((int(label.width*sc),int(label.height*sc)),Image.Resampling.LANCZOS)
                x=[-60,820,470][j]+age*[40,-60,12][j]
                paste(base,label,x,[-40,90,45][j],.38*(1-ease(t,33.72,34.08)))
        text=v32.gold_text('THE PONZI SCHEME',110,p['scheme_title_size'],1.33)
        # Keep the entire title in frame; scale to the available safe width.
        if text.width > 1120:
            ratio=1120/text.width
            text=text.resize((1120,max(1,int(text.height*ratio))),Image.Resampling.LANCZOS)
        a=ease(t,32.82+p['scheme_reveal_delay'],33.74+p['scheme_reveal_delay'])
        count=int(len('THE PONZI SCHEME')*a+.0001)
        # Per-letter discrete onset, but keep glyph contours same as full text.
        if count>0:
            visible=min(text.width,int(text.width*(count/len('THE PONZI SCHEME'))+.5))
            crop=text.crop((0,0,visible,text.height))
            if t>34.20:
                k=ease(t,34.20,34.45)
                ar=np.asarray(crop).copy()
                ar[:,:,1]=np.clip(ar[:,:,1].astype(float)*(1-.48*k),0,255).astype('uint8')
                ar[:,:,2]=np.clip(ar[:,:,2].astype(float)+118*k,0,255).astype('uint8')
                crop=Image.fromarray(ar,'RGBA')
            paste(base,crop,(W-text.width)//2,295,1.0)
    return base


def storm_scene(t,p):
    img=v32.atmosphere(21,(14,26,21)).copy();d=ImageDraw.Draw(img,'RGBA')
    smoke=v32.smoke_layer();paste(img,smoke,-35,-72,.50)
    # Continuous storm cloud banks and distant desert ridgeline with pyramid
    # silhouettes remain behind the seated subject throughout this shot.
    clouds=v32.smoke_layer().resize((1440,650),Image.Resampling.LANCZOS)
    paste(img,clouds,-80,-70,.72)
    d.polygon([(0,500),(170,457),(360,490),(590,403),(772,470),(951,425),(1100,479),(1280,410),(1280,720),(0,720)], fill=(10,16,15,248))
    for px,py,sz in [(145,485,92),(1010,456,138),(1120,472,72)]:
        d.polygon([(px-sz,py),(px,py-sz*.68),(px+sz,py)],fill=(31,28,25,235))
    d.polygon([(0,575),(300,539),(565,585),(908,515),(1280,570),(1280,720),(0,720)], fill=(9,13,14,245))
    tx=v32.gold_text('UNTOLD TRUTH',188,.90,1.24)
    if tx.width>1120:
        k=1120/tx.width;tx=tx.resize((1120,int(tx.height*k)),Image.Resampling.LANCZOS)
    q=ease(t,34.64,35.22)
    paste(img,tx,(W-tx.width)//2,225-(1-q)*32,q)
    seated=v32.seated_back().resize((485,585),Image.Resampling.LANCZOS)
    paste(img,seated,365,250,ease(t,34.64,35.21))
    # Foreground figure enters from screen-right and crosses right-to-left.
    enter=ease(t,35.94,36.56)
    if enter>0:
        stage=Image.new('RGBA',(850,940),(0,0,0,0))
        subj=v32.investor_reveal()
        paste(stage,subj,10,0,1.0)
        money=v30.money_note(True,1).resize((285,430),Image.Resampling.LANCZOS).rotate(74,expand=True,resample=Image.Resampling.BICUBIC)
        palm=v30.count_hand(2,False).resize((425,300),Image.Resampling.LANCZOS)
        paste(stage,money,405,395,1.0)
        paste(stage,palm,305,440,1.0)
        sc=.92 + p['storm_zoom']*ease(t,36.52,37.34)
        stage=stage.resize((int(stage.width*sc),int(stage.height*sc)),Image.Resampling.LANCZOS)
        x=1280-p['storm_slide_range']*enter
        paste(img,stage,x,18,enter)
    # background title 'BEHIND THE SCAM' begins below as source does
    qt=ease(t,36.69,37.28)
    if qt:
        low=v32.gold_text('BEHIND THE SCAM',109,.86,1.1)
        paste(img,low,65,553-(1-qt)*20,qt)
    qt=ease(t,37.74,38.02)
    if qt:img=cfade(img,Image.new('RGBA',(W,H),(255,253,233,255)),qt)
    return img


def charles_scene(t,p):
    img=Image.new('RGBA',(W,H),(1,0,2,255))
    alpha=ease(t,42.47,42.81)*(1-ease(t,46.63,47.03))
    main=v32.gold_text('CHARLES PONZI',140,.85,p['charles_stretch'])
    # stable material/glyphs: no font swap, no frame-to-frame sprite mutation.
    if abs(p['charles_gold']-1)>1e-6:
        mat=np.asarray(main).copy()
        mat[:,:,:3]=np.uint8(np.clip(mat[:,:,:3].astype(float)*p['charles_gold'],0,255))
        main=Image.fromarray(mat,'RGBA')
    paste(img,main,(W-main.width)/2,292,alpha)
    # conceal -> top-to-bottom reveal. Same subtitle object each time.
    sub=v32.gold_text('THE FINANCIAL IDIOT WHO SCAMMED THE WORLD',44,.81,1.22)
    reveal=ease(t,43.34,43.94)
    if reveal>0:
        h=max(1,int(sub.height*reveal));crop=sub.crop((0,0,sub.width,h))
        paste(img,crop,(W-sub.width)/2,494,alpha)
    return img


def chapter_scene(t,p):
    bg=v32.atmosphere(53,(17,7,14)).copy()
    # fire starts behind the notes then expands to full height.
    fire=v32.fire_bg()
    fire_alpha=ease(t,50.20,54.55)*.90*p['chapter_fire']
    if fire_alpha:paste(bg,fire,0,int((1-fire_alpha)*150),fire_alpha)
    stage=Image.new('RGBA',(W,H),(0,0,0,0))
    notes=v32.cash_notes()
    # Each banknote begins separately, held vertical. All 3 are registered to
    # the SAME parent so no arbitrary rotation/position reset at t=51.
    for j,(xx,yy,st,sc) in enumerate([(-100,-100,48.43,1.02),(430,-185,48.62,1.13),(913,-117,48.78,1.05)]):
        q=ease(t,st,st+.31)
        if q>0:
            note=notes[j]
            note=note.resize((int(note.width*sc),int(note.height*sc)),Image.Resampling.LANCZOS)
            paste(stage,note,xx,yy-220*(1-q),q)
    qper=ease(t,49.19+p['chapter_portrait_delay'],49.78+p['chapter_portrait_delay'])
    if qper:
        face=v32.fedora_vintage().resize((500,635),Image.Resampling.LANCZOS)
        paste(stage,face,384,215+120*(1-qper),qper)
    qtri=ease(t,49.16,49.76)
    if qtri:
        d=ImageDraw.Draw(stage,'RGBA')
        d.line([(640,132),(250,689),(1036,689),(640,132)],fill=(255,232,181,int(204*qtri)),width=7)
    zoom=p['chapter_depth_scale'] * (1.18-.17*ease(t,49.05,52.8))
    if abs(zoom-1)>.002:
        mat=cv2.getRotationMatrix2D((W/2,H/2),0,zoom)
        arr=cv2.warpAffine(np.asarray(stage),mat,(W,H),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
        stage=Image.fromarray(arr,'RGBA')
    bg.alpha_composite(stage)
    titleq=ease(t,50.32,50.67)
    bandq=ease(t,50.67,51.08)
    if bandq:
        d=ImageDraw.Draw(bg,'RGBA');d.rectangle((0,555,W,643),fill=(0,0,1,int(bandq*237)))
    tt=v32.gold_text('LIVING BEYOND HIS MEANS',58,.90,1.18,serif=True)
    paste(bg,tt,(W-tt.width)/2,570,titleq)
    chapter=v32.gold_text('CHAPTER I',39,.94,1.06,serif=True)
    paste(bg,chapter,(W-chapter.width)/2,650,ease(t,50.99,51.40))
    exitq=ease(t,54.93,55.13)
    if exitq:bg=cfade(bg,Image.new('RGBA',(W,H),(254,203,80,255)),exitq*.68)
    return bg


def pyramid_scene(t,p):
    im=v32.atmosphere(33,(15,5,11),horizon=True).copy();d=ImageDraw.Draw(im,'RGBA')
    # Sunset red horizontal band, independent stable background.
    d.polygon([(0,588),(220,554),(540,605),(1000,564),(1280,594),(1280,H),(0,H)], fill=(23,10,8,255))
    u=max(0,t-57.40)
    camz=u*p['pyramid_cam_speed']*2.75
    camx=.34*u
    # World-space depth test: near pyramid moves much faster than distant ones.
    objects=[(-2.30,7.35,2.45,2.70),(3.05,12.85,1.87,1.98),(-1.2,18.5,1.05,1.05),(4.5,23.0,.83,.88)]
    for wx,z0,ww,hh in sorted(objects,key=lambda a:a[1],reverse=True):
        z=max(.32,z0-camz)
        f=600
        sx=W/2+(wx-camx)*f/z
        sy=408+260/z
        w=ww*f/z*2.0 * (p['pyramid_near_scale'] if z0<6 else 1)
        h=hh*f/z*2.55 * (p['pyramid_near_scale'] if z0<6 else 1)
        v32.pyramid_mesh(im,sx,sy,w,h)
    # Source begins revealing giant currency numbers and then the NEXT fiery
    # scene *before* minute-end. Neither the pyramids nor number freezes on the
    # final frame. Use temporally overlapping source-style occlusion.
    qnum=ease(t,58.96,59.09)*(1-ease(t,59.30,59.50))
    if qnum:
        num=v32.gold_text('100',330,1.15,1.48,serif=True)
        scale=1.85-.88*ease(t,59.00,59.48)  # actual zoom OUT
        num=num.resize((int(num.width*scale),int(num.height*scale)),Image.Resampling.LANCZOS)
        paste(im,num,-340+180*ease(t,59.0,59.42),108,qnum*.69)
    nextq=ease(t,59.56,59.96)
    if nextq:
        im=Image.blend(im,v32.atmosphere(63,(30,8,7),horizon=True),nextq*.88).convert('RGBA')
        # Ring of fire is in front of departing pyramids but BEHIND next
        # scene's Ponzi cutout. Offscreen overscan hides sprite boundaries.
        bg=Image.new('RGBA',(W,H),(0,0,0,0))
        bd=ImageDraw.Draw(bg,'RGBA')
        r=230+420*nextq;cx=770;cy=360
        for j in range(7):
            rr=r-j*15
            bd.arc((cx-rr,cy-rr,cx+rr,cy+rr),58,295,
                   fill=(255,max(80,197-j*13),25,int((90+18*j)*nextq)),width=max(9,49-j*4))
        bd.ellipse((cx-r*.7,cy-r*.7,cx+r*.7,cy+r*.7),fill=(255,104,22,int(60*nextq)))
        glow=bg.filter(ImageFilter.GaussianBlur(35))
        im.alpha_composite(glow);im.alpha_composite(bg)
        man=v32.fedora_vintage().resize((380,560),Image.Resampling.LANCZOS)
        paste(im,man,700,204+(1-nextq)*80,ease(t,59.70,59.97)*.95)
    return im



@functools.lru_cache(1)
def paired_cash_fans_art():
    """Two source-matched fan groups over the vault beat; neither is removed."""
    bg=v32.atmosphere(612,(23,22,20)).copy();d=ImageDraw.Draw(bg,'RGBA')
    # Dark industrial vault wall with one main wheel and lower lock detail.
    d.rectangle((0,0,W,H),fill=(34,32,29,255))
    d.rectangle((34,25,1244,695),outline=(117,109,93,185),width=18)
    d.line((70,86,1205,86),fill=(177,158,119,105),width=8)
    d.line((70,654,1205,654),fill=(13,14,15,170),width=15)
    d.ellipse((375,-88,917,454),fill=(39,40,39,255),outline=(112,110,101,255),width=14)
    d.ellipse((432,-31,860,397),outline=(161,151,129,195),width=7)
    for a in range(0,360,45):
        import math as _m
        x1=646+235*_m.cos(_m.radians(a));y1=183+235*_m.sin(_m.radians(a))
        x2=646+80*_m.cos(_m.radians(a));y2=183+80*_m.sin(_m.radians(a))
        d.line((x1,y1,x2,y2),fill=(139,135,124,205),width=11)
    d.ellipse((598,135,694,231),fill=(19,21,21,255),outline=(176,164,137,255),width=8)
    d.ellipse((612,149,680,217),outline=(98,102,98,255),width=6)
    d.ellipse((592,434,700,542),fill=(24,25,25,255),outline=(141,132,113,225),width=8)
    # Title sits behind cash, matching the source's money line.
    title=v32.gold_text('MILLIONS OF DOLLARS',100,.92,1.12)
    paste(bg,title,(W-title.width)//2,250,.96)
    note=v32.v30.money_note(False,1).resize((270,122),Image.Resampling.LANCZOS)
    # Two separate, evenly layered fans with two supporting hands.
    for cx0,cy0,spread in [(300,647,315),(980,647,315)]:
        for i in range(13):
            angle=-56+112*i/12
            rad=math.radians(angle)
            cx=cx0+math.sin(rad)*spread
            cy=cy0-math.cos(rad)*240
            card=note.rotate(-angle*.82,expand=True,resample=Image.Resampling.BICUBIC)
            paste(bg,card,cx-card.width/2,cy-card.height/2,1.0)
        hand_x=cx0-46
        d=ImageDraw.Draw(bg,'RGBA')
        d.polygon([(hand_x-35,720),(hand_x-10,615),(hand_x+42,576),(hand_x+91,599),(hand_x+86,720)],fill=(181,128,102,255),outline=(91,59,47,220))
        d.ellipse((hand_x-10,566,hand_x+100,643),fill=(186,132,104,255),outline=(91,59,47,220),width=4)
    return bg

def money_fan_scene(t):
    scene=paired_cash_fans_art().copy()
    # Push both fans toward camera together, preserving their separation as the
    # source transitions from two readable props into one overlapping close-up.
    q=ease(t,11.58,12.22)
    scale=.78+1.12*q
    mat=cv2.getRotationMatrix2D((640,510),0,scale)
    a=cv2.warpAffine(np.asarray(scene),mat,(W,H),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
    return Image.fromarray(a,'RGBA')

SHOT_WINDOWS = {name: (start, end) for name, start, end in INTERVALS}
SHOT_WINDOWS['S02_CASH_TRANSITION'] = (11.58, 12.95)


def load_timing(path):
    """Map playback-local seconds to animation-local seconds per shot."""
    data = json.loads(Path(path).read_text())
    for name, points in data.items():
        if name not in SHOT_WINDOWS:
            raise ValueError(f'Unknown shot: {name}')
        duration = SHOT_WINDOWS[name][1] - SHOT_WINDOWS[name][0]
        if (len(points) < 2 or points[0] != [0, 0]
                or any(not math.isclose(v, duration, abs_tol=1e-8) for v in points[-1])
                or any(a[0] >= b[0] or a[1] > b[1] for a, b in zip(points, points[1:]))):
            raise ValueError(f'{name}: timing needs ordered keys from [0, 0] to [{duration:.2f}, {duration:.2f}]')
    return data


def scene_and_frame(bgr,t,params=None,timing=None):
    if timing:
        for name, points in timing.items():
            start,end = SHOT_WINDOWS[name]
            if start <= t < end:
                mapped = float(np.interp(t-start, *zip(*points)))
                t = min(start+mapped, math.nextafter(end, start))
                break
    p={**DEFAULTS,**(params or {})}
    base=image_from_bgr(bgr)
    if 11.58<=t<12.95:
        new=money_fan_scene(t)
        q=ease(t,11.58,11.72)*(1-ease(t,12.80,12.95))
        return cfade(base,new,q).convert('RGB')
    if 3.60<=t<5.28:
        new=clock_scene(t,p);q=ease(t,3.60,3.88)*(1-ease(t,5.20,5.28))
    elif 27.13<=t<29.55:
        new=network_scene(t,p,False);q=ease(t,27.13,27.36)*(1-ease(t,29.44,29.55))
    elif 32.38<=t<34.52:
        new=network_scene(t,p,True);q=ease(t,32.38,32.59)*(1-ease(t,34.43,34.52))
    elif 34.52<=t<38.02:
        new=storm_scene(t,p);q=ease(t,34.52,34.76)*(1-ease(t,37.95,38.02))
    elif 42.48<=t<47.05:
        new=charles_scene(t,p);q=ease(t,42.48,42.71)*(1-ease(t,46.86,47.05))
    elif 48.45<=t<55.12:
        new=chapter_scene(t,p);q=ease(t,48.45,48.66)*(1-ease(t,54.95,55.12))
    elif 57.40<=t<60.0:
        new=pyramid_scene(t,p);q=ease(t,57.40,57.63)
    else:
        return base.convert('RGB')
    return cfade(base,new,q).convert('RGB')


def track(obj,t,p=None):
    """Analytic, inspectable procedural object trajectory; not source landmark evidence."""
    p={**DEFAULTS,**(p or {})}
    if obj=='clock_camera':return {'scale':1+p['portrait_zoom']*ease(t,4.32,5.20),'x':690.,'y':355.,'visible':3.60<=t<5.28}
    if obj=='storm_group':
        q=ease(t,35.94,36.56)
        return {'x':-790 + p['storm_slide_range']*q,'y':18.,'scale':.92+p['storm_zoom']*ease(t,36.52,37.34),'visible':35.94<=t<38.02,'alpha':q}
    if obj=='network_platform':
        return {'x':640.,'y':230.,'scale':p['network_scale']*(1+p['network_dolly']*ease(t,27.97,28.95)),'visible':27.13<=t<29.55}
    if obj=='pyramid_camera':return {'x':.34*max(0,t-57.4),'z':max(0,t-57.4)*p['pyramid_cam_speed']*2.75,'visible':57.40<=t<60}
    if obj=='chapter_portrait':return {'alpha':ease(t,49.19+p['chapter_portrait_delay'],49.78+p['chapter_portrait_delay']),'visible':48.45<=t<55.12}
    if obj=='charles_title':return {'scale_y':p['charles_stretch'],'visible':42.48<=t<47.05}
    return {'visible':False}


def render(base_path=ROOT/'ponzi_v32_PROCEDURAL_FINAL.mp4',out=HERE/'Ponzi_V33_PROCEDURAL.mp4',params=None,crf=22,start_frame=0,end_frame=N,timing=None):
    cap=cv2.VideoCapture(str(base_path));cap.set(cv2.CAP_PROP_POS_FRAMES,start_frame)
    if not cap.isOpened():raise FileNotFoundError(base_path)
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-', '-an','-c:v','libx264','-preset','ultrafast','-crf',str(crf),'-pix_fmt','yuv420p','-movflags','+faststart',str(out)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for i in range(start_frame,end_frame):
            ok,bgr=cap.read()
            if not ok:raise RuntimeError('Missing base frame '+str(i))
            im=scene_and_frame(bgr,i/FPS,params,timing)
            proc.stdin.write(np.asarray(im).tobytes())
            if i%250==0:print('V33 render',i,'/',end_frame,flush=True)
    finally:
        cap.release();proc.stdin.close()
    if proc.wait():raise RuntimeError('ffmpeg video encoding failed')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--base',default=str(ROOT/'ponzi_v32_PROCEDURAL_FINAL.mp4'))
    ap.add_argument('--output',default=str(HERE/'Ponzi_V33_PROCEDURAL.mp4'));ap.add_argument('--params')
    ap.add_argument('--still',type=float)
    ap.add_argument('--timing', type=Path)
    ap.add_argument('--start-frame', type=int, default=0)
    ap.add_argument('--end-frame', type=int, default=N)
    a=ap.parse_args()
    if not 0 <= a.start_frame < a.end_frame <= N:
        ap.error('expected 0 <= start-frame < end-frame <= 1500')
    timing=load_timing(a.timing) if a.timing else None
    params=json.load(open(a.params)) if a.params else None
    if a.still is not None:
        cap=cv2.VideoCapture(a.base);cap.set(cv2.CAP_PROP_POS_FRAMES,int(a.still*FPS));ok,frame=cap.read();cap.release()
        if not ok:raise RuntimeError('Frame absent')
        scene_and_frame(frame,a.still,params,timing).save(a.output)
    else:render(a.base,a.output,params,start_frame=a.start_frame,end_frame=a.end_frame,timing=timing)
