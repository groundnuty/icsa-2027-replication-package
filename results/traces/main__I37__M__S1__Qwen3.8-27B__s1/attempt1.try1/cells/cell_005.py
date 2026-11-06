import xarray as xr, time, numpy as np
base = "/data/icsa2027_data_20261101T090944Z/s1z"
ts = time.time()
n = 20
lat0, lat1, lon0, lon1 = 60.09, 61.29, 20.01, 21.21
tot = 0.0
for i in range(n):
    # sample some dates from the needed ranges
    ymd = ["19911227","19920101","19950615","20000229","20021231","20030105",
           "20120601","20120701","20120831","19930301"][i % 10]
    p = f"{base}/sst_{ymd}.nc"
    t0 = time.time()
    ds = xr.open_dataset(p, engine="h5netcdf", decode_times=False)
    a = ds['analysed_sst'].sel(latitude=slice(lat0, lat1), longitude=slice(lon0, lon1)).values
    tot += time.time() - t0
    ds.close()
print(f"n={n}, total {tot:.2f}s, per file {tot/n*1000:.1f} ms")
print("sample shape", a.shape, a.dtype)
print("nan count in region (2012-07-01 file):", np.isnan(a).sum(), "of", a.size)
