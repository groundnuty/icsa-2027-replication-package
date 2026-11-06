import numpy as np, datetime as dt
thr = np.load('/work/thr.npy'); sea = np.load('/work/sea.npy')
target_arr = np.load('/work/target_arr.npy'); doy_target = np.load('/work/doy_target.npy')
mhw = np.load('/work/mhw.npy')
Tt, N = target_arr.shape
dates = [dt.date(2009,6,1)+dt.timedelta(days=i) for i in range(Tt)]
ac = mhw.sum(axis=0)
for t in range(Tt):
    print(dates[t].isoformat(), f"doy={doy_target[t]:3d}", "active cells:", int(ac[t]), end="  ")
    if (t+1)%4==0: print()
print()
# sample cell trace: one with an MHW
c = np.where(sea & (mhw.sum(axis=1)>0))[0][100]
print("\ncell", c, "lat/lon idx:", c//60, c%60)
s = target_arr[:, c]
th = thr[c, doy_target]
for t in range(Tt):
    mark = "HOT" if s[t]>=th[t] else "   "
    print(f"{dates[t].isoformat()} sst={s[t]:7.2f} thr={th[t]:7.2f} mhw={mhw[c,t]} {mark}")
