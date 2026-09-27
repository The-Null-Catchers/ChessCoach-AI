from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANDROID = ROOT / "android"
MANIFEST = ANDROID / "app" / "src" / "main" / "AndroidManifest.xml"

if not MANIFEST.exists():
    raise SystemExit("Android project not found. Run flutter create first.")

text = MANIFEST.read_text(encoding="utf-8")
if re.search(r'android:label="[^"]*"', text):
    text = re.sub(
        r'android:label="[^"]*"',
        'android:label="ChessCoach AI"',
        text,
        count=1,
    )
else:
    text = text.replace(
        "<application",
        '<application android:label="ChessCoach AI"',
        1,
    )
MANIFEST.write_text(text, encoding="utf-8")

densities = ["mdpi", "hdpi", "xhdpi", "xxhdpi", "xxxhdpi"]
for density in densities:
    source = ROOT / "branding" / f"mipmap-{density}" / "ic_launcher.png"
    target_dir = ANDROID / "app" / "src" / "main" / "res" / f"mipmap-{density}"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "ic_launcher.png"
    if not source.exists():
        raise SystemExit(f"Missing launcher icon: {source}")
    shutil.copyfile(source, target)

print("Applied ChessCoach AI Android name and launcher icons.")
