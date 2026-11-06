import numpy as np, json, datetime as dt
OUT="/tmp/mhw"
tgt = np.load(f"{OUT}/tgt.npy").reshape(92, 3600)
thr_s = np.load(f"{OUT}/thr_s.npy")
clim_s = np.load(f"{OUT}/clim_s.npy")
sea = np.load(f"{OUT}/sea.npy")
D_tgt = np.load(f"{OUT}/D_tgt.npy")
dates = json.load(open(f"{OUT}/dates.json"))
tgt_dates = [dt.date.fromisoformat(s) for s in dates["tgt_dates"]]
hot = (tgt >= thr_s[D_tgt]) & sea[None,:]

margin = tgt - thr_s[D_tgt]
margin[:, ~sea] = np.nan
anom = tgt - clim_s[D_tgt]
anom[:, ~sea] = np.nan
print("day            nhot  max_margin  mean_anom")
for i in range(0, 92, 2):
    print(tgt_dates[i].isoformat(), f"{int(hot[i].sum()):5d} {np.nanmax(margin[i]):+8.3f} {np.nanmean(anom[i]):+8.3f}")
