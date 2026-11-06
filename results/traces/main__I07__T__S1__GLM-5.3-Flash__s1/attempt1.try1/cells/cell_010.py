import fsspec, numpy as np, time, datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
import h5py
ILA, ILA2, ILO, ILO2 = 48, 107, 353, 413

def read_one(dstr):
    p = f"{base}/sst_{dstr}.nc"
    for attempt in range(4):
        try:
            with fs.open(p,'rb') as f:
                with h5py.File(f,'r') as h:
                    arr = h['analysed_sst'][0, ILA:ILA2+1, ILO:ILO2+1]
                    t = h['time'][0]
            return dstr, arr, t
        except Exception as ex:
            if attempt==3: return dstr, None, str(ex)[:100]
            time.sleep(0.5*(attempt+1))

d0 = dt.date(2021,6,1)
test = [(d0+dt.timedelta(days=i)).strftime('%Y%m%d') for i in range(64)]
t0=time.time()
res={}
with ThreadPoolExecutor(8) as ex:
    futs = [ex.submit(read_one, s) for s in test]
    for fu in as_completed(futs):
        dstr, arr, t = fu.result()
        res[dstr]=arr
print("64 files threaded-8:", round(time.time()-t0,2),"s; fails:", sum(1 for v in res.values() if v is None))
