import xarray as xr, numpy as np, time, datetime as dt
import warnings; warnings.filterwarnings('ignore')

d0 = dt.date(1991,12,27); d1 = dt.date(2003,1,5)
baseline_dates = [d0 + dt.timedelta(days=i) for i in range((d1-d0).days+1)]
t0 = dt.date(2004,6,1); t1 = dt.date(2004,8,31)
target_dates = [t0 + dt.timedelta(days=i) for i in range((t1-t0).days+1)]

lati = slice(34, 94); loji = slice(213, 273)
S_base = np.empty((len(baseline_dates), 60, 60), dtype=np.float64)
S_tgt  = np.empty((len(target_dates), 60, 60), dtype=np.float64)
meta = {}

def load_block(dates, arr, tag):
    for i, d in enumerate(dates):
        ds = xr.open_dataset(f'/work/data/sst_{d.strftime("%Y%m%d")}.nc', engine='h5netcdf')
        if not meta:
            meta['lat'] = ds['latitude'].values.astype(np.float64)[lati]
            meta['lon'] = ds['longitude'].values.astype(np.float64)[loji]
        tv = np.datetime64(ds['time'].values[0]).astype('datetime64[D]').astype(dt.date)
        assert tv == d, (tag, i, tv, d)
        assert ds['latitude'].values[0] == 53.5 and ds['longitude'].values[0] == 9.0 and ds['latitude'].size==626 and ds['longitude'].size==1051
        arr[i] = ds['analysed_sst'].values[0, lati, loji]
        ds.close()
        if i % 500 == 0:
            print(tag, i, d, flush=True)

t_start = time.time()
load_block(baseline_dates, S_base, 'base')
print("baseline done", time.time()-t_start, flush=True)
load_block(target_dates, S_tgt, 'tgt')
print("target done", time.time()-t_start, flush=True)

np.save('/work/S_base.npy', S_base)
np.save('/work/S_tgt.npy', S_tgt)
np.savez('/work/coords.npz', lat=meta['lat'], lon=meta['lon'],
         baseline_dates=np.array(baseline_dates).astype('datetime64[D]'),
         target_dates=np.array(target_dates).astype('datetime64[D]'))
print("saved. shapes:", S_base.shape, S_tgt.shape)
print("finite base:", S_base.isfinite().sum(), "of", S_base.size, " tgt:", S_tgt.isfinite().sum(), "of", S_tgt.size)
