import numpy as np, datetime as dt

sst = np.load('/work/sst_cube.npy')
times = np.load('/work/times.npy').astype('datetime64[D]')
NB = 4027  # baseline window 1991-12-27..2003-01-05

CUM = [31,29,31,30,31,30,31,31,30,31,30,31]
def dayofyear(d):
    return sum(CUM[:d.month-1]) + d.day

# sea cells
i0, i1 = 4028, 4119
sea = np.isfinite(sst[i0:i1+1]).all(axis=0)
print("sea cells:", int(sea.sum()))
np.save('/work/sea_mask.npy', sea)

# pool index per doy
doys_all = np.array([dayofyear(dt.date(1991,12,27)+dt.timedelta(days=k)) for k in range(NB)])
yrs_all  = np.array([(dt.date(1991,12,27)+dt.timedelta(days=k)).year for k in range(NB)])
in_base = (yrs_all >= 1992) & (yrs_all <= 2002)
base_pos = np.where(in_base)[0]
base_doys = doys_all[in_base]
print("baseline days:", len(base_pos), "expect 4018")

pool_idx = {}
for d in range(1, 367):
    if d == 60:
        continue
    offs = np.arange(-5, 6)
    w = ((d - 1 + offs) % 366) + 1
    pool_idx[d] = base_pos[np.isin(base_doys, w)]

counts = np.array([len(v) for v in pool_idx.values()])
print("pool sizes: min", counts.min(), "max", counts.max(), "mean", round(counts.mean(),1))
print("doy1:", len(pool_idx[1]), "doy153:", len(pool_idx[153]), "doy366:", len(pool_idx[366]), "doy59:", len(pool_idx[59]), "doy61:", len(pool_idx[61]))
# verify 29 Feb entries included in d=55 and d=65 pools
feb29_pos = base_pos[base_doys == 60]
print("Feb29 baseline days:", len(feb29_pos))
print("55-pool contains Feb29:", bool(np.isin(feb29_pos, pool_idx[55]).all()))
print("65-pool contains Feb29:", bool(np.isin(feb29_pos, pool_idx[65]).all()))
print("60 in any pool? ", any((base_doys[np.isin(base_pos, pool_idx[d])] == 60).any() for d in pool_idx))
