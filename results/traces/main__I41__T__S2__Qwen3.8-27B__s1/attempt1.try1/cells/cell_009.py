import fsspec, xarray as xr, numpy as np, pandas as pd, os
os.makedirs("work", exist_ok=True)
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine="h5netcdf")

t = pd.DatetimeIndex(ds.time.values)
target = pd.date_range("2021-06-01","2021-08-31")
ti = t.get_indexer(target)

lat = ds.latitude.values; lon = ds.longitude.values
eps = 1e-9
li = np.where((lat >= 61.57-eps) & (lat <= 62.77+eps))[0]
lj = np.where((lon >= 20.17-eps) & (lon <= 21.37+eps))[0]
lat0,lat1,lon0,lon1 = li[0],li[-1],lj[0],lj[-1]

sub = ds['analysed_sst'].isel(time=ti, latitude=slice(lat0,lat1+1), longitude=slice(lon0,lon1+1))
sst_t = sub.values.astype(np.float64)
finite = np.isfinite(sst_t).all(axis=0)
np.savez("work/target.npz", sst=sst_t, lat=lat[lat0:lat1+1], lon=lon[lon0:lon1+1],
         time=ds.time.values[ti].astype("datetime64[ns]"), li=li, lj=lj, sea=finite)
print("sea cells:", int(finite.sum()), "saved work/target.npz")
