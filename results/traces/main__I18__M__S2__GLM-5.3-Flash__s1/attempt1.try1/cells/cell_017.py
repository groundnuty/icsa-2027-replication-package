import numpy as np

hot = np.load("/tmp/hot.npy"); sea = np.load("/tmp/sea.npy")
T = hot.shape[0]
hot_cells = hot.reshape(T, -1)[:, sea.reshape(-1)]
nsea = hot_cells.shape[1]

def runs_of(seq):
    runs = []; t = 0; L = len(seq)
    while t < L:
        if seq[t]:
            u = t
            while u+1 < L and seq[u+1]: u += 1
            runs.append([t, u]); t = u+1
        else:
            t += 1
    return runs

def detect_A(seq):
    """runs>=5 are MHWs; join MHWs separated by 1-2 non-hot days; gap days belong."""
    mhw_runs = [r for r in runs_of(seq) if r[1]-r[0]+1 >= 5]
    merged = []
    for r in mhw_runs:
        if merged and r[0]-merged[-1][1]-1 <= 2:
            merged[-1][1] = r[1]
        else:
            merged.append(list(r))
    out = np.zeros(len(seq), bool)
    for s, e in merged: out[s:e+1] = True
    return out

def detect_A_indep(seq):
    """Independent rewrite: boundaries via diff, filter, merge."""
    seq = np.asarray(seq, bool)
    T = len(seq)
    d = np.diff(np.concatenate([[0], seq.view(np.int8), [0]]))
    starts = np.flatnonzero(d == 1); ends = np.flatnonzero(d == -1) - 1
    keep = (ends - starts + 1) >= 5
    starts, ends = starts[keep], ends[keep]
    out = np.zeros(T, bool)
    if len(starts):
        cur_s, cur_e = starts[0], ends[0]
        for s, e in zip(starts[1:], ends[1:]):
            if s - cur_e <= 3:   # gap = s-cur_e-1 <= 2
                cur_e = e
            else:
                out[cur_s:cur_e+1] = True; cur_s, cur_e = s, e
        out[cur_s:cur_e+1] = True
    return out

mhw_cells = np.zeros((T, nsea), bool)
for n in range(nsea):
    a = detect_A(hot_cells[:, n])
    b = detect_A_indep(hot_cells[:, n])
    assert np.array_equal(a, b), n
    mhw_cells[:, n] = a
print("OK: both A-implementations agree on all cells")
print("mhw sea-cell-days:", mhw_cells.sum(), "of", T*nsea)
active = mhw_cells.any(axis=1)
print("active days:", active.sum(), "of", T)
print("active:", "".join("1" if x else "0" for x in active))

# --- verification of smoothing and percentile (independent routes) ---
thr_raw = np.load("/tmp/thr_raw.npy"); thr = np.load("/tmp/thr.npy")
c = (30, 30)
# check 1: smoothed doy150 (idx149) == mean raw 135..165
manual = thr_raw[135:166, c[0], c[1]].mean()
print("thr[149] vs manual mean raw135..165:", thr[149, 30, 30], manual, abs(thr[149,30,30]-manual) < 1e-9)
# check 2: wrap: smoothed idx0 == mean raw 351..365 + 0..15
manual0 = np.concatenate([thr_raw[351:366, 30, 30], thr_raw[0:16, 30, 30]]).mean()
print("thr[0] vs manual wrapped mean:", thr[0, 30, 30], manual0, abs(thr[0,30,30]-manual0) < 1e-9)
# check 3: day-60 rule pre-smoothing
print("raw day60 == mean(raw59,raw61):", np.allclose(thr_raw[59], 0.5*(thr_raw[58]+thr_raw[60])))

# check 4: manual Hazen percentile on one pool (cell 30,30, doy 200)
base = np.load("/tmp/base.npy"); bt = np.load("/tmp/base_times.npy")
import datetime as dt
EPOCH = np.datetime64("1970-01-01")
bdates = EPOCH + bt.astype("timedelta64[D]")
def doy366(dates):
    years = dates.astype("datetime64[Y]").astype(int) + 1970
    doy_std = (dates - (years-1970).astype("datetime64[Y]")).astype(int) + 1
    leap = (years % 4 == 0) & ((years % 100 != 0) | (years % 400 == 0))
    return np.where(leap | (doy_std < 60), doy_std, doy_std + 1)
doy_b = doy366(bdates)
d = 200
members = bt[(bdates >= np.datetime64("1992-01-01")) & (bdates <= np.datetime64("2002-12-31")) & (doy_b == d)]
pool_days = np.concatenate([np.arange(m-5, m+6) for m in members])
pool = base[np.isin(bt, pool_days)][:, 30, 30]
vals = np.sort(pool[~np.isnan(pool)])
n = len(vals)
h = (n-1)*0.9
lo, hi = int(np.floor(h)), int(np.ceil(h))
manual_q = vals[lo] + (h-lo)*(vals[hi]-vals[lo]) if hi > lo else vals[lo]
print("pool size doy200 cell30,30:", n, " manual hazen:", manual_q, " stored:", thr_raw[d-1, 30, 30], abs(manual_q-thr_raw[d-1,30,30])<1e-9)

np.save("/tmp/mhw_final.npy", mhw_cells); np.save("/tmp/active_final.npy", active)
# events
tt = np.load("/tmp/tgt_times.npy")
tdates = (EPOCH + tt.astype("timedelta64[D]")).astype(str)
idx = np.flatnonzero(active)
evs = []
s = idx[0]; prev = idx[0]
for i in idx[1:]:
    if i != prev+1:
        evs.append((s, prev)); s = i
    prev = i
evs.append((s, prev))
events = [{"onset": str(tdates[a]), "end": str(tdates[b])} for a, b in evs]
import json; print(json.dumps(events))
np.save("/tmp/events_final.npy", np.array(evs))
