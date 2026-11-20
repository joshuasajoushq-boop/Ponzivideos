# Ponzi video project

## Minute 2

- [College directional reveal](minute2/college_directional/README.md) — latest college transition revision, renderer, and exact input recovery instructions.
- [Money and title geometry](minute2/money_geometry/README.md) — renderer and report for the money sequence.

## Minute 1

Editable source and review tools for the latest Minute 1 procedural render.

### Included

- `Ponzi_Minute1_100Pass.py`: the 100-round whole-minute review and render driver.
- `engine/latest_v33/`: V33 renderer and its V32/V30 Python dependencies.
- `Ponzi_Minute1_Vector_Trace.html`: local frame comparison and vector annotation tool.
- `Ponzi_Minute1_Trace_Annotations.json`: starter map for scene objects and known issues.
- `Ponzi_Minute1_100Pass_Report.json`: diagnostics and limits of the 100-pass review.
- `Ponzi_Minute1_100Pass_README.txt`: original handoff notes.

### Run

Requires Python 3, OpenCV, NumPy, Pillow, and FFmpeg.

The video inputs and rendered MP4 are kept in ChatGPT Library rather than Git history. To render, obtain the Minute 1 source package from Library and place its media files at the paths expected by the driver:

- `reference.mp4` beside `Ponzi_Minute1_100Pass.py`
- `ponzi_v32_PROCEDURAL_FINAL.mp4` in `engine/latest_v33/`

Then run:

```bash
python Ponzi_Minute1_100Pass.py --passes 100
```

Open `Ponzi_Minute1_Vector_Trace.html` in a browser and load the reference and rendered videos to inspect frames and export annotations.

The report explicitly does not claim 99% semantic accuracy. Photographic likeness and exact object geometry still need traced masks and review.
