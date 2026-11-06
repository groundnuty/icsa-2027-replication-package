import numpy as np, pandas as pd, os, warnings

d = np.load("work/coords.npz")
lat, lon = d['lat'], d['lon']
t_base = pd.to_datetime(d['t_base'])   # 1991-12-27 .. 2003-01-05 (4028 days)
t_tgt  = pd.to_datetime(d['t_tgt'])    # 2005-06-01 .. 2005-08-31 (92 days)

# --- day-of-year mapping by (month, day), leap-aligned: Feb29->60, Mar1->61 always
def doy_convention(ts):
    doy = ts.dayofyear.copy()          # natural
    leap = ts.is_leap_year
    # for non-leap years, dates Mar 1..Dec 31 shift +1 (natural 60..365 -> 61..366)
    after_feb = (ts.month > 2)
    doy = np.where(leap | ~after_feb, doy, doy + 1)
    return doy

db = doy_convention(t_base); dt_ = doy_convention(t_tgt)
print("check doys: 1992-02-28=%d 1992-02-29=%d 1992-03-01=%d 1993-02-28=%d 1993-03-01=%d 1993-12-31=%d 1992-12-31=%d" % (
    db[np.where(t_base==pd.Timestamp("1992-02-28"))[0][0]],
    db[np.where(t_base==pd.Timestamp("1992-02-29"))[0][0]],
    db[np.where(t_base==pd.Timestamp("1992-03-01"))[0][0]],
    db[np.where(t_base==pd.Timestamp("1993-02-28"))[0][0]],
    db[np.where(t_base==pd.Timestamp("1993-03-01"))[0][0]],
    db[np.where(t_base==pd.Timestamp("1993-12-31"))[0][0]],
    db[np.where(t_base==pd.Timestamp("1992-12-31"))[0][0]]))
print("unique target doys:", dt_.min(), dt_.max(), "n unique", len(np.unique(dt_)))

# --- pools: for each core baseline date Y (1992-01-01..2002-12-31), its +-5 calendar days enter pool(doy(Y))
win_dates = t_base
core = (win_dates >= pd.Timestamp("1992-01-01")) & (win_dates <= pd.Timestamp("2002-12-31"))
core_idx = np.where(core)[0]
print("window n=%d core n=%d core first=%s last=%s" % (len(win_dates), core_idx.size,
      str(win_dates[core_idx[0]].date()), str(win_dates[core_idx[-1]].date())))

pools = {dd: [] for dd in range(1, 367)}
for j in core_idx:
    dj = db[j]
    for k in range(j-5, j+6):
        assert 0 <= k < len(win_dates), (j, k)
        pools[dj].append(k)
lens = np.array([len(pools[dd]) for dd in range(1, 367)])
print("pool lengths: min=%d max=%d ; doy60 len=%d" % (lens.min(), lens.max(), len(pools[60])))
print("doy1 pool date range:", str(win_dates[pools[1][0]].date()), "..", str(win_dates[pools[1][-1]].date()), "n=", len(pools[1]))
print("doy366 pool date range:", str(win_dates[pools[366][0]].date()), "..", str(win_dates[pools[366][-1]].date()), "n=", len(pools[366]))
# 29 Feb values must appear in pools of neighbouring doys (e.g. 55..65) 
i229 = np.where(t_base == pd.Timestamp("1992-02-29"))[0][0]
in_pools = [dd for dd in range(1,367) if i229 in pools[dd]]
print("1992-02-29 appears in pools:", in_pools)
np.save("work/pools_check.npy", np.array([0]))
import pickle
with open("work/pools.pkl","wb") as fh: pickle.dump(pools, fh)
print("pools saved")
