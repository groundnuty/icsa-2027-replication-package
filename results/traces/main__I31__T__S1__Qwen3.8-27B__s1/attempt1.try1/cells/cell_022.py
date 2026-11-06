
import numpy as np, datetime
thr_s = np.load('work/thr_smooth.npy')
thr_raw = np.load('work/thr_raw.npy')
S_tgt = np.load('work/S_tgt.npy')
lat = np.load('work/lat.npy'); lon = np.load('work/lon.npy')
N = 3600; T = 92
sea = np.load('work/sea.npy')
t0 = datetime.date(2017,6,1)
tgt_dates = [t0 + datetime.timedelta(days=i) for i in range(T)]
mday = [31,29,31,30,31,30,31,31,30,31,30,31]
cp = np.concatenate([[0], np.cumsum(mday)[:-1]])
doy_t = cp[[d.month for d in tgt_dates]] + np.array([d.day for d in tgt_dates])

S64 = S_tgt.astype(np.float64).reshape(T, N)
H = (S64 >= thr_s[doy_t]) & sea[None, :]
hot_per_day = H.sum(axis=1)
print("hot per day, every 6th day:")
for i in range(0, 92, 6):
    print(" ", tgt_dates[i], int(hot_per_day[i]))
i = tgt_dates.index(datetime.date(2017,7,15))
print("Jul15 idx:", i, "doy:", int(doy_t[i]))
cs = np.where(sea)[0]
c = int(cs[1000])
ci = np.unravel_index(c, (60,60))
print("cell", c, "lat,lon:", lat[ci], lon[ci])
print("  SST Jul15 (K):", float(S_tgt[i, ci]))
print("  thr_raw doy197:", float(thr_raw[196, c]), " thr_smooth doy197:", float(thr_s[196, c]))
print("  max SST Jul15 sea:", float(S64[i][sea].max()), " thr smooth doy197 max sea:", float(thr_s[196][sea].max()))
print("  sea cells SST>=thr Jul15:", int((S64[i][sea] >= thr_s[196][sea]).sum()))
nd = np.where(hot_per_day > 0)[0]
print("days with hot days:", [int(x) for x in nd])
for di in nd[:10]:
    print("  day", int(di), tgt_dates[di], "nhot:", int(hot_per_day[di]))
