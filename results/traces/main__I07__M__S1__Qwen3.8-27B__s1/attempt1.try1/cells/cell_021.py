import numpy as np, json
from datetime import date, timedelta
import xarray as xr

z = np.load("/tmp/sst_data.npz")
T = z["T"]; ttimes = z["ttimes"]
s2 = np.load("/tmp/step2.npz")
thr_s = s2["thr_s"]; sea = s2["sea"]
cum = [0,31,60,91,121,152,182,213,244,274,305,335]
def doy(d): return cum[d.month-1] + d.day
def to_date(ts):
    s = str(ts); return date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
tgt_dates = [to_date(t) for t in ttimes]
tgt_doy = np.array([doy(d) for d in tgt_dates]) - 1
T60 = T.reshape(92, 3600); sea_flat = sea.ravel(); ncell = int(sea.sum())
hot = T60[:, sea_flat] >= thr_s[:, tgt_doy].T

def mhw_mask(h):
    n = len(h); out = np.zeros(n, dtype=bool); idx = np.where(h)[0]
    if idx.size == 0: return out
    brk = np.where(np.diff(idx) > 1)[0] + 1
    runs = list(np.split(idx, brk)); evs = []; last_i = -1
    for i, r in enumerate(runs):
        if len(r) >= 5:
            if evs and i == last_i + 1 and (r[0] - (runs[last_i][-1] + 1)) <= 2:
                evs[-1] = (evs[-1][0], r[-1])
            else:
                evs.append((r[0], r[-1]))
            last_i = i
    for s_, e_ in evs: out[s_:e_+1] = True
    return out

inmhw = np.array([mhw_mask(hot[:, c]) for c in range(ncell)])
active = inmhw.any(axis=0)
print("active first 15 days:", active[:15].astype(int).tolist())
print("active days 60..75:", active[60:75].astype(int).tolist())
print("active day68 (Aug 8):", active[68], "day69 (Aug 9):", active[69])

# cells in MHW on day 0
c0 = np.where(inmhw[:, 0])[0]
print("cells in MHW on 2021-06-01:", len(c0))
for c in c0[:5]:
    print("  cell", c, "hot days 0-14:", hot[0:15, c].astype(int).tolist())

# cells in MHW on day 68
c68 = np.where(inmhw[:, 68])[0]
print("cells in MHW on 2021-08-08:", len(c68))
for c in c68[:5]:
    print("  cell", c, "hot days 60-74:", hot[60:75, c].astype(int).tolist())

# fresh raw-file check: cell (lat idx 48..107 / lon 353..412) -> pick center cell
lat_idx, lon_idx = 77, 382  # (48+29, 353+29)
ds = xr.open_dataset("/data/icsa2027_data_20261101T090944Z/s1z/sst_20210715.nc", engine="h5netcdf")
raw = float(ds['analysed_sst'].isel(time=0, latitude=lat_idx, longitude=lon_idx).values)
print("raw SST 2021-07-15 at (54.46+29*0.02, 16.06+29*0.02):", raw, "K")
cached = T[44, lat_idx-48, lon_idx-353]  # 2021-07-15 is day 45 (idx 44)
print("cached:", cached, "match:", raw == cached)
flat = (lat_idx-48)*60 + (lon_idx-353)
is_sea = sea_flat[flat]
print("is sea cell:", bool(is_sea), "hot on that day:", bool(hot[44, np.searchsorted(sea_flat, flat)]) if is_sea else None)
print("doy of 2021-07-15:", doy(date(2021,7,15)), "thr:", thr_s[np.searchsorted(sea_flat, flat), 182] if is_sea else None)
ds.close()
