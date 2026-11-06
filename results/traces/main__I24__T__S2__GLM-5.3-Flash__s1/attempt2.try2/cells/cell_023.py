import numpy as np, pickle, json, datetime as dt, os
from numpy.lib.stride_tricks import sliding_window_view

ext = np.load("/work/ext64.npy")           # (4028,60,60) float64
tgt = np.load("/work/tgt64.npy")           # (92,60,60) float64
thresh_raw = np.load("/work/thresh_raw.npy")  # (366,60,60)
clim_raw = np.load("/work/clim_raw.npy")
sea = np.load("/work/sea.npy")
with open("/work/masks.pkl","rb") as fh: masks = pickle.load(fh)
with open("/work/dates_ext_tgt.pkl","rb") as fh: dd = pickle.load(fh)
ext_dates, tgt_dates = dd["ext_dates"], dd["tgt_dates"]

# check: no sea cell has any NaN in the extended baseline window
n_any_nan = int((~np.isfinite(ext)).sum(axis=0).astype(bool).sum())
print("cells with >=1 NaN in ext window:", n_any_nan, "(expect 296 land only)")

def doy_of(d64):
    d = d64.astype("datetime64[D]").item()
    y = d.year
    yd = d.timetuple().tm_yday
    leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    if not leap and yd >= 60:
        yd += 1
    return yd

# --- day 60 fill ---
for arr in (thresh_raw, clim_raw):
    arr[59] = 0.5 * (arr[58] + arr[60])
print("day60 fill done; thresh d59,d60,d61 at cell[10,10]:",
      np.round(thresh_raw[58:61, 10, 10], 5))

# --- circular 31-day centred moving mean ---
def circ_smooth31(a):
    # a: (366, ...) -> centred 31-day mean, wrap mod 366
    pad = np.concatenate([a[-15:], a, a[:15]], axis=0)
    win = sliding_window_view(pad, 31, axis=0)   # (366, ..., 31)
    return win.mean(axis=-1)

thresh_s = circ_smooth31(thresh_raw)
clim_s = circ_smooth31(clim_raw)
print("smoothed shapes:", thresh_s.shape, clim_s.shape)
# spot check: smoothing at day 150 = mean raw 135..165
manual = thresh_raw[134:166, 10, 10].mean()
print("check smooth d150 cell[10,10]:", thresh_s[149,10,10], "vs manual:", manual, "diff:", abs(thresh_s[149,10,10]-manual))
print("clim_s sample (cell[10,10], d150..d156):", np.round(clim_s[149:156,10,10],4))
print("thresh_s range over sea cells: min/max:",
      float(np.nanmin(thresh_s)), float(np.nanmax(thresh_s)))
print("clim_s range over sea cells: min/max:",
      float(np.nanmin(clim_s)), float(np.nanmax(clim_s)))

# --- hot mask on target period ---
doys = np.array([doy_of(d) for d in tgt_dates])
print("target doys first/last:", doys[0], doys[-1], "unique count:", np.unique(doys).size)
thr_t = thresh_s[doys - 1]          # (92,60,60)
hot = np.greater_equal(tgt, thr_t, where=np.isfinite(tgt), out=np.zeros_like(tgt, dtype=bool))
hot = tgt >= thr_t                   # NaN >= NaN -> False; simpler and correct
hot &= np.isfinite(tgt)
print("hot days total:", int(hot.sum()), "of", hot.size, " per-day hot counts min/max:",
      int(hot.sum(axis=(1,2)).min()), int(hot.sum(axis=(1,2)).max()))
np.save("/work/thresh_s.npy", thresh_s)
np.save("/work/clim_s.npy", clim_s)
np.save("/work/hot.npy", hot)
print("stage C part 1 done")
