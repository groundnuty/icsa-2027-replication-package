import fsspec, numpy as np, time, datetime as dt, json, re
from concurrent.futures import ThreadPoolExecutor, as_completed
import h5py
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
ILA, ILA2, ILO, ILO2 = 48, 107, 353, 413

# inspect time attrs once
with fs.open(f"{base}/sst_19920101.nc",'rb') as f:
    with h5py.File(f,'r') as h:
        print("time attrs:", dict(h['time'].attrs))
        print("time val:", h['time'][0], h['time'].dtype)
        print("sst dims:", h['analysed_sst'].dims)

def dates_range(a,b):
    d=a; out=[]
    while d<=b: out.append(d); d+=dt.timedelta(days=1)
    return out

need = dates_range(dt.date(1991,12,27), dt.date(2003,1,5)) + dates_range(dt.date(2021,6,1), dt.date(2021,8,31))
need_str = [d.strftime('%Y%m%d') for d in need]

def read_one(dstr):
    p = f"{base}/sst_{dstr}.nc"
    for attempt in range(5):
        try:
            with fs.open(p,'rb') as f:
                with h5py.File(f,'r') as h:
                    arr = h['analysed_sst'][0, ILA:ILA2+1, ILO:ILO2+1]
                    tattr = dict(h['time'].attrs)
            return dstr, np.asarray(arr, dtype=np.float32), tattr
        except Exception as ex:
            if attempt==4: return dstr, None, str(ex)[:150]
            time.sleep(0.5*(attempt+1))

t0=time.time()
data = {}
meta_err = []
with ThreadPoolExecutor(8) as ex:
    futs = [ex.submit(read_one, s) for s in need_str]
    done=0
    for fu in as_completed(futs):
        dstr, arr, tattr = fu.result()
        done+=1
        if arr is None:
            meta_err.append((dstr, tattr))
        else:
            data[dstr] = arr
        if done % 500 == 0: print(done, "files,", round(time.time()-t0,1), "s")
print("loaded:", len(data), "failed:", len(meta_err), "in", round(time.time()-t0,1), "s")
if meta_err: print(meta_err[:5])
np.save('/tmp/loaded_ok.npy', np.array([1]))
# stack in chronological order
T = len(need_str)
cube = np.empty((T, ILA2-ILA+1, ILO2-ILO+1), dtype=np.float32)
for i,s in enumerate(need_str):
    cube[i] = data[s]
np.savez_compressed('/tmp/region_cube.npz', dates=np.array(need_str), cube=cube)
print("cube shape:", cube.shape, "saved.")
# quick sanity
print("target finite frac:", np.isfinite(cube[-92:]).mean())
print("sample values:", cube[-1, 30, 30], cube[0, 30, 30])
