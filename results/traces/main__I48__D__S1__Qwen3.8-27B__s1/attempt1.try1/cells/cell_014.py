import numpy as np, xarray as xr, os, datetime, time

LOCAL = '/work/data'
t0 = time.time()

ref = xr.open_dataset(f'{LOCAL}/sst_20160601.nc', engine='h5netcdf')
lat_all = ref['latitude'].values.astype('float64')
lon_all = ref['longitude'].values.astype('float64')
lat_idx = np.where((lat_all >= 64.51) & (lat_all <= 65.71))[0]
lon_idx = np.where((lon_all >= 21.97) & (lon_all <= 23.17))[0]
lat_vals = ref['latitude'].values[lat_idx]
lon_vals = ref['longitude'].values[lon_idx]
ref.close()
ncells = len(lat_idx) * len(lon_idx)
print("cells:", ncells)

def daterange(a, b):
    d = a
    while d <= b:
        yield d
        d += datetime.timedelta(days=1)

ext_dates = list(daterange(datetime.date(1991,12,27), datetime.date(2003,1,5)))
tgt_dates = list(daterange(datetime.date(2016,6,1), datetime.date(2016,8,31)))
print("ext days:", len(ext_dates), "tgt days:", len(tgt_dates))

def load_region(d):
    p = f'{LOCAL}/sst_{d.strftime("%Y%m%d")}.nc'
    ds = xr.open_dataset(p, engine='h5netcdf')
    v = ds['analysed_sst']
    assert v.dtype == np.float32, f"bad dtype {v.dtype} {p}"
    tcoord = str(v['time'].values[0])[:10]
    assert tcoord == d.strftime('%Y-%m-%d'), f"time mismatch {tcoord} vs {d} in {p}"
    arr = v.values[0][lat_idx][:, lon_idx].astype('float64').ravel()
    ds.close()
    return arr

tgt = np.empty((len(tgt_dates), ncells), dtype='float64')
for i, d in enumerate(tgt_dates):
    tgt[i] = load_region(d)
print(f"target loaded {time.time()-t0:.1f}s")
fin = np.isfinite(tgt).all(axis=0)
print("sea cells (finite all target days):", int(fin.sum()), "of", ncells)

ext = np.empty((len(ext_dates), ncells), dtype='float64')
for i, d in enumerate(ext_dates):
    ext[i] = load_region(d)
print(f"all loaded {time.time()-t0:.1f}s")

np.save('/work/tgt.npy', tgt)
np.save('/work/ext.npy', ext)
np.save('/work/lat_idx.npy', lat_idx)
np.save('/work/lon_idx.npy', lon_idx)
np.save('/work/lat_vals.npy', lat_vals)
np.save('/work/lon_vals.npy', lon_vals)
np.save('/work/sea_mask.npy', fin)
