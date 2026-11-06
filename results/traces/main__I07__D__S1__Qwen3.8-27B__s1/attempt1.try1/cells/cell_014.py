import numpy as np
from datetime import date, timedelta

S_base = np.load('/work/S_base.npy')
start0 = date(1991,12,27)
N = S_base.shape[0]
assert N == (date(2003,1,5) - start0).days + 1

def doy_of(dt):
    return (date(2000, dt.month, dt.day) - date(2000,1,1)).days + 1

# fixed (month,day) -> doy table: leap-year ordinal mapping
assert doy_of(date(2001,1,1))==1
assert doy_of(date(2001,2,28))==59 and doy_of(date(2000,2,29))==60
assert doy_of(date(2021,3,1))==61 and doy_of(date(2021,12,31))==366
assert doy_of(date(2021,6,1))==153, doy_of(date(2021,6,1))
assert doy_of(date(2021,8,31))==244, doy_of(date(2021,8,31))

M = np.zeros((366, N), dtype=bool)
ndays_per_doy = np.zeros(367, dtype=int)
d = date(1992,1,1)
while d <= date(2002,12,31):
    idx = (d - start0).days
    k = doy_of(d)
    ndays_per_doy[k] += 1
    i0 = max(0, idx-5); i1 = min(N, idx+6)
    M[k-1, i0:i1] = True
    d += timedelta(days=1)

pool_sizes = M.sum(axis=1)
print("baseline days counted:", ndays_per_doy.sum(), "(expect 4018)")
print("doy60 occurrences in baseline:", ndays_per_doy[60], "(expect 2: 1996, 2000)")
neq60 = np.arange(366) != 59
print("pool size min/max (d!=60):", pool_sizes[neq60].min(), pool_sizes[neq60].max())
print("d!=60 with pool != 121:", (pool_sizes[neq60] != 121).sum())
w = np.where(M[0])[0]
print("doy1 pool:", date.fromordinal(start0.toordinal()+w.min()), "to", date.fromordinal(start0.toordinal()+w.max()))
w = np.where(M[365])[0]
print("doy366 pool:", date.fromordinal(start0.toordinal()+w.min()), "to", date.fromordinal(start0.toordinal()+w.max()))
i_feb29_96 = (date(1996,2,29)-start0).days
i_feb29_00 = (date(2000,2,29)-start0).days
print("feb29-1996 in pools: doy59:", M[58,i_feb29_96], "doy60:", M[59,i_feb29_96], "doy61:", M[60,i_feb29_96])
print("feb29-2000 in pools: doy59:", M[58,i_feb29_00], "doy60:", M[59,i_feb29_00], "doy61:", M[60,i_feb29_00])
# also confirm no baseline date with doy 60 contributed anywhere else
print("doy60 pool size (should be 0):", pool_sizes[59])
np.save('/work/M.npy', M)
np.save('/work/doy_of.npy', np.array([doy_of(date(2000,1,1)+timedelta(days=k)) for k in range(366)]))
print("saved M", M.shape)
