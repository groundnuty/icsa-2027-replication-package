import xarray as xr, numpy as np, json

ds = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print(ds)
mhw = ds['mhw'].values
print('mhw dtype:', ds['mhw'].dtype, '| shape:', mhw.shape)
print('time:', str(ds['time'].values[0])[:10], '..', str(ds['time'].values[-1])[:10], '| n =', len(ds['time']))
print('lat:', ds['lat'].values[0], '..', ds['lat'].values[-1], '| n =', len(ds['lat']))
print('lon:', ds['lon'].values[0], '..', ds['lon'].values[-1], '| n =', len(ds['lon']))
print('unique values:', np.unique(mhw), '| sum:', int(mhw.sum()))

with open('/work/output/report.json') as f:
    rep = json.load(f)
print('report keys:', sorted(rep.keys()))
print('events:', rep['events'])
print('complete:', rep['complete'])
print('baseline:', rep['baseline_analysed'], '| target:', rep['target_analysed'])
