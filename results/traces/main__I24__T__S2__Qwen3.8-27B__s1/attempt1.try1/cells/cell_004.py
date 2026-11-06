import fsspec, xarray as xr, numpy as np, time, os
t0 = time.time()
fs = fsspec.filesystem('onedata')
p = "icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
f = fs.open(p, "rb")
ds = xr.open_dataset(f, engine="h5netcdf")

lat_idx = np.arange(204, 264)
lon_idx = np.arange(63, 123)

sel = dict(latitude=ds.latitude[lat_idx], longitude=ds.longitude[lon_idx])

tb = ds.analysed_sst.sel(time=slice("1991-12-27","2003-01-05"), **sel).load()
print("baseline read", time.time()-t0, "shape", tb.shape, tb.dims)
tt = ds.analysed_sst.sel(time=slice("2004-06-01","2004-08-31"), **sel).load()
print("target read", time.time()-t0, "shape", tt.shape)

tb2 = tb.assign_coords(time=tb.time)
sub = xr.Dataset({
    "analysed_sst": ("time", "latitude", "longitude", np.concatenate([tb.values, tt.values], axis=0)),
}, coords={
    "time": np.concatenate([tb.time.values, tt.time.values]),
    "latitude": tb.latitude.values,
    "longitude": tb.longitude.values,
})
sub.analysed_sst.attrs["units"] = "kelvin"
os.makedirs("/tmp/mhw", exist_ok=True)
sub.to_netcdf("/tmp/mhw/subset.nc")
print("saved", time.time()-t0, "total days:", sub.sizes["time"])
# sanity: check dates
print("first", sub.time.values[0], "last", sub.time.values[-1])
# check contiguity of the two segments
seg1 = sub.time[:4028].values
seg2 = sub.time[4028:].values
print("seg1 days:", len(seg1), "seg2 days:", len(seg2))
d1 = np.diff(seg1).astype("timedelta64[D]")
print("seg1 non-daily diffs:", (d1 != np.timedelta64(1,"D")).sum())
d2 = np.diff(seg2).astype("timedelta64[D]")
print("seg2 non-daily diffs:", (d2 != np.timedelta64(1,"D")).sum())
ds.close(); f.close()
