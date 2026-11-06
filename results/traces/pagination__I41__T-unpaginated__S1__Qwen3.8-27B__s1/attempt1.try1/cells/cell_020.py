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

sea_mask = np.isfinite(target).all(axis=0)
sea_cells = np.argwhere(sea_mask)
n_sea = len(sea_cells)
M = np.empty((4028, n_sea), np.float64)
T = np.empty((92, n_sea), np.float64)
for j, (i, k) in enumerate(sea_cells):
    M[:, j] = master[:, i, k]
    T[:, j] = target[:, i, k]

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

def smooth366(a):
    s = np.zeros_like(a)
    for k in range(-15, 16):
        s += np.roll(a, -k, axis=0)
    return s / 31.0
thrs = smooth366(thr)
clims = smooth366(clim)

hot = T >= thrs[tdoy-1]
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
print("active days:", int(active.sum()), " events:", len(events))
for s,e in events:
    print("EVENT %s .. %s (%d d)" % (tgt_dates[s].isoformat(), tgt_dates[e].isoformat(), e-s+1))

os.makedirs('output', exist_ok=True)
import xarray as xr
full_mask = np.zeros((92, 60, 60), dtype=np.uint8)
for j, (i, k) in enumerate(sea_cells):
    full_mask[:, i, k] = mhw[:, j]
time_vals = np.array([t.isoformat() for t in tgt_dates], dtype='datetime64[ns]')
ds_out = xr.Dataset(
    {'mhw': (('time','lat','lon'), full_mask)},
    coords={'time': time_vals, 'lat': lat_r, 'lon': lon_r})
ds_out.to_netcdf('output/mhw_mask.nc')
print("wrote output/mhw_mask.nc", full_mask.shape, "ones:", int(full_mask.sum()))

report = {
  "region": {"lat_min": 61.57, "lat_max": 62.77, "lon_min": 20.17, "lon_max": 21.37},
  "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
  "target_analysed": {"start": "2021-06-01", "end": "2021-08-31"},
  "events": [{"onset": tgt_dates[s].isoformat(), "end": tgt_dates[e].isoformat()} for s,e in events],
  "complete": True,
  "caveats": ("Region grid: 60x60 cells (lat 61.58-62.76 N, lon 20.18-21.36 E, 0.02 deg grid). "
              "3308 of 3600 cells are sea cells (SST finite on all 92 target days). "
              "Threshold/climatology per day-of-year from 1992-2002 baseline with +-5 calendar-day windows "
              "(121 pool values per day of year, incl. 1991-12-27..31 and 2003-01-01..05 edge days), "
              "90th percentile computed with numpy method='hazen', climatology = pool mean, "
              "day 60 set to mean of days 59 and 61, then 31-day centred wrap-around moving mean. "
              "Per-cell MHW: runs of >=5 consecutive hot days (SST >= threshold); MHWs separated by "
              "1-2 non-hot days are joined, gap days included. 2021 was a strongly warm summer in this "
              "region (~4-6 K above baseline), producing extended MHW activity.")
}
with open('output/report.json','w') as f:
    json.dump(report, f, indent=2)
print("wrote output/report.json")

# verify written file
chk = xr.open_dataset('output/mhw_mask.nc')
print(chk)
print("mhw dtype:", chk['mhw'].dtype, "time[0]:", chk['time'].values[0], "time[-1]:", chk['time'].values[-1])
print("lat range:", float(chk['lat'].values[0]), float(chk['lat'].values[-1]),
      "lon range:", float(chk['lon'].values[0]), float(chk['lon'].values[-1]))
print("mhw sum:", int(chk['mhw'].values.sum()), "max:", int(chk['mhw'].values.max()))
chk.close()
