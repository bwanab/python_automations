#!/usr/bin/env python3
#
'''
This script goes through all the directories of google photos, uses exif data to determine the camera
that took the picture and weeds out all the iphone, ipad and nikon d80 shots since they're saved elsewhere
and moves the rest to a new temporary folder for further processing.
'''

import os
from PIL import Image, ExifTags

path = "/Users/williamallen/Downloads/Takeout/Google Photos"

to_path = "/Users/williamallen/tmp_google_non_jpegs"

video_types = set(['3gp', 'mp4', 'mov'])

non_video_types = set(['gif', 'png'])

filenames = []
model_key = None
date_key_map = {}

for d in os.listdir(path):
    dirname = os.path.join(path, d)
    if os.path.isdir(dirname):
        filenames += [os.path.join(dirname, f) for f in os.listdir(dirname)
                      if f.lower().split('.')[-1] in non_video_types]

                      ## if f.lower().split('.')[-1] in video_types]
for f in filenames:
    to_filename = os.path.join(to_path, f.split('/')[-1])
    cmd = "cp '" + f + "' " + to_filename
    print(cmd)
    os.system(cmd)
