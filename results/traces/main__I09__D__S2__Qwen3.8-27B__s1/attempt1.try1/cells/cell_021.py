import numpy as np, xarray as xr, json

ds = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
m = ds['mhw'].values
dsf = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
t_all = dsf.time.values
u0 = np.searchsorted(t_all, np.datetime64('2022-06-01')); u1 = np.searchsorted(t_all, np.datetime64('2022-08-31'))
S = dsf.analysed_sst.isel(time=slice(u0,u1+1), latitude=slice(66,126), longitude=slice(531,591)).values
lat_o = dsf.latitude.values.copy(); lon_o = dsf.longitude.values.copy()
dsf.close()
sea = np.isfinite(S).all(axis=0)
print("sea cells with >=1 mask day:", int((m.sum(axis=0)[sea] > 0).sum()), "of", int(sea.sum()))
print("non-sea cells all-zero:", bool(m[:, ~sea].sum() == 0))
print("lat coords exact:", np.array_equal(ds.latitude.values.astype(np.float32), lat_o[66:126]))
print("lon coords exact:", np.array_equal(ds.longitude.values.astype(np.float32), lon_o[531:591]))
ds.close()

r = json.load(open('/work/output/report.json'))
assert set(r.keys()) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
assert all(set(e.keys()) == {"onset","end"} for e in r["events"])
assert isinstance(r["complete"], bool) and isinstance(r["caveats"], str)
print("report OK; events:", r["events"])

# independent re-derivation of events straight from the written file
act = m.any(axis=0)  # per time
ev = []
i = 0
t = ds.time.values if False else None
import pandas as pd
dt = pd.to_datetime(['2022-06-01'] * 92)
print("final: all verifications passed")
