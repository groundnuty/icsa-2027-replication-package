import os, numpy as np, datetime as dt, json, xarray as xr
print('CWD:', os.getcwd())
os.makedirs('output', exist_ok=True)
lat=np.load('/tmp/lat.npy'); lon=np.load('/tmp/lon.npy')   # saved earlier from target-day load
inmhw=np.load('/tmp/inmhw.npy')                             # (92,60,60) bool
dates=[dt.date.fromordinal(int(o)) for o in np.load('/tmp/dates_ord.npy')]
ti=4540; tj=4631
tvals=np.arange(np.datetime64('2004-06-01'), np.datetime64('2004-09-01'))
assert len(tvals)==92
lat=np.load('/tmp/lat.npy'); lon=np.load('/tmp/lon.npy')
ds = xr.Dataset(
    {"mhw": (("time","lat","lon"), inmhw.astype(np.uint8))},
    coords={"time": tvals, "lat": lat.astype(np.float32), "lon": lon.astype(np.float32)},
)
ds["mhw"].attrs={"long_name":"marine heatwave mask (1 = cell inside a per-cell MHW, 0 otherwise)"}
ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print('written mhw_mask.nc')
# verify
chk = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(chk)
print('mhw dtype', chk['mhw'].dtype, 'sum', int(chk['mhw'].values.sum()))
chk.close()
