import xarray as xr
import numpy as np, time

path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')
t = ds.time.values
print("t[3647]=", t[3647], "t[7674]=", t[7674], "t[11109]=", t[11109], "t[11200]=", t[11200])

SLAT = slice(438, 498)   # 62.26..63.44
SLON = slice(487, 547)   # 18.74..19.92

def read_block(t0, t1, tag):
    s = time.time()
    a = ds.analysed_sst.isel(time=slice(t0, t1+1), latitude=SLAT, longitude=SLON).values
    a = np.ascontiguousarray(a, dtype=np.float64)
    print(f"{tag}: {a.shape} {a.nbytes/1e6:.1f} MB in {time.time()-s:.1f}s finite {np.isfinite(a).mean():.4f}", flush=True)
    return a

chunks = []
for a0 in range(3647, 7675, 400):
    a1 = min(a0 + 399, 7674)
    chunks.append(read_block(a0, a1, f"baseline {t[a0]}..{t[a1]}"))
base = np.concatenate(chunks, axis=0)
np.save('/tmp/base.npy', base)
print("baseline saved:", base.shape, "first date idx 3647, count", base.shape[0])

target = read_block(11109, 11200, "target")
np.save('/tmp/target.npy', target)

np.save('/tmp/lat.npy', ds.latitude.values)
np.save('/tmp/lon.npy', ds.longitude.values)
np.save('/tmp/time_all.npy', t)
ds.close()
print("done")
