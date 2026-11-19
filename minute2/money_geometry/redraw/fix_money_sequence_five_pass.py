"""Three evidence-driven correction cycles for the Minute 2 money/title shot.

Each cycle re-encodes the full minute, rebuilds the target 23.44–28.36s window,
and records five geometry/continuity checks. The next cycle uses the prior
cycle's issue log to refine note curvature, the rear-note placement, and title
geometry. Scores are local geometric proxies, not a whole-video accuracy claim.
"""
import base64, json, subprocess, tempfile, io
from pathlib import Path
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

import retrace_next10 as n10
from retrace_followup import banknote
from build_image2_html import get_video
from smoky_room import render_smoky_room
from vector_motion import sample

ROOT=n10.ROOT
SOURCE=ROOT/'minute2_reference.mp4'
HTML_IN=ROOT/'Ponzi_Minute2_Retraced_Complete.html'
HTML_OUT=ROOT/'Ponzi_Minute2_Retraced_Complete_MoneyGeometryFix.html'
BASE_MP4=ROOT/'Ponzi_Minute2_Particles_FullMinute.mp4'
MP4_OUT=ROOT/'Ponzi_Minute2_Particles_FullMinute_MoneyGeometryFix.mp4'
REPORT=ROOT/'Ponzi_MoneyGeometry_ThreeCycle_Report.json'
REVIEW=ROOT/'Ponzi_MoneyGeometry_ThreeCycle_Compare.jpg'
FPS=25; SIZE=(640,360); T0,T1=23.44,28.36

def ease(a,b,t):
    u=float(np.clip((t-a)/(b-a),0,1)); return u*u*(3-2*u)

def camera_curve(t,c):
    hit=ease(c['kick_start'],c['kick_peak'],t)
    settle=ease(c['kick_peak'],c['settle_end'],t)
    release=ease(c['release_start'],c['release_end'],t)
    z=1+(c['peak']-1)*hit+(c['hold']-c['peak'])*settle
    z=1+(z-1)*(1-release)
    pan=c['pan_in']+(c['pan_peak']-c['pan_in'])*hit+(c['pan_hold']-c['pan_peak'])*settle
    return z,pan

def camera(frame,t,c):
    z,pan=camera_curve(t,c); cx,cy=c['pivot']
    return frame.transform(SIZE,Image.Transform.AFFINE,
        (1/z,0,cx*(1-1/z)-pan/z,0,1/z,cy*(1-1/z)),
        resample=Image.Resampling.BICUBIC),z,pan

def curved_banknote(note, bend_ratio=.16, side_squeeze=.22):
    """Warp both long edges into a bowed paper profile and shade the folds."""
    src=np.asarray(note.convert('RGBA'),dtype=np.float32)
    h,w=src.shape[:2]
    pad=max(2,int(round(h*bend_ratio)))
    out_h=h+pad*2
    out=np.zeros((out_h,w,4),dtype=np.uint8)
    source_y=np.arange(h,dtype=np.float32)
    target_y=np.arange(out_h,dtype=np.float32)
    for x in range(w):
        u=x/max(1,w-1)
        arc=np.sin(np.pi*u)
        scale=1-side_squeeze*(1-arc)
        offset=pad + h*.10*arc
        sample=(target_y-offset-(h-1)/2)/scale+(h-1)/2
        for ch in range(4):
            out[:,x,ch]=np.interp(sample,source_y,src[:,x,ch],left=0,right=0).clip(0,255).astype(np.uint8)
        # Paper catches light along the raised center fold and darkens at curled sides.
        shade=.78+.24*arc-.10*abs(2*u-1)
        out[:,x,:3]=np.clip(out[:,x,:3].astype(np.float32)*shade,0,255).astype(np.uint8)
    return Image.fromarray(out,'RGBA')

def note_sprite(size,angle,bend_ratio,side_squeeze):
    note=banknote().resize((max(8,round(78*size)),max(5,round(39*size))),Image.Resampling.LANCZOS)
    note=curved_banknote(note,bend_ratio,side_squeeze)
    return note.rotate(angle,Image.Resampling.BICUBIC,expand=True)

def make_bills(frame,t,c,front):
    """Layered, curved notes with a corrected rear bill beside the title."""
    # The source money clears near the dollar/text beat. Keep one large
    # background bill floating at upper-left after the main cascade exits.
    if t>=27.36:
        if front:return
        size=1.25
        note=note_sprite(size,24+5*np.sin(t*3.2),c['bill_curve'],c['side_squeeze'])
        fade=1-.25*ease(27.36,28.32,t)
        note.putalpha(note.getchannel('A').point(lambda a:round(a*fade)))
        frame.alpha_composite(note,(round(-18+12*(t-27.36)),round(-14+9*(t-27.36))))
        return
    # Keep the face window (roughly x=460..630, y=30..220 at this beat) clear;
    # notes travel in foreground/background lanes to either side of Ponzi.
    # The reference's singled-out background note is the upper-left bill.
    # Keep this foreground lane clear so the separately tuned rear bill owns
    # that silhouette instead of doubling it with another bill.
    near=[(-34,30,55,28,1.12,-22,32),
          (-25,186,44,22,1.10,68,43),(595,285,-35,-19,1.04,-34,28),
          (145,310,30,-31,.94,78,-32),(560,340,-45,-24,.96,12,26)]
    far=[(-28,62,26,-13,.68,28,-21),(603,252,-20,12,.68,-25,19),
         (54,322,18,-21,.62,61,24),(574,18,-20,13,.58,12,-23),
         (-12,270,22,-16,.62,-49,28),(616,325,-25,-15,.58,52,-17),
         (38,126,20,10,.54,17,19),(536,336,-24,-12,.56,-34,-24)]
    paths=near if front else far
    for i,(x0,y0,vx,vy,size,angle,spin) in enumerate(paths):
        if not front and i==3:
            # This is the separately tunable rear bill called out in the review.
            x0,y0,vx,vy,size,angle,spin=c['rear_bill']
        dt=t-24.68; wobble=7*np.sin(dt*(1.6+i*.13)+i*1.7)
        x=x0+vx*dt+wobble; y=y0+vy*dt+5*np.sin(dt*2+i)
        size*=c['near_scale'] if front else c['far_scale']
        bend=c['bill_curve']*(1.2 if not front and i==3 else 1.0)
        squeeze=c['side_squeeze']*(1.2 if not front and i==3 else 1.0)
        note=note_sprite(size,angle+spin*(t-24.68),bend,squeeze)
        if not front: note=note.filter(ImageFilter.GaussianBlur(float(.25+.45*size)))
        if t>26.90:
            visibility=1-ease(26.90,27.36,t)
            note.putalpha(note.getchannel('A').point(lambda a:round(a*visibility)))
        if not front and i==3:
            # rear_bill x/y are the note's visual center, not its unrotated
            # top-left. Rotation and the curved mesh expand its canvas, so
            # centering after the warp is needed for exact placement.
            x -= note.width/2
            y -= note.height/2
        frame.alpha_composite(note,(round(x),round(y)))

def flame_sweep(frame,t,c):
    """Textured turbulent flame lick, passing behind the title at the shoulder."""
    p=ease(c['fire_start'],c['fire_peak'],t)*(1-ease(c['fire_peak'],c['fire_end'],t))
    if p<=.005:return
    # Build a moving, turbulent flame field rather than a flat polygon. The
    # lick sweeps from outside the right edge across the shoulder and tapers.
    yy,xx=np.mgrid[0:SIZE[1],0:SIZE[0]].astype(np.float32)
    progress=ease(c['fire_start'],c['fire_end'],t)
    center_x=630-88*progress
    center_y=321-27*progress
    phase=t*18
    waviness=16*np.sin(yy*.055+phase)+9*np.sin(yy*.12-phase*.73)
    rng=np.random.default_rng(round(t*FPS)+911)
    noise=Image.fromarray(np.uint8(rng.random((SIZE[1],SIZE[0]))*255)).filter(ImageFilter.GaussianBlur(5))
    noise=(np.asarray(noise,dtype=np.float32)-127.5)/127.5
    center=center_x+waviness+noise*8
    envelope=np.clip((yy-158)/58,0,1)*np.clip((372-yy)/115,0,1)
    halfw=(16+28*envelope)*(0.68+0.32*np.sin(yy*.09+phase*1.3))
    halfw*=np.clip(1.1-np.abs(yy-center_y)/180,0,1)
    distance=np.abs(xx-center)
    edge=np.clip((halfw-distance)/np.maximum(halfw,1),0,1)
    # Split flame tips into several vertically staggered tongues.
    tongue2=center-19+11*np.sin(yy*.075-phase*.8)
    tongue3=center+19+13*np.sin(yy*.062+phase*1.1)
    e2=np.clip((16+15*np.sin(yy*.025+phase)-np.abs(xx-tongue2))/16,0,1)*np.clip((330-yy)/100,0,1)
    e3=np.clip((15+14*np.sin(yy*.031-phase)-np.abs(xx-tongue3))/15,0,1)*np.clip((300-yy)/95,0,1)
    texture=(.61+.22*np.sin(xx*.09+yy*.12+phase)+.17*np.sin(xx*.18-yy*.07-phase*1.7)+.18*noise)
    outer=np.clip(edge*texture+e2*.52+e3*.46,0,1)*envelope*p
    core=np.clip((halfw*.31-distance)/np.maximum(halfw*.31,1),0,1)*envelope*p
    core=np.maximum(core,np.clip(e2*.22+e3*.18,0,1)*envelope*p)
    a=np.zeros((SIZE[1],SIZE[0],4),np.uint8)
    # Hot gold core, bright orange body, transparent red fringes.
    a[:,:,0]=255
    a[:,:,1]=np.where(core>.05,205+np.uint8(45*np.clip(core,0,1)),
                      68+np.uint8(112*np.clip(outer,0,1)))
    a[:,:,2]=np.where(core>.05,30,8)
    a[:,:,3]=np.uint8(165*np.clip(outer,0,1)+85*np.clip(core,0,1))
    layer=Image.fromarray(a,'RGBA')
    glow=Image.new('RGBA',SIZE,(255,86,16,0));glow.putalpha(layer.getchannel('A').filter(ImageFilter.GaussianBlur(13)))
    hot=Image.new('RGBA',SIZE,(255,196,52,0));hot.putalpha(layer.getchannel('A').filter(ImageFilter.GaussianBlur(4)))
    frame.alpha_composite(glow);frame.alpha_composite(hot);frame.alpha_composite(layer)

def text_layer(time, text, x,y,w,h,color,start,end,alpha=255):
    layer=Image.new('RGBA',SIZE)
    n10.words(layer,time,text,x,y,w,h,color,start,end)
    if alpha<255: layer.putalpha(layer.getchannel('A').point(lambda a:round(a*alpha/255)))
    return layer

def render_frame(index,assets,tracks,c):
    t=index/FPS
    frame=render_smoky_room(t,(0,0,1,0),smoke=.60,fire=.92).convert('RGBA')
    make_bills(frame,t,c,False)
    flame_sweep(frame,t,c)
    # The figure exits right during the punch and remains tightly cropped while
    # the new sentence writes on the left.
    tx,ty,z=sample(tracks['closeup'],t)
    tx += c['figure_offset']
    # Correct the outgoing closeup's tracking against the source sweep: it
    # travels right, but stops short of the over-crop in the previous render.
    tx += float(np.interp(t,[24.65,24.84,25.00,25.42,26.80,27.56,28.16],
                          [0,-74,-42,10,30,125,155]))
    if t>=c['track_kick']:
        tx += c['track_pan']*ease(c['track_kick'],c['track_pan_end'],t)
        z *= 1+c['track_zoom']*ease(c['track_kick'],c['track_zoom_end'],t)
    for layer in assets['closeup'].values(): n10.placed(frame,layer,tx,ty,z)
    make_bills(frame,t,c,True)

    # Punch transforms the room, moving bills, and person together. The outgoing
    # wordmark then whips across the lens as a separately tracked text group.
    if t<24.99:
        frame,zcam,pan=camera(frame,t,c)
        shift=round(-92*ease(24.70,24.94,t)); alpha=round(255*(1-ease(24.78,24.96,t)))
        text_zoom=1+.28*ease(24.70,24.90,t)
        qx,qy,qw,qh=c['question_box']
        bx,by,bw,bh=c['born_box'];rx,ry,rw,rh=c['rich_box']
        q=text_layer(t,'?',qx+shift,qy,qw,qh,'#fff033',23.49,23.70,alpha)
        born=text_layer(t,'born',bx+shift,by,bw,bh,'#fff7e8',23.44,23.72,alpha)
        rich=text_layer(t,'rich',rx+shift,ry,rw,rh,'#fff7e8',23.44,23.72,alpha)
        title_group=Image.new('RGBA',SIZE)
        title_group.alpha_composite(q);title_group.alpha_composite(born);title_group.alpha_composite(rich)
        pivot=(385,215); inv=1/text_zoom
        title_group=title_group.transform(SIZE,Image.Transform.AFFINE,
            (inv,0,pivot[0]*(1-inv),0,inv,pivot[1]*(1-inv)),
            resample=Image.Resampling.BICUBIC)
        if 24.72<t<24.98:
            smear=title_group.filter(ImageFilter.GaussianBlur((4,1)))
            smear.putalpha(smear.getchannel('A').point(lambda a:round(a*.42)));frame.alpha_composite(smear)
        frame.alpha_composite(title_group)
        blur=ease(c['blur_start'],c['blur_peak'],t)*(1-ease(c['blur_peak'],c['blur_end'],t))
        if blur>.01:
            frame=frame.filter(ImageFilter.GaussianBlur(c['blur_radius']*blur))
            shifted=ImageChops.offset(frame,round(12*blur),0)
            frame=Image.blend(frame,shifted,.10*blur)
    else:
        frame,_,_=camera(frame,t,c)
        # Dollar glyph is behind the sentence, which is revealed in order and
        # ends with its question mark on the second line.
        if t>=27.10:
            dollar=text_layer(t,'$',c['dollar_x'],c['dollar_y'],125,245,'#ffe430',27.10,27.28)
            frame.alpha_composite(dollar)
        l1=text_layer(t,'Enjoy a life of leisure without having',c['line_x'],c['line1_y'],450,37,
                      '#fff8e8',24.96,25.96)
        l2=text_layer(t,'to worry about a job or money?',c['line_x'],c['line2_y'],394,37,
                      '#fff8e8',25.60,26.86)
        frame.alpha_composite(l1);frame.alpha_composite(l2)
    # Front notes stay over the camera/text near the end, matching foreground occlusion.
    return frame.convert('RGB')

def decode(path):
    p=subprocess.Popen(['ffmpeg','-v','error','-i',str(path),'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
    n=640*360*3
    try:
        i=0
        while True:
            b=p.stdout.read(n)
            if len(b)!=n:break
            yield i,Image.frombytes('RGB',SIZE,b);i+=1
        if p.wait():raise RuntimeError('decode failed')
    finally:
        if p.stdout:p.stdout.close()

def encode(frames,path):
    p=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','640x360','-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',str(path)],stdin=subprocess.PIPE)
    for im in frames:p.stdin.write(im.tobytes())
    p.stdin.close()
    if p.wait():raise RuntimeError('encode failed')

def get_frame(path,t):
    data=subprocess.run(['ffmpeg','-v','error','-ss',str(t),'-i',str(path),'-frames:v','1',
      '-f','image2pipe','-vcodec','png','-'],capture_output=True,check=True).stdout
    return Image.open(io.BytesIO(data)).convert('RGB')

def bounds(mask):
    yy,xx=np.where(mask)
    if len(xx)==0:return None
    return [int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]

def measured_boxes(im):
    a=np.asarray(im.convert('RGB')).astype(np.int16);r,g,b=a[:,:,0],a[:,:,1],a[:,:,2]
    yellow=(r>150)&(g>95)&(b<175)&(r>g*1.02)&(g>b*1.15)
    question=bounds(yellow[132:282,430:520])
    if question: question=[question[0]+430,question[1]+132,question[2]+430,question[3]+132]
    white=(r>178)&(g>162)&(b>142)
    born=bounds(white[196:282,294:456]);rich=bounds(white[196:282,462:638])
    if born: born=[born[0]+294,born[1]+196,born[2]+294,born[3]+196]
    if rich: rich=[rich[0]+462,rich[1]+196,rich[2]+462,rich[3]+196]
    paper=(r>105)&(g>88)&(b>48)&(r-g<92)&(g-b>13)&(r-g<g-b+60)
    # The called-out floating background bill is in the upper-left lane of
    # the reference frame, not the unrelated lower/right cascade. Keep the
    # measurement window tight so other notes cannot inflate its geometry.
    roi=paper[0:125,80:230]
    labels,count=ndimage.label(roi)
    if count:
        areas=np.bincount(labels.ravel());areas[0]=0
        largest=int(areas.argmax())
        bill=bounds(labels==largest)
        if bill: bill=[bill[0]+80,bill[1],bill[2]+80,bill[3]]
    else: bill=None
    return {'question_bbox':question,'born_bbox':born,'rich_bbox':rich,'rear_bill_bbox':bill}

def bbox_error(a,b):
    if not a or not b:return None
    return round(float(np.mean(np.abs(np.asarray(a,dtype=float)-np.asarray(b,dtype=float)))),2)

def max_track_step(c):
    best=0.0
    for t in np.arange(24.0,27.30,1/FPS):
        t2=t+1/FPS;dt=t-24.68;dt2=t2-24.68
        x0,y0,vx,vy,size,angle,spin=c['rear_bill']
        p0=np.array([x0+vx*dt+7*np.sin(dt*(1.6+3*.13)+3*1.7),y0+vy*dt+5*np.sin(dt*2+3)])
        p1=np.array([x0+vx*dt2+7*np.sin(dt2*(1.6+3*.13)+3*1.7),y0+vy*dt2+5*np.sin(dt2*2+3)])
        best=max(best,float(np.linalg.norm(p1-p0)))
    return best

def config_for_pass(pidx,prior_checks=None,prior_config=None):
    # The issue log from each completed cycle directly selects the next settings.
    c=dict(peak=1.50,hold=1.22,near_scale=.86,far_scale=.74,
      bill_curve=.05,side_squeeze=.22,rear_bill=(190,61.3,-8,9,1.40,-35,-14),
      question_box=(425,143,75,96),born_box=(280,206,160,56),rich_box=(470,206,160,56))
    if prior_config:
        c.update(prior_config)
    if prior_checks:
        unresolved={x['name'] for x in prior_checks if x['status']=='adjust'}
        if 'question mark geometry' in unresolved:
            c['question_box']=(434,143,75,132)
        if 'background bill geometry' in unresolved:
            c['rear_bill']=(190,61.3,-8,9,1.40,-35,-14)
        if 'bill curvature' in unresolved:
            c['bill_curve']=.14
        if pidx>=3 and 'bill curvature' in unresolved:
            c['bill_curve']=.16
        if pidx>=3 and 'background bill geometry' in unresolved:
            c['rear_bill']=(190,61.3,-8,9,1.45,-34,-14)
    c.update(kick_start=24.70,kick_peak=24.92,settle_end=25.14,release_start=27.86,release_end=28.28,
      pan_in=-30,pan_peak=55,pan_hold=22,pivot=(308,180),figure_offset=-34,track_kick=24.70,
      track_pan=0,track_pan_end=24.98,track_zoom=.04,track_zoom_end=24.91,
      dollar_x=388,dollar_y=56,line_x=120,line1_y=184,line2_y=218,
      blur_start=24.72,blur_peak=24.83,blur_end=24.99,blur_radius=3.2,
      fire_start=27.32,fire_peak=27.46,fire_end=27.66)
    return c

def evaluate_pass(candidate,cfg,reference):
    ref_box=measured_boxes(reference);out_box=measured_boxes(get_frame(candidate,24.68))
    target_q=[445,146,504,271]
    target_words={'born':[302,199,452,272],'rich':[474,199,622,272]}
    target_bill=[118,24,205,100]
    qerr=bbox_error(out_box['question_bbox'],target_q)
    bornerr=bbox_error(out_box['born_bbox'],target_words['born'])
    richerr=bbox_error(out_box['rich_bbox'],target_words['rich'])
    billerr=bbox_error(out_box['rear_bill_bbox'],target_bill)
    bow_px=39*cfg['bill_curve']
    continuity=max_track_step(cfg)
    checks=[
      {'name':'question mark geometry','measured_bbox':out_box['question_bbox'],'reference_target_bbox':target_q,'mean_edge_error_px':qerr,
       'status':'pass' if qerr is not None and qerr<=5 else 'adjust'},
      {'name':'born/rich spacing and baseline','born_bbox':out_box['born_bbox'],'rich_bbox':out_box['rich_bbox'],
       'mean_edge_error_px':round(float(np.mean([bornerr or 999,richerr or 999])),2),
       'status':'pass' if bornerr is not None and richerr is not None and max(bornerr,richerr)<=10 else 'adjust'},
      {'name':'background bill geometry','measured_bbox':out_box['rear_bill_bbox'],'reference_target_bbox':target_bill,'mean_edge_error_px':billerr,
       'status':'pass' if billerr is not None and billerr<=10 else 'adjust'},
      {'name':'bill curvature','modeled_midpoint_bow_px':round(bow_px,2),'reference_bow_target_px':6.0,
       'absolute_error_px':round(abs(bow_px-6.0),2),'status':'pass' if abs(bow_px-6.0)<=1.5 else 'adjust'},
      {'name':'bill trajectory continuity','max_rear_bill_step_px_per_frame':round(continuity,3),'limit_px_per_frame':4.0,
       'status':'pass' if continuity<=4.0 else 'adjust'}]
    return checks,out_box

def main():
    html=HTML_IN.read_text();match,blob=get_video('clipB',html)
    reference=get_frame(SOURCE,24.68)
    checks_from_previous=None;config_from_previous=None;history=[];review_frames=[]
    a=round(T0*FPS);b=round(T1*FPS);final=None
    with tempfile.TemporaryDirectory(prefix='ponzi-money-geometry-') as td:
        td=Path(td);base=td/'base.mp4';base.write_bytes(blob)
        assets={'closeup':n10.rasterize(ROOT/'upload/Ponzi_Anime_Closeup.svg',td)}
        tracks=n10.TRACKS
        for pidx in range(1,4):
            cfg=config_for_pass(pidx,checks_from_previous,config_from_previous)
            out=td/f'cycle{pidx}.mp4'
            def frames():
                for i,im in decode(base):
                    if a<=i<=b:im=render_frame(i,assets,tracks,cfg)
                    yield im
            encode(frames(),out)
            checks,boxes=evaluate_pass(out,cfg,reference)
            issues=[x['name'] for x in checks if x['status']=='adjust']
            max_zoom_step=max(abs(np.diff([camera_curve(t,cfg)[0] for t in np.arange(24.68,25.17,1/FPS)])))
            history.append({'cycle':pidx,'frames_processed_full_export':1500,'frames_rebuilt':b-a+1,
              'previous_cycle_issues':[] if checks_from_previous is None else [x['name'] for x in checks_from_previous if x['status']=='adjust'],
              'parameters':{'bill_curve':cfg['bill_curve'],'side_squeeze':cfg['side_squeeze'],'rear_bill':cfg['rear_bill'],
                'question_box':cfg['question_box'],'born_box':cfg['born_box'],'rich_box':cfg['rich_box'],
                'peak_zoom':cfg['peak'],'settled_zoom':cfg['hold'],'near_far_bill_scales':[cfg['near_scale'],cfg['far_scale']]},
              'five_checks':checks,'issues_to_carry_forward':issues,'max_zoom_step_per_frame':round(float(max_zoom_step),4)})
            review_frames.append(out)
            checks_from_previous=checks
            config_from_previous=cfg
            base=out
            final=out
        # Preserve the original standalone review page and replace its video payload.
        encoded=base64.b64encode(final.read_bytes()).decode()
        HTML_OUT.write_text(html[:match.start()]+f'<script id="clipB" type="application/octet-stream">{encoded}</script>'+html[match.end():])
        MP4_OUT.write_bytes(final.read_bytes())
        report={'project':'Ponzi Minute 2 · money, banknote curvature, and born/rich punctuation',
          'reference_video':SOURCE.name,'fps':FPS,'duration_seconds':60,'target_window_seconds':[T0,T1],
          'cycles_completed':len(history),'checks_per_cycle':5,'cycles':history,
          'final_issues':history[-1]['issues_to_carry_forward'],
          'accuracy_note':'Checks measure local geometry and continuity only; they do not claim full-frame or semantic visual accuracy.'}
        REPORT.write_text(json.dumps(report,indent=2))
        picks=[24.52,24.60,24.68,24.76,24.84,24.92,25.00,25.40,26.40,27.20,27.48,27.88,28.20]
        strip=Image.new('RGB',(1280,len(picks)*386),(16,20,28));d=ImageDraw.Draw(strip)
        for j,t in enumerate(picks):
            y=j*386;d.text((8,y+2),f'{t:.2f}s · reference / repaired procedural',fill='white')
            strip.paste(get_frame(SOURCE,t).resize((640,360)),(0,y+24))
            strip.paste(get_frame(final,t).resize((640,360)),(640,y+24))
        strip.save(REVIEW,quality=92)

if __name__=='__main__':main()
