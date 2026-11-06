import numpy as np, xarray as xr, hashlib
ds = xr.open_dataset('/work/sst_s2.nc', engine="h5netcdf")
v = ds['analysed_sst']
print("FULL COMMENT:", repr(ds.attrs.get('comment')))
t = ds['time'].values
def idx(d): return int((t == np.datetime64(d))[0])
il = np.arange(404, 464); io = np.arange(559, 619)
dates = ['1982-01-01','1990-06-01','1995-01-15','1996-07-01','2000-01-01','2003-01-05','2009-07-01','2015-07-01','2023-12-31']
hashes = {}
for d in dates:
    a = np.ascontiguousarray(v.isel(time=idx(d), latitude=il, longitude=io).values, dtype=np.float64)
    h = hashlib.md5(a.tobytes()).hexdigest()
    hashes[d] = h
    print(d, h)
print("all equal:", len(set(hashes.values())) == 1)

# one cell across years
ic, io_ = 430, 590
col = v.isel(latitude=ic, longitude=io_).values
print("cell (430,590) across all years, unique values:", np.unique(col[np.isfinite(col)])[:20])
print("n finite over 42y:", np.isfinite(col).sum(), "of", col.size)
ds.close()
