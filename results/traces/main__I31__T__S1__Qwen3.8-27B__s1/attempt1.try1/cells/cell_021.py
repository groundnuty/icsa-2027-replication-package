
import numpy as np, datetime
thr_s = np.load('work/thr_smooth.npy')
thr_raw = np.load('work/thr_raw.npy')
S_tgt = np.load('work/S_tgt.npy')
N = 3600; T = 92
sea = np.load('work/sea.npy')
t0 = datetime.date(2017,6,1)
tgt_dates = [t0 + datetime.timedelta(days=i) for i in range(T)]

# per-day hot count with current H definition
H = (S_tgt.astype(np.float64).reshape(T, N) >= thr_s[doy_t:= (lambda mday=[31,29,31,30,31,30,31,31,30,31,30,31], cp=np.concatenate([[0], np.cumsum(mday)[:-1]]): cp[[d.month for d in tgt_dates]] + np.array([d.day for d in tgt_dates]) - 1 + np.array([d.day for d in tgt_dates]))())
# simpler: recompute properly
mday = [31,29,31,30,31,30,31,31,30,31,30,31]
cp = np.concatenate([[0], np.cumsum(mday)[:-1]])
doy_t = cp[[d.month for d in tgt_dates]] + np.array([d.day for d in tgt_dates])
H = (S_tgt.astype(np.float64).reshape(T, N) >= thr_s[doy_t]) & sea[None, :]
hot_per_day = H.sum(axis=1)
print("hot counts per day (Jun1..Aug31):")
for i in range(0, 92, 6):
    print(tgt_dates[i], int(hot_per_day[i]))
i = tgt_dates.index(datetime.date(2017,7,15))
print("Jul15 idx:", i, "doy:", doy_t[i])
c = int(np.where(sea)[0][1000])
print("cell", c, "lat/lon:", )
lat = np.load('work/lat.npy'); lon = np.load('work/lon.npy')
ci = np.unravel_index(c, (60,60))
print("  lat,lon:", lat[ci], lon[ci])
print("  SST Jul15 (K):", S_tgt[i, ci])
print("  thr_raw doy197:", thr_raw[196, c], " thr_smooth doy197:", thr_s[196, c])
print("  max SST over Jul15 sea cells:", float(S_tgt[i][sea].max()), " thr smooth doy197 max over sea:", float(thr_s[196][sea].max()))
print("  how many sea cells SST>=thr on Jul15:", int((S_tgt[i].reshape(N)[sea] >= thr_s[196][sea]).sum()))
# where are the hot days?
print("day indices with hot days:", np.where(hot_per_day > 0)[0][:40])
for di in np.where(hot_per_day > 0)[0][:8]:
    print("  day", di, tgt_dates[di], "nhot:", int(hot_per_day[di]))
