#!/usr/bin/env python3
"""Patch only Image 2's procedural portrait in the existing standalone HTML."""
from __future__ import annotations
import base64, re, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
HTML_IN=ROOT/'rollback'/'Ponzi_Minute2_Restored_Geometry.html'
HTML_OUT=ROOT/'Ponzi_Minute2_Image2_AnimeTrace.html'
VIDEO_OUT=ROOT/'redraw'/'Ponzi_Minute2_Image2_AnimeTrace.mp4'
FPS=25; WIDTH=640; HEIGHT=360; NFRAMES=60*FPS
PATCH_FRAMES=range(467,586) # 18.68–23.40, including the follow-up question


def get_video(tag_id, html):
    m=re.search(r'<script[^>]*id="'+re.escape(tag_id)+r'"[^>]*>(.*?)</script>',html,re.S)
    if not m: raise RuntimeError(f'Missing embedded video {tag_id}')
    return m,base64.b64decode(m.group(1).strip())


def patched_frames():
    sys.path.insert(0,str(ROOT/'redraw'))
    import render_image2_anime as anime
    from vector_motion import TRACKS, draw_caption
    renderer=anime.install_patch()
    renderer.v12.CUSTOM_CAPTION_BRUSH = True
    frames={}
    for frame_no in PATCH_FRAMES:
        absolute_source_time=60.0+frame_no/FPS
        # Keep the anime cutout from the prior pass. Replace only its generated
        # lettering with editable caption tracks sampled at this timeline frame.
        frame=renderer.render(absolute_source_time).convert('RGBA')
        time = frame_no / FPS
        for caption in TRACKS['captions']:
            start, end = caption['active']
            if start <= time < end:
                draw_caption(frame, time, caption)
        frames[frame_no]=frame.convert('RGB').tobytes()
    return frames


def reencode(input_mp4:Path, output_mp4:Path, replacements):
    decoder=subprocess.Popen([
        'ffmpeg','-v','error','-i',str(input_mp4),'-f','rawvideo','-pix_fmt','rgb24','-'
    ],stdout=subprocess.PIPE)
    encoder=subprocess.Popen([
        'ffmpeg','-y','-v','error','-f','rawvideo','-pixel_format','rgb24',
        '-video_size',f'{WIDTH}x{HEIGHT}','-framerate',str(FPS),'-i','-',
        '-an','-c:v','libx264','-preset','slow','-crf','17','-pix_fmt','yuv420p',str(output_mp4)
    ],stdin=subprocess.PIPE)
    frame_bytes=WIDTH*HEIGHT*3
    try:
        for i in range(NFRAMES):
            data=decoder.stdout.read(frame_bytes)
            if len(data)!=frame_bytes: raise RuntimeError(f'Video ended early at frame {i}')
            encoder.stdin.write(replacements.get(i,data))
        encoder.stdin.close()
        if decoder.wait()!=0 or encoder.wait()!=0: raise RuntimeError('FFmpeg failed while rebuilding the embedded render')
    finally:
        if decoder.stdout: decoder.stdout.close()


def main():
    html=(HTML_IN if HTML_IN.exists() else HTML_OUT).read_text(encoding='utf-8')
    match,model_bytes=get_video('clipB',html)
    target=patched_frames()
    VIDEO_OUT.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ponzi-image2-') as td:
        model=Path(td)/'model.mp4';model.write_bytes(model_bytes)
        reencode(model,VIDEO_OUT,target)
    encoded=base64.b64encode(VIDEO_OUT.read_bytes()).decode('ascii')
    replacement=f'<script id="clipB" type="application/octet-stream">{encoded}</script>'
    html=html[:match.start()]+replacement+html[match.end():]
    html=html.replace('<title>Ponzi Minute 2 · Geometry review</title>','<title>Ponzi Minute 2 · Image 2 anime-trace review</title>',1)
    # Visible banner in the existing inspector identifies the exact limited edit.
    html=html.replace('<h1>Ponzi Minute 2 · Geometry review</h1>','<h1>Ponzi Minute 2 · Image 2 anime-trace review</h1>',1)
    HTML_OUT.write_text(html,encoding='utf-8')
    print(f'HTML: {HTML_OUT} ({HTML_OUT.stat().st_size:,} bytes)')
    print(f'Video: {VIDEO_OUT} ({VIDEO_OUT.stat().st_size:,} bytes)')
    print(f'Patched frames: {len(target)} ({min(PATCH_FRAMES)/FPS:.2f}s–{max(PATCH_FRAMES)/FPS:.2f}s); all other frame pixels came from the original embedded procedural render before final video encoding.')

if __name__=='__main__': main()
