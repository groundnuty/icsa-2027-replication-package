import os, numpy as np, time
p = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
print("cwd:", os.getcwd())
st = os.stat(p)
print("file size GB:", st.st_size/1e9)

# quantile check: hazen == Hyndman-Fan type 5
def hazen_manual(x, q):
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    h = q*n + 0.5  # 1-based virtual index (type 5)
    lo = int(np.floor(h)); hi = int(np.ceil(h))
    lo = min(max(lo,1),n); hi = min(max(hi,1),n)
    g = h - np.floor(h)
    return x[lo-1] + g*(x[hi-1]-x[lo-1])
rng = np.random.default_rng(0)
x = rng.normal(size=37)
print("hazen match:", np.isclose(np.quantile(x,0.9,method="hazen"), hazen_manual(x,0.9)))
print("nanquantile hazen ok:", np.nanquantile(np.array([1.,2.,np.nan,4.]),0.9,method="hazen"))

import importlib
for m in ["netCDF4","h5netcdf","scipy","numba"]:
    try:
        importlib.import_module(m); print(m,"available")
    except Exception as e: print(m,"NO")

# timing test: read 5 days of region
import h5py
t0=time.time()
f = h5py.File(p,"r")
d = f["analysed_sst"]
r = d[1000:1005, 182:242, 690:750]
t1=time.time()
print("5 days region read:", round(t1-t0,2),"s; shape",r.shape,"nan frac:", float(np.isnan(r).mean()))
r2 = d[2000:2010, 182:242, 690:750]
t2=time.time()
print("10 more days:", round(t2-t1,2),"s")
f.close()
