import numpy as np, pickle

sst = np.load("/tmp/mhw_work/sst.npy").astype("float64")
targ_pos = np.load("/tmp/mhw_work/targ_pos.npy")
thresh = np.load("/tmp/mhw_work/thresh.npy")
clim = np.load("/tmp/mhw_work/clim.npy")
meta = pickle.load(open("/tmp/mhw_work/meta.pkl", "rb"))
target_md = meta["target_md"]
MDAYS = [31,29,31,30,31,30,31,31,30,31,30,31]
CUM = [0]
for nd in MDAYS: CUM.append(CUM[-1]+nd)
targ_doy = np.array([CUM[m-1]+d for (m, d) in target_md])

sst_t = sst[targ_pos]
thr_t = thresh[targ_doy-1]
clim_t = clim[targ_doy-1]

sea = np.isfinite(sst_t).all(axis=0)
print("sea cells:", sea.sum())
print("target SST over sea: mean %.3f min %.3f max %.3f" % (np.nanmean(sst_t[:,sea]), np.nanmin(sst_t[:,sea]), np.nanmax(sst_t[:,sea])))
print("threshold over sea:  mean %.3f min %.3f max %.3f" % (np.nanmean(thr_t[:,sea]), np.nanmin(thr_t[:,sea]), np.nanmax(thr_t[:,sea])))
print("clim over sea:       mean %.3f" % np.nanmean(clim_t[:,sea]))
print("SST - threshold, sea: mean %.3f, max %.3f, p99 %.3f" % (np.nanmean((sst_t-thr_t)[:,sea]), np.nanmax((sst_t-thr_t)[:,sea]), np.nanpercentile((sst_t-thr_t)[:,sea], 99)))
print("SST - clim, sea:      mean %.3f, min %.3f, max %.3f" % (np.nanmean((sst_t-clim_t)[:,sea]), np.nanmin((sst_t-clim_t)[:,sea]), np.nanmax((sst_t-clim_t)[:,sea])))

# per-day regional means
for t in [0, 10, 30, 50, 70, 91]:
    m, d = target_md[t]
    print("2004-%02d-%02d: SST regional mean %.2f, thresh mean %.2f, clim mean %.2f" %
          (m, d, np.nanmean(sst_t[t][sea]), np.nanmean(thr_t[t][sea]), np.nanmean(clim_t[t][sea])))

# same cell as before (28,59) time series
i, j = 28, 59
print("\ncell (28,59): first 12 days: SST vs threshold vs clim")
for t in range(12):
    m, d = target_md[t]
    print("  2004-%02d-%02d  SST %.2f  thr %.2f  clim %.2f" % (m, d, sst_t[t,i,j], thr_t[t,i,j], clim_t[t,i,j]))
