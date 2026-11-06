def doy_shift(k):
    if k <= 59: return k + 1
    if k == 60: return 0   # Feb 29
    return k - 60
for k, exp in [(1,2),(59,60),(60,0),(61,1),(62,2),(183,123),(365,305),(366,306),(91,31)]:
    got = doy_shift(k)
    assert got == exp, (k, got, exp)
print('doy_shift ok')
pool_of = [[] for _ in range(366)]
for kk in range(1, 367):
    pool_of[doy_shift(kk) - 1].append(kk)
mult = [(i+1, pool_of[i]) for i in range(366) if len(pool_of[i]) > 1]
print('slots with multiple members:', mult)
print('slot 60 (day 60):', pool_of[59])
print('slot 1:', pool_of[0], 'slot 306:', pool_of[305], 'slot 365:', pool_of[364])
# Windows: for slot s (1..366), pool = dates with cal-doy k in union over pool_of[s-1] of k+-5
D = dt.date(1992,1,1)
BASE_END = dt.date(2002,12,31)
doy_of = {}
d = D
while d <= dt.date(2003,12,31):
    doy_of[d] = doy_cal(d) if False else None
    d += dt.timedelta(days=1)
