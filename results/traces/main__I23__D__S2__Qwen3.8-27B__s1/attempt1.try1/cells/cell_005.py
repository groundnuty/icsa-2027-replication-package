import xarray as xr
import numpy as np
import time as _time
import pickle

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat_i = np.arange(196, 256)
lon_i = np.arange(485, 545)

t0=_time.time()
V_win = ds.analysed_sst.isel(time=slice(3647, 7675), latitude=lat_i, longitude=lon_i).values.astype(np.float64)
t1=_time.time()
V_tgt = ds.analysed_sst.isel(time=slice(11474, 11566), latitude=lat_i, longitude=lon_i).values.astype(np.float64)
t2=_time.time()
print("read window (4028d):", t1-t0, "s; shape:", V_win.shape, "finite frac:", np.isfinite(V_win).mean())
print("read target (92d):", t2-t1, "s; shape:", V_tgt.shape, "finite frac:", np.isfinite(V_tgt).mean())

# sea cells: finite on every target day
sea = np.all(np.isfinite(V_tgt), axis=0)
print("sea cells:", sea.sum(), "of", sea.size)
print("land cells:", (~sea).sum())

# save for later steps
with open('/work/data.pkl','wb') as f:
    pickle.dump({'V_win': V_win, 'V_tgt': V_tgt,
                 'lat': ds.latitude.values, 'lon': ds.longitude.values,
                 'time_win': ds.time.values[3647:7675], 'time_tgt': ds.time.values[11474:11566]}, f)
print("saved")
