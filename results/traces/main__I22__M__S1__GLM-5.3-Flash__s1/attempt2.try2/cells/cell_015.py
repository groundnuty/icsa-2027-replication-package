import numpy as np
def doy_shift(k):
    # map calendar day-of-year k (1..365 non-leap, 1..366 leap) to 1..366 numbering (Feb29=60)
    if k <= 59: return k + 1
    if k == 60: return 0   # Feb 29
    return k
for k, exp in [(1,2),(59,60),(60,0),(61,61),(62,62),(120,120),(365,365),(366,366)]:
    got = doy_shift(k)
    assert got == exp, (k, got, exp)
print('doy_shift ok')
pool_of = [[] for _ in range(366)]
for kk in range(1, 367):
    s = doy_shift(kk)
    if s: pool_of[s-1].append(kk)
mult = [(i+1, pool_of[i]) for i in range(366) if len(pool_of[i]) > 1]
print('slots with multiple members:', mult)
print('slot 60:', pool_of[59])
print('slot 1:', pool_of[0], 'slot 2:', pool_of[1], 'slot 61:', pool_of[60], 'slot 365:', pool_of[364], 'slot 366:', pool_of[365])
