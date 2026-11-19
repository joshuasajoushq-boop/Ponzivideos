# Ponzi Minute 2 money and title geometry fix

This folder contains the reproducible correction pass for the frame shown at
24.68 seconds, plus the measured report from three full-minute cycles. Each
cycle rebuilds frames 23.44–28.36 seconds and checks five criteria: question
mark geometry, born/rich text spacing, the marked background bill's position,
bill curvature, and bill trajectory continuity.

## Inputs needed to rerun

The original repository did not contain the Minute 2 source media. The exact
reference and renderer inputs were recovered from the Library source package.
Place these files in this folder before running the renderer:

- `minute2_reference.mp4`
- `Ponzi_Minute2_Retraced_Complete.html`
- `Ponzi_Minute2_Particles_FullMinute.mp4`
- `upload/Ponzi_Anime_Closeup.svg`

The Python helpers and their `image2_motion.json` config are included beside
the correction script under `redraw/`.

## Run

From `redraw/`, run:

```sh
python fix_money_sequence_five_pass.py
```

The script performs three successive 60-second exports. Each pass carries
successful settings forward and applies the prior pass's unresolved checks to
the next pass. It writes the standalone review HTML, repaired MP4, contact
sheet, and JSON report into the parent folder.

The final report records 15 local geometry/continuity checks across the three
cycles. All five criteria passed in cycles 2 and 3. These measurements are
specific to this shot and do not claim overall frame or semantic accuracy.
