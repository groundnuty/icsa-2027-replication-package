import numpy as np, h5py, pandas as pd
import xarray as xr
p = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
f = h5py.File(p, "r")
d = f["analysed_sst"]
print("shape", d.shape, "dtype", d.dtype, "chunks", d.chunks, "compression", d.compression, "shuffle", d.shuffle)
print("attrs:", dict(d.attrs))
f.close()

ds = xr.open_dataset(p, engine="h5netcdf")
t = ds["time"].values
print("time dtype", t.dtype, "n", len(t), "first", t[0], "last", t[-1])
dd = np.diff(t).astype("timedelta64[D]")
print("all daily consecutive:", bool(np.all(dd == np.timedelta64(1, "D"))))
lat = ds["latitude"].values; lon = ds["longitude"].values
print("lat", lat.dtype, lat[:3], lat[-3:])
print("lon", lon.dtype, lon[:3], lon[-3:])
print("lat steps", np.unique(np.round(np.diff(lat.astype('float64')),6)))
print("lon steps", np.unique(np.round(np.diff(lon.astype('float64')),6)))

latm = (lat >= 57.13) & (lat <= 58.33)
lonm = (lon >= 22.79) & (lon <= 23.99)
i0, i1 = np.where(latm)[0][[0,-1]]; j0, j1 = np.where(lonm)[0][[0,-1]]
print("lat idx", i0, i1, "vals", lat[i0], lat[i1], "n", i1-i0+1)
print("lon idx", j0, j1, "vals", lon[j0], lon[j1], "n", j1-j0+1)
print("lat vals:", lat[latm])
print("lon vals:", lon[lonm])

tt = pd.to_datetime(t)
ti = np.where((tt >= "2014-06-01") & (tt <= "2014-08-31"))[0]
print("target n", len(ti), tt[ti[0]].date(), tt[ti[-1]].date())
bi = np.where((tt >= "1991-12-27") & (tt <= "2003-01-05"))[0]
print("baseline span n", len(bi), tt[bi[0]].date(), tt[bi[-1]].date())
yrs = tt[bi].year
print("years range", yrs.min(), yrs.max(), "1996-02-29 in data:", int((tt==np.datetime64('1996-02-29')).sum()))
tgt_days = pd.date_range("2014-06-01","2014-08-31",freq="D")
print("target days present:", int(np.isin(tgt_days.values, t)), "of", len(tgt_days))
