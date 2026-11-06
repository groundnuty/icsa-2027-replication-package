import numpy as np, datetime as dt
data = np.load('/work/S.npz', allow_pickle=True)
S_base = data['S_base']; S_tgt = data['S_tgt']
dates = [dt.date.fromisoformat(s) for s in data['dates']]
n_base = 4028
base_dates = dates[:n_base]
d0 = base_dates[0]

def doy(d):
    return (d.replace(year=2020) - dt.date(2020,1,1)).days + 1

bl_start = (dt.date(1992,1,1) - d0).days
bl_end   = (dt.date(2002,12,31) - d0).days
baseline_pos = np.arange(bl_start, bl_end+1)
bl_doy = np.array([doy(base_dates[p]) for p in baseline_pos])

pools = {}
for d in range(1, 367):
    if d == 60: continue
    pos = baseline_pos[bl_doy == d]
    sets = [np.arange(max(p-5,0), min(p+5, n_base-1)+1) for p in pos]
    tset = np.unique(np.concatenate(sets))
    pools[d] = tset

sizes = sorted({len(p) for d,p in pools.items()})
print("pool size set:", sizes)
for d in (1, 31, 59, 61, 153, 244, 365, 366):
    tset = pools[d]
    ds_ = [base_dates[i].isoformat() for i in tset]
    print(d, "size:", len(tset), "first:", ds_[0], "last:", ds_[-1])
# verify pool d=1 boundaries: should span 1991-12-27..2002-01-06 in 11 blocks
t1 = pools[1]
print("d=1 blocks:", [(base_dates[t1[0]].isoformat(), base_dates[t1[-1]].isoformat())])
np.save('/work/pools.npy', pools, allow_pickle=True)
