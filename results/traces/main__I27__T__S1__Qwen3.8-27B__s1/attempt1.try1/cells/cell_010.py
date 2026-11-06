
import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
BASE = '/icsa2027_data_20261101T090944Z/s1z'
p = f"{BASE}/sst_20080701.nc"
f = fs.open(p, "rb")
ds = xr.open_dataset(f, engine="h5netcdf")
lat = ds['latitude'].isel(latitude=slice(217,277)).values.astype(np.float32)
lon = ds['longitude'].isel(longitude=slice(421,481)).values.astype(np.float32)
f.close()
np.save('/tmp/mhw/lat.npy', lat)
np.save('/tmp/mhw/lon.npy', lon)
print("lat:", lat[0], lat[-1], len(lat))
print("lon:", lon[0], lon[-1], len(lon))
print("lat bounds check:", (lat >= 57.83-1e-9).all(), (lat <= 59.03+1e-9).all(), (lon >= 17.41-1e-9).all(), (lon <= 18.61+1e-9).all())

A = np.load('/tmp/mhw/target.npy').squeeze(axis=1)
print("target array:", A.shape, A.dtype)
finite_all = np.all(np.isfinite(A), axis=0)
print("sea cells (finite all 92 days):", finite_all.sum(), "of", finite_all.size)
print("target overall min/max finite:", np.nanmin(A), np.nanmax(A))
# check for any cell that is sometimes finite sometimes not (partial)
nfinite = np.isfinite(A).sum(axis=0)
print("cells with 0 finite days:", (nfinite==0).sum(), " partial:", ((nfinite>0)&(nfinite<92)).sum(), " full:", (nfinite==92).sum())
