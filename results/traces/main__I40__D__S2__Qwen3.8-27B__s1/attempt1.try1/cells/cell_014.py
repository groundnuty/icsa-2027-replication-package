import numpy as np, xarray as xr, hashlib
ds = xr.open_dataset('/work/sst_s2.nc', engine="h5netcdf")
v = ds['analysed_sst']
t = ds['time'].values
def idx(d): return int((t == np.datetime64(d))[0])
il = np.arange(404, 464); io = np.arange(559, 619)

# scan 1982..1992 yearly (July 15 and Jan 15) to find when field changes
prev = None
for y in range(1982, 1995):
    for mmdd in ['01-15','07-15']:
        d = f"{y}-{mmdd}"
        a = np.ascontiguousarray(v.isel(time=idx(d), latitude=il, longitude=io).values, dtype=np.float64)
        h = hashlib.md5(a.tobytes()).hexdigest()
        print(d, h, "CHANGED" if prev and h != prev else "")
        prev = h
ds.close()
