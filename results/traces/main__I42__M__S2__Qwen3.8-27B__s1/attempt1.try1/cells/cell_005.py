import xarray as xr
import numpy as np, time, sys

path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')
v = ds.analysed_sst

def t(tag, fn):
    s = time.time()
    r = fn()
    dt = time.time() - s
    mb = r.nbytes/1e6
    print(f"{tag}: {mb:.2f} MB in {dt:.2f}s -> {mb/max(dt,1e-9):.2f} MB/s; finite {np.isfinite(r).sum()}/{r.size}", flush=True)
    return r

# one day, region only via isel
a = t("region 1 day", lambda: v.isel(time=slice(3647,3648), latitude=slice(438,498), longitude=slice(487,547)).values)
# 10 days region
b = t("region 10 days", lambda: v.isel(time=slice(3647,3657), latitude=slice(438,498), longitude=slice(487,547)).values)
# one full day plane via isel
c = t("full plane 1 day", lambda: v.isel(time=slice(3647,3648)).values)
ds.close()
