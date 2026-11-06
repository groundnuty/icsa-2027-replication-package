script = r'''
import os, h5py, numpy as np, datetime as dt, time
from multiprocessing import Pool

base = "/data/icsa2027_data_20261101T090944Z/s1z"
work = "/work"
LAT0, LAT1, LON0, LON1 = 218, 278, 601, 661  # region slices

start = dt.date(1991,12,27); end = dt.date(2013,8,31)
ndays = (end-start).days+1
dates = [start+dt.timedelta(days=i) for i in range(ndays)]
NPB = 128
nb = (ndays + NPB - 1)//NPB
print("ndays:", ndays, "blocks:", nb)

def process_block(b):
    lo = b*NPB; hi = min(ndays, lo+NPB)
    out = np.full((hi-lo, 60, 60), np.nan, np.float32)
    for k in range(hi-lo):
        d = dates[lo+k]
        p = os.path.join(base, "sst_"+d.strftime("%Y%m%d")+".nc")
        for attempt in range(4):
            try:
                with h5py.File(p, "r") as f:
                    out[k] = f["analysed_sst"][0, LAT0:LAT1, LON0:LON1]
                break
            except Exception as e:
                if attempt == 3:
                    print("FAILED", d, repr(e), flush=True)
                else:
                    time.sleep(1+attempt)
    return b, out

if __name__ == "__main__":
    t0 = time.time()
    with Pool(16) as pool:
        for b, arr in pool.imap_unordered(process_block, range(nb)):
            np.save(os.path.join(work, "cache", "block_%02d.npy" % b), arr)
            print("block %02d done, elapsed %.1fs" % (b, time.time()-t0), flush=True)
    print("ALL DONE %.1fs" % (time.time()-t0))
'''
with open("extract.py", "w") as f:
    f.write(script)
print("written")
import subprocess
r = subprocess.run(["python", "extract.py"], capture_output=True, text=True, timeout=7200)
print(r.stdout[-3000:])
print("STDERR:", r.stderr[-2000:])
print("rc:", r.returncode)
