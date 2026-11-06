import os, time, xarray as xr, numpy as np, datetime as dt
from concurrent.futures import ProcessPoolExecutor

D = "/data/icsa2027_data_20261101T090944Z/s1z"

def read_one(fn):
    ds = xr.open_dataset(os.path.join(D, fn), engine="h5netcdf")
    v = ds["analysed_sst"].isel(time=0, latitude=slice(132,192), longitude=slice(436,496)).values.astype(np.float32)
    ds.close()
    return v

if __name__ == "__main__":
    fns = [f"sst_{c:%Y%m%d}.nc" for c in [dt.date(1992,1,1)+dt.timedelta(days=i) for i in range(30)]]
    for nw in [4, 8]:
        t0 = time.time()
        with ProcessPoolExecutor(max_workers=nw) as ex:
            res = list(ex.map(read_one, fns, chunksize=1))
        arr = np.array(res)
        print(f"workers={nw}: 30 files in {time.time()-t0:.2f}s, shape {arr.shape}")
