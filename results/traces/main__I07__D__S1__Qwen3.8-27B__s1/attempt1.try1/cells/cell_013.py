import numpy as np
from datetime import date, timedelta

S_base = np.load('/work/S_base.npy')   # (4028, 60, 60) from 1991-12-27
S_tgt  = np.load('/work/S_tgt.npy')    # (92, 60, 60) 2021-06-01..08-31

start0 = date(1991,12,27)
N = S_base.shape[0]
assert N == (date(2003,1,5) - start0).days + 1

def doy_of(dt):
    # map by (month, day) on a fixed (leap) calendar: 2000
    return (date(2000, dt.month, dt.day) - date(2000,1,1)).days + 1

# sanity of mapping
assert doy_of(date(2000,1,1))==1 and doy_of(date(2000,2,28))==59 and doy_of(date(2000,2,29))==60
assert doy_of(date(2021,3,1))==61 and doy_of(date(2021,12,31))==366
assert doy_of(date(2021,6,1))==152 and doy_of(date(2021,8,31))==243

# pool membership matrix M: (366, N)
M = np.zeros((366, N), dtype=bool)
d = date(1992,1,1)
end = date(2002,12,31)
ndays_per_doy = np.zeros(367, dtype=int)
while d <= end:
    idx = (d - start0).days
    k = doy_of(d)
    ndays_per_doy[k] += 1
    i0 = max(0, idx-5); i1 = min(N, idx+6)
    M[k-1, i0:i1] = True
    d += timedelta(days=1)

pool_sizes = M.sum(axis=1)
print("baseline days counted:", ndays_per_doy.sum(), "(expect 4018)")
print("distinct DOYs present:", (ndays_per_doy[1:367]>0).sum(), "(expect 365, doy60 twice? )")
print("doy60 count (skipped in M):", ndays_per_doy[60])
print("pool size min/max (d!=60):", pool_sizes[np.arange(366)!=59].min(), pool_sizes[np.arange(366)!=59].max())
print("any d!=60 with pool size != 121:", (pool_sizes[np.arange(366)!=59] != 121).sum())

# check pool endpoints for doy 1 and 366
print("doy1 pool dates:", start0, "+", np.where(M[0])[0].min(), "->", np.where(M[0])[0].max())
print("  i.e.", date.fromordinal(start0.toordinal()+np.where(M[0])[0].min()), "to", date.fromordinal(start0.toordinal()+np.where(M[0])[0].max()))
w = np.where(M[365])[0]
print("doy366 pool:", date.fromordinal(start0.toordinal()+w.min()), "to", date.fromordinal(start0.toordinal()+w.max()))
# doy 59 pool in 1996 should include Feb 29 1996
i_feb29_96 = (date(1996,2,29)-start0).days
print("feb29-1996 in doy59 pool:", M[58, i_feb29_96], " in doy61 pool:", M[60, i_feb29_96], " in doy60 pool:", M[59, i_feb29_96])
np.save('/work/M.npy', M)
