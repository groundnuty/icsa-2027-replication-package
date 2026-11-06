import os, time, json, datetime as dt
import h5py, numpy as np
from concurrent.futures import ProcessPoolExecutor

D = "/data/icsa2027_data_20261101T090944Z/s1z"
I0,I1,J0,J1 = 196,256,485,545
OUT = "/tmp/mhw"
os.makedirs(OUT, exist_ok=True)

def rng(a,b):
    t=a
    while t<=b:
        yield t
        t+=dt.timedelta(days=1)

ext_dates = list(rng(dt.date(1991,12,27), dt.date(2003,1,5)))
tgt_dates = list(rng(dt.date(2013,6,1), dt.date(2013,8,31)))
print("ext days:", len(ext_dates), ext_dates[0], ext_dates[-1])
print("tgt days:", len(tgt_dates), tgt_dates[0], tgt_dates[-1])

def work(s):
    with h5py.File(f"{D}/sst_{s}.nc","r") as f:
        return s, f["analysed_sst"][0, I0:I1, J0:J1][:].astype(np.float64)

def load(dates):
    keys = [d.strftime("%Y%m%d") for d in dates]
    t0=time.time()
    out = {}
    with ProcessPoolExecutor(max_workers=16) as ex:
        for k,v in ex.map(work, keys, chunksize=16):
            out[k]=v
    arr = np.array([out[k] for k in keys], dtype=np.float64)
    print(f"loaded {len(keys)} files in {time.time()-t0:.1f}s shape={arr.shape}")
    return arr

ext = load(ext_dates)
tgt = load(tgt_dates)
np.save(f"{OUT}/ext.npy", ext)
np.save(f"{OUT}/tgt.npy", tgt)
json.dump({"ext_dates":[d.isoformat() for d in ext_dates],
           "tgt_dates":[d.isoformat() for d in tgt_dates]}, open(f"{OUT}/dates.json","w"))

# coords from one file
with h5py.File(f"{D}/sst_20130601.nc","r") as f:
    lat = f["latitude"][:].astype(np.float64); lon = f["longitude"][:].astype(np.float64)
    latf = f["latitude"][:]; lonf = f["longitude"][:]
np.save(f"{OUT}/lat.npy", lat[I0:I1]); np.save(f"{OUT}/lon.npy", lon[J0:J1])
np.save(f"{OUT}/lat_f32.npy", latf[I0:I1].astype(np.float32))
np.save(f"{OUT}/lon_f32.npy", lonf[J0:J1].astype(np.float32))
print("saved. lat range", lat[I0], lat[I1-1], "lon range", lon[J0], lon[J1-1])
print("ext finite fraction:", np.isfinite(ext).mean(), "tgt finite fraction:", np.isfinite(tgt).mean())
