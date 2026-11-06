
import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
lat = ds['latitude']; lon = ds['longitude']; sst = ds['analysed_sst']
print("lat dtype:", lat.dtype, "n:", len(lat), "first:", float(lat.values[0]), "last:", float(lat.values[-1]))
print("lat monotone inc:", bool((np.diff(lat.values)>0).all()))
print("lon dtype:", lon.dtype, "n:", len(lon), "first:", float(lon.values[0]), "last:", float(lon.values[-1]))
print("lon monotone inc:", bool((np.diff(lon.values)>0).all()))
dl = np.diff(lat.values); dl = dl[1:3]
print("lat diffs:", dl[:5], "lon diffs:", np.diff(lon.values)[:5])
print("sst dims:", sst.dims, sst.dtype, sst.attrs)
# region cell counts (inclusive bounds)
lm, lx = 54.45, 55.65
om, ox = 16.05, 17.25
li = np.where((lat.values >= lm - 1e-12) & (lat.values <= lx + 1e-12))[0]
oi = np.where((lon.values >= om - 1e-12) & (lon.values <= ox + 1e-12))[0]
print("region lat idx:", li[0], li[-1], "count:", len(li))
print("region lon idx:", oi[0], oi[-1], "count:", len(oi))
print("region lat values:", lat.values[li])
print("region lon values:", lon.values[oi])
ds.close(); f.close()
