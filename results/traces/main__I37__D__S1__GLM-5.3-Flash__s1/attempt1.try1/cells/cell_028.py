import numpy as np, datetime as dt

sst = np.load('/work/sst_cube.npy')          # (4120, 61, 61) float64
times = np.load('/work/times.npy').astype('datetime64[D]')

CUM = [31,29,31,30,31,30,31,31,30,31,30,31]
def dayofyear(d):
    return sum(CUM[:d.month-1]) + d.day

dates = [dt.date(1991,12,27)+dt.timedelta(days=k) for k in range(4010)] \
      + [dt.date(2012,6,1)+dt.timedelta(days=k) for k in range(92)]
assert len(dates) == sst.shape[0]
assert all(times[k] == np.datetime64(dates[k]) for k in (0, 4009, 4010, 4119))

# sea cells
idx_t0, idx_t1 = 4010, 4101
sea = np.isfinite(sst[idx_t0:idx_t1+1]).all(axis=0)
print("sea cells:", int(sea.sum()))
np.save('/work/sea_mask.npy', sea)

# build pool index: for each doy d (1..366, d!=60), indices into sst[0:4010]
doys_all = np.array([dayofyear(d) for d in dates[:4010]])
yrs_all  = np.array([d.year for d in dates[:4010]])
in_base  = (yrs_all >= 1992) & (yrs_all <= 2002)
base_pos = np.where(in_base)[0]
base_doys = doys_all[in_base]
print("baseline positions:", len(base_pos), "doys min/max:", base_doys.min(), base_doys.max())

pool_idx = {}
for d in range(1, 367):
    if d == 60:
        continue
    # circular window on 366-day doy ring
    offs = np.arange(-5, 6)
    w = ((d - 1 + offs) % 366) + 1
    mask = np.isin(base_doys, w)
    pool_idx[d] = base_pos[mask]

counts = np.array([len(pool_idx[d]) for d in range(1, 367) if d != 60])
print("pool sizes: min", counts.min(), "max", counts.max(), "mean", counts.mean())
print("doy 1 pool size:", len(pool_idx[1]), "doy 366:", len(pool_idx[366]), "doy 153:", len(pool_idx[153]))
# no day-60 baseline dates should be in any pool
n60 = int((base_doys == 60).sum())
print("baseline Feb29 days:", n60, "-> appear in neighbours' pools (should be ~11):",
      sum(len(pool_idx[d]) for d in range(1,367) if d != 60), "entries vs expected",
      len(base_pos)*11)
np.save('/work/dummy.npy', np.array([0]))
