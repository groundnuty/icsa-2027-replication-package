import numpy as np, json, os
from datetime import date, timedelta
import h5py

m = xr = None
import xarray as xr
ds2 = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
m = ds2['mhw'].values
tdates = [date(2005,6,1)+timedelta(days=i) for i in range(m.shape[0])]
active = m.any(axis=(1,2))
idx = np.flatnonzero(active)
br = np.flatnonzero(np.diff(idx) > 1)
starts = np.concatenate(([idx[0]], idx[br+1])); ends = np.concatenate((idx[br], [idx[-1]]))
ev = [(tdates[s].isoformat(), tdates[e].isoformat()) for s,e in zip(starts,ends)]
rep = json.load(open('/work/output/report.json'))
print("events from nc:", ev)
print("report events:", [(e['onset'], e['end']) for e in rep['events']])
print("match:", ev == [(e['onset'], e['end']) for e in rep['events']])
print("report keys:", sorted(rep.keys()))
with h5py.File('/work/output/mhw_mask.nc','r') as f:
    print("on-disk mhw dtype:", f['mhw'].dtype, "| fill attr:", '_FillValue' in f['mhw'].attrs)
    print("dims:", {k: len(v) for k,v in f.items() and []} if False else dict(f['mhw'].shape))
print("time coord raw:", ds2['time'].encoding.get('units'), ds2['time'].encoding.get('dtype'))
print("output files:", sorted(os.listdir('/work/output')))
print("report:", json.dumps(rep))
