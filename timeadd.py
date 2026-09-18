#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 23 11:47:48 2021

@author: williamallen
"""

from datetime import timedelta

'''
usage:
    
    t = timeadd.init()
    t += timeadd.add(t, 1, 30)
    timeadd.display(t)
    
    (1, 30)
    
    t += timeadd.add(t, 0, -15)
    timeadd.display(t)
    
    (1, 15)
    
    t += timeadd.add(t, 1, 45)
    timeadd.display(t)
    (3, 0)
'''

def init():
    return timedelta() 
    
def add(t, m, s):
    t += timedelta(seconds=m*60 + s)
    return t

def display(t):
    m = t.seconds // 60
    s = t.seconds - m * 60
    return m,s

    
