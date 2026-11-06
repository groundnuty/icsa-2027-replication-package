
import numpy as np, pickle
M = np.load('/work/work/M.npy')
active = np.load('/work/work/active.npy')
with open('/work/work/dates.pkl','rb') as f: D = pickle.load(f)
target_dates, sea = D['target'], D['sea']
dates = {t.isoformat(): k for k, t in enumerate(target_dates)}

print("active on 2014-07-18:", active[dates['2014-07-18']], " 2014-07-19:", active[dates['2014-07-19']],
      " 2014-08-20:", active[dates['2014-08-20']], " 2014-08-21:", active[dates['2014-08-21']])
# cells active on onset
k = dates['2014-07-19']
print("cells in MHW on onset day:", int(M[k].sum()), "of", len(sea))
# active day sequence
seq = [(t.isoformat(), int(active[i])) for i,t in enumerate(target_dates)]
print("first/last active:", [t for t,a in seq if a][0], [t for t,a in seq if a][-1])

# spot check hotspot for cell 0 on 2014-07-19
S_t = np.load('/work/work/S_t.npy'); TH_s = np.load('/work/work/TH_s.npy')
ml = [31,29,31,30,31,30,31,31,30,31,30,31]
leap_cum = np.zeros(13, int)
for m in range(12): leap_cum[m+1] = leap_cum[m] + ml[m]
def doy(dt): return int(leap_cum[dt.month-1] + dt.day)
i0, j0 = sea[0]
for dstr in ['2014-07-18','2014-07-19','2014-07-20']:
    k = dates[dstr]
    d = doy(target_dates[k])
    print(dstr, "doy", d, "SST:", S_t[k, i0, j0], "thr:", TH_s[d-1, 0], "hot:", S_t[k, i0, j0] >= TH_s[d-1, 0])
