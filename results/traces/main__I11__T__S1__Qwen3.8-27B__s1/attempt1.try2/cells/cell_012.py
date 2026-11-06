
import io, os, pickle, time
import fsspec, xarray as xr, numpy as np
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base='/icsa2027_data_20261101T090944Z/s1z/'
dates = pickle.load(open("/work/dates.pkl","rb"))
all_days = sorted(set(dates["baseline_win"]) | set(dates["target"]))

def load(s):
    out = f"/work/reg/{s}.npy"
    if os.path.exists(out) and os.path.getsize(out) > 1000:
        return (s, "skip")
    p = base + "sst_" + s.replace("-","") + ".nc"
    try:
        with fs.open(p, "rb") as f:
            ds = xr.open_dataset(f, engine="h5netcdf")
            a = ds["analysed_sst"].values
            tv = ds["time"].values[0]
            ds.close()
        reg = np.ascontiguousarray(a[0, 109:169, 373:433]).astype(np.float64)
        buf = io.BytesIO(); np.save(buf, reg)
        tmp = out + ".tmp"
        with open(tmp,"wb") as g: g.write(buf.getvalue())
        os.replace(tmp, out)
        return (s, "ok" if np.datetime64(tv) == np.datetime64(s+"T00:00:00") else f"TIME-MISMATCH:{tv}")
    except Exception as e:
        return (s, f"ERR:{type(e).__name__}:{str(e)[:80]}")

t0 = time.time()
n_ok = n_skip = 0
problems = []
with ThreadPoolExecutor(max_workers=24) as ex:
    futs = [ex.submit(load, s) for s in all_days]
    for i, fu in enumerate(futs):
        s, st = fu.result()
        if st in ("ok","skip"):
            if st=="ok": n_ok+=1
            else: n_skip+=1
        else:
            problems.append((s,st))
        if (i+1) % 500 == 0:
            print(f"{i+1}/{len(all_days)} ok={n_ok} skip={n_skip} problems={len(problems)} elapsed={time.time()-t0:.0f}s")
print("DONE ok=",n_ok,"skip=",n_skip,"total problems",len(problems), problems[:5])
pickle.dump({"problems":problems}, open("/work/dlstatus.pkl","wb"))
