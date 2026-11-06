
import numpy as np, datetime as dt, time

# ---- load ----
B = np.concatenate([np.load(f'/tmp/mhw/baseline_part{i}.npy') for i in range(9)], axis=0)
A = np.load('/tmp/mhw/target.npy').squeeze(axis=1)
lat = np.load('/tmp/mhw/lat.npy'); lon = np.load('/tmp/mhw/lon.npy')
print("B:", B.shape, B.dtype, "A:", A.shape, A.dtype)

bdates = [dt.date(1991,12,27) + dt.timedelta(days=i) for i in range(B.shape[0])]
tdates = [dt.date(2008,6,1) + dt.timedelta(days=i) for i in range(A.shape[0])]
print("baseline span:", bdates[0], bdates[-1], " target span:", tdates[0], tdates[-1])

# ---- doy mapping (leap-year calendar by month-day) ----
cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def doy_of(ds):  # np array of dt.date
    return cum[np.array([d.month for d in ds])-1] + np.array([d.day for d in ds])
bdoy = doy_of(bdates)
print("bdoy sample:", list(zip(bdates[:3], bdoy[:3])), list(zip(bdates[5:8], bdoy[5:8])), bdoy.min(), bdoy.max())

# ---- sea cells ----
sea = np.all(np.isfinite(A), axis=0)
print("sea cells:", sea.sum())

# ---- baseline date indices (1992-01-01 .. 2002-12-31) ----
base_idx = np.array([i for i,d in enumerate(bdates) if dt.date(1992,1,1) <= d <= dt.date(2002,12,31)])
print("base_idx:", base_idx.min(), base_idx.max(), len(base_idx))
# check they are contiguous 5..4017
assert base_idx.min()==5 and base_idx.max()==4017 and len(base_idx)==4013
