import numpy as np
thr_sm = np.load('/work/thr_sm.npy'); clim_sm = np.load('/work/clim_sm.npy')
doys = np.load('/work/doys.npy'); sea = np.load('/work/sea.npy')
V_tgt = np.load('/work/V_tgt.npy').astype(np.float64).reshape(92, 3600)

# threshold vs climatology for target doys
t90 = thr_sm[doys-1]; cl = clim_sm[doys-1]
print("thr range:", np.nanmin(t90), np.nanmax(t90), " clim range:", np.nanmin(cl), np.nanmax(cl))
print("fraction thr > clim:", (t90 > cl).mean())
# how much above climatology (K)
print("thr-clim: min %.2f med %.2f max %.2f" % (np.nanmin(t90-cl), np.nanmedian(t90-cl), np.nanmax(t90-cl)))
# SST vs threshold: fraction of hot days
hot = V_tgt >= t90
print("overall hot fraction:", hot[sea].mean() if False else hot[:, sea].mean())
# per-day hot cell counts
hc = hot.sum(axis=1)
print("per-day hot cells min/max:", hc.min(), hc.max())
# threshold NaN count (should be 0 for sea cells)
print("thr NaN in target window (all cells):", np.isnan(t90).sum(), "sea cells:", np.isnan(t90[:, sea]).sum())
