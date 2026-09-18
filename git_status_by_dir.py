#!/usr/bin/env python3
#
'''
This script goes through all the directories in src and executes 'git status' to determine whether
there are files that need to be saved.
'''

import os

path = "/Users/williamallen/src/"

for d in os.listdir(path):
    dirname = os.path.join(path, d)
    if os.path.isdir(dirname):
        print("------------ ", dirname, " -----------------")
        os.chdir(dirname)
        os.system('git status')
