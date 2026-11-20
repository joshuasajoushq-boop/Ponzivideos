# Minute 3 procedural rebuild

This directory contains the Minute 3 20-pass procedural review driver, its compact results, frame metrics, and a source-only package with the renderer dependencies. The source package excludes reference and rendered videos.

## Results

The review completed 20 full-minute passes and 4,000 scene/category checks, accepting 56 editable transform changes. The gate did not certify 99% visual accuracy: 13 of 20 scenes remain composite-only, and the current metrics do not establish semantic equivalence to the photographic reference. See `ponzi_minute3_report_summary.json` for the audit and remaining limits.

## Run

Requires Python 3, OpenCV, NumPy, and FFmpeg. Extract `ponzi_minute3_procedural_source.zip` and place the Minute 3 source reference at the path expected by `ponzi_v8.py`; then run:

```bash
python ponzi_minute3_self_eval.py
```

The driver performs at least 20 complete passes. It writes its report, configuration, and render beside itself. Reference and rendered video deliverables are kept in ChatGPT Library, not Git history.
