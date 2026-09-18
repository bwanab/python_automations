#!/usr/bin/env python3

from pathlib import Path
import os
from PIL import Image, ExifTags

home_dir = Path.home()
path = home_dir / "Downloads" / "Takeout" / "Google Photos"

dont_use_cameras = set(['iPhone 6', 'iPad 2', 'NIKON D80'])
cameras_found = set()
filenames = []

for d in os.listdir(path):
    dirname = os.path.join(path, d)
    if os.path.isdir(dirname):
        filenames += [os.path.join(dirname, f) for f in os.listdir(dirname) if f.lower().endswith('.jpg')]
for f in filenames:
    print(f)
