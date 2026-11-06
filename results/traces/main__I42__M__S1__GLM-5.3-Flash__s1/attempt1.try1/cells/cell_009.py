import numpy as np, h5py, pickle
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

# ---- day-of-year mapping (month/day based, 1..366, leap-year style) ----
MD_CUM = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_of(dt):
    return MD_CUM[dt.month-1] + dt.day

checks = {(1,1):1,(1,31):31,(2,28):59,(2,29):60,(3,1):61,(3,31):92,(6,1):153,
          (12,31):366,(6,15):167,(2,1):32}
for (m,dd),exp in checks.items():
    got = doy_of(date(2000,m,dd))
    assert got==exp, (m,dd,got,exp)
print("doy mapping OK; e.g. 2012-06-01 ->", doy_of(date(2012,6,1)))

# ---- build per-doy sorted baseline date lists (d=1..366, skip 60) ----
baseline_start, baseline_end = date(1992,1,1), date(2002,12,31)
all_base_dates = []
d = baseline_start
while d <= baseline_end:
    all_base_dates.append(d); d += timedelta(days=1)
print("baseline dates:", all_base_dates[0], all_base_dates[-1], len(all_base_dates))
base_doy = np.array([doy_of(d) for d in all_base_dates])

win_dates = {}
for d in range(1, 367):
    if d == 60: continue
    lo, hi = max(1, d-5), min(366, d+5)
    mask = (base_doy >= lo) & (base_doy <= hi) & (base_doy != 60)
    win_dates[d] = [all_base_dates[k] for k in np.where(mask)[0]]
print("d=1  window:", win_dates[1][0], win_dates[1][-1], "n=", len(win_dates[1]))
print("d=55 window:", win_dates[55][0], win_dates[55][-1], "n=", len(win_dates[55]))
print("d=65 window:", win_dates[65][0], win_dates[65][-1], "n=", len(win_dates[65]))
print("d=366 window:", win_dates[366][0], win_dates[366][-1], "n=", len(win_dates[366]))
print("d=167 window:", win_dates[167][0], win_dates[167][-1], "n=", len(win_dates[167]))
with open("/work/window_dates.pkl", "wb") as f:
    pickle.dump({"lat_idx": lat_idx, "lon_idx": lon_idx, "win_dates": win_dates}, f)
print("saved")
