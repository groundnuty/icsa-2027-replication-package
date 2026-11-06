import xarray as xr, numpy as np, os, time
from concurrent.futures import ThreadPoolExecutor
base = "/data/icsa2027_data_20261101T090944Z/s1z"
from datetime import date, timedelta
dates = []
cur = date(1992,3,1)
while cur <= date(1992,3,20):
    dates.append(cur); cur += timedelta(days=1)
files = [os.path.join(base,f"sst_{d.strftime('%Y%m%d')}.nc") for d in dates]

def read_one(p):
    ds = xr.open_dataset(p, engine="h5netcdf")
    v = ds["analysed_sst"].values.astype("float64")
    ds.close()
    return v

t0=time.time()
with ThreadPoolExecutor(max_workers=8) as ex:
    out = list(ex.map(read_one, files))
dt = time.time()-t0
print("19 files with 8 workers:", round(dt,2), "s; first shape", out[0].shape)
