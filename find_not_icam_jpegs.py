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

to_path = "/Users/williamallen/tmp_google_photos"

dont_use_cameras = set(['iPhone 6', 'iPad 2', 'NIKON D80'])
cameras_found = set()
filenames = []
file_exif_map = {}
model_key = None
date_key_map = {}

for d in os.listdir(path):
    dirname = os.path.join(path, d)
    if os.path.isdir(dirname):
        filenames += [os.path.join(dirname, f) for f in os.listdir(dirname) if f.lower().endswith('.jpg')]
    for f in filenames:
        if "edited" not in f:
            filename = os.path.join(dirname, f)
            img = Image.open(filename)
            img_exif = img.getexif()
            if img_exif:
                img_exif_dict = dict(img_exif)
                file_exif_map[f] = img_exif_dict
                model_key = None
                for key in img_exif_dict.keys():
                    if ExifTags.TAGS[key] == 'Model':
                        model_key = key
                    elif "date" in ExifTags.TAGS[key].lower():
                        date_key_map[key] = ExifTags.TAGS[key]

for f,img_exif_dict in file_exif_map.items():
    camera = img_exif_dict.get(model_key)
    if camera not in dont_use_cameras:
        cameras_found.add(camera)
        to_filename = os.path.join(to_path, f.split('/')[-1])
        cmd = "cp '" + f + "' " + to_filename
        print(cmd)
        os.system(cmd)
print(cameras_found)
