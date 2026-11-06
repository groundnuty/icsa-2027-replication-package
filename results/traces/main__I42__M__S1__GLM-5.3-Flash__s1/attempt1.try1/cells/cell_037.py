import numpy as np
from datetime import date, timedelta

sst_t = np.load("/work/sst_target.npy")
thr_s = np.load("/work/thr_smooth2.npy")
mhw = np.load("/work/mhw_final.npy")
MD_CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
target_dates = []
d = date(2012,6,1)
while d <= date(2012,8,31):
    target_dates.append(d); d += timedelta(days=1)
doys = np.array([MD_CUM[t.month-1]+t.day for t in target_dates])

for (ii,jj) in [(55,56),(56,53),(57,59)]:
    m = mhw[:,ii,jj]
    if m.any():
        idx = np.where(m)[0]
        a, b = idx[0], idx[-1]
        print(f"cell({ii},{jj}): MHW {target_dates[a]} .. {target_dates[b]}")
        for k in range(a, b+1):
            print(f"   {target_dates[k]}: sst={sst_t[k,ii,jj]:.3f} K  thr={thr_s[doys[k]-1,ii,jj]:.3f} K  diff={sst_t[k,ii,jj]-thr_s[doys[k]-1,ii,jj]:+.3f}")
