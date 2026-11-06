import os, time, datetime as dt, numpy as np
from concurrent.futures import ProcessPoolExecutor

D = "/data/icsa2027_data_20261101T090944Z/s1z"
LA0, LA1, LO0, LO1 = 132, 192, 436, 496

def read_one(fn):
    import xarray as xr, datetime as dtf, numpy as np
    ds = xr.open_dataset(os.path.join(D, fn), engine="h5netcdf")
    v = ds["analysed_sst"].isel(time=0, latitude=slice(LA0, LA1), longitude=slice(LO0, LO1)).values.astype(np.float32)
    t = ds["time"].values[0]
    ds.close()
    expect = np.datetime64(dtf.datetime.strptime(fn[4:12], "%Y%m%d"), "ns")
    return v, bool(t != expect)

if __name__ == "__main__":
    ext_dates = [dt.date(1991,12,27) + dt.timedelta(days=i) for i in range((dt.date(2003,1,5)-dt.date(1991,12,27)).days+1)]
    tgt_dates = [dt.date(2015,6,1) + dt.timedelta(days=i) for i in range((dt.date(2015,8,31)-dt.date(2015,6,1)).days+1)]
    all_dates = ext_dates + tgt_dates
    fns = [f"sst_{c:%Y%m%d}.nc" for c in all_dates]
    print("files to read:", len(fns), "ext:", len(ext_dates), "tgt:", len(tgt_dates))
    t0 = time.time()
    vals, bads = [], []
    with ProcessPoolExecutor(max_workers=16) as ex:
        for i, (v, b) in enumerate(ex.map(read_one, fns, chunksize=4)):
            vals.append(v); bads.append(b)
            if (i+1) % 500 == 0: print(f"  {i+1}/{len(fns)}  {time.time()-t0:.0f}s", flush=True)
    arr = np.stack(vals)
    print("read done: %.1f s, shape %s" % (time.time()-t0, arr.shape), "time mismatches:", sum(bads))
    ext = arr[:len(ext_dates)]; tgt = arr[len(ext_dates):]
    print("ext finite frac: %.4f" % np.isfinite(ext).mean())
    print("tgt finite frac: %.4f" % np.isfinite(tgt).mean())
    sea = np.all(np.isfinite(tgt), axis=0)
    print("sea cells (finite on every target day):", int(sea.sum()), "of", sea.size)
    np.savez_compressed("/work/cache_sst.npz",
                        ext=ext, tgt=tgt,
                        ext_ord=np.array([c.toordinal() for c in ext_dates], dtype=np.int32),
                        tgt_ord=np.array([c.toordinal() for c in tgt_dates], dtype=np.int32))
    print("cached to /work/cache_sst.npz, size:", os.path.getsize("/work/cache_sst.npz")/1e6, "MB")
