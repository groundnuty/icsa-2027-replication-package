import numpy as np, warnings, json, os
from datetime import date, timedelta

dat = np.load('/tmp/sst_data.npz')
master = dat['master']; target = dat['target']
lat_r = dat['lat_region'].astype(np.float32)
lon_r = dat['lon_region'].astype(np.float32)

def daterange(a,b):
    o=[]
    while a<=b: o.append(a); a+=timedelta(days=1)
    return o
base_dates = daterange(date(1991,12,27), date(2003,1,5))
tgt_dates  = daterange(date(2021,6,1), date(2021,8,31))
base_all   = daterange(date(1992,1,1), date(2002,12,31))

mdays=[31,29,31,30,31,30,31,31,30,31,30,31]; cum=[0]
for m in mdays: cum.append(cum[-1]+m)
doyf = lambda m,dd: cum[m-1]+dd
tdoy = np.array([doyf(x.month, x.day) for x in tgt_dates])

# sea cells
sea_mask = np.isfinite(target).all(axis=0)
sea_cells = np.argwhere(sea_mask)
n_sea = len(sea_cells)
M = np.empty((4028, n_sea), np.float64)
T = np.empty((92, n_sea), np.float64)
for j, (i, k) in enumerate(sea_cells):
    M[:, j] = master[:, i, k]
    T[:, j] = target[:, i, k]

# pools
mord  = np.array([x.toordinal() for x in base_dates])
bords = np.array([x.toordinal() for x in base_all])
bdoy  = np.array([doyf(x.month, x.day) for x in base_all])
pool_idx = {}
for dd in range(1, 367):
    if dd == 60: continue
    b = bords[bdoy == dd]
    mask = np.zeros(4028, dtype=bool)
    for bo in b:
        mask |= (mord >= bo-5) & (mord <= bo+5)
    pool_idx[dd] = np.where(mask)[0]
assert all(len(v) == 121 for v in pool_idx.values())

# thresholds & climatology, 0-based arrays of length 366 (index = doy-1)
thr = np.full((366, n_sea), np.nan)
clim = np.full((366, n_sea), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=RuntimeWarning)
    for dd in range(1, 367):
        if dd == 60: continue
        blk = M[pool_idx[dd], :]
        thr[dd-1, :] = np.nanquantile(blk, 0.9, axis=0, method="hazen")
        clim[dd-1, :] = np.nanmean(blk, axis=0)
thr[59, :] = 0.5*(thr[58, :] + thr[60, :])
clim[59, :] = 0.5*(clim[58, :] + clim[60, :])

# wrap-around centred 31-day mean: day d averages d-15..d+15 (mod 366)
def smooth366(a):
    s = np.zeros_like(a)
    for k in range(-15, 16):
        s += np.roll(a, -k, axis=0)
    return s / 31.0
thrs = smooth366(thr)
clims = smooth366(clim)

# sanity
print("thr summer raw range: %.2f..%.2f | smoothed: %.2f..%.2f" % (
    np.nanmin(thr[152:244]), np.nanmax(thr[152:244]), np.nanmin(thrs[152:244]), np.nanmax(thrs[152:244])))
print("clim summer range: %.2f..%.2f" % (np.nanmin(clims[152:244]), np.nanmax(clims[152:244])))

# hot days
hot = T >= thrs[tdoy-1]
print("hot cell-days:", int(hot.sum()), " days with >=1 hot cell:", int(hot.any(axis=1).sum()))

# per-cell MHWs
n_days = 92
mhw = np.zeros((n_days, n_sea), dtype=np.uint8)
for c in range(n_sea):
    h = hot[:, c]
    starts, ends = [], []
    i = 0
    while i < n_days:
        if h[i]:
            j = i
            while j+1 < n_days and h[j+1]: j += 1
            starts.append(i); ends.append(j); i = j+1
        else:
            i += 1
    keep = [(s,e) for s,e in zip(starts,ends) if e-s+1 >= 5]
    merged = []
    for s,e in keep:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s,e])
    for s,e in merged:
        mhw[s:e+1, c] = 1
print("cells with >=1 MHW:", int((mhw.any(axis=0)).sum()))

# regional events
active = mhw.any(axis=1)
events = []
i = 0
while i < n_days:
    if active[i]:
        j = i
        while j+1 < n_days and active[j+1]: j += 1
        events.append((i, j)); i = j+1
    else:
        i += 1
print("active days:", int(active.sum()), "of", n_days)
for s,e in events:
    print("EVENT %s .. %s (%d d)" % (tgt_dates[s].isoformat(), tgt_dates[e].isoformat(), e-s+1))
print("num events:", len(events))

# ---------- outputs ----------
os.makedirs('output', exist_ok=True)
import xarray as xr
full_mask = np.zeros((92, 60, 60), dtype=np.uint8)
for j, (i, k) in enumerate(sea_cells):
    full_mask[:, i, k] = mhw[:, j]
time_vals = np.array([t.toordinal() for t in tgt_dates], dtype='datetime64[D]').astype('datetime64[ns]')
ds_out = xr.Dataset(
    {'mhw': (('time','lat','lon'), full_mask)},
    coords={'time': time_vals, 'lat': lat_r, 'lon': lon_r})
ds_out.to_netcdf('output/mhw_mask.nc')
print("wrote output/mhw_mask.nc", full_mask.shape, full_mask.sum())

report = {
  "region": {"lat_min": 61.57, "lat_max": 62.77, "lon_min": 20.17, "lon_max": 21.37},
  "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
  "target_analysed": {"start": "2021-06-01", "end": "2021-08-31"},
  "events": [{"onset": tgt_dates[s].isoformat(), "end": tgt_dates[e].isoformat()} for s,e in events],
  "complete": True,
  "caveats": ("Region grid: 60x60 cells (lat 61.58-62.76 N, lon 20.18-21.36 E, 0.02 deg). "
              "3308 of 3600 cells are sea cells (SST finite on all 92 target days). "
              "Threshold/climatology per day-of-year from 1992-2002 baseline with +-5-day windows "
              "(121 pool values per day of year), 90th percentile by numpy method='hazen', "
              "day 60 = mean of days 59 and 61, then 31-day centred wrap-around moving mean. "
              "MHW: runs of >=5 hot days (SST >= threshold), 1-2 day non-hot gaps joined.")
}
with open('output/report.json','w') as f:
    json.dump(report, f, indent=2)
print("wrote output/report.json")
print(json.dumps(report["events"]))
np.savez_compressed('/tmp/final_state.npz', full_mask=full_mask, thrs=thrs, clim=clims,
                    sea_cells=sea_cells, tdoy=tdoy)
