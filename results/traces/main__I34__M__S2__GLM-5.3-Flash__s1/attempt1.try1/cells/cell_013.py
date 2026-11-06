import numpy as np, pandas as pd, json

maskA = np.load("work/maskA.npy"); maskB = np.load("work/maskB.npy")
sea = np.load("work/sea.npy")
z = np.load("work/data.npz")
targ = z["targ"].astype(np.float64)
targ_dates = pd.DatetimeIndex(z["targ_dates"].astype(str))
c = np.load("work/clim.npz")
thr_s = c["thr_s"]; targ_doy = c["targ_doy"]
thr_t = thr_s[targ_doy - 1]
hot = np.zeros(targ.shape, dtype=bool)
hot[:, sea] = targ[:, sea] >= thr_t[:, sea]
nt = targ.shape[0]

# ---- independent re-implementation of variant A (different algorithm) ----
def detect_A_alt(h, min_run=5, max_gap=2):
    n = len(h)
    # label hot runs
    runs = []
    i = 0
    while i < n:
        if h[i]:
            j = i
            while j + 1 < n and h[j+1]: j += 1
            runs.append([i, j]); i = j + 1
        else: i += 1
    mhw = [r for r in runs if r[1]-r[0]+1 >= min_run]
    if not mhw: return []
    # iteratively join MHWs with gap <= max_gap (repeat until stable)
    while True:
        merged = False
        for k in range(len(mhw)-1):
            if mhw[k+1][0] - mhw[k][1] - 1 <= max_gap:
                mhw[k] = [mhw[k][0], mhw[k+1][1]]
                del mhw[k+1]; merged = True; break
        if not merged: break
    return [tuple(r) for r in mhw]

def mask_from(h, evs):
    m = np.zeros(len(h), dtype=bool)
    for s, e in evs: m[s:e+1] = True
    return m

ok = True
for i in range(60):
    for j in range(60):
        if not sea[i, j]: continue
        e1 = detect_A_alt(hot[:, i, j])
        m1 = mask_from(hot[:, i, j], e1)
        m2 = maskA[:, i, j].astype(bool)
        if not np.array_equal(m1, m2):
            ok = False; print("MISMATCH", i, j)
print("variant A mask reproduced by independent implementation:", ok)

# ---- structural checks on maskA ----
viol = 0
for i in range(60):
    for j in range(60):
        if not sea[i, j]:
            if maskA[:, i, j].any(): viol += 1
            continue
        m = maskA[:, i, j].astype(bool); h = hot[:, i, j]
        # every mask run must contain >=5 hot days OR be an internal gap (then its enclosing run has >=5 hot on each side)
        runs = []
        k = 0
        while k < nt:
            if m[k]:
                l = k
                while l+1 < nt and m[l+1]: l += 1
                runs.append((k, l)); k = l+1
            else: k += 1
        for s, e in runs:
            if h[s:e+1].sum() < 5: viol += 1
print("structural violations:", viol)
print("mask cell-days:", int(maskA.sum()), "| variant B cell-days:", int(maskB.sum()))

# ---- regional events (variant A) ----
active = maskA.reshape(nt, -1).max(axis=1).astype(bool)
evs = []
k = 0
while k < nt:
    if active[k]:
        l = k
        while l+1 < nt and active[l+1]: l += 1
        evs.append((k, l)); k = l+1
    else: k += 1
print("regional events (variant A):")
for s, e in evs:
    print("  ", targ_dates[s].date(), "->", targ_dates[e].date(), f"({e-s+1} days)")
# for comparison: variant B regional events
activeB = maskB.reshape(nt, -1).max(axis=1).astype(bool)
evsB = []
k = 0
while k < nt:
    if activeB[k]:
        l = k
        while l+1 < nt and activeB[l+1]: l += 1
        evsB.append((k, l)); k = l+1
    else: k += 1
print("regional events (variant B, for comparison):")
for s, e in evsB:
    print("  ", targ_dates[s].date(), "->", targ_dates[e].date(), f"({e-s+1} days)")
print("active days A:", int(active.sum()), "| B:", int(activeB.sum()))
