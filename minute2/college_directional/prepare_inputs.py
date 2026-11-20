"""Recover the exact renderer inputs from two downloaded project artifacts."""
import argparse
import base64
import hashlib
from pathlib import Path
import re
import zipfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("second_punch_review", type=Path)
parser.add_argument("right_reveal_zip", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()

html = args.second_punch_review.read_text(encoding="utf-8")
clips = dict(re.findall(r'<script id="(clip[AB])"[^>]*>(.*?)</script>', html, re.S))
with zipfile.ZipFile(args.right_reveal_zip) as archive:
    preserve = archive.read("Ponzi_Minute2_College_Reveal.mp4")

inputs = {
    "reference.mp4": (base64.b64decode(clips["clipA"]), "e2352ed190aba1073944fba8e342429c2b167bae33df95013edc7056c83b353e"),
    "second_punch.mp4": (base64.b64decode(clips["clipB"]), "9159da788a5e32175c38bbe399df19280636a1658081b06916b9d4da7d94f5ac"),
    "preserve.mp4": (preserve, "2e35ce3218dad27609cbd1bfb957dd2db955ac793c0845b4e667d6b957eca945"),
}
for name, (data, expected) in inputs.items():
    if hashlib.sha256(data).hexdigest() != expected:
        raise SystemExit(f"Incorrect input version for {name}")
args.output.mkdir(parents=True, exist_ok=True)
for name, (data, _) in inputs.items():
    (args.output / name).write_bytes(data)
