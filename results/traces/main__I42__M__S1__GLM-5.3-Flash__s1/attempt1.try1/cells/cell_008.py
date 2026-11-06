import numpy as np, h5py, json, time
from datetime import date, timedelta

base = "/data/icsa2027_data_20261101T090944Z/s1z"

# ---- region indices ----
with h5py.File(f"{base}/sst_19920601.nc", "r") as fh:
    lat = fh["latitude"][:]
    lon = fh["longitude"][:]
lat_idx = np.where((lat >= 62.25 - 1e-6) & (lat <= 63.45 + 1e-6))[0]
lon_idx = np.where((lon >= 18.73 - 1e-6) & (lon <= 19.93 + 1e-6))[0]
print("nlat", len(lat_idx), "nlon", len(lon_idx),
      "lat:", lat[lat_idx[0]], lat[lat_idx[-1]], "lon:", lon[lon_idx[0]], lon[lon_idx[-1]])

# ---- day-of-year mapping (month/day based, leap-year style 1..366) ----
MD_CUM = [0,31,59,61,92,122,153,183,213,244,275,274,306]
def doy_of(dt):
    m, dd = dt.month, dt.day
    return MD_CUM[m-1] + dd

# sanity checks
checks = {(1,1):1,(1,31):31,(2,28):59,(2,29):60,(3,1):61,(12,31):366,(6,15):152+15}
for (m,dd),exp in checks.items():
    got = doy_of(date(2000,m,dd))
    assert got==exp, (m,dd,got,exp)
print("doy mapping OK; 2012-06-01 ->", doy_of(date(2012,6,1)))

# ---- build per-doy sorted baseline date lists (d=1..366, skip 60) ----
all_base_dates = [baseline_start + timedelta(days=k) for k in range(0, 11*365 + 3)]
all_base_dates = [d for d in all_base_dates if baseline_start <= d <= baseline_end]
print("baseline dates:", all_base_dates[0], all_base_dates[-1], len(all_base_dates))
base_doy = np.array([doy_of(d) for d in all_base_dates])

win_dates = {}  # doy -> list of dates (sorted), excluding doy 60 pool
for d in range(1, 367):
    if d == 60: continue
    lo, hi = d-5, d+5
    if lo < 1: lo = 1
    if hi > 366: hi = 366
    mask = (base_doy >= lo) & (base_doy <= hi) & (base_doy != 60)
    win_dates[d] = [all_base_dates[k] for k in np.where(mask)[0]]
# checks
print("d=1 window:", win_dates[1][0], win_dates[1][-1], "n=", len(win_dates[1]))
print("d=55 window:", win_dates[55][0], win_dates[55][-1], "n=", len(win_dates[55]))
print("d=65 window:", win_dates[65][0], win_dates[65][-1], "n=", len(win_dates[65]))
print("d=366 window:", win_dates[366][0], win_dates[366][-1], "n=", len(win_dates[366]))
print("d=180 window:", win_dates[180][0], win_dates[180][-1], "n=", len(win_dates[180]))
import pickle
with open("/work/window_dates.pkl", "wb") as f:
    pickle.dump({"lat_idx": lat_idx, "lon_idx": lon_idx, "win_dates": win_dates}, f)
print("saved")
