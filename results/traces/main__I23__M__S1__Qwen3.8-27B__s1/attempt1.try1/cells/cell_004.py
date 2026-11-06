import os, re
import h5py, numpy as np

d = "/data/icsa2027_data_20261101T090944Z/s1z"
p = d + "/sst_20130601.nc"
with h5py.File(p, "r") as f:
    print(list(f.keys()))
    print("vars:", {k: f[k].shape for k in f})
    lat = f["latitude"][:]
    lon = f["longitude"][:]
    print("lat", lat.dtype, lat.shape, lat[:5], lat[-5:])
    print("lon", lon.dtype, lon.shape, lon[:5], lon[-5:])
    v = f["analysed_sst"]
    print("sst", v.dtype, v.shape, v.attrs if hasattr(v,'attrs') else None)

# region mask
lat64 = lat.astype(np.float64); lon64 = lon.astype(np.float64)
lm = (lat64 >= 57.41-1e-9) & (lat64 <= 58.61+1e-9)
nm = (lon64 >= 18.69-1e-9) & (lon64 <= 19.89+1e-9)
li = np.flatnonzero(lm); ji = np.flatnonzero(nm)
print("lat idx", li.min(), li.max(), "n=", len(li), "vals:", lat64[li.min()], lat64[li.max()])
print("lon idx", ji.min(), ji.max(), "n=", len(ji), "vals:", lon64[ji.min()], lon64[ji.max()])

# check date coverage of files we need
import datetime as dt
def rng(a,b):
    t=a
    while t<=b:
        yield t.strftime("%Y%m%d")
        t+=dt.timedelta(days=1)
need = list(rng(dt.date(1991,12,27), dt.date(2003,1,5))) + list(rng(dt.date(2013,6,1), dt.date(2013,8,31)))
missing = [s for s in need if not os.path.exists(f"{d}/sst_{s}.nc")]
print("need", len(need), "missing:", missing[:20], len(missing))
files = set(x for x in os.listdir(d) if x.startswith("sst_") and x.endswith(".nc"))
dates = sorted(x[4:12] for x in files)
print("first", dates[0], "last", dates[-1], "total", len(dates))
# any gaps in overall range?
dset = set(dates)
all_dates = list(rng(dt.date(1982,1,1), dt.date(2026,11,1)))
gap = [s for s in all_dates if s not in dset and s >= dates[0]]
print("gaps:", gap[:10], len(gap))
