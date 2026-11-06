import json
import numpy as np
import xarray as xr

ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(ds)
m = ds['mhw'].values
print("dtype:", m.dtype, "shape:", m.shape)
print("unique values:", np.unique(m))
print("sum:", int(m.sum()))

# verify coords against original dataset slice
ds0 = xr.open_dataset('/work/data/sst_20100601.nc', engine='h5netcdf')
lat0 = ds0.latitude.values[260:320]; lon0 = ds0.longitude.values[485:545]
print("lat match:", np.array_equal(ds['lat'].values, lat0), " lon match:", np.array_equal(ds['lon'].values, lon0))
t = ds['time'].values
print("time first/last:", t[0], t[-1], "n:", len(t))
# non-sea cells all zero?
sea_mask = ~np.isnan(ds0['analysed_sst'].values[0, 260:320, 485:545])
print("land cells all-zero in mhw:", bool((m[:, ~sea_mask] == 0).all()))
ds0.close()

# per-day active counts from file
per_day = m.max(axis=(1,2))
days = [str(d)[:10] for d in t]
active_days = [days[i] for i in range(len(days)) if per_day[i]]
print("active days:", len(active_days), active_days[0], "..", active_days[-1])

rep = json.load(open('output/report.json'))
print("report keys:", sorted(rep.keys()))
print("events:", rep['events'])
import os
for f in ['output/mhw_mask.nc', 'output/report.json']:
    print(f, os.path.getsize(f), "bytes")
