# Ponzi motion and asset guide

Use [motion-index.json](motion-index.json) to find effects, source functions, shot windows,
asset descriptions and reusable geometry. The measurements describe the procedural
renderers, with source comparisons kept in the pass reports. They are starting points
for another video. Match the new video's framing and subject landmarks.

## Coordinates and timing

- Use a top-left origin. X increases right, Y increases down. Divide X and width by
  frame width, and Y and height by frame height. Multiply by the destination dimension
  when applying an effect to another canvas. Keep cutout aspect ratio and crop separately.
- Timeline positions use minute-relative seconds unless identified otherwise. Add 60 seconds
  for Minute 2's full-video time. At 25 fps, six frames are 0.24 seconds.
- An asset's page origin, visible alpha bounds, and a camera pivot are different
  measurements. Keep the page origin when swapping an existing cutout. To preserve framing,
  align visible landmarks first, then match the frame-relative visible width and height.
- Scale is a multiplier. Rotation values in the money renderer are degrees.
  Pyramid camera coordinates are scene units rather than normalized screen positions.

## Change a shot

**Minute 1.** The V33 renderer's `DEFAULTS` and `BOUNDS` describe controls such as
camera zoom, title size, reveal delay and pyramid speed. Pass overrides with `--params`.
Use `--timing style/minute1-timing-example.json` to remap the local animation clock inside
a named shot. Keys are [playback local seconds, source animation local seconds].
The first and last keys pin the outer boundaries. Adjacent shots keep their original clocks.
The timing map retimes the whole procedural composition within that shot. Adjust the individual
effect parameter when the rest of the composition should retain its timing.

```sh
python engine/latest_v33/v33_renderer.py --base /path/to/ponzi_v32_PROCEDURAL_FINAL.mp4 \
  --output /tmp/ponzi-pyramid-test.mp4 --start-frame 1425 --end-frame 1500 \
  --timing style/minute1-timing-example.json
```

The end frame is exclusive. The range above includes the lead-in to the pyramid shot.
Use `--still 57.68` and a PNG output for a still. V33 includes the Python code for V32/V30,
but requires the separate V32 video input. See the root README for full-minute setup.

**Minute 2 money.** Pass `--controls style/minute2-money-controls-example.json` to
`minute2/money_geometry/redraw/fix_money_sequence_five_pass.py`.
A supplied key wins over automatic pass adjustments. Inspect `config_for_pass` for the full
set of keys. To inspect without replacing the full review, use
`--still-frame 617 --still-output /tmp/money.png`. The still uses first-pass defaults
plus overrides. For the final pass's measured title boxes, consult the report and pass those
boxes explicitly. See the shot README for full-render inputs.

**Minute 2 college.** Copy the shot's `controls.json` and pass it with `--controls`.
Pass 2 supplies the final render. Move `reveal` and `finish` together to change its timing;
change their difference to adjust duration. Set `equations_enabled` to false to isolate the
background and cutouts. `--still-frame 911` writes one PNG without re-exporting the minute.
Use the shot README to recover exact media inputs and run the renderer.

## Create or swap a cutout

Draw new vector artwork with TraceFrame or build SVG paths with Python. Use stable group IDs
for actual independently composited parts, and include an SVG `title` and `desc` stating
who or what is shown, pose, crop, foreground props and provenance. Preserve clean transparency.
Keep source footage, text, background and glow out of the foreground silhouette. Record
the asset page size, visible bounds, anchor landmarks, layer order and shot IDs in the index.

- Money: supply `--cutout /path/to/portrait.svg`. Keep the SVG viewBox and
  top-level group order aligned with the original. The renderer rasterizes the groups
  independently with Inkscape, then places them with a shared transform.
- College: use `--woman-cutout /path/to/portrait.png`. For an SVG authored in TraceFrame,
  export a 640×360 RGBA PNG and align its eye, hairline and shoulder to the supplied
  `Woman_Transparent.png` before rendering. Replacement PNGs skip the built-in edge cleanup.
- Minute 1: the tracked V33 shapes are Python-generated or inherited from the V32 plate.
  Use the generator named in the index for artwork edits. A change to an inherited
  flattened shot requires its source renderer or a new isolated layer.

## Verify the edit

Save a new output. Compare several frames before, during and after the effect, then play
the surrounding seconds at native speed. Check title readability, subject scale, silhouette edge,
occlusion order and both neighboring cuts. Keep the default config available for a direct A/B.
For asset swaps, preview the isolated alpha over a light and a dark background before rendering.
The index covers explicit tracked recipes in the checked-in code. Inherited plate-only imagery
does not provide editable source layers, and there is no complete per-frame source landmark dataset.
