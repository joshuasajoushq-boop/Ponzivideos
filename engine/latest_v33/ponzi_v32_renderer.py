#!/usr/bin/env python3
"""Video-specific V32 procedural reconstruction, prioritizing annotated continuity defects.

Only procedural V31 frames and programmatically drawn primitives contribute pixels.
The source documentary is NEVER read by this renderer. Source footage is consumed
separately by the V32 QA optimizer for measurements. Same object/asset sprite reused
throughout its whole lifetime (font, silhouette, depth, and texture persistence).

Usage:
    python ponzi_v32_renderer.py --base ponzi_v31.mp4 --out ponzi_v32_semantic.mp4
    python ponzi_v32_renderer.py --base ponzi_v31.mp4 --still 50.8 --out check.png
"""
import math, random, subprocess, argparse, importlib.util
from functools import lru_cache
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT=Path(__file__).resolve().parent
W,H,FPS=1280,720,25
V31_DEFAULT=ROOT/'ponzi_v31.mp4'
_spec=importlib.util.spec_from_file_location('v30assets', str(ROOT/'ponzi_v30_renderer.py'))
v30=importlib.util.module_from_spec(_spec); _spec.loader.exec_module(v30)
FONT='/usr/share/fonts/truetype/noto/NotoSans-ExtraCondensedBlack.ttf'
SERIF='/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'

def ease(t,a,b):
    if b<=a:return float(t>=b)
    q=max(0.,min(1.,(t-a)/(b-a)))
    return q*q*(3-2*q)

def pste(dst,spr,x,y,a=1.):
    if a<=0:return
    if a<0.999:
        spr=spr.copy();spr.putalpha(spr.getchannel('A').point(lambda z:int(z*a)))
    x,y=int(round(x)),int(round(y))
    l=max(0,x);u=max(0,y);r=min(dst.width,x+spr.width);b=min(dst.height,y+spr.height)
    if r>l and b>u:dst.alpha_composite(spr.crop((l-x,u-y,r-x,b-y)),(l,u))

def crossfade(dst,frame,q):return Image.blend(dst.convert('RGB'),frame.convert('RGB'),max(0.,min(1.,q))).convert('RGBA')

def title(s,size=100,xscale=1,yscale=1,serif=False):
    return v30.title_sprite(s,size,xscale,yscale,fiery=not serif,serif=serif)


@lru_cache(48)
def gold_text(s,size=100,xscale=1,yscale=1,serif=False):
    """Stable video-specific orange-to-yellow gradient and fine deterministic grain."""
    mask=v30.title_sprite(s,size,xscale,yscale,fiery=False,serif=serif).getchannel('A')
    w,h=mask.size
    y,x=np.mgrid[0:h,0:w]
    q=y/max(1,h-1)
    n=np.random.default_rng(2000+sum(map(ord,s))).normal(0,7,(h,w))
    a=np.empty((h,w,4),dtype=np.uint8)
    a[:,:,0]=np.uint8(np.clip(224+30*q+n,0,255))
    a[:,:,1]=np.uint8(np.clip(128+109*q+n,0,255))
    a[:,:,2]=np.uint8(np.clip(27-8*q+n*.30,0,255))
    a[:,:,3]=np.asarray(mask)
    return Image.fromarray(a,'RGBA')

@lru_cache(8)
def atmosphere(seed=3,base_color=(18,15,18),horizon=False):
    rng=np.random.default_rng(seed)
    n=rng.normal(0,1,(120,212)).astype('float32')
    n=cv2.GaussianBlur(n,(0,0),10)
    n=cv2.resize(n,(W,H),interpolation=cv2.INTER_CUBIC)
    n=n/max(1e-6,np.std(n))
    y=np.linspace(0,1,H,dtype=np.float32)[:,None]
    arr=np.empty((H,W,4),np.uint8)
    c=np.array(base_color,dtype=np.float32)
    for k in range(3):arr[:,:,k]=np.clip(c[k]+n*7+(y-.5)*(-9+5*k),0,255)
    if horizon:
        band=np.exp(-((y-.63)/.075)**2)
        arr[:,:,0]=np.clip(arr[:,:,0].astype(float)+150*band,0,255)
        arr[:,:,1]=np.clip(arr[:,:,1].astype(float)+57*band,0,255)
        arr[:,:,2]=np.clip(arr[:,:,2].astype(float)+4*band,0,255)
    arr[:,:,3]=255
    return Image.fromarray(arr,'RGBA')

@lru_cache(4)
def network_base(seed=32,red=False):
    img=atmosphere(seed, (25,7,13) if red else (21,11,10)).copy()
    d=ImageDraw.Draw(img,'RGBA');rng=random.Random(928+seed)
    verts=[(rng.randint(-170,1450),rng.randint(-60,800)) for j in range(96)]
    for i,(x,y) in enumerate(verts):
        neighbors=sorted([(math.hypot(x-xx,y-yy),xx,yy) for j,(xx,yy) in enumerate(verts) if j!=i])[:3]
        for k,(dist,xx,yy) in enumerate(neighbors):
            if dist<440:
                d.line((x,y,xx,yy),fill=(254,142,30,105 if not red else 125),width=2+(i%3==0))
                if i%7==0:d.ellipse((x-4,y-4,x+4,y+4), fill=(255,198,84,205))
    im_glow=img.filter(ImageFilter.GaussianBlur(5))
    return Image.blend(im_glow,img,0.81)

@lru_cache(2)
def pyramidal_platform_sprite():
    """Stepped emissive truncated pyramid: explicit front/side faces, actual perspective."""
    im=Image.new('RGBA',(780,540),(0,0,0,0));sh=Image.new('RGBA', im.size,(0,0,0,0));sd=ImageDraw.Draw(sh,'RGBA');d=ImageDraw.Draw(im,'RGBA')
    for i in range(4):
        top_y=80+i*95; left=245-i*58; right=535+i*58
        # top trapezoid projected in depth
        pts=[(left,top_y),(right,top_y),(right+85,top_y+38),(left-85,top_y+38)]
        d.polygon(pts,fill=(161+18*i,224+8*i,48,215))
        d.polygon([(left-85,top_y+38),(right+85,top_y+38),(right+85,top_y+55),(left-85,top_y+55)],fill=(55,101,22,225))
        d.line((left-85,top_y+38,right+85,top_y+38),fill=(251,245,109,255),width=7)
        d.line((left,top_y,right,top_y),fill=(239,254,124,255),width=5)
        sd.polygon(pts,fill=(245,255,72,155))
        for xx in np.linspace(left+35,right-35,4):
            d.ellipse((xx-5,top_y-5,xx+5,top_y+5),fill=(255,255,215,245))
    glow=sh.filter(ImageFilter.GaussianBlur(29))
    glow.alpha_composite(im)
    return glow

@lru_cache(2)
def startled_portrait():
    im=v30.gray_portrait().copy();d=ImageDraw.Draw(im,'RGBA')
    d.ellipse((304,494,456,656),fill=(26,14,18,255),outline=(83,48,40,255),width=7)
    d.ellipse((340,515,419,636),fill=(79,34,39,255))
    return im

@lru_cache(2)
def seated_back():
    im=Image.new('RGBA',(570,690),(0,0,0,0));d=ImageDraw.Draw(im,'RGBA')
    d.polygon([(104,690),(144,320),(218,265),(360,265),(432,330),(493,690)],fill=(17,20,25,255))
    d.ellipse((196,84,380,292),fill=(48,43,39,255))
    d.polygon([(191,130),(224,62),(365,58),(395,157)],fill=(27,30,31,255))
    d.polygon([(130,373),(187,302),(216,540),(170,690)],fill=(38,40,43,255))
    d.polygon([(401,329),(450,395),(498,690),(428,685)],fill=(33,36,40,255))
    # chair back: beige fabric and dark rails
    d.rounded_rectangle((128,548,455,790),radius=33,fill=(198,180,143,245),outline=(49,47,43,255),width=12)
    d.rectangle((144,605,435,690),fill=(36,39,44,255))
    return im

@lru_cache(2)
def investor_reveal():
    im=Image.new('RGBA',(750,900),(0,0,0,0));d=ImageDraw.Draw(im,'RGBA')
    d.polygon([(225,850),(185,325),(247,235),(505,235),(600,850)],fill=(22,22,31,255))
    d.ellipse((308,85,500,300),fill=(190,148,124,255),outline=(72,53,44,255),width=5)
    d.pieslice((295,75,520,193),180,360,fill=(32,27,23,255))
    d.polygon([(302,251),(408,440),(485,255)],fill=(239,226,204,255))
    d.polygon([(403,322),(425,319),(459,520),(405,568),(382,520)],fill=(124,62,48,255))
    return im

@lru_cache(1)
def fedora_vintage():
    im=v30.chapter_person().copy();d=ImageDraw.Draw(im,'RGBA')
    # vintage hat in foreground above the eyes, directional brim
    d.ellipse((136,86,439,154),fill=(147,97,39,255),outline=(56,39,28,255),width=6)
    d.polygon([(201,35),(382,39),(425,118),(158,118)],fill=(152,107,51,255))
    d.polygon([(178,96),(410,96),(422,121),(155,121)],fill=(64,44,36,255))
    d.line((189,90,398,92),fill=(224,175,88,255),width=7)
    return im

@lru_cache(1)
def fire_bg():
    return v30.fire_background(1)

@lru_cache(2)
def cash_notes():
    n=v30.money_note(True,1).resize((405,820),Image.Resampling.LANCZOS)
    # stable glyph/material throughout shot
    return [n.rotate(a,expand=True,resample=Image.Resampling.BICUBIC) for a in (-9,0,8)]

@lru_cache(2)
def smoke_layer():
    im=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(im,'RGBA'); rng=random.Random(879)
    for i in range(80):
        x=rng.randint(-200,1450); y=rng.randint(-120,770); r=rng.randint(100,260)
        d.ellipse((x-r,y-r,x+r,y+r),fill=(86+rng.randint(0,40),88+rng.randint(0,30),77+rng.randint(0,23),rng.randint(9,33)))
    return im.filter(ImageFilter.GaussianBlur(60))


def people_scene(t, cfg):
    # one scene identity across all frames, text assets have constant shape and texture
    img=atmosphere(41,(37,39,38)).copy()
    haze=smoke_layer()
    pste(img,haze,40*math.sin((t-24)*.22)-55,0,.75)
    # previous scene right edge lingers, but fades smoothly
    pre=title('M',235,.91,1.1)
    pste(img,pre,1150,225,(1-ease(t,25.05,26.26))*.34)
    person=v30.covered_face_person().resize((645,678),Image.Resampling.LANCZOS)
    pste(img,person,380,145,ease(t,24.38,25.02)*.98)
    slope_deg=cfg.get('people_slant',-4.0)
    line=gold_text('THOUSANDS OF INNOCENT',110,.83,1.12)
    line=line.rotate(slope_deg,expand=True,resample=Image.Resampling.BICUBIC)
    q=ease(t,24.93,25.44)
    pste(img,line,105,210-(1-q)*23,q)
    big=gold_text('PEOPLE',242,1.04,1.18)
    big=big.resize((975,287),Image.Resampling.LANCZOS)
    big=big.rotate(slope_deg-1.0,expand=True,resample=Image.Resampling.BICUBIC)
    bq=ease(t,25.47,25.94)
    # bounce is small, not an oscillatory retype. fixed identity throughout.
    bounce=-12*math.sin(math.pi*bq)*(1-bq)
    pste(img,big,112,320-(1-bq)*28+bounce,bq)
    # towards final light wipe, only distinct transition event at source timing
    qf=ease(t,26.61,27.08)
    if qf>0:
        gl=Image.new('RGBA',(W,H),(0,0,0,0));d=ImageDraw.Draw(gl,'RGBA')
        x=-350+qf*1780
        d.polygon([(x-200,0),(x+40,0),(x+550,H),(x+180,H)], fill=(250,105,45,int(200*qf)))
        gl=gl.filter(ImageFilter.GaussianBlur(35));img.alpha_composite(gl)
        img=crossfade(img,Image.new('RGBA',(W,H),(255,247,205,255)),max(0,qf-.45)*.75)
    return img


def network_scene(t,cfg,scheme=False):
    img=network_base(31 if not scheme else 17,red=scheme).copy()
    if not scheme:
        q=ease(t,27.32,27.78)
        plat=pyramidal_platform_sprite()
        zoom=1+cfg.get('network_dolly',.14)*ease(t,27.9,28.6)
        plat=plat.resize((int(plat.width*zoom),int(plat.height*zoom)),Image.Resampling.LANCZOS)
        pste(img,plat,(W-plat.width)/2,295,q)
        f=ease(t,28.03,28.45)
        if f>0:
            face=startled_portrait().resize((600,625),Image.Resampling.LANCZOS)
            zoom2=1+.14*ease(t,28.1,28.7)
            face=face.resize((int(face.width*zoom2),int(face.height*zoom2)),Image.Resampling.LANCZOS)
            # depth: face back, network wire overlay above in final
            pste(img,face,(W-face.width)/2,-20,f*.54)
            if f>.10:
                wire=network_base(31).copy()
                img=Image.blend(img,wire,.13*f).convert('RGBA')
        # independent light pulse along pyramid base
        if t>29.03:
            qf=ease(t,29.06,29.42)
            img=crossfade(img,Image.new('RGBA',(W,H),(248,236,195,255)),qf*.70)
    else:
        # Receding illuminated pyramid (persistent, not a flat rectangle)
        plat=pyramidal_platform_sprite()
        pste(img,plat,275,325,.88)
        # moving numbers in depth during background expansion
        for j in range(3):
            phase=(t-32.38)*(.22+.09*j)
            if phase>0 and phase<2:
                s=title('100',110,.86,1.15)
                sc=.70+phase*(.24+.16*j)
                s=s.resize((int(s.width*sc),int(s.height*sc)),Image.Resampling.BICUBIC)
                pste(img,s,[-120,790,380][j]-sc*90,[-30,110,45][j]+phase*10,(1-ease(t,33.4,34.1))*.19)
        # Phrase reveals left to right by original letter positions, no font swaps
        q=ease(t,32.80,33.83)
        tx=title('THE PONZI SCHEME',105,.93,1.20)
        width=int(tx.width*q)
        if width>0:
            crop=tx.crop((0,0,width,tx.height))
            if t>=34.28:
                # gold to magenta continuous tint, but same contours and asset
                r=ease(t,34.24,34.49)
                a=np.asarray(crop).copy()
                a[:,:,0]=np.uint8(np.clip(a[:,:,0]*1.00,0,255))
                a[:,:,1]=np.uint8(np.clip(a[:,:,1]*(1-.53*r),0,255))
                a[:,:,2]=np.uint8(np.clip(a[:,:,2]+115*r,0,255))
                crop=Image.fromarray(a,'RGBA')
            pste(img,crop,165,274,1.0)
    return img


def storm_scene(t,cfg):
    img=atmosphere(21,(17,29,24)).copy()
    # cloudy sky and sloping dark land
    pste(img,smoke_layer(),0,-65,.40)
    d=ImageDraw.Draw(img,'RGBA')
    d.polygon([(0,500),(170,457),(360,490),(590,403),(772,470),(951,425),(1100,479),(1280,410),(1280,720),(0,720)],fill=(12,17,16,248))
    d.polygon([(0,575),(300,539),(565,585),(908,515),(1280,570),(1280,720),(0,720)],fill=(10,15,15,245))
    # text behind seated figure, perspective large but stable
    tx=title('UNTOLD TRUTH',187,.90,1.28)
    q=ease(t,34.63,35.22)
    pste(img,tx,96,220-(1-q)*33,q)
    seated=seated_back().resize((480,580),Image.Resampling.LANCZOS)
    pste(img,seated,365,265,ease(t,34.60,35.23))
    # Subject holding money enters from left via movement, then gently zooms
    q1=ease(t,35.96,36.57)
    if q1:
        subj=investor_reveal()
        sc=.86+cfg.get('hand_zoom',.10)*ease(t,36.53,37.34)
        subj=subj.resize((int(subj.width*sc),int(subj.height*sc)),Image.Resampling.LANCZOS)
        xx=-830 + q1*690
        pste(img,subj,xx,40,1)
        cash=v30.money_note(True,1).resize((270,395),Image.Resampling.LANCZOS).rotate(74,expand=True)
        hand=v30.count_hand(2,False).resize((425,300),Image.Resampling.LANCZOS)
        pste(img,cash,xx+445,376,1)
        pste(img,hand,xx+330,404,1)
    # source flash at 37.75-38.02
    lf=ease(t,37.75,37.98)
    if lf:img=crossfade(img,Image.new('RGBA',(W,H),(255,250,225,255)),lf)
    return img


def charles_scene(t,cfg):
    im=Image.new('RGBA',(W,H),(0,0,3,255))
    # ONE asset throughout, no abrupt font/texture identity switch
    sprite=gold_text('CHARLES PONZI',122,.90,cfg.get('title_stretch',1.16))
    x=(W-sprite.width)/2;y=208
    q=ease(t,42.52,42.86)*(1-ease(t,46.65,47.02))
    pste(im,sprite,x,y,q)
    # Source subtitle concealed and revealed downward, not flat fade
    sub=gold_text('THE FINANCIAL IDIOT WHO SCAMMED THE WORLD',43,.82,1.0)
    s=ease(t,43.31,43.89)
    if s>0:
        h=max(1,int(sub.height*s));crop=sub.crop((0,0,sub.width,h))
        pste(im,crop,(W-sub.width)/2,357,s*.96)
    return im


def chapter_scene(t,cfg):
    img=atmosphere(53,(22,8,13)).copy()
    # Fire belongs behind the full three-banknote assemblage, climbs from 50.3 to 54.7
    fire=fire_bg().copy()
    fq=ease(t,50.20,54.63)
    if fq>0:
        # background only, never covers the cutouts or typography
        pste(img,fire,0,int(210*(1-fq)),fq*.78)
    qcam=ease(t,49.04,52.75)
    # Compose whole scene offscreen for one consistent camera transform.
    stage=Image.new('RGBA',(W,H),(0,0,0,0))
    notes=cash_notes()
    for j,(x,y,st,sc) in enumerate([(-130,-140,48.44,1.06),(442,-202,48.64,1.12),(910,-155,48.78,1.04)]):
        q=ease(t,st,st+.39)
        if q:
            n=notes[j]
            n=n.resize((int(n.width*sc),int(n.height*sc)),Image.Resampling.LANCZOS)
            pste(stage,n,x,y-(1-q)*190,q)
    # triangular frame behind character, held fixed throughout
    qq=ease(t,49.07,49.63)
    if qq:
        d=ImageDraw.Draw(stage,'RGBA')
        d.line([(642,125),(270,685),(1012,685),(642,125)],fill=(248,226,199,int(190*qq)),width=7)
    p=ease(t,49.18,49.78)
    if p:
        per=fedora_vintage().resize((510,635),Image.Resampling.LANCZOS)
        pste(stage,per,383,215+(1-p)*170,p)
    # slow camera pullback of the entire rig, not resetting assets
    zoom=cfg.get('chapter_start_zoom',1.14)-.16*qcam
    if abs(zoom-1)>1e-4:
        M=cv2.getRotationMatrix2D((W/2,H/2),0,zoom)
        arr=cv2.warpAffine(np.asarray(stage),M,(W,H),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
        stage=Image.fromarray(arr,'RGBA')
    img.alpha_composite(stage)
    # chapter title appears before black strip, then strip underneath it
    tx=gold_text('LIVING BEYOND HIS MEANS',58,.86,1.08,serif=True)
    textq=ease(t,50.25,50.62)
    bandq=ease(t,50.66,51.02)
    if bandq:
        d=ImageDraw.Draw(img,'RGBA')
        d.rectangle((0,555,W,642),fill=(2,1,3,int(bandq*225)))
    pste(img,tx,(W-tx.width)//2,570,textq)
    chapter=title('CHAPTER II',40,1,1,serif=True)
    pste(img,chapter,(W-chapter.width)//2,653,ease(t,50.96,51.32)*.94)
    # no element swaps. At the exit only, subtle gold flash transition
    exitq=ease(t,54.91,55.13)
    if exitq:img=crossfade(img,Image.new('RGBA',(W,H),(255,206,97,255)),exitq*.65)
    return img


def pyramid_mesh(im,cx,base,w,h,shade=1):
    d=ImageDraw.Draw(im,'RGBA'); apex=(cx,base-h)
    left=(cx-w*.5,base);right=(cx+w*.5,base)
    d.polygon([apex,left,(cx-w*.04,base)],fill=(216,164,95,255))
    d.polygon([apex,(cx-w*.04,base),right],fill=(86,57,38,255))
    for j in range(1,max(8,int(h/17))):
        q=j/max(8,int(h/17))
        y=apex[1]+h*q; hh=w*q*.5
        d.line((cx-hh,y,cx+hh,y),fill=(241,186,110,160),width=max(1,int(w/350)))
    d.line([apex,(cx-w*.04,base)],fill=(247,204,138,170),width=max(2,int(w/260)))


def pyramid_flythrough(t,cfg):
    im=atmosphere(33,(22,6,11),horizon=True).copy()
    d=ImageDraw.Draw(im,'RGBA')
    # foreground ground and sunset
    d.polygon([(0,590),(250,555),(570,620),(1000,566),(1280,593),(1280,H),(0,H)],fill=(26,12,10,255))
    u=max(0,t-57.40)
    speed=cfg.get('pyramid_dolly',1.0)
    cam=u*speed*2.2
    # world positions, separated Z: near left, mid right, far near horizon
    objects=[(-2.6,5.8,2.0,2.35), (2.1,7.4,1.50,1.60), (-.6,15.0,.8,.75), (3.8,18.5,.9,.8)]
    for wx,z0,width,height in sorted(objects,key=lambda x:x[1],reverse=True):
        z=max(.36,z0-cam)
        focal=530
        x=640+wx*focal/z
        by=400+255/z+115/z*(width-1)
        ww=width*focal/z*2.0
        hh=height*focal/z*2.5
        pyramid_mesh(im,x,by,ww,hh)
    # light energy approaching next scene from 59.62, not a hard cut
    q=ease(t,59.62,59.97)
    if q:
        gl=Image.new('RGBA',(W,H),(0,0,0,0));gd=ImageDraw.Draw(gl,'RGBA')
        gd.ellipse((-370,-20,380+q*1100,800),fill=(254,124,35,int(q*215)))
        gl=gl.filter(ImageFilter.GaussianBlur(48));im.alpha_composite(gl)
    return im

# Persistent intervals. None of these are merely single annotated frames.
PATCHES=[('S10',24.27,27.13),('S11',27.13,29.55),('S13',32.38,34.52),('S14',34.52,38.02),('S17',42.48,47.05),('S19',48.45,55.12),('S21',57.40,60.0)]
DEFAULT_PARAMS=dict(people_slant=-4.0,network_dolly=.14,hand_zoom=.10,title_stretch=1.45,chapter_start_zoom=1.14,pyramid_dolly=1.0)

def frame(original,t,params=None):
    cfg=DEFAULT_PARAMS if params is None else {**DEFAULT_PARAMS,**params}
    if 24.27<=t<27.13:
        new=people_scene(t,cfg)
        q=ease(t,24.27,24.63)*(1-ease(t,27.02,27.13))
    elif 27.13<=t<29.55:
        new=network_scene(t,cfg,False)
        q=ease(t,27.13,27.35)*(1-ease(t,29.44,29.55))
    elif 32.38<=t<34.52:
        new=network_scene(t,cfg,True)
        q=ease(t,32.38,32.58)*(1-ease(t,34.43,34.52))
    elif 34.52<=t<38.02:
        new=storm_scene(t,cfg)
        q=ease(t,34.52,34.76)*(1-ease(t,37.94,38.02))
    elif 42.48<=t<47.05:
        new=charles_scene(t,cfg)
        q=ease(t,42.48,42.70)*(1-ease(t,46.87,47.05))
    elif 48.45<=t<55.12:
        new=chapter_scene(t,cfg)
        q=ease(t,48.45,48.61)*(1-ease(t,54.95,55.12))
    elif 57.40<=t<60.0:
        new=pyramid_flythrough(t,cfg)
        q=ease(t,57.40,57.63)  # end begins showing next subject via fire overlay
    else:return original
    return crossfade(original,new,q)

def render(base=V31_DEFAULT,out=ROOT/'ponzi_v32_SEMANTIC.mp4',params=None,crf=23):
    cap=cv2.VideoCapture(str(base))
    if not cap.isOpened():raise FileNotFoundError(base)
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r','25','-i','-',
       '-an','-c:v','libx264','-preset','ultrafast','-crf',str(crf),'-pix_fmt','yuv420p','-movflags','+faststart',str(out)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for i in range(1500):
            ok,bgr=cap.read()
            if not ok:raise RuntimeError(f'base missing frame {i}')
            t=i/FPS
            pil=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGBA),'RGBA')
            img=frame(pil,t,params)
            proc.stdin.write(np.asarray(img.convert('RGB')).tobytes())
            if i%100==0:print('V32 semantic render',i,'/1500',flush=True)
    finally:
        cap.release()
        if proc.stdin:proc.stdin.close()
    if proc.wait()!=0:raise RuntimeError('ffmpeg failed')

def still(t,base=V31_DEFAULT,params=None):
    cap=cv2.VideoCapture(str(base));cap.set(cv2.CAP_PROP_POS_FRAMES,int(t*FPS));ok,bgr=cap.read();cap.release()
    if not ok:raise RuntimeError('Cannot read base video')
    pil=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGBA),'RGBA')
    return frame(pil,t,params)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',default=str(V31_DEFAULT));p.add_argument('--out',default=str(ROOT/'ponzi_v32_SEMANTIC.mp4'));p.add_argument('--still',type=float);p.add_argument('--params',type=str)
    a=p.parse_args();params=None
    if a.params:
        import json
        params=json.load(open(a.params)).get('semantic_parameters')
    if a.still is not None:still(a.still,a.base,params).convert('RGB').save(a.out)
    else:render(a.base,a.out,params)
