#!/usr/bin/env python3
"""Ponzi: The Financial Idiot Who Scammed the World — procedural V30 patch renderer.

This overlay-only reconstruction consumes V29 PROCEDURAL frames (never reference pixels).
It corrects missing semantic objects/scene mechanics in selected intervals. The original
footage is used only by the independent QA optimizer, never in this renderer.

Runs in two modes: `--video` to create a complete 25FPS procedural minute, or
`--still SEC --out file.png` to inspect one frame. This file plus V29 video and
source renderer can serve as a resumable starting point for further revisions.
"""
from __future__ import annotations
import argparse, functools, math, random, json, subprocess, os
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

ROOT=Path('/mnt/data')
DEFAULT_BASE=ROOT/'ponzi_v29_PROCEDURAL.mp4'
W,H,FPS,N=1280,720,25,1500
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf'
FONT_TALL='/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf'
SERIF='/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'

def sm(t,a,b):
    if b<=a:return float(t>=b)
    x=max(0,min(1,(t-a)/(b-a)))
    return x*x*(3-2*x)

def gauss(t,center,sigma):return math.exp(-0.5*((t-center)/sigma)**2)

def paste(dst,sprite,x,y,a=1):
    if a<=0:return
    if a<0.999:
        sprite=sprite.copy();sprite.putalpha(sprite.getchannel('A').point(lambda p:int(p*a)))
    x=int(x);y=int(y)
    lx=max(0,x);ty=max(0,y);rx=min(dst.width,x+sprite.width);by=min(dst.height,y+sprite.height)
    if lx<rx and ty<by:dst.alpha_composite(sprite.crop((lx-x,ty-y,rx-x,by-y)),(lx,ty))

def blend(orig,new,q):
    return Image.blend(orig.convert('RGB'),new.convert('RGB'),max(0,min(1,q))).convert('RGBA')

@functools.lru_cache(32)
def font(sz,tall=False):return ImageFont.truetype(FONT_TALL if tall else FONT,int(sz))

@functools.lru_cache(128)
def money_note(vertical=True,variant=0):
    w,h=(160,252) if vertical else (285,128)
    im=Image.new('RGBA',(w,h),(0,0,0,0));d=ImageDraw.Draw(im,'RGBA')
    d.rounded_rectangle((3,3,w-3,h-3),radius=5,fill=(206,214,191,250),outline=(44,76,53,255),width=4)
    d.rounded_rectangle((12,11,w-12,h-11),radius=4,outline=(52,86,64,230),width=3)
    d.rounded_rectangle((22,21,w-22,h-21),radius=4,outline=(70,106,76,175),width=2)
    for i in range(18):
        q=i/18
        if vertical:d.arc((22+i//2,17+i*3,w-22-i//2,h-17-i*3),0,360,fill=(45,86,55,85),width=1)
        else:d.arc((35+i*2,19+i//2,w-35-i*2,h-19-i//2),0,360,fill=(45,86,55,85),width=1)
    d.ellipse((w*.24,h*.29,w*.76,h*.69),outline=(39,68,49,230),width=4)
    d.ellipse((w*.39,h*.38,w*.61,h*.49),fill=(58,79,65,210))
    d.polygon([(w*.38,h*.60),(w*.40,h*.52),(w*.6,h*.52),(w*.64,h*.60)],fill=(58,79,65,210))
    d.text((17,16),'100',font=font(24),fill=(48,78,57,250))
    if vertical:d.text((31,h-56),'100',font=font(29),fill=(48,78,57,250))
    else:d.text((w-93,h-50),'100',font=font(24),fill=(48,78,57,250))
    if variant:d.polygon([(0,0),(w*.1,0),(w*.25,h*.3)],fill=(230,238,214,70))
    return im

@functools.lru_cache(1)
def gray_portrait():
    """Layered stylized portrait, neck/shoulders; intentionally not a photo."""
    im=Image.new('RGBA',(760,780),(0,0,0,0));d=ImageDraw.Draw(im,'RGBA')
    d.polygon([(105,780),(205,610),(555,610),(665,780)],fill=(25,28,35,255))
    d.polygon([(306,610),(380,710),(453,610)],fill=(219,218,207,255))
    d.polygon([(370,715),(387,735),(372,778),(349,744)],fill=(75,32,36,255))
    d.ellipse((160,217,266,434),fill=(173,176,175,255));d.ellipse((495,217,602,434),fill=(173,176,175,255))
    d.ellipse((208,60,555,659),fill=(193,194,192,255),outline=(49,54,61,255),width=7)
    d.pieslice((199,43,561,242),180,360,fill=(28,32,36,255))
    d.polygon([(205,223),(240,94),(490,83),(555,226),(518,135),(286,121)],fill=(28,32,36,255))
    for cx in (305,459):
        d.arc((cx-58,258,cx+58,314),185,352,fill=(41,48,52,255),width=10)
        d.ellipse((cx-34,304,cx+34,360),fill=(232,230,220,255),outline=(46,48,52,255),width=5)
        d.ellipse((cx-13,310,cx+13,346),fill=(22,26,31,255))
        d.ellipse((cx-5,312,cx+3,320),fill=(249,244,229,255))
    d.polygon([(379,334),(347,455),(404,462)],fill=(160,166,164,255))
    d.line((331,516,430,516),fill=(64,68,72,255),width=5)
    return im

@functools.lru_cache(1)
def sinister_portrait():
    im=gray_portrait().copy();d=ImageDraw.Draw(im,'RGBA')
    for side in (-1,1):
        for j in range(9):
            cx=380+side*(130+j*14)
            d.arc((cx-140,80,cx+140,650),70 if side>0 else 110,290 if side>0 else 250,fill=(28,14,16,230),width=21)
    d.ellipse((286,285,351,374),fill=(39,8,11,245));d.ellipse((418,285,481,374),fill=(39,8,11,245))
    d.ellipse((311,315,327,337),fill=(247,212,66,255));d.ellipse((443,315,459,337),fill=(247,212,66,255))
    d.ellipse((293,495,475,653),fill=(37,7,10,255),outline=(131,55,28,255),width=7)
    for j in range(7):d.rectangle((313+j*23,513,330+j*23,546),fill=(223,210,184,255))
    return im

@functools.lru_cache(8)
def count_hand(phase=0,flip=False):
    """Five distinct counting poses with curved fingers, not one static hand."""
    im=Image.new('RGBA',(565,395),(0,0,0,0));d=ImageDraw.Draw(im,'RGBA')
    # connected sleeve reaches image edge
    d.polygon([(0,310),(150,270),(264,296),(301,395),(0,395)],fill=(28,28,38,255))
    d.polygon([(130,269),(225,257),(260,306),(168,318)],fill=(239,227,211,255))
    d.ellipse((213,194,414,364),fill=(215,161,124,255),outline=(149,95,75,255),width=5)
    bend=[-58,-27,0,34,67][phase%5]
    starts=[(260,230),(287,210),(316,217),(345,237)]
    for j,(x,y) in enumerate(starts):
        ex=x+66+math.cos(j+phase*.43)*28
        ey=y-118+(phase-2)*16+j*10+bend*.32
        d.line((x,y,ex,ey),fill=(213,151,115,255),width=max(20,38-j*4))
        d.ellipse((ex-16,ey-16,ex+16,ey+16),fill=(224,165,128,255))
        d.line((x-10,y+5,ex-10,ey-2),fill=(155,100,80,78),width=3)
    if flip:im=ImageOps.mirror(im)
    return im

@functools.lru_cache(2)
def fire_background(seed=0):
    w,h=1280,720
    im=Image.new('RGBA',(w,h),(13,5,10,255));d=ImageDraw.Draw(im,'RGBA')
    for y in range(h):
        q=y/h
        d.line((0,y,w,y),fill=(int(14+110*q),int(6+15*q),int(8+3*q),255),width=1)
    rng=random.Random(seed+402)
    glow=Image.new('RGBA',(w,h),(0,0,0,0));g=ImageDraw.Draw(glow,'RGBA')
    for i in range(47):
        cx=i*31-50;r=rng.uniform(40,135);height=rng.uniform(280,720)
        g.ellipse((cx-r*.85,h-height*.8,cx+r*.85,h+190),fill=(235,59,10,95))
        d.polygon([(cx-r,h+40),(cx-r*.65,h-height*.34),(cx+rng.uniform(-23,30),h-height),(cx+r*.56,h-height*.46),(cx+r,h+40)],fill=(245,73+rng.randrange(60),7+rng.randrange(28),235))
        d.polygon([(cx-r*.50,h+30),(cx,h-height*.74),(cx+r*.36,h+30)],fill=(255,164,25,180))
    im=Image.alpha_composite(im,glow.filter(ImageFilter.GaussianBlur(38)))
    return im

@functools.lru_cache(32)
def title_sprite(text,size=115,scale_x=1.0,scale_y=1.0,fiery=False,serif=False):
    f=ImageFont.truetype(SERIF if serif else FONT_TALL,size)
    b=f.getbbox(text,stroke_width=2)
    w,h=b[2]-b[0]+24,b[3]-b[1]+24
    mask=Image.new('L',(w,h),0);md=ImageDraw.Draw(mask)
    md.text((12-b[0],12-b[1]),text,font=f,fill=255,stroke_width=1)
    w2=max(1,int(w*scale_x));h2=max(1,int(h*scale_y))
    mask=mask.resize((w2,h2),Image.Resampling.LANCZOS)
    layer=Image.new('RGBA',(w2,h2),(0,0,0,0))
    a=np.zeros((h2,w2,4),np.uint8);yy,xx=np.mgrid[:h2,:w2]
    rng=np.random.default_rng(851+len(text))
    noise=rng.normal(0,18 if fiery else 5,size=(h2,w2))
    q=yy/max(1,h2)
    if fiery:
        a[:,:,0]=np.clip(186+58*q+noise,0,255);a[:,:,1]=np.clip(143-62*q+noise,0,255);a[:,:,2]=np.clip(36-18*q+noise*.4,0,255)
        # irregular fire-like brightness in glyphs
        fl=np.clip(np.sin(xx*.047+q*12)*np.cos(q*19),0,1)*45
        a[:,:,0]=np.clip(a[:,:,0].astype(float)+fl,0,255)
    else:
        a[:,:,0]=np.clip(251-18*q+noise,0,255);a[:,:,1]=np.clip(223-96*q+noise,0,255);a[:,:,2]=np.clip(33+19*q+noise*.5,0,255)
    a[:,:,3]=np.asarray(mask)
    return Image.fromarray(a,'RGBA')

@functools.lru_cache(4)
def chapter_bill(angle=0):
    im=money_note(True,1).resize((280,590),Image.Resampling.LANCZOS)
    return im.rotate(angle,expand=True,resample=Image.Resampling.BICUBIC)

@functools.lru_cache(2)
def chapter_person():
    im=gray_portrait().resize((550,660),Image.Resampling.LANCZOS)
    tinted=Image.new('RGBA',im.size,(174,112,41,0))
    tinted.putalpha(im.getchannel('A').point(lambda p:int(p*.24)))
    im.alpha_composite(tinted)
    return im


def flames_scene(t):
    if t<17.70:
        bg=Image.new('RGBA',(W,H),(6,6,13,255))
    else:
        f=sm(t,17.70,18.25)
        fire=fire_background(int(t*5)%2)
        bg=Image.blend(Image.new('RGBA',(W,H),(7,6,12,255)),fire,f)
    if t <18.63:
        face=gray_portrait().resize((840,858),Image.Resampling.LANCZOS)
        paste(bg,face,250,-68,1.0)
        # vertical money in hand: stack stays supported near face
        for k in range(3):
            note=money_note(True,k%2).rotate([12,-7,3][k],expand=True,resample=Image.Resampling.BICUBIC)
            paste(bg,note,515+k*48,345-k*16,.96)
        hold=count_hand(2,flip=True).resize((600,420),Image.Resampling.LANCZOS)
        paste(bg,hold,665,393,.98)
        # five-pose animated counting: ghost predecessors plus primary
        phase=int((t-16.12)*11)%5
        motion_x=190+65*math.sin((t-16.15)*2*math.pi*3.3)
        motion_y=350+26*math.sin((t-16.15)*2*math.pi*3.3+.9)
        for trail in (2,1,0):
            hand=count_hand((phase-trail)%5).resize((565,395),Image.Resampling.LANCZOS)
            hand=hand.rotate(-7+8*math.sin((t-trail*.04)*8),expand=True,resample=Image.Resampling.BICUBIC)
            paste(bg,hand,motion_x-trail*36,motion_y-trail*12,[.96,.21,.10][trail])
    else:
        face=sinister_portrait().resize((900,900),Image.Resampling.LANCZOS)
        paste(bg,face,225,-30,1)
    return bg


def smoke_texture(t):
    """Procedural soft cloud/smoke; never an ink-shaped hard opaque wipe."""
    rng=random.Random(2206)
    smk=Image.new('RGBA',(1280,720),(0,0,0,0));d=ImageDraw.Draw(smk,'RGBA')
    for j in range(36):
        xx=rng.randint(-130,1380)+52*math.sin(t*.35+j*.8)
        yy=rng.randint(-120,640)+36*math.cos(t*.51+j*1.2)
        rr=rng.randint(70,240)
        d.ellipse((xx-rr,yy-rr,xx+rr,yy+rr),fill=(29+rng.randrange(29),27+rng.randrange(19),29+rng.randrange(15),rng.randrange(35,100)))
    return smk.filter(ImageFilter.GaussianBlur(46))


@functools.lru_cache(1)
def covered_face_person():
    im=gray_portrait().resize((680,710),Image.Resampling.LANCZOS)
    d=ImageDraw.Draw(im,'RGBA')
    # despair pose: both hands fully cover eyes and face, left/right cuffs
    for mirrored in (False,True):
        # fingers are separate tapered rounded strokes; torso remains visible
        cx=293 if not mirrored else 404
        sign=1 if not mirrored else -1
        d.polygon([(cx-sign*70,590),(cx-sign*81,460),(cx-sign*65,268),(cx-sign*32,222),(cx+sign*26,250),(cx+sign*52,470)],fill=(189,185,180,255))
        for j in range(4):
            fx=cx+sign*(j*14-24)
            d.line((fx,250,fx+sign*12,475),fill=(127,130,126,110),width=3)
    return im


def tilted_text_scene(baseim,t):
    """Group-tilted, depth-ordered typography with no duplicated base titles."""
    # Rebuild the background as smoke, keeping only muted original atmosphere.
    blur = baseim.convert('RGB').filter(ImageFilter.GaussianBlur(65))
    veil=Image.new('RGB',(W,H),(22,25,29))
    im=Image.blend(veil,blur,0.44).convert('RGBA')
    paste(im,smoke_texture(round(t*.25)*4),0,0,.95)
    # distressed foreground figure emerges through the cloud at a measured interval
    qperson=sm(t,24.36,24.96)
    person=covered_face_person()
    paste(im,person,360,128,qperson*.94)
    # persistent gold remnant from preceding SCAM scene along right edge
    rem=title_sprite('M',255,.95,1.0)
    paste(im,rem,1095,330,(1-sm(t,25.32,26.36))*.29)
    def put_tilt(txt,x,y,sz,wx,wy,a):
        s=title_sprite(txt,sz,wx,wy)
        s=s.rotate(-7.5,expand=True,resample=Image.Resampling.BICUBIC)
        paste(im,s,x,y,a)
    q1=sm(t,24.86,25.13);q2=sm(t,25.07,25.40);q3=sm(t,25.39,25.84)
    put_tilt('THOUSANDS',93,215-(1-q1)*27,112,.93,1.08,q1)
    put_tilt('OF INNOCENT',608,258-(1-q2)*30,82,.94,1.10,q2)
    put_tilt('PEOPLE',72,340-(1-q3)*38,225,1.08,1.12,q3)
    return im


def network_platform(baseim,t):
    im=baseim.copy()
    q=sm(t,27.26,27.81)*(1-sm(t,29.06,29.48))
    if q<.01:return im
    center=640+38*math.sin(t*1.5);dy=20*math.sin(t*2.4)
    glow=Image.new('RGBA',(W,H),(0,0,0,0));g=ImageDraw.Draw(glow,'RGBA')
    for j in range(3):
        yy=446+j*67+dy
        ww=465-j*50
        g.polygon([(center-ww*.43,yy-38),(center+ww*.43,yy-38),(center+ww*.56,yy+5),(center-ww*.56,yy+5)],fill=(189,247,39,int(q*(125+35*j))))
        g.line([(center-ww*.56,yy+5),(center+ww*.56,yy+5)], fill=(243,250,82,int(q*200)),width=8)
        g.line([(center-ww*.43,yy-38),(center+ww*.43,yy-38)],fill=(255,210,44,int(q*155)),width=7)
    im=Image.alpha_composite(im,glow.filter(ImageFilter.GaussianBlur(19)))
    im=Image.alpha_composite(im,glow)
    return im


def scheme_red(baseim,t):
    if t<34.10:return baseim
    q=sm(t,34.10,34.29)
    a=np.array(baseim.convert('RGB'),dtype=np.float32)
    # warm dark-red background with gold network kept distinguishable
    out=a.copy();out[:,:,0]=np.clip(a[:,:,0]*(1+.08*q)+q*19,0,255)
    out[:,:,1]=np.clip(a[:,:,1]*(1-.24*q),0,255)
    out[:,:,2]=np.clip(a[:,:,2]*(1+.13*q)+q*32,0,255)
    im=Image.fromarray(out.astype('uint8'),'RGB').convert('RGBA')
    # kinetic title color shift to pink/magenta
    if t>34.26:
        d=ImageDraw.Draw(im,'RGBA')
        b=title_sprite('THE PONZI SCHEME',89,1.0,1.14)
        # bright pink overlay on active golden word region
        colored=Image.new('RGBA',b.size,(225,68,150,0)); colored.putalpha(b.getchannel('A'))
        colored=colored.rotate(-2,expand=True,resample=Image.Resampling.BICUBIC)
        d.rectangle((60,310,1200,475),fill=(29,6,19,100))
        paste(im,colored,118,325,sm(t,34.26,34.40))
    return im


def charles_title_scene(t):
    im=Image.new('RGBA',(W,H),(0,0,2,255))
    a=sm(t,42.60,42.95)
    main=title_sprite('CHARLES PONZI',137,.84,1.50,True)
    paste(im,main,(W-main.width)//2,241-(1-a)*17,a)
    # subtly shifting highlight/noise texture with warmer fire tint
    return im


def chapter_scene(t):
    im=Image.new('RGBA',(W,H),(21,12,15,255))
    d=ImageDraw.Draw(im,'RGBA')
    # money first: 3 vertical cutouts at different depth and tilt; each enters in sequence.
    positions=[(230,-80,-9,.84,48.42),(515,-70,2,1.00,48.60),(845,-95,12,.91,48.77)]
    for x,y,ang,sc,st in positions:
        q=sm(t,st,st+.34)
        if q>0:
            note=chapter_bill(ang);note=note.resize((int(note.width*sc),int(note.height*sc)),Image.Resampling.BICUBIC)
            paste(im,note,x-int((1-q)*26),y+int((1-q)*130),q)
    # faint triangular frame and grain
    q1=sm(t,48.90,49.45)
    if q1>0:
        frame=Image.new('RGBA',(W,H),(0,0,0,0));fd=ImageDraw.Draw(frame,'RGBA')
        fd.polygon([(640,147),(290,670),(995,670)],outline=(249,229,199,int(185*q1)),width=6)
        paste(im,frame,0,0,q1)
    q2=sm(t,49.05,49.70)
    if q2>0:
        p=chapter_person().resize((590,650),Image.Resampling.LANCZOS)
        # slight camera rotation/tilt while portrait rises into view
        p=p.rotate(-4.5*sm(t,49.7,50.5),expand=True,resample=Image.Resampling.BICUBIC)
        paste(im,p,330,230+int((1-q2)*230),q2)
    # text is added before its black band; band appears afterward
    qtxt=sm(t,50.15,50.43)
    if qtxt:
        tx=title_sprite('LIVING BEYOND HIS MEANS',60,1.02,1.06,True,True)
        paste(im,tx,(W-tx.width)//2,574,qtxt)
    qband=sm(t,50.54,50.82)
    if qband:
        band=Image.new('RGBA',(W,90),(0,0,0,int(230*qband)))
        paste(im,band,0,558,qband)
        tx=title_sprite('LIVING BEYOND HIS MEANS',60,1.02,1.06,True,True)
        paste(im,tx,(W-tx.width)//2,574,qtxt)
    if t>50.93:
        tx=title_sprite('CHAPTER',32,1.0,1.0,False,True)
        paste(im,tx,(W-tx.width)//2,659,sm(t,50.93,51.18)*.9)
    # fire along money edge after chapter text is present
    f=sm(t,50.28,50.98)
    if f>0:
        fire=fire_background(1)
        # burn overlay only on edges, foreground remains visible
        edge=fire.crop((0,420,1280,720)).resize((W,300))
        paste(im,edge,0,515,.17*f)
    return im


def pyramid_surface(im,cx,by,w,h,shade):
    d=ImageDraw.Draw(im,'RGBA')
    # sloped stepped polygon facets, stronger recession and occlusion than icon triangles
    left=(cx-w*.50,by);right=(cx+w*.50,by);apex=(cx,by-h)
    d.polygon([apex,left,(cx-w*.08,by)],fill=(207,152,92,255))
    d.polygon([apex,(cx-w*.08,by),right],fill=(94,61,39,255))
    steps=max(6,int(h/12))
    for j in range(steps):
        q=(j+1)/steps;y=apex[1]+h*q
        half=w*.5*q
        d.line((cx-half,y,cx+half,y),fill=(252,201,118,int(155*q)),width=max(1,int(w/250)))
    for j in range(8):
        q=(j+.5)/8
        x=cx-w*.48*q
        d.line((x,by-h*q,x+8,by-h*q+8),fill=(92,57,38,110),width=3)


def pyramids_flythrough(t):
    """Continuous dolly through staggered pyramids, no fixed row-of-icons."""
    im=Image.new('RGBA',(W,H),(22,10,11,255));d=ImageDraw.Draw(im,'RGBA')
    for y in range(H):
        q=y/H
        d.line((0,y,W,y),fill=(int(22+42*q),int(10+17*q),int(14+5*q),255),width=1)
    # red/orange atmospheric horizon with flowing light
    glow=Image.new('RGBA',(W,H),(0,0,0,0));gd=ImageDraw.Draw(glow,'RGBA')
    gd.ellipse((-200,328,1480,520),fill=(235,72,19,115))
    gd.line((0,453,1280,444),fill=(249,107,17,200),width=13)
    paste(im,glow.filter(ImageFilter.GaussianBlur(24)),0,0,.95)
    # independent depth planes, camera travels past near left structure
    u=max(0,t-57.35)
    targets=[
        # x0, depth factor, base y, width at start, height at start
        (180,2.75,780,460,440),
        (850,.92,673,410,380),
        (1290,1.25,732,380,345),
        (540,.42,615,220,195),
    ]
    for x0,z,base_y,w,h in sorted(targets,key=lambda p:p[1]):
        # camera dolly: foreground approaches and slides out, deeper objects lag
        scale=1 + u*.47*z
        dx=-u*180*z
        cx=x0+dx
        by=base_y + u*42*z
        pyramid_surface(im,cx,by,w*scale,h*scale,z)
    return im

PATCHES=[('S08_COUNTING_FLAMES',16.08,19.83),('S10_TEXT_TILT_SMOKE',24.82,26.77),('S11_PLATFORM',27.13,29.52),('S13_RED_SCHEME',34.08,34.52),('S17_FIERY_TITLE',42.48,47.04),('S19_VERTICAL_MONEY_CHAPTER',48.40,51.30),('S21_PYRAMID_FLYTHROUGH',57.30,59.02)]

def patch_frame(original,t):
    if 16.08<=t<19.83:
        patch=flames_scene(t)
        q=sm(t,16.08,16.27)*(1-sm(t,19.62,19.83))
        return blend(original,patch,q)
    if 24.82<=t<26.77:
        patch=tilted_text_scene(original,t)
        return blend(original,patch,sm(t,24.82,24.94)*(1-sm(t,26.69,26.77)))
    if 27.13<=t<29.52:return network_platform(original,t)
    if 34.08<=t<34.52:return scheme_red(original,t)
    if 42.48<=t<47.04:
        return blend(original,charles_title_scene(t),sm(t,42.48,42.66)*(1-sm(t,46.94,47.04)))
    if 48.40<=t<51.30:
        return blend(original,chapter_scene(t),sm(t,48.40,48.61)*(1-sm(t,51.12,51.30)))
    if 57.30<=t<59.02:
        return blend(original,pyramids_flythrough(t),sm(t,57.30,57.52)*(1-sm(t,58.90,59.02)))
    return original


def render(out,basevideo=DEFAULT_BASE,start=0,end=60,crf=23,scale=1):
    cap=cv2.VideoCapture(str(basevideo))
    if not cap.isOpened(): raise FileNotFoundError(basevideo)
    cap.set(cv2.CAP_PROP_POS_FRAMES,int(start*FPS))
    w,h=int(W*scale),int(H*scale)
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{w}x{h}','-framerate',str(FPS),'-i','-',
         '-an','-c:v','libx264','-preset','veryfast','-crf',str(crf),'-pix_fmt','yuv420p','-movflags','+faststart',str(out)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for i in range(int(start*FPS),int(end*FPS)):
            ok,f=cap.read()
            if not ok: raise RuntimeError(f'Missing base procedural frame {i}')
            t=i/FPS
            orig=Image.fromarray(cv2.cvtColor(f,cv2.COLOR_BGR2RGB)).convert('RGBA')
            new=patch_frame(orig,t)
            arr=np.asarray(new.convert('RGB'))
            if scale!=1:arr=cv2.resize(arr,(w,h),interpolation=cv2.INTER_AREA)
            proc.stdin.write(arr.tobytes())
            if i%125==0:print(f'PROCEDURAL frame {i}/1500',flush=True)
    finally:
        cap.release()
        if proc.stdin:proc.stdin.close()
    if proc.wait()!=0:raise RuntimeError('Encoder failed')


def get_still(t,basevideo=DEFAULT_BASE):
    cap=cv2.VideoCapture(str(basevideo));cap.set(cv2.CAP_PROP_POS_FRAMES,int(t*FPS));ok,f=cap.read();cap.release()
    if not ok:raise RuntimeError('Frame missing')
    return patch_frame(Image.fromarray(cv2.cvtColor(f,cv2.COLOR_BGR2RGB)).convert('RGBA'),t)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--video',action='store_true');p.add_argument('--still',type=float)
    p.add_argument('--out',default=str(ROOT/'ponzi_v30_PROCEDURAL_BASE.mp4'));p.add_argument('--base',default=str(DEFAULT_BASE));p.add_argument('--crf',type=int,default=22);p.add_argument('--start',type=float,default=0);p.add_argument('--end',type=float,default=60)
    a=p.parse_args()
    if a.still is not None:get_still(a.still,a.base).save(a.out)
    elif a.video:render(a.out,a.base,start=a.start,end=a.end,crf=a.crf)
    else:p.print_help()
