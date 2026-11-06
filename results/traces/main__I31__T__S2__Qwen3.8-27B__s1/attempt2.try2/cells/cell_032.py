import numpy as np
zc = np.load('/work/hot_correct.npz')
hot = zc['hot']; sea_flat = zc['sea_flat']
T = hot.shape[1]; C = hot.shape[0]
t_dates = zc['t_dates']

def true_runs(x):
    n = len(x)
    d = np.diff(x.astype(np.int8))
    s = np.where(d == 1)[0] + 1; e = np.where(d == -1)[0] + 1
    if x[0]: s = np.concatenate(([0], s))
    if x[-1]: e = np.concatenate((e, [n]))
    return s, e

# ALTERNATIVE interpretation: fill 1-2 day gaps between HOT days first, then >=5 rule, then merge 1-2 gaps between resulting MHWs
alt_mhw_days = 0; alt_cells = 0
alt_active = np.zeros(T, bool)
for c in range(C):
    if not sea_flat[c]: continue
    h = hot[c].copy()
    # fill gaps of 1-2 between hot days (single pass; gaps are maximal non-hot runs)
    gs, ge = true_runs(~h)
    for a, b in zip(gs, ge):
        if b - a in (1, 2) and a > 0 and h[a-1] and b < T and h[b]:
            h[a:b] = True
    inm = np.zeros(T, bool)
    s_, e_ = true_runs(h)
    for a, b in zip(s_, e_):
        if b - a >= 5: inm[a:b] = True
    if inm.any():
        alt_cells += 1
        alt_mhw_days += int(inm.sum())
        alt_active |= inm
s_, e_ = true_runs(alt_active)
alt_events = [(str(t_dates[a])[:10], str(t_dates[b-1])[:10]) for a, b in zip(s_, e_)]
print("ALT interpretation: cells with MHW:", alt_cells, " MHW cell-days:", alt_mhw_days)
print("ALT events:", alt_events)

# also: what are the near-miss structures? list all maximal hot runs of length 3-4 with their cells/dates
near = []
for c in range(C):
    if not sea_flat[c]: continue
    s_, e_ = true_runs(hot[c])
    for a, b in zip(s_, e_):
        if b - a in (3, 4):
            near.append((b - a, c, str(t_dates[a])[:10], str(t_dates[b-1])[:10]))
near.sort(reverse=True)
print("\nhot runs of length 3-4 (top 15 by length):")
for L, c, a, b in near[:15]:
    print(f"  len={L} cell=({c//60},{c%60}) {a}..{b}")
print("total 3-4 runs:", len(near))
