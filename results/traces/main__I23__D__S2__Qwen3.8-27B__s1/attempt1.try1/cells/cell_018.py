import numpy as np
import pickle

with open('/work/thr.pkl','rb') as f:
    T = pickle.load(f)
thr_raw, sea2, doy_tgt, V_tgt = T['thr'], T['sea2'], T['doy_tgt'], T['V_tgt']
# NOTE: thr here is unsmoothed, doy60 still NaN (fill not yet applied in this file)
thr_raw[60] = 0.5*(thr_raw[59] + thr_raw[61])

SST = V_tgt.reshape(92, 3600)[:, sea2].T      # (K, 92)
thr_day = thr_raw[doy_tgt].T                  # (K, 92) raw per-day threshold
diff = SST - thr_day
print("raw: mean diff %.3f K, median %.3f K, frac >= 0: %.4f" %
      (np.nanmean(diff), np.nanmedian(diff), (diff >= 0).mean()))

# smoothed
from numpy.lib.stride_tricks import sliding_window_view
def smooth366(A):
    B = A[1:].T
    pad = np.concatenate([B[:, -15:], B, B[:, :15]], axis=1)
    S = sliding_window_view(pad, 31, axis=1).mean(axis=2)
    return np.vstack([np.zeros((1, B.shape[0])), S.T])
thr_s = smooth366(thr_raw)
thr_day_s = thr_s[doy_tgt].T
diff_s = SST - thr_day_s
print("smoothed: mean diff %.3f K, median %.3f K, frac >= 0: %.4f" %
      (np.nanmean(diff_s), np.nanmedian(diff_s), (diff_s >= 0).mean()))

# look at one cell in detail
c = 0
lat_vals = None
print("\ncell0: lat/lon?", end=" ")
cidx = np.flatnonzero(sea2)[0]
lati, loni = np.unravel_index(cidx, (60,60))
print((57.42+0.02*lati), (18.70+0.02*loni))
print("doy range", doy_tgt.min(), doy_tgt.max())
print("SST  june 5..15:", np.round(SST[c, 4:15], 2))
print("thr_s june 5..15:", np.round(thr_day_s[c, 4:15], 2))
print("thr_raw june 5..15:", np.round(thr_day[c, 4:15], 2))

# yearly context: mean SST over target vs threshold curve
print("\nmean SST over period (sea cells):", SST.mean(axis=0).mean(),
      "| smoothed thr over period:", thr_day_s.mean(axis=0).mean())

# per-day hot fraction (smoothed)
hf = (diff_s >= 0).mean(axis=0)
print("per-day hot frac min/max: %.3f / %.3f" % (hf.min(), hf.max()))
print("top hot days:", [(str(np.datetime64(T['time_tgt'][i], 'D')), round(hf[i],3)) for i in np.argsort(hf)[-8:]])
