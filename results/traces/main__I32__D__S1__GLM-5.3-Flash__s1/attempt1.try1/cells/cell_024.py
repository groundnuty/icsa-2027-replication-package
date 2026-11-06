import numpy as np, json, xarray as xr
from datetime import date, timedelta

ds = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print(ds)
m = ds['mhw'].values
print("dtype:", m.dtype, "sum:", int(m.sum()), "shape:", m.shape)
T = np.load('/work/T.npy')
sea = np.isfinite(T).all(axis=0)
land_mhw = m[:, ~sea].sum()
print("mhw on land cells (should be 0):", int(land_mhw))
print("mhw matches saved mask:", np.array_equal(m, np.load('/work/mhw_mask.npy').astype(np.uint8)))

# re-derive events from written file
active = m.any(axis=(1,2)).astype(bool)
idx = np.flatnonzero(active)
breaks = np.flatnonzero(np.diff(idx) > 1) if idx.size else []
starts = np.concatenate(([idx[0]], idx[breaks+1])) if idx.size else []
ends = np.concatenate((idx[breaks], [idx[-1]])) if idx.size else []
tdates = [date(2005,6,1)+timedelta(days=i) for i in range(m.shape[0])]
ev = [(tdates[s].isoformat(), tdates[e].isoformat()) for s,e in zip(starts,ends)]
rep = json.load(open('/work/output/report.json'))
print("events in nc:", ev)
print("events in report:", [(e['onset'], e['end']) for e in rep['events']])
print("match:", ev == [(e['onset'], e['end']) for e in rep['events']])
print("report keys:", sorted(rep.keys()))
# coordinate values match dataset's (from consolidated file)
import h5py
f = h5py.File('/work/sst_s2.nc','r')
lat0 = f['latitude'][:][278:338]; lon0 = f['longitude'][:][613:673]
f.close()
print("lat match:", np.array_equal(ds['lat'].values, lat0), "lon match:", np.array_equal(ds['lon'].values, lon0))
tv = ds['time'].values
print("time values int32 seconds since 1981-01-01:", tv[:3], "...", tv[-3:])
print("first/last time -> date:", date(1981,1,1)+timedelta(days=int(tv[0])//86400), date(1981,1,1)+timedelta(days=int(tv[-1])//86400))
