import xarray as xr, numpy as np
p = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20120701.nc"
ds = xr.open_dataset(p, engine="h5netcdf")
v = ds["analysed_sst"]
print("attrs:", dict(v.attrs))
print(v.encoding)
lat = ds.latitude.values.astype(np.float64)
lon = ds.longitude.values.astype(np.float64)
i0 = np.searchsorted(lat, 54.45 - 1e-6)
# find cells inclusive with tolerance
tol = 1e-6
lat_sel = np.where((lat >= 54.45 - tol) & (lat <= 55.65 + tol))[0]
lon_sel = np.where((lon >= 16.05 - tol) & (lon <= 17.25 + tol))[0]
print("lat range selected:", lat[lat_sel[0]], lat[lat_sel[-1]], "n=", len(lat_sel))
print("lon range selected:", lon[lon_sel[0]], lon[lon_sel[-1]], "n=", len(lon_sel))
print("neighbors excluded below:", lat[lat_sel[0]-1] if lat_sel[0]>0 else None, lat[lat_sel[-1]+1] if lat_sel[-1]<len(lat)-1 else None)
print("neighbors excluded below lon:", lon[lon_sel[0]-1] if lon_sel[0]>0 else None, lon[lon_sel[-1]+1] if lon_sel[-1]<len(lon)-1 else None)
data = v.values  # (1, 626, 1051)
sub = data[0, lat_sel[0]:lat_sel[-1]+1, lon_sel[0]:lon_sel[-1]+1].astype(np.float64)
print("sub shape:", sub.shape)
print("min,max,finite count:", np.nanmin(sub), np.nanmax(sub), np.isfinite(sub).sum(), "of", sub.size)
print("unique nonfinite:", np.unique(~np.isfinite(sub)))
land = np.isnan(sub)
print("land fraction:", land.mean())
print("sample values:", sub[ipv6-5, ipv6-5])
ds.close()
