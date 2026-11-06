import h5py, numpy as np, time, datetime as dt, os

BASE="/data/icsa2027_data_20261101T090944Z/s1z"

# region indices (recompute from first file to be safe)
f = h5py.File(f"{BASE}/sst_20080601.nc","r")
lat = f["latitude"][:]; lon = f["longitude"][:]
tcoord = f["time"][:]
f.close()
li = np.where((lat>=56.63)&(lat<=57.83))[0]
lo = np.where((lon>=20.23)&(lon<=21.43))[0]
print("lat idx", li.min(), li.max(), li.size, "lon idx", lo.min(), lo.max(), lo.size)
np.save("/tmp/li.npy", li); np.save("/tmp/lo.npy", lo)
np.save("/tmp/lat.npy", lat[li]); np.save("/tmp/lon.npy", lon[lo])
print("tcoord dtype", tcoord.dtype, tcoord[:2])

def date_list(a, b):
    a=dt.date.fromisoformat(a); b=dt.date.fromisoformat(b)
    return [a+dt.timedelta(i) for i in range((b-a).days+1)]

base_days = date_list("1991-12-27","2003-01-05")
tgt_days  = date_list("2008-06-01","2008-08-31")
all_days  = base_days + tgt_days
print(len(base_days), len(tgt_days), len(all_days))
np.save("/tmp/days.npy", np.array([d.strftime("%Y%m%d") for d in all_days]))

def load_batch(daystrs, start_row, out):
    t0=time.time()
    li=np.load("/tmp/li.npy"); lo=np.load("/tmp/lo.npy")
    for i,ds in enumerate(daystrs):
        fn=f"{BASE}/sst_{ds}.nc"
        with h5py.File(fn,"r") as f:
            x = f["analysed_sst"][0, li.min():li.max()+1, lo.min():lo.max()+1]
        out[start_row+i] = np.asarray(x, dtype=np.float64)
        if i and i%250==0:
            print(f"  {i}/{len(daystrs)}  {time.time()-t0:.0f}s", flush=True)
    print(f"batch done {len(daystrs)} files in {time.time()-t0:.0f}s")

N=len(all_days)
out=np.zeros((N,60,60), dtype=np.float64)
BATCH=400
for s in range(0, N, BATCH):
    dstrs=[d.strftime("%Y%m%d") for d in all_days[s:s+BATCH]]
    load_batch(dstrs, s, out)
np.save("/tmp/Xall.npy", out)
print("saved Xall", out.shape, out.nbytes/1e6, "MB")
print("finite frac overall", np.isfinite(out).mean())
