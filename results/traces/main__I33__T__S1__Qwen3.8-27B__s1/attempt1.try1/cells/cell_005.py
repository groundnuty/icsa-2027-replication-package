
import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
base = '/icsa2027_data_20261101T090944Z/s1z'
p = f'{base}/sst_20140601.nc'
with fs.open(p, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print("attrs of analysed_sst:", ds['analysed_sst'].attrs)
    sst = ds['analysed_sst'].values  # (1, 626, 1051)
    lat = ds['latitude'].values; lon = ds['longitude'].values
print("sst dtype:", sst.dtype)
# find region indices
tol = 1e-4
i0 = np.searchsorted(lat, 59.05 - tol); i1 = np.searchsorted(lat, 60.25 + tol, side='right')
j0 = np.searchsorted(lon, 21.25 - tol); j1 = np.searchsorted(lon, 22.45 + tol, side='right')
print("lat idx", i0, i1, "lon idx", j0, j1)
print("lat range:", lat[i0], "...", lat[i1-1], " n=", i1-i0)
print("lon range:", lon[j0], "...", lon[j1-1], " n=", j1-j0)
sub = sst[0, i0:i1, j0:j1]
print("sub shape:", sub.shape)
print("min/max/mean:", np.nanmin(sub), np.nanmax(sub), np.nanmean(sub))
print("finite count:", np.isfinite(sub).sum(), "of", sub.size)
print("sample values:", sub[:3,:5])
print("any values < 200K or > 320K?", np.any((sub<200)&(sub>0)), np.any(sub>320))
