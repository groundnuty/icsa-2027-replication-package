import xarray as xr, numpy as np, time, json

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
t = ds.time.values

def tindex(date):
    target = np.datetime64(date)
    i = int(np.searchsorted(t, target))
    assert t[i] == target, (date, t[i])
    return i

lat_idx = slice(322, 382)   # 59.94..61.12
lon_idx = slice(485, 545)   # 18.70..19.88

ranges = [
    ("part1", "1991-12-27", "1996-12-31"),
    ("part2", "1997-01-01", "2003-01-05"),
    ("part3", "2009-06-01", "2009-08-31"),
]
meta = {}
for name, d0, d1 in ranges:
    i0, i1 = tindex(d0), tindex(d1)
    n = i1 - i0 + 1
    dates = t[i0:i1+1]
    meta[name] = {"start": str(d0), "end": str(d1), "n": n, "i0": int(i0), "i1": int(i1)}
    s = time.time()
    # read in blocks of 300 to keep individual reads moderate
    chunks = []
    blk = 300
    for s_ in range(0, n, blk):
        e = min(s_ + blk, n)
        arr = ds.analysed_sst.isel(time=slice(i0+s_, i0+e), latitude=lat_idx, longitude=lon_idx).values
        chunks.append(arr)
    full = np.concatenate(chunks, axis=0).astype(np.float64)
    np.save(f"/tmp/{name}.npy", full)
    print(name, "shape:", full.shape, "saved in %.1f s" % (time.time()-s), "finite frac:", round(float(np.isfinite(full).mean()),4), flush=True)

json.dump(meta, open("/tmp/meta.json","w"), indent=1)
ds.close()
print("done")
