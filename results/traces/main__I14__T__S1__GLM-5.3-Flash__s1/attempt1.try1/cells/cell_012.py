import numpy as np, pandas as pd, pickle, json, os

with open('/tmp/stepA.pkl','rb') as fh:
    D = pickle.load(fh)
thresh_s, clim_s = D['thresh_s'], D['clim_s']
sst, sea = D['sst'], D['sea']
tdates, tdoy = D['tdates'], D['tdoy']
print("load ok; sst", sst.shape, "sea cells", int(sea.sum()))

# ---- hot days (sea cells only; land stays False) ----
hot = np.zeros(sst.shape, dtype=bool)
hot[:, sea] = sst[:, sea] >= thresh_s[tdoy - 1, :]

# ---- per-cell MHWs: runs >=5, then join gaps <=2 (gap days included) ----
def per_cell_mhw(hot, min_run=5, max_gap=2):
    mhw = np.zeros_like(hot)
    T, N = hot.shape
    h = np.vstack([np.zeros((1, N), bool), hot, np.zeros((1, N), bool)])
    d = np.diff(h.astype(np.int8), axis=0)
    starts = np.where(d.ravel() == 1)[0]     # run start indices (original coords)
    ends   = np.where(d.ravel() == -1)[0]    # run end (exclusive)
    L = ends - starts
    keep = L >= min_run
    st, en = starts[keep], ends[keep]
    segs = []
    if len(st):
        cs, ce = int(st[0]), int(en[0])
        for s, e in zip(st[1:], en[1:]):
            s, e = int(s), int(e)
            if s - ce <= max_gap:            # gap of 1 or 2 non-hot days
                ce = e
            else:
                segs.append((cs, ce)); cs, ce = s, e
        segs.append((cs, ce))
    for s, e in segs:
        mhw[s:e, :] = True if False else mhw[s:e, :]  # placeholder
    # set mask properly per segment
    mhw = np.zeros_like(hot)
    for s, e in segs:
        mhw[s:e, :] = True
    return mhw, segs, len(st), len(ends)

mhw, segs, n_runs5, n_runs_all = per_cell_mhw(hot)
print("runs total:", n_runs_all, "| runs >=5:", n_runs5, "| merged per-cell MHW segments:", len(segs))
print("gap-join checks: sum(mhw)= ", int(mhw.sum()))
# sanity: mhw must imply hot OR gap-day (non-hot but between two MHWs)
nonhot_in_mhw = int((mhw & ~hot).sum())
print("non-hot gap days inside MHWs:", nonhot_in_mhw)

# ---- regional events ----
active = mhw.any(axis=1)
print("active days:", int(active.sum()), "/", len(active))
events = []
i = 0
while i < len(active):
    if active[i]:
        j = i
        while j + 1 < len(active) and active[j + 1]:
            j += 1
        events.append((i, j))
        i = j + 1
    else:
        i += 1
ev = [{"onset": str(tdates[a].date()), "end": str(tdates[b].date())} for a, b in events]
print("regional events:", json.dumps(ev, indent=1))
# active-day runs length distribution
lens = [b - a + 1 for a, b in events]
print("event lengths:", lens)

# cells in MHW per event (diagnostic)
for (a, b) in events:
    print(f"event {tdates[a].date()}..{tdates[b].date()}: max cells in MHW/day = {int(mhw[a:b+1].sum(axis=1).max())}")

with open('/tmp/stepB.pkl','wb') as fh:
    pickle.dump({'mhw': mhw, 'hot': hot, 'active': active, 'events': events, 'ev': ev,
                 'tdates': tdates, 'latvals': D['latvals'], 'lonvals': D['lonvals'],
                 'n_runs5': n_runs5, 'segs': segs}, fh)
print("saved stepB")
