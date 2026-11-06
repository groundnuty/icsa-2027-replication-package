import numpy as np, h5py, time as _t
import xarray as xr
p = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
print("numpy", np.__version__)
f = h5py.File(p, "r")
print(list(f.keys()))
d = f["analysed_sst"]
print("shape", d.shape, "dtype", d.dtype, "chunks", d.chunks, "compression", d.compression, "shuffle", d.shuffle())
print("scale/offset attrs:", dict(f["analysed_sst"].attrs))
f.close()

ds = xr.open_dataset(p, engine="h5netcdf")
t = ds["time"].values
print("time dtype", t.dtype, "n", len(t), "first", t[0], "last", t[-1])
dd = np.diff(t).astype("timedelta64[D]")
print("all daily consecutive:", np.all(dd == np.timedelta64(1, "D")))
lat = ds["latitude"].values; lon = ds["longitude"].values
print("lat", lat.dtype, lat[:3], lat[-3:])
print("lon", lon.dtype, lon[:3], lon[-3:])
print("lat step uniq", np.unique(np.round(np.diff(lat.astype('float64')),6))[:5])
print("lon step uniq", np.unique(np.round(np.diff(lon.astype('float64')),6))[:5])

# region selection
latm = (lat >= 57.13) & (lat <= 58.33)
lonm = (lon >= 22.79) & (lon <= 23.99)
i0, i1 = np.where(latm)[0][[0,-1]]; j0, j1 = np.where(lonm)[0][[0,-1]]
print("lat idx", i0, i1, "vals", lat[i0], lat[i1], "n", i1-i0+1)
print("lon idx", j0, j1, "vals", lon[j0], lon[j1], "n", j1-j0+1)

# time indices
import pandas as pd
tt = pd.to_datetime(t)
tgt = (tt >= "2014-06-01") & (tt <= "2014-08-31")
ti = np.where(tgt)[0]
print("target n", len(ti), tt[ti[0]].date(), tt[ti[-1]].date())
base = (tt >= "1991-12-27") & (tt <= "2003-01-05")
bi = np.where(base)[0]
print("baseline span n", len(bi), tt[bi[0]].date(), tt[bi[-1]].date())
