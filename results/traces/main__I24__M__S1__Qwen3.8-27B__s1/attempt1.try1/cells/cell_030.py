import numpy as np, datetime as dt, os, time, json
t0 = time.time()
OUT = "/work/mhw"

z = np.load(f"{OUT}/results1.npz")
thr_s = z["thr_s"]; clim_s = z["clim_s"]
sea_r = z["sea_r"].astype(int); sea_c = z["sea_c"].astype(int)
nsea = len(sea_r)
tgt_dates = [dt.datetime.fromisoformat(x.astype(str)) for x in z["tgt_dates"]]

tgt = np.load(f"{OUT}/tgt_0000_0092.npy")  # (92,60,60)
mlen = [31,29,31,30,31,30,31,31,30,31,30,31]
mcum = [0] + list(np.cumsum(mlen))
def doy(d): return mcum[d.month-1] + d.day
doy_t = np.array([doy(d.date()) for d in tgt_dates])
print("target doys:", doy_t.min(), doy_t.max())

T = tgt[:, sea_r, sea_c]                    # (92, nsea)
thr_t = thr_s[doy_t - 1]                    # (92, nsea)
assert np.isfinite(T).all(), "sea cell with non-finite target SST!"
hot = T >= thr_t                            # (92, nsea)
print("hot fraction:", hot.mean())

# ---- per-cell MHW: runs >=5, merge gaps <=2 ----
mcell = np.zeros((92, nsea), dtype=np.uint8)
n_mhw_events = 0
for c in range(nsea):
    h = hot[:, c].view(np.int8)
    d = np.diff(np.concatenate(([0], h, [0])))
    st = np.flatnonzero(d == 1)
    en = np.flatnonzero(d == -1) - 1
    keep = (en - st + 1) >= 5
    st, en = st[keep], en[keep]
    ms, me = [], []
    for s, e in zip(st, en):
        if ms and s - me[-1] - 1 <= 2:
            me[-1] = e
        else:
            ms.append(int(s)); me.append(int(e))
    for s, e in zip(ms, me):
        mcell[s:e+1, c] = 1
    n_mhw_events += len(ms)
print("total per-cell MHWs:", n_mhw_events, "cells with >=1 MHW:", (mcell.sum(axis=0)>0).sum())

# ---- regional events ----
active = mcell.any(axis=1)
d = np.diff(np.concatenate(([0], active.view(np.int8), [0])))
ev_st = np.flatnonzero(d == 1)
ev_en = np.flatnonzero(d == -1) - 1
events = [(tgt_dates[s].date().isoformat(), tgt_dates[e].date().isoformat(), e-s+1) for s, e in zip(ev_st, ev_en)]
print("active days:", int(active.sum()), "of 92")
for e in events:
    print("event:", e[0], "->", e[1], "len", e[2])

np.savez(f"{OUT}/results2.npz", mcell=mcell,
         ev_st=ev_st.astype(int), ev_en=ev_en.astype(int),
         active=active)
print("elapsed %.1fs" % (time.time()-t0))
