
import numpy as np, datetime
thr_s = np.load('work/thr_smooth.npy')
S_tgt = np.load('work/S_tgt.npy')
lat = np.load('work/lat.npy'); lon = np.load('work/lon.npy')
N = 3600; T = 92
sea = np.load('work/sea.npy')
t0 = datetime.date(2017,6,1)
tgt_dates = [t0 + datetime.timedelta(days=i) for i in range(T)]
# explicit correct mapping: days-before-month table keyed by month
dbm = {1:0, 2:31, 3:60, 4:91, 5:121, 6:152, 7:182, 8:213, 9:244, 10:274, 11:305, 12:335}
doy_t = np.array([dbm[d.month] + d.day for d in tgt_dates])
print("doy checks: Jun1", int(doy_t[0]), "Jun30", int(doy_t[29]), "Jul15", int(doy_t[44]), "Jul31", int(doy_t[60]), "Aug1", int(doy_t[61]), "Aug31", int(doy_t[91]))
S64 = S_tgt.astype(np.float64).reshape(T, N)
print("day | doy | maxSST(sea) | maxThr(doy,sea) | nHot | maxSST-thr over cells")
for i in range(0, 92, 6):
    doy = doy_t[i]
    ms = S64[i][sea].max(); mt = thr_s[doy-1][sea].max()
    nh = int((S64[i][sea] >= thr_s[doy-1][sea]).sum())
    mx = (S64[i][sea] - thr_s[doy-1][sea]).max()
    print(f"{tgt_dates[i]} | {doy} | {ms:.2f} | {mt:.2f} | {nh} | {mx:.2f}")
# also: max over sea of (SST - thr) per day, full resolution
diff = S64 - thr_s[doy_t]  # (92, N)
md = diff[sea[None, :]].max(axis=1)
print("max anomaly per day (first 20):", [(str(tgt_dates[i])[:10], round(float(md[i]),2)) for i in range(20)])
neg = md < 0
print("days with max anomaly < 0:", [str(tgt_dates[i]) for i in np.where(neg)[0]][:30])
