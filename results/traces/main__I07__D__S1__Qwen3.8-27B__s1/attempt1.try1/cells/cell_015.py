import numpy as np
from datetime import date, timedelta

S_base = np.load('/work/S_base.npy')
start0 = date(1991,12,27)
N = S_base.shape[0]

def doy_of(dt):
    return (date(2000, dt.month, dt.day) - date(2000,1,1)).days + 1

M = np.zeros((366, N), dtype=bool)
n_win = 0
d = date(1992,1,1)
while d <= date(2002,12,31):
    k = doy_of(d)
    if k != 60:  # day 60 gets no pool of its own
        idx = (d - start0).days
        i0 = max(0, idx-5); i1 = min(N, idx+6)
        M[k-1, i0:i1] = True
        n_win += 1
    d += timedelta(days=1)
print("windows added:", n_win, "(expect 4018-3 = 4015)")

pool_sizes = M.sum(axis=1)
neq60 = np.arange(366) != 59
print("day60 pool size:", pool_sizes[59], "(expect 0)")
print("d!=60 pool sizes all 121:", (pool_sizes[neq60] == 121).all())

# feb29 dates: in day59 & day61 pools only, NOT day60
for y in (1992,1996,2000):
    i = (date(y,2,29)-start0).days
    assert M[58, i] and M[60, i] and not M[59, i], y
print("feb29 membership ok (in 59 & 61 pools, not 60)")
# day60 pool contains nothing, but day 60 threshold later = mean(59,61)
np.save('/work/M.npy', M)
print("M saved")
