import os, shutil, numpy as np, fsspec, xarray as xr, json

print("cwd:", os.getcwd())
du = shutil.disk_usage(os.getcwd())
print("disk free GB:", round(du.free/1e9, 2))

fs = fsspec.filesystem('onedata')
path = "icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
f = fs.open(path, "rb")
ds = xr.open_dataset(f, engine="h5netcdf")
t = ds.time.values
print("t0 t1:", t[0], t[-1], t.size)
# continuity check
assert np.all(np.diff(t) == np.timedelta64(1, "D")), "time not continuous"
print("time continuous daily: OK")

def idx_of(datestr):
    d = np.datetime64(datestr)
    i = int((d - t[0]) / np.timedelta64(1, "D"))
    assert t[i] == d, (i, t[i], d)
    return i

for s in ["1991-12-27","1991-12-31","1992-01-01","2002-12-31","2003-01-01","2003-01-05",
          "2004-06-01","2004-08-31","1992-02-29","2004-02-29","2001-03-01"]:
    print(s, "->", idx_of(s))

lat = ds.latitude.values; lon = ds.longitude.values
la = lat.astype('float64'); lo = lon.astype('float64')
lat_idx = np.where((la >= 57.57) & (la <= 58.77))[0]
lon_idx = np.where((lo >= 10.25) & (lo <= 11.45))[0]
print("lat cells:", lat_idx.size, lon cells if False else "lon cells:", lon_idx.size)
print("lat range:", lat[lat_idx[0]], lat[lat_idx[-1]], " lon range:", lon[lon_idx[0]], lon[lon_idx[-1]])

ext_i0, ext_i1 = idx_of("1991-12-27"), idx_of("2003-01-05")
tgt_i0, tgt_i1 = idx_of("2004-06-01"), idx_of("2004-08-31")
print("ext indices:", ext_i0, ext_i1, "days:", ext_i1-ext_i0+1)
print("tgt indices:", tgt_i0, tgt_i1, "days:", tgt_i1-tgt_i0+1)

np.savez("/tmp/idxmeta.npz", lat_idx=lat_idx, lon_idx=lon_idx,
         ext=np.array([ext_i0, ext_i1]), tgt=np.array([tgt_i0, tgt_i1]))
print("saved idxmeta")
