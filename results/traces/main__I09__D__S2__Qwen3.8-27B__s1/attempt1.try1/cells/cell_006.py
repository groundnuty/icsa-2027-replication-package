import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds.latitude.values
lon = ds.longitude.values

eps = 1e-6
lat_sel = np.where((lat >= 54.81 - eps) & (lat <= 56.01 + eps))[0]
lon_sel = np.where((lon >= 19.61 - eps) & (lon <= 20.81 + eps))[0]
print("n lat:", len(lat_sel), "from idx", lat_sel[0], "to", lat_sel[-1])
print("lat values:", [f"{v:.4f}" for v in lat[lat_sel][:3]], "...", [f"{v:.4f}" for v in lat[lat_sel][-3:]])
print("n lon:", len(lon_sel), "from idx", lon_sel[0], "to", lon_sel[-1])
print("lon values:", [f"{v:.4f}" for v in lon[lon_sel][:3]], "...", [f"{v:.4f}" for v in lon[lon_sel][-3:]])

t = ds.time.values
t0 = np.datetime64('2022-06-01')
t1 = np.datetime64('2022-08-31')
ti0 = np.searchsorted(t, t0)
ti1 = np.searchsorted(t, t1)
print("target time idx:", ti0, ti1, "count:", ti1-ti0+1)
print("target dates:", t[ti0], t[ti1])

# extended baseline window
b0 = np.datetime64('1991-12-27')
b1 = np.datetime64('2003-01-05')
bi0 = np.searchsorted(t, b0)
bi1 = np.searchsorted(t, b1)
print("ext baseline idx:", bi0, bi1, "count:", bi1-bi0+1)
print("ext baseline dates:", t[bi0], t[bi1])
ds.close()
