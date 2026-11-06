import numpy as np, pickle

sst = np.load("/tmp/mhw_work/sst.npy").astype("float64")
targ_pos = np.load("/tmp/mhw_work/targ_pos.npy")
thresh = np.load("/tmp/mhw_work/thresh.npy")
meta = pickle.load(open("/tmp/mhw_work/meta.pkl", "rb"))
target_md = meta["target_md"]
lat_vals, lon_vals = meta["lat_vals"], meta["lon_vals"]
MDAYS = [31,29,31,30,31,30,31,31,30,31,30,31]
CUM = [0]
for nd in MDAYS: CUM.append(CUM[-1]+nd)
targ_doy = np.array([CUM[m-1]+d for (m, d) in target_md])
sst_t = sst[targ_pos]; thr_t = thresh[targ_doy-1]
hot = np.where(np.isfinite(sst_t) & np.isfinite(thr_t), sst_t >= thr_t, False)
idx = np.argwhere(hot)
print("hot cell-days:", len(idx))
for t, i, j in idx:
    m, d = target_md[t]
    print(f"  2004-{m:02d}-{d:02d} cell lat={lat_vals[i]:.2f} lon={lon_vals[j]:.2f}: SST {sst_t[t,i,j]:.3f} vs thr {thr_t[t,i,j]:.3f} (+{sst_t[t,i,j]-thr_t[t,i,j]:.3f})")

# max anomaly per day (over sea), to show robustness
sea = np.isfinite(sst_t).all(axis=0)
anom = np.where(sea[None,:,:], sst_t - thr_t, np.nan)
mx = np.nanmax(anom.reshape(92, -1), axis=1)
print("\nmax cell anomaly per day: overall max %.3f K, days with any positive: %d" % (np.nanmax(mx), int((mx > 0).sum())))
print("daily max anomalies (every 10th day):", np.round(mx[::10], 3))
