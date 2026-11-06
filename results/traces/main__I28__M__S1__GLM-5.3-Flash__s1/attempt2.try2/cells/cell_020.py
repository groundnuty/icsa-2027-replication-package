script = r'''
import numpy as np, datetime as dt, os
work = "/work"
thr_s = np.load(work+"/thr_s.npy"); tf = np.load(work+"/target_finite.npy")
blocks = sorted(os.listdir(work+"/cache"))
parts = [np.load(work+"/cache/"+b, mmap_mode="r") for b in blocks]
data32 = np.concatenate(parts, axis=0)
start = dt.date(1991,12,27)
dates = [start + dt.timedelta(days=i) for i in range(data32.shape[0])]

def isleap(y): return y%4==0 and (y%100!=0 or y%400==0)
pools = {}
for d in range(1,367):
    if d == 60: continue
    wins = set()
    for y in range(1992,2003):
        if d == 366 and not isleap(y): continue
        B = dt.date(y,1,1)+dt.timedelta(days=d-1)
        for o in range(-5,6): wins.add(B+dt.timedelta(days=o))
    pools[d] = sorted(wins)

# hazen check vs np.quantile on real pools (sample)
rng = np.random.default_rng(7)
ok = True
for _ in range(20):
    d = int(rng.choice([x for x in range(1,367) if x != 60]))
    r, c = rng.integers(0,60), rng.integers(0,60)
    if not tf[r,c]: continue
    idx = [(x-start).days for x in pools[d]]
    v = np.asarray(data32[idx, r, c], np.float64)
    a = np.sort(v[np.isfinite(v)])
    n = a.size; h = (n-1)*0.9+1; lo, hi = int(np.floor(h)), int(np.ceil(h))
    ref = a[lo-1] + (h-lo)*(a[hi-1]-a[lo-1])
    npq = np.quantile(v, 0.9, method="hazen")
    if not (np.isclose(ref, npq, rtol=0, atol=1e-10) and np.isclose(npq, thr_s[d-1, r, c], rtol=0, atol=1e-9)):
        ok = False; print("mismatch", d, r, c, ref, npq, thr_s[d-1,r,c])
print("hazen == np.quantile(hazen) == pipeline on 20 samples:", ok)
# MATLAB toy check: quantile([1..5],0.9) = 4.6 in MATLAB
toy = np.arange(1,6.0)
print("toy quantile 0.9 (expect 4.6):", np.quantile(toy, 0.9, method="hazen"))
del parts, data32

# was the region hot on days just before 2013-06-01? (informational caveat check)
parts = [np.load(work+"/cache/"+b, mmap_mode="r") for b in blocks]
data32 = np.concatenate(parts, axis=0)
ti0 = dates.index(dt.date(2013,6,1))
tdoy = [dates[ti0-k].timetuple().tm_yday for k in range(1,8)]
for k, dy in enumerate(tdoy, 1):
    i = ti0 - k
    sst = np.asarray(data32[i], np.float64)
    hot = np.greater_equal(sst, thr_s[dy-1]) & tf
    print("2013-%02d-%02d hot cells (would-be):" % (dates[i].month, dates[i].day), int(hot.sum()))
'''
open("/work/check2.py","w").write(script)
import subprocess
r = subprocess.run(["python","/work/check2.py"], capture_output=True, text=True, timeout=3600)
print(r.stdout); print("STDERR:", r.stderr[-1500:]); print("rc:", r.returncode)
