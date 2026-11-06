script = r'''
import numpy as np, datetime as dt, os, json

work = "/work"
thr_s = np.load(work+"/thr_s.npy"); tf = np.load(work+"/target_finite.npy")
mhw = np.load(work+"/mhw_mask.npy")
data32 = np.concatenate([np.load(work+"/cache/"+b, mmap_mode="r") for b in sorted(os.listdir(work+"/cache"))], axis=0)
start = dt.date(1991,12,27)
dates = [start + dt.timedelta(days=i) for i in range(data32.shape[0])]
ti0 = dates.index(dt.date(2013,6,1))
june_cells = mhw[0].astype(bool)   # cells inside an MHW on 2013-06-01

print("Pre-period context (final thresholds), cells hot on:")
runs_end_may31 = 0
for k in range(10, 0, -1):
    i = ti0 - k
    d = dates[i]; dy = d.timetuple().tm_yday
    hot = np.greater_equal(np.asarray(data32[i], np.float64), thr_s[dy-1]) & tf
    print("  %s: %d" % (d, int(hot.sum())))
    if k <= 5:
        # consecutive-hot run ending May 31 among June-1 MHW cells?
        pass
# longest consecutive hot run ending 2013-05-31, restricted to June-1 MHW cells
hotseq = []
for k in range(7, 0, -1):
    i = ti0 - k; d = dates[i]; dy = d.timetuple().tm_yday
    hotseq.append(np.greater_equal(np.asarray(data32[i], np.float64), thr_s[dy-1]))
hot_jun1 = np.greater_equal(np.asarray(data32[ti0], np.float64), thr_s[151])
mask = june_cells
runlen = np.zeros((60,60), int)
for h in hotseq:            # May 25..31 order
    runlen = (runlen + 1) * h
print("cells in MHW on Jun 1 with >=5 consecutive hot days ending May 31:", int(((runlen >= 5) & mask & hot_jun1).sum()))
print("cells in MHW on Jun 1 hot on May 31:", int((hotseq[-1] & mask).sum()))
'''

open("/work/precontext.py","w").write(script)
import subprocess
r = subprocess.run(["python","/work/precontext.py"], capture_output=True, text=True, timeout=3600)
print(r.stdout); print("STDERR:", r.stderr[-800:]); print("rc:", r.returncode)
