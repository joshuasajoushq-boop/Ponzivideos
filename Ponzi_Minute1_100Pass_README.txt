Ponzi minute 1 — 100-pass procedural correction handoff

Deliverables
- Ponzi_Minute1_100Pass_Corrected.mp4: updated 60-second, 1280x720, 25 fps render.
- Ponzi_Minute1_100Pass.py: repeatable fixed-100-pass full-minute analysis/correction loop.
- Ponzi_Minute1_100Pass_Report.json: per-pass counts and diagnostics; explicitly does not certify semantic accuracy.
- Ponzi_Minute1_Vector_Trace.html: local browser tool for synced video compare and vector annotations.
- Ponzi_Minute1_Trace_Annotations.json: starter object/issue map; trace vectors can be exported from the HTML.

The pass loop walks all 1,500 frames and reviews all ten named scene correction sets on each of 100 passes (1,500,000 frame/set reviews). It renders/encodes once after the iterations to avoid degrading the result with repeated lossy encodes. Image statistics are only technical diagnostics; no 99% visual-accuracy claim is made.

Corrections made in this render
- Centered and fit the scheme and storm title text inside the safe frame.
- Reversed the money-carrying foreground character to enter from screen-right and travel leftward.
- Added storm-cloud texture and distant pyramid silhouettes behind the seated figure.
- Corrected chapter label from CHAPTER II to CHAPTER I.

Open issues
- Photographic likeness, watch/clock image, hands, currency texture, precise cloud detail, and source-specific scene backgrounds remain materially different because matching cutouts and registered masks are absent.
- Exact chair/person identity continuity and source-frame geometric accuracy still require traced masks/landmarks and re-render review. The HTML tool can capture those traces; the current JSON is a starter template, not completed tracing.
- No Metascore-style rating was used.

Rebuild source archive includes the reference video, procedural base MP4, and renderer dependencies. Requires Python 3, OpenCV, NumPy, Pillow, and FFmpeg.
