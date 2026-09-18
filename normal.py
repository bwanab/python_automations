#!/usr/bin/env python3

import math

def normal_pdf(mu, var, x):
    return (1.0 / math.sqrt(2 * math.pi * var)) * math.exp((-1.0 / (2 * var)) * (x - mu) ** 2 )


print (normal_pdf(2, 1, -5))
