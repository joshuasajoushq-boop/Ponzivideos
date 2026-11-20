"""Render and review the Minute 2 gallery and college changes at 25 fps."""
import argparse
import base64
import io
import json
import math
import re
import subprocess as sp
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 640, 360, 25
SIZE = W, H
GALLERY = range(0)
COLLEGE = range(858, 962)
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
Y, X = np.mgrid[:H,:W].astype('float32')
# Face center readings from the reference at the native frame timestamps.
TRACK = [(34.32,432),(34.48,432),(35.20,429),(35.48,404),
         (35.72,353),(35.84,320),(35.92,285),(36.00,246),
         (36.12,207),(36.24,181),(36.36,169),(36.56,166),(38.44,166)]


def ease(a,b,t):
    x = np.clip((t-a)/(b-a),0,1)
    return x*x*(3-2*x)


def read_frames(path, frames):
    data = sp.check_output(['ffmpeg','-v','error','-ss',str(frames.start/FPS),
                            '-i',str(path),'-frames:v',str(len(frames)),
                            '-pix_fmt','rgb24','-f','rawvideo','-'])
    step = W*H*3
    if len(data) != step*len(frames):
        raise ValueError(f'Unexpected frame count or dimensions in {path}')
    return {i:Image.frombytes('RGB',SIZE,data[j*step:(j+1)*step])
            for j,i in enumerate(frames)}


def extract(image, outline):
    mask = Image.new('L',SIZE)
    ImageDraw.Draw(mask).polygon(outline,fill=255)
    layer = image.convert('RGBA')
    layer.putalpha(mask.filter(ImageFilter.GaussianBlur(.85)))
    return layer


def soft_gallery(image, strength, halo_pixels):
    rgb = np.asarray(image,dtype='float32')
    broad = np.asarray(image.filter(ImageFilter.GaussianBlur(8)),dtype='float32')
    local = np.asarray(image.filter(ImageFilter.GaussianBlur(2.2)),dtype='float32')
    # Limit the suppression to the marked amber halos in the gallery.
    window = sum(np.exp(-((X-x)**2+(Y-y)**2)/(2*halo_pixels**2))
                 for x,y in [(10,225),(245,232)])
    warm = np.clip((rgb[:,:,0]-rgb[:,:,2]-10)/36,0,1)
    low_frequency = np.maximum(local-broad,0)
    result = rgb-low_frequency*(np.clip(window,0,1)*warm*strength)[:,:,None]
    return Image.fromarray(np.uint8(result.clip(0,255)))


def corridor():
    image = Image.new('RGB',SIZE,'#190707')
    draw = ImageDraw.Draw(image)
    draw.polygon([(0,0),(303,113),(303,250),(0,360)],fill='#360b0b')
    draw.polygon([(640,0),(355,113),(355,250),(640,360)],fill='#390b0a')
    draw.polygon([(0,360),(303,250),(355,250),(640,360)],fill='#450d0b')
    for x in (18,76,130,183,230,265,393,428,478,535,595):
        u = abs(x-330)/330
        top = 110-90*u
        bottom = 250+78*u
        draw.polygon([(x,top),(x+20*u+4,top+12),(x+20*u+4,bottom-14),(x,bottom)],fill='#1e0608')
        draw.line([(x,top),(x,bottom)],fill='#570f0e',width=3)
    glow = np.exp(-((X-318)/247)**2-((Y-210)/149)**2)
    return Image.fromarray(np.uint8(np.asarray(image.filter(ImageFilter.GaussianBlur(1.6)))+
                                    glow[:,:,None]*[49,3,3]))


def incoming_face():
    im = Image.new('RGBA',SIZE)
    d = ImageDraw.Draw(im)
    d.polygon([(228,360),(246,235),(303,189),(459,187),(555,237),(640,360)],fill='#261b1d')
    d.polygon([(282,70),(328,39),(423,35),(474,69),(469,147),(438,215),
               (399,241),(357,227),(309,178),(292,130)],fill='#80564b')
    d.polygon([(370,64),(433,53),(470,84),(459,170),(423,222),(392,236),
               (418,177),(406,141),(383,127)],fill='#a77562')
    d.polygon([(283,81),(267,59),(286,32),(324,20),(408,13),(465,31),(492,68),
               (487,98),(440,76),(357,81),(303,100)],fill='#24161a')
    d.polygon([(306,112),(344,103),(371,115),(340,125)], fill='#382126')
    d.polygon([(397,115),(432,104),(458,110),(430,124)],fill='#3b2427')
    for x in (342,429):
        d.ellipse((x-11,115,x+11,123),fill='#96695b')
        d.ellipse((x-4,114,x+4,123),fill='#291b1d')
    d.polygon([(383,116),(368,162),(392,170),(407,160)],fill='#6a433b')
    d.line([(352,193),(379,197),(413,190)],fill='#4b2d30',width=5)
    return im.filter(ImageFilter.GaussianBlur(3.2))


def handwritten(seed):
    """Draw irregular pen strokes for E = mc² on a transparent card."""
    rng = np.random.default_rng(seed)
    im = Image.new('RGBA',(184,65))
    d = ImageDraw.Draw(im)
    paths = [
      [(28,8),(21,4),(12,8),(10,17),(22,24),(13,24),(6,32),(5,40),(12,47),(24,45),(29,41)],
      [(35,25),(54,23)],[(35,34),(53,32)],
      [(62,43),(68,24),(66,37),(76,26),(81,30),(79,42),(87,27),(93,30),(91,42)],
      [(118,26),(109,24),(101,30),(98,38),(103,44),(116,42)],
      [(124,13),(129,6),(137,7),(139,12),(129,22),(141,21)]]
    for path in paths:
        points = [(x+rng.uniform(-1.5,1.5),y+rng.uniform(-1.4,1.4)) for x,y in path]
        d.line(points,fill=(242,210,182,210),width=int(rng.integers(2,4)),joint='curve')
    return im.crop((0,0,146,53))


def equations(canvas,t,config,cards,near):
    rng=np.random.default_rng(802+near)
    for i in range(23 if near else 55):
        x,y=rng.uniform(-60,656),rng.uniform(-16,355)
        start=rng.uniform(34.12,36.95)
        duration=rng.uniform(1.05,2.3) if near else rng.uniform(2.2,4.5)
        p=(t-start)/duration
        if not 0<p<1:
            continue
        if near:
            scale=rng.uniform(.28,.58)+1.0*p**1.6
            x+=(-135 if i%3 else 85)*p*config['depth_speed']
            y-=62*p
            alpha=.64
            # Allow an occasional foreground overlap while keeping her eyes readable.
            if 100<x<245 and 67<y<128:
                alpha*=.33
        else:
            scale=rng.uniform(.12,.35)+.12*p
            x+=28*p
            y-=11*p
            alpha=.43
        alpha*=min(1,p*6,(1-p)*4)
        card=cards[i%len(cards)].resize((round(146*scale),round(53*scale)),Image.Resampling.LANCZOS)
        if near and scale>.78:
            card=card.filter(ImageFilter.GaussianBlur(.65+scale*.65))
        elif not near:
            card=card.filter(ImageFilter.GaussianBlur(.35))
        card.putalpha(card.getchannel('A').point(lambda a:round(a*alpha)))
        canvas.alpha_composite(card,(round(x),round(y)))


def clean_alpha(layer, trim):
    pixels=np.array(layer)
    # Retrace the back of the hair and neck to exclude the old corridor.
    ys=[0,8,20,40,62,85,110,135,155,175,190,204,224]
    xs=[478,508,530,548,557,561,554,547,535,517,490,516,640]
    boundary=np.interp(Y,ys,xs)
    edge=np.clip((boundary-X+1+(1-trim)*9)/2,0,1)
    edge[Y>=224]=1
    r,g,b=(pixels[:,:,i].astype('float32') for i in range(3))
    spill=np.clip((r-np.maximum(g,b)-21)/22,0,1)
    hair_zone=(Y<224)&((X>495)|(X<413))
    pixels[:,:,3]=np.uint8(pixels[:,:,3]*edge*(1-spill*hair_zone))
    pixels[:,:,0]=np.uint8(np.maximum(0,r-np.maximum(0,r-np.maximum(g,b)-12)*hair_zone))
    pixels[pixels[:,:,3]==0,:3]=0
    return Image.fromarray(pixels)


def new_scene(old,t,config,assets):
    room, woman, ponzi, face, cards = assets
    scene = room.convert('RGBA')
    title = Image.new('RGBA',SIZE)
    text = ImageDraw.Draw(title)
    text.text((-20,40),'COLLEGE',font=ImageFont.truetype(FONT,96),fill='#d8af26')
    if config.get("refined"):
        title = title.resize((502,H),Image.Resampling.LANCZOS)
    title.putalpha(title.getchannel("A").point(lambda a:round(a*(1-ease(36.22,36.42,t)))))
    scene.alpha_composite(title)
    # Keep the distant figure registered to the reference corridor.
    anchored = Image.new('RGBA',SIZE)
    anchored.alpha_composite(ponzi,(-config["anchor"],0))
    cover = ease(config["cover_start"],config["cover_end"],t)
    cover_map = np.clip((cover*330-(X+13*np.sin(Y*.038)))/70,0,1)
    anchored.putalpha(Image.fromarray(np.uint8(np.asarray(anchored.getchannel('A'))*(1-cover_map))))
    scene.alpha_composite(anchored)
    # Follow the incoming edge from screen-left, beneath the woman.
    progress=ease(config['reveal'],config['finish'],t)
    front=-55+progress*770
    wave=17*np.sin(Y*.022+1.2)+11*np.sin(Y*.061+t)
    matte=np.clip((front-X+wave)/54,0,1)
    shade = np.exp(-((X-390)/197)**2-((Y-171)/147)**2)
    rear = Image.fromarray(np.uint8(np.stack([14+55*shade,7+19*shade,9+16*shade],axis=-1))).convert('RGBA')
    if config.get("refined"):
        face = face.copy()
        face.putalpha(face.getchannel("A").point(lambda a:round(a*.68)))
    face = face.copy()
    visibility = np.clip((205-Y)/66,0,1)
    face.putalpha(Image.fromarray(np.uint8(np.asarray(face.getchannel('A'))*visibility)))
    rear.alpha_composite(face,(config['face_x'],config['face_y']))
    
    scene = Image.composite(rear,scene,Image.fromarray(np.uint8(matte*255)))
    equations(scene,t,config,cards,False)
    measured = np.interp(min(t,36.36),*zip(*TRACK))
    x = round((measured-464)*config['travel'])
    x = round(x*ease(34.51,35.03,t))
    x += round(config['cross']*ease(35.34,35.68,t)*(1-ease(35.80,36.30,t)))
    scene.alpha_composite(clean_alpha(woman,config['clean']),(x,0))
    equations(scene,t,config,cards,True)
    # The following flash grows from the lower-right edge before joining the
    # existing Other Plans transition.
    f = ease(38.08,38.34 if config.get("refined") else 38.42,t)
    if f>0:
        field = np.sqrt(((X-535)*.91)**2+((Y-356)*1.25)**2)
        alpha = np.clip((f*220-field+9*np.sin(X*.077+Y*.044))/40,0,1)
        light = Image.new('RGBA',SIZE,(255,225,177))
        light.putalpha(Image.fromarray(np.uint8(alpha*255)))
        scene.alpha_composite(light)
    weight = ease(34.32,34.56,t)*(1-ease(38.20,38.44,t))
    return Image.blend(old,scene.convert('RGB'),weight),464+x


def encode(base, output, replacements):
    source = sp.Popen(['ffmpeg','-v','error','-i',str(base),'-pix_fmt','rgb24',
                       '-f','rawvideo','-'],stdout=sp.PIPE)
    target = sp.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pixel_format','rgb24',
                       '-video_size','640x360','-framerate','25','-i','-','-i',str(base),
                       '-map','0:v','-map','1:a?','-c:a','copy','-c:v','libx264','-preset',
                       'fast','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',str(output)],stdin=sp.PIPE)
    step = W*H*3
    i = 0
    while data := source.stdout.read(step):
        target.stdin.write(replacements[i].tobytes() if i in replacements else data)
        i += 1
    target.stdin.close()
    if source.wait() or target.wait():
        raise RuntimeError('Video encode failed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base',type=Path)
    parser.add_argument('reference',type=Path)
    parser.add_argument('out',type=Path)
    parser.add_argument('--preserve',type=Path,required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    windows = (GALLERY,COLLEGE)
    old = {i:im for w in windows for i,im in read_frames(args.base,w).items()}
    ref = {i:im for w in windows for i,im in read_frames(args.reference,w).items()}
    plate = old[862]
    woman = extract(plate,[(382,90),(386,53),(405,24),(442,7),(479,4),(514,12),(541,30),(566,58),
      (577,87),(574,123),(560,158),(538,183),(520,191),(545,206),(572,213),
      (598,236),(609,281),(640,332),(640,359),(307,359),(319,293),(333,251),
      (350,221),(406,202),(405,176),(393,151),(388,116)])
    ponzi = extract(plate,[(155,101),(163,73),(183,60),(205,61),(224,73),(225,94),(219,125),
      (210,147),(231,160),(242,181),(244,240),(231,272),(244,289),(246,359),
      (120,359),(120,291),(131,281),(146,281),(127,259),(125,221),(130,180),(147,154),(171,141)])
    assets = corridor(),woman,ponzi,incoming_face(),[handwritten(i+70) for i in range(8)]
    common=dict(travel=1.,refined=True,face_x=-12,face_y=-41,anchor=50,cross=27,
                cover_start=35.82,cover_end=36.15)
    configs=[
       dict(common,reveal=36.23,finish=36.58,depth_speed=.82,clean=.80),
       dict(common,reveal=36.20,finish=36.51,depth_speed=1.15,clean=1.),
    ]
    base_frames=read_frames(args.preserve,COLLEGE)
    passes=[]; thumbnails=[]
    marks = [875,885,893,897,901,905,909,910,917,948]
    for index,config in enumerate(configs,1):
        frames = {}; errors=[]
        for i,im in old.items():
            t=i/FPS
            if i in GALLERY:
                weight = ease(7.20,7.36,t)*(1-ease(7.76,7.96,t))
                clean = soft_gallery(im,config['glint']*weight,config['halo'])
                pix = np.asarray(clean,dtype='float32')
                median = np.asarray(clean.filter(ImageFilter.MedianFilter(9)),dtype='float32')
                orange = np.clip(((pix[:,:,0]-pix[:,:,2])-(median[:,:,0]-median[:,:,2])-12)/27,0,1)
                edge = np.clip((75-X)/22,0,1)
                frames[i] = Image.fromarray(np.uint8(pix+(median-pix)*(edge*orange*weight)[:,:,None]))
            else:
                frames[i],x = new_scene(im,t,config,assets)
                if 35.40 <= t <= 36.56:
                    errors.append(abs(x-np.interp(t,*zip(*TRACK))))
        passes.append(dict(pass_number=index,frames=len(frames),settings=config,
                          mean_head_track_error_px=round(float(np.mean(errors)),2),
                          notes=['Retrace the matte and replace the circular reveal with a directional edge',
                                 'Advance the sweep and strengthen foreground parallax while trimming the hair edge'][index-1]))
        thumbnails.append([frames[i].resize((256,144)) for i in marks])
    results = args.out
    encode(args.preserve,results/'Ponzi_Minute2_College_Reveal.mp4',frames)
    report=dict(fps=25,windows=[[COLLEGE.start/25,(COLLEGE.stop-1)/25]],passes=passes,
                limitations='Head error compares with manually marked positions only. New face is stylized vector geometry; woman and small Ponzi were isolated from the prior procedural render.')
    (results/'Ponzi_Minute2_College_Passes.json').write_text(json.dumps(report,indent=2))
    sheet = Image.new('RGB',(768,len(marks)*168),'#151921')
    d = ImageDraw.Draw(sheet)
    for j,i in enumerate(marks):
        y=j*168
        d.text((8,y+3),f'{i/FPS:.2f}s   Reference                         Pass 1                           Pass 2',fill='white')
        for col,im in enumerate([ref[i].resize((256,144))]+[row[j] for row in thumbnails]):
            sheet.paste(im,(col*256,y+22))
    sheet.save(results/'Ponzi_Minute2_College_Comparison.jpg',quality=92)
    clean_alpha(woman,1.).save(results/'Woman_Transparent.png')
    gif_frames = []
    for i in range(886,952):
        panel = Image.new('RGB',(640,200),'#171921')
        ImageDraw.Draw(panel).text((8,3),f'{i/FPS:.2f}s   Reference                                      Updated render',fill='white')
        panel.paste(ref[i].resize((320,180)),(0,20))
        panel.paste(frames[i].resize((320,180)),(320,20))
        gif_frames.append(panel)
        if i==911:
            panel.save(results/'College_Still.jpg',quality=94)
    gif_frames[0].save(results/'College_Preview.gif',save_all=True,append_images=gif_frames[1:],duration=40,loop=0)
    gallery = []
    for i in sorted(frames):
        images = []
        for im in (ref[i],base_frames[i],frames[i]):
            buffer=io.BytesIO()
            im.resize((384,216)).save(buffer,'JPEG',quality=82)
            images.append(base64.b64encode(buffer.getvalue()).decode())
        gallery.append([i,*images])
    html = """<!doctype html><meta charset=utf-8><title>Minute 2 college reveal</title>
<style>body{background:#151921;color:white;font:16px system-ui;margin:24px}main{display:flex;gap:12px}figure{margin:0;flex:1}img{width:100%}input{width:min(70vw,720px)}button{margin:8px 6px 8px 0}</style>
<h1>Minute 2 frame review</h1><button id=prev>Previous frame</button><button id=next>Next frame</button>
<input id=seek type=range min=0 value=0 aria-label="Frame"><output id=time></output>
<main><figure><figcaption>Reference</figcaption><img></figure><figure><figcaption>Previous render</figcaption><img></figure><figure><figcaption>Updated pass 2</figcaption><img></figure></main>
<script>const frames=DATA;const seek=document.querySelector('#seek');seek.max=frames.length-1;
function show(){const [n,...imgs]=frames[+seek.value];document.querySelector('#time').value=(n/25).toFixed(2)+' s · frame '+n;document.querySelectorAll('img').forEach((im,i)=>im.src='data:image/jpeg;base64,'+imgs[i]);}
seek.oninput=show;document.querySelector('#prev').onclick=()=>{seek.stepDown();show()};document.querySelector('#next').onclick=()=>{seek.stepUp();show()};show();</script>"""
    (results/'Ponzi_Minute2_College_Review.html').write_text(html.replace('DATA',json.dumps(gallery)))


if __name__ == '__main__':
    main()
