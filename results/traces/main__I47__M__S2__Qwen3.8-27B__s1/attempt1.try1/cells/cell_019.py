import numpy as np, pandas as pd, json

m = np.load("work/mhw.npz")
mhw = m["mhw"]; tgt_dates = m["tgt_dates"].astype("datetime64[D]"); active = m["active"]
st = np.load("work/stats.npz")
z = np.load("work/sst.npz", allow_pickle=False)
tgt64 = z["tgt_arr"].astype(np.float64).reshape(z["tgt_arr"].shape[0], -1)
sea_idx = st["sea_idx"]
thr_s = st["thr_s"]

# --- (b) manual hazen check on one pool ---
win_idx = np.load("work/win_idx.npy", allow_pickle=True).item()
base64 = z["base_arr"].astype(np.float64").reshape(z["base_arr"].shape[0], -1)
# note: float64' typo would fail; do it right
base64 = z["base_arr"].astype(np.float64).reshape(z["base_arr"].shape[0], -1)
c = sea_idx[0]
P = base64[win_idx[153]][:, c]
x = np.sort(P)
n = len(x)
i = n * 0.9 + 0.5            # Hazen: p = (i - 0.5)/n  =>  i = n p + 0.5 (1-based)
lo = int(np.floor(i)) - 1
frac = i - np.floor(i)
manual = x[lo] + frac * (x[lo + 1] - x[lo])
npval = np.quantile(P, 0.9, method="hazen")
print("hazen manual:", manual, "numpy:", npval, "match:", np.isclose(manual, npval))
print("thr_s[0, 152] (doy153 smoothed) vs raw thr[0,152]:", st["thr_s"][0, 152], st["thr"][0, 152])

# --- (a) independent MHW detection (pandas-based, different code path) ---
td = pd.DatetimeIndex(tgt_dates.astype("datetime64[ns]"))
cum = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 366])
tgt_doy = cum[(td.month - 1).to_numpy()] + td.day.to_numpy()

def mhw_runs_independent(h):
    # h: 1-d bool array (time)
    # return list of (start,end) merged MHW intervals
    s = pd.Series(h.astype(int))
    grp = (s != s.shift()).cumsum()
    runs = []
    for g, sub in s.groupby(grp):
        if sub.iloc[0] == 1 and len(sub) >= 5:
            runs.append([sub.index[0], sub.index[-1]])
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] - 1 <= 2:
            merged[-1][1] = r[1]
        else:
            merged.append(list(r))
    return merged

n_sea = len(sea_idx)
mhw2 = np.zeros_like(mhw)
for c in range(n_sea):
    sst = tgt64[:, sea_idx[c]]
    hot = sst >= thr_s[c, tgt_doy - 1]
    for a, b in mhw_runs_independent(hot):
        mhw2[a:b+1, c] = 1
print("independent mask identical:", bool((mhw == mhw2).all()))

# active-day profile
prof = pd.Series(active, index=[str(d) for d in tgt_dates])
print(prof[prof].groupby(prof.index.str[:7]).sum())
# per-event cell participation
ev = json.load(open("work/events.json"))
for s, e in ev:
    i0 = list(map(str, tgt_dates)).index(s)
    i1 = list(map(str, tgt_dates)).index(e)
    sub = mhw[i0:i1+1]
    print(f"event {s}..{e}: {i1-i0+1} days, mean cells in MHW {sub.mean(axis=1).round(1)}")
    print("   first/last day cells:", sub[0].sum(), sub[-1].sum())
