import numpy as np
import xarray as xr
import json

ds = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print(ds)
m = ds['mhw'].values
z = np.load('/work/intermediate.npz')
Mref = z['M'].reshape(92, 60, 60).astype(np.uint8)
print("values identical to computed mask:", np.array_equal(m, Mref))
print("dtype:", m.dtype, "shape:", m.shape)
print("time:", ds.time.values[0], "->", ds.time.values[-1], "n=", len(ds.time))
print("lat:", ds.latitude.values[0], "->", ds.latitude.values[-1], "n=", len(ds.latitude))
print("lon:", ds.longitude.values[0], "->", ds.longitude.values[-1], "n=", len(ds.longitude))
print("mask total ones:", int(m.sum()))

dsf = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
t_all = dsf.time.values
u0 = np.searchsorted(t_all, np.datetime64('2022-06-01')); u1 = np.searchsorted(t_all, np.datetime64('2022-08-31'))
S = dsf.analysed_sst.isel(time=slice(u0,u1+1), latitude=slice(66,126), longitude=slice(531,591)).values
lat_o = dsf.latitude.values.copy(); lon_o = dsf.longitude.values.copy()
dsf.close()
sea = np.isfinite(S).all(axis=0)
print("non-sea cells have mask all-zero:", bool(m[:, ~sea].sum() == 0))
print("sea cells with >=1 mask day:", int((m.sum(axis=0)[sea.ravel()] > 0).sum()))
print("lat coords exact:", np.array_equal(ds.latitude.values.astype(np.float32), lat_o[66:126]))
print("lon coords exact:", np.array_equal(ds.longitude.values.astype(np.float32), lon_o[531:591]))

r = json.load(open('/work/output/report.json'))
assert set(r.keys()) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
assert all(set(e.keys()) == {"onset","end"} for e in r["events"])
print("report fields OK:", sorted(r.keys()))
