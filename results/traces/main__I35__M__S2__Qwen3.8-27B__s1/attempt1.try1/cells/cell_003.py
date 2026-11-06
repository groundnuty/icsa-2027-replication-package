import xarray as xr, numpy as np, time

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
t = ds.time.values

def tindex(date):
    target = np.datetime64(date)
    i = np.searchsorted(t, target)
    assert t[i] == target, (date, t[i])
    return i

i0 = tindex("1992-01-01")
print("index of 1992-01-01:", i0, "of", len(t))

# test read speed: 200 consecutive timesteps, region subset
lat_idx = slice(322, 382)
lon_idx = slice(485, 545)
tt = slice(i0, i0+200)
s0 = time.time()
block = ds.analysed_sst.isel(time=tt, latitude=lat_idx, longitude=lon_idx).values
t1 = time.time()
print("shape:", block.shape, "dtype:", block.dtype)
print("finite frac:", np.isfinite(block).mean())
print("min/max finite:", np.nanmin(block), np.nanmax(block))
print("read 200 timesteps in %.2f s" % (t1-s0))
