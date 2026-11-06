import xarray as xr, numpy as np, time
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
lat = ds["latitude"].values; lon = ds["longitude"].values
lati = np.where((lat >= 63.31) & (lat <= 64.51))[0]
loni = np.where((lon >= 21.31) & (lon <= 22.51))[0]
t0=time.time()
sub = ds["analysed_sst"].isel(time=3660, latitude=lati, longitude=loni).values  # 1992-01-01 approx
t1=time.time()
print("first read", t1-t0, "s", sub.shape, sub.dtype)
print("nan frac", np.isnan(sub).mean(), "sample", sub[0,:5])
t0=time.time()
sub2 = ds["analysed_sst"].isel(time=3661, latitude=lati, longitude=loni).values
t1=time.time()
print("second read", t1-t0, "s")
t0=time.time()
sub3 = ds["analysed_sst"].isel(time=3662, latitude=lati, longitude=loni).values
t1=time.time()
print("third read", t1-t0, "s")
# check time indexing
times = ds["time"].values
import pandas as pd
print("time[3660]=", times[3660], "time[3661]=", times[3661])
idx19920101 = np.where(times == np.datetime64("1992-01-01"))[0]
print("index of 1992-01-01:", idx19920101)
print("time dtype", ds["analysed_sst"].dtype)
