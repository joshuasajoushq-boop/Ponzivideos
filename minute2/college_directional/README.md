# Minute 2 college reveal

This two-pass revision covers the college transition at 34.32–38.44 seconds
at 25 fps. The renderer uses a directional matte, separate equation depths,
and a refined alpha boundary for the woman's hair. It preserves the Ponzi
cover timing from the preceding revision. A faint edge remains at the shoulder.

- [Latest frame review](https://chatgpt.com/library?file_id=libfile_e51f85e341488191a0d0aa760c91c632&account_id=personal)
- [Latest render bundle](https://chatgpt.com/library?file_id=libfile_8b96a37b4f848191b704ed9e7734cf67&account_id=personal)

## Rerender

Use Python with NumPy and Pillow, FFmpeg on PATH, and the DejaVu Serif font
at the path specified in the renderer. Download the two exact input artifacts:

1. [Second punch review HTML](https://chatgpt.com/library?file_id=libfile_10a5f090003081918112365054487026&account_id=personal), which embeds the reference and clean procedural input.
2. [Previous right reveal ZIP](https://chatgpt.com/library?file_id=libfile_1d3e7f9306e48191ad2ed680ae27f302&account_id=personal), which provides the full-minute render outside the edited window.

From this directory, run:

```sh
python prepare_inputs.py /path/to/second-punch.html /path/to/right-reveal.zip inputs
python ponzi_college_reveal.py inputs/second_punch.mp4 inputs/reference.mp4 out --preserve inputs/preserve.mp4
```

The input preparation script checks all three SHA-256 digests. The renderer
produces the full MP4, standalone review, preview GIF, stills, pass report,
and transparent cutout. The committed PNG is the exported cutout for reuse.
The renderer derives its matte from the procedural input.
