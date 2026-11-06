import json, os
import numpy as np
import xarray as xr
from datetime import date, timedelta

meta = json.load(open('/tmp/meta.json'))
lat_region = np.array(meta['lat32'], dtype=np.float32)
lon_region = np.array(meta['lon32'], dtype=np.float32)
z = np.load('/tmp/mhw_final.npz')
in_mhw = z['in_mhw']; sea_idx = z['sea_idx']; thr_sm = z['thr_sm']
sst = np.load('/tmp/sst_region.npy')
dates = [date.fromisoformat(d) for d in meta['dates']]
date_to_idx = {d: i for i, d in enumerate(dates)}

def doy(d):
    cum = {1:0, 2:31, 3:60, 4:91, 5:121, 6:152, 7:182, 8:213, 9:244, 10:274, 11:305, 12:335}
    return cum[d.month] + d.day

c2 = int(np.argmax(in_mhw.sum(axis=1)))
tgt_dates = [date(2008,6,1) + timedelta(days=k) for k in range(92)]
cell_idx = sea_idx[c2]
vals, thrs = [], []
for t, d in enumerate(tgt_dates):
    vals.append(sst[date_to_idx[d], cell_idx])
    thrs.append(thr_sm[c2, doy(d)-1])
hotpy = [bool(v >= th) for v, th in zip(vals, thrs)]
runs = []
i = 0
while i < 92:
    if hotpy[i]:
        j = i
        while j + 1 < 92 and hotpy[j+1]:
            j += 1
        runs.append((i, j)); i = j + 1
    else:
        i += 1
kept = [(s, e) for s, e in runs if e - s + 1 >= 5]
merged = []
for s, e in kept:
    if merged and s - merged[-1][1] - 1 <= 2:
        merged[-1] = (merged[-1][0], e)
    else:
        merged.append((s, e))
maskpy = [False]*92
for s, e in merged:
    for t in range(s, e+1):
        maskpy[t] = True
print(f"busiest cell {c2} (region cell {cell_idx}): hot runs:", runs)
print("merged spans:", merged)
print("matches pipeline mask:", np.array_equal(np.array(maskpy), in_mhw[c2]))

mhw = np.zeros((92, 60, 60), dtype=np.uint8)
row, col = np.unravel_index(sea_idx, (60, 60))
for t in range(92):
    mhw[t, row, col] = in_mhw[:, t].astype(np.uint8)
print("mhw sum:", int(mhw.sum()), "days with any:", int((mhw.sum(axis=(1,2)) > 0).sum()))
print("ones per day 0..25:", [int(mhw[t].sum()) for t in range(26)])

os.makedirs('/work/output', exist_ok=True)
time_coord = np.array([np.datetime64(str(d), 'ns') for d in tgt_dates])
ds_out = xr.Dataset(
    {'mhw': (('time', 'latitude', 'longitude'), mhw)},
    coords={'time': time_coord, 'latitude': lat_region, 'longitude': lon_region},
)
ds_out.to_netcdf('/work/output/mhw_mask.nc')

events = [(date(2008,6,1), date(2008,6,21))]
report = {
    "region": {"lat_min": 54.13, "lat_max": 55.33, "lon_min": 14.67, "lon_max": 15.87},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2008-06-01", "end": "2008-08-31"},
    "events": [{"onset": str(a), "end": str(b)} for a, b in events],
    "complete": True,
    "caveats": "",
}
with open('/work/output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

chk = xr.open_dataset('/work/output/mhw_mask.nc')
print(chk)
print("mhw dtype:", chk['mhw'].dtype, "values:", np.unique(chk['mhw'].values))
print("time:", chk['time'].values[0], "...", chk['time'].values[-1])
print("lat:", chk['latitude'].values[0], chk['latitude'].values[-1], "lon:", chk['longitude'].values[0], chk['longitude'].values[-1])
chk.close()
print("free /work MB:", os.statvfs('/work').f_bavail * os.statvfs('/work').f_bsize / 1e6)
print(open('/work/output/report.json').read())
