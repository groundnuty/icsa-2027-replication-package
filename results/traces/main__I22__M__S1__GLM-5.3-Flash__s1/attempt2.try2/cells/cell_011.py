import datetime as dt
def doy_shift(k):
    if k <= 59: return k + 1
    if k == 60: return 0   # Feb 29 marker
    return k
# test:
for k, exp in [(1,2),(59,60),(60,0),(61,1),(91,31),(183,123),(365,305),(366,306)]:
    assert doy_shift(k) == exp, (k, doy_shift(k), exp)
print('doy_shift ok')
# Now build pool membership per day-of-year (366 slots of the mapping)
pool_of = [[] for _ in range(366)]  # pool_of[k] = list of shifted-doys that map to slot k (k=0..365)
for kk in range(1, 367):
    pool_of[doy_shift(kk) - 1].append(kk)  # shifted doy s=1..366 -> index s-1
for idx in range(366):
    pool_of[idx] = np_ok = [k for k in pool_of[idx]]
print('slots with multiple members:', [(i+1, pool_of[i]) for i in range(366) if len(pool_of[i]) > 1][:10])
print('slot 59 (day 60):', pool_of[59])
print('slot 0:', pool_of[0], 'slot 305:', pool_of[305])
