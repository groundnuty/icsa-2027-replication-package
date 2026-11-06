import numpy as np, xarray as xr, os, json, datetime as dt, time

NC = '/work/nc'
meta = json.load(open('/work/dates.json'))
bw = [dt.date.fromisoformat(s) for s in meta['baseline_window']]
tg = [dt.date.fromisoformat(s) for s in meta['target']]
alldates = bw + tg
n = len(alldates)
data = np.empty((n, 60, 60), dtype='float64')
t0 = time.time()
LA, LO = 438, 487
for i, d in enumerate(alldates):
    ds = xr.open_dataset(f'{NC}/sst_{d:%Y%m%d}.nc', engine='h5netcdf')
    t = ds['time'].values[0]
    if np.datetime64(d.isoformat()) != t:
        print('TIME MISMATCH', d, t)
    data[i] = ds['analysed_sst'].isel(time=0, latitude=slice(LA, LA+60), longitude=slice(LO, LO+60)).values.astype('float64')
    ds.close()
    if i % 800 == 799:
        print(i+1, round(time.time()-t0,1), 's', flush=True)
print('loaded', data.shape, 'in', round(time.time()-t0,1), 's')
np.save('/work/data.npy', data)
print('nan frac overall:', round(float(np.isnan(data).mean()),4))
tg_data = data[len(bw):]
sea = np.isfinite(tg_data).all(axis=0)
print('sea cells (finite all target days):', int(sea.sum()))
nan_any = np.isnan(tg_data).any(axis=0)
print('cells with any NaN in target period:', int(nan_any.sum()), '= land cells?', int((~sea).sum()))
print('non-sea cells with some finite data:', int((nan_any & sea==False & ~np.isnan(tg_data).all(axis=0)).sum()))
