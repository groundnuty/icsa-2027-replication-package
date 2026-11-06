import numpy as np, json, datetime as dt, xarray as xr
data = np.load('/work/data.npy')
thr_s = np.load('/work/thr_s.npy').reshape(366,60,60)
meta = json.load(open('/work/dates.json'))
tg = [dt.date.fromisoformat(s) for s in meta['target']]
bw = [dt.date.fromisoformat(s) for s in meta['baseline_window']]
tg_data = data[4028:4120]

# verify direct read of one target file and one baseline file against arrays
d = dt.date(2017,7,15)
ds = xr.open_dataset('/work/nc/sst_20170715.nc', engine='h5netcdf')
v = ds['analysed_sst'].isel(time=0, latitude=slice(438,498), longitude=slice(487,547)).values.astype('float64')
i_tg = tg.index(d)
print('target 2017-07-15 matches:', np.allclose(v, tg_data[i_tg], equal_nan=True))
db = dt.date(1997,7,15)
ds2 = xr.open_dataset('/work/nc/sst_19970715.nc', engine='h5netcdf')
vb = ds2['analysed_sst'].isel(time=0, latitude=slice(438,498), longitude=slice(487,547)).values.astype('float64')
i_bw = bw.index(db)
print('baseline 1997-07-15 matches:', np.allclose(vb, data[i_bw], equal_nan=True))

cum = [0,31,60,91,121,152,182,213,244,274,305,335]
def md_doy(dd): return cum[dd.month-1] + dd.day
tg_doy = np.array([md_doy(x) for x in tg])
excess = tg_data - thr_s[tg_doy-1]
print('max excess (SST - threshold):', np.nanmax(excess), 'K')
print('min excess:', np.nanmin(excess), 'K')
print('days with any excess > 0:', int((excess > 0).any(axis=(1,2)).sum()))
print('cells with any excess > 0:', int((excess > 0).any(axis=0).sum()))
# regional mean series: SST vs threshold
sst_mean = np.nanmean(tg_data, axis=(1,2))
thr_mean = np.nanmean(thr_s[tg_doy-1], axis=(1,2))
for k in range(0, 92, 7):
    print(tg[k], 'regSST', round(sst_mean[k],2), 'regTHR', round(thr_mean[k],2), 'diff', round(sst_mean[k]-thr_mean[k],2))
