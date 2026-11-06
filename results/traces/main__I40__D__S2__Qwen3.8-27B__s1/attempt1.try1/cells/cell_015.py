import numpy as np, xarray as xr, hashlib
ds = xr.open_dataset('/work/sst_s2.nc', engine="h5netcdf")
v = ds['analysed_sst']
t = ds['time'].values

def hash_slice(tidx, slat=None, slon=None):
    a = v.isel(time=tidx,
               latitude=slat if slat is not None else slice(None),
               longitude=slon if slon is not None else slice(None)).values
    a = np.ascontiguousarray(a, dtype=np.float64)
    return hashlib.md5(a.tobytes()).hexdigest()

dates = np.linspace(0, len(t)-1, 20).astype(int)
print("whole-field hashes at 20 spaced indices:")
prev=None
for i in dates:
    h = hash_slice(i)
    print(i, t[i], h, "CHANGED" if prev and h!=prev else "")
    prev=h

# central Baltic region
latc = slice(300, 340); lonc = slice(300, 340)
print("\ncentral Baltic subregion:")
prev=None
for d in ['1992-01-01','1992-07-01','1996-01-01','1996-07-01','2000-07-01','2009-07-01']:
    i = int((t == np.datetime64(d))[0])
    h = hash_slice(i, latc, lonc)
    print(d, h, "CHANGED" if prev and h!=prev else "")
    prev=h

# a single central-baltic cell over first 400 days
cell = v.isel(latitude=320, longitude=320).values[:400]
u = np.unique(cell)
print("\ncell(320,320) first 400 days: n_unique =", len(u), u[:15])
ds.close()
