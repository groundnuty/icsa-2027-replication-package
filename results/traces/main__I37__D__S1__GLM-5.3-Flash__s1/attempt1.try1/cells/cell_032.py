import numpy as np, datetime as dt

sst = np.load('/work/sst_cube.npy')
times = np.load('/work/times.npy').astype('datetime64[D]')
NB = 4027
sea = np.load('/work/sea_mask.npy')

CUM = [31,29,31,30,31,30,31,31,30,31,30,31]
def dayofyear(d):
    return sum(CUM[:d.month-1]) + d.day

doys_all = np.array([dayofyear(dt.date(1991,12,27)+dt.timedelta(days=k)) for k in range(NB)])
yrs_all  = np.array([(dt.date(1991,12,27)+dt.timedelta(days=k)).year for k in range(NB)])
base_pos = np.where((yrs_all >= 1992) & (yrs_all <= 2002))[0]
base_doys = doys_all[base_pos]
n60 = int((base_doys == 60).sum())
print("Feb29 baseline days:", n60)

pool_idx = {}
for d in range(1, 367):
    if d == 60:
        continue
    w = (((d - 1 + np.arange(-5, 6)) % 366) + 1)
    pool_idx[d] = base_pos[np.isin(base_doys, w)]

# --- correct check: are Feb29 *positions* included in pools of d=55..65 ---
feb29_pos = base_pos[base_doys == 60]
for d in [55, 56, 57, 58, 59, 61, 62, 63, 64, 65]:
    print(f"doy {d}: contains Feb29 pos -> {bool(np.isin(feb29_pos, pool_idx[d]).any())}, size {len(pool_idx[d])}")
# and confirm none of the pools is doy-60-labelled (d=60 never queried; check d=59 pool excludes Mar1 etc.)
for d in [59, 61]:
    wd = sorted(set(base_doys[np.isin(base_pos, pool_idx[d])]))
    print(f"doy {d} pool doys: {wd}")
