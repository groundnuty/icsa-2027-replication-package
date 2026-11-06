import numpy as np, pandas as pd, pickle, json

with open('/tmp/stepA.pkl','rb') as fh:
    D = pickle.load(fh)
thresh_s = D['thresh_s']
sst, sea = D['sst'], D['sea']
tdates, tdoy = D['tdates'], D['tdoy']
T = sst.shape[0]
sst_flat = sst.reshape(T, -1)                        # (92, 3600)
print("sst", sst.shape, "sea cells", int(sea.sum()))

# ---- hot days (sea cells only; land stays False) ----
hot = np.zeros((T, 3600), dtype=bool)
hot[:, sea] = sst_flat[:, sea] >= thresh_s[tdoy - 1, :]
print("hot days total:", int(hot.sum()))

# ---- per-cell MHWs: runs >=5, then join gaps <=2 (gap days included) ----
def per_cell_mhw(hot, min_run=5, max_gap=2):
    Tn, N = hot.shape
    h = np.vstack([np.zeros((1, N), bool), hot, np.zeros((1, N), bool)])
    dd = np.diff(h.astype(np.int8).ravel(order='C'))  # careful: need diff along time per column
    return None

def per_cell_mhw(hot, min_run=5, max_gap=2):
    Tn, N = hot.shape
    padded = np.zeros((Tn + 2, N), dtype=np.int8)
    padded[1:-1] = hot
    dv = np.diff(padded, axis=0)                     # (Tn+1, N); +1 at run start, -1 after end
    starts_r, starts_c = np.where(dv == 1)
    ends_r, ends_c = np.where(dv == -1)
    assert np.array_equal(starts_c, ends_c)          # columns have alternating rises/falls
    L = ends_r - starts_r
    keep = L >= min_run
    st, en = starts_r[keep], ends_r[keep]
    segs = []
    if len(st):
        cs, ce = int(st[0]), int(en[0])
        for s, e in zip(st[1:], en[1:]):
            s, e = int(s), int(e)
            if s - ce <= max_gap:
                ce = e
            else:
                segs.append((cs, ce)); cs, ce = s, e
        segs.append((cs, ce))
    mhw = np.zeros_like(hot)
    for s, e in segs:
        mhw[s:e, :] = True
    return mhw, segs, int(keep.sum()), len(st)

mhw_flat, segs, n_runs5, n_runs_all = per_cell_mhw(hot)
print("runs total:", n_runs_all, "| runs >=5:", n_runs5, "| per-cell MHW segments after join:", len(segs))
print("non-hot gap days inside per-cell MHWs:", int((mhw_flat & ~hot).sum()))
raw_len = [int((ends - st)) for st, ends in []] if False else None

# ---- regional events ----
active = mhw_flat.any(axis=1)
print("active days:", int(active.sum()), "/", T)
events = []
i = 0
while i < T:
    if active[i]:
        j = i
        while j + 1 < T and active[j + 1]:
            j += 1
        events.append((i, j)); i = j + 1
    else:
        i += 1
ev = [{"onset": str(tdates[a].date()), "end": str(tdates[b].date())} for a, b in events]
print("regional events:", json.dumps(ev))
print("event lengths (days):", [b - a + 1 for a, b in events])
for (a, b) in events:
    sub = mhw_flat[a:b+1]
    print(f"  {tdates[a].date()}..{tdates[b].date()}: cells-in-MHW per day min/max = {int(sub.sum(axis=1).min())}/{int(sub.sum(axis=1).max())}")

mhw = mhw_flat.reshape(T, 60, 60).astype(np.uint8)
with open('/tmp/stepB.pkl','wb') as fh:
    pickle.dump({'mhw': mhw, 'hot': hot.reshape(T,60,60), 'active': active, 'events': events, 'ev': ev,
                 'tdates': tdates, 'latvals': D['latvals'], 'lonvals': D['lonvals'],
                 'n_runs5': n_runs5, 'segs': segs, 'clim_s': D['clim_s'], 'thresh_s': D['thresh_s']}, fh)
print("saved stepB")
