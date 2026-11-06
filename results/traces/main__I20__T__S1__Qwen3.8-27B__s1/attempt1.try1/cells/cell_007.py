import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
f = fs.open("icsa2027_data_20261101T090944Z/s2z/sst_s2.nc", "rb")
ds = xr.open_dataset(f, engine="h5netcdf")
v = ds["analysed_sst"]
print("attrs:", dict(v.attrs))
print("dims:", dict(ds.sizes))
lat = ds.latitude.values; lon = ds.longitude.values
print("lat range:", lat.min(), lat.max(), "lon range:", lon.min(), lon.max())
print("lat step:", np.diff(lat)[:3], "lon step:", np.diff(lon)[:3])
print("time[0]:", ds.time.values[0], "time[-1]:", ds.time.values[-1])
print("dtypes:", v.dtype, lat.dtype, lon.dtype, ds.time.dtype)

# region masks
latm = (lat >= 57.33) & (lat <= 58.53)
lonm = (lon >= 9.03) & (lon <= 10.23)
print("n lat:", latm.sum(), lat[latm][0], lat[latm][-1])
print("n lon:", lonm.sum(), lon[lonm][0], lon[lonm][-1])

t0 = time.time()
a = v.sel(time="1992-06-15").values
print("full slice shape", a.shape, a.dtype, "time %.2fs" % (time.time()-t0))
print("sample values:", a[300, 20], a[300, 21], np.nanmin(a), np.nanmax(a), np.isnan(a).mean())
t0 = time.time()
b = v.sel(time="1992-06-15", latitude=slice(57.33, 58.53), longitude=slice(9.03, 10.23)).values
print("region slice", b.shape, "time %.2fs" % (time.time()-t0))
print("finite frac in region:", np.isfinite(b).mean())
# check fill value: land
land = ~np.isfinite(a)
print("land frac:", land.mean())
t0 = time.time()
c = v.sel(time="1992-06-15", latitude=slice(57.34, 58.52), longitude=slice(9.04, 10.22)).values
print("region2", c.shape, "time %.2fs" % (time.time()-t0))
f.close()