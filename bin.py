#!/usr/bin/env python3

import math

def chose(n, x):
    return math.factorial(n) / (math.factorial(x) * math.factorial(n - x))

def bin(n, p, x):
    return chose(n, x) * p ** x * (1 - p) ** (n - x)

#chose(3, 0)

answer = 0
for x in range(3):
    answer += bin(3, 0.2, x)
print(answer)
