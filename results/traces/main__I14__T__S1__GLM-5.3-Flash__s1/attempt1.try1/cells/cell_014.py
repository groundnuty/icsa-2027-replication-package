import numpy as np, pandas as pd, pickle, json

with open('/tmp/stepA.pkl','rb') as fh:
    D = pickle.load(fh)
thresh_s = D['thresh_s']
sst, sea = D['sst'], D['sea']
tdates, tdoy = D['tdates'], D['tdoy']
T = sst.shape[0]
sst_flat = sst.reshape(T, -1)

hot = np.zeros((T, 3600), dtype=bool)
hot[:, sea] = sst_flat[:, sea] >= thresh_s[tdoy - 1, :]
print("hot days total:", int(hot.sum()))

def per_cell_mhw(hot, min_run=5, max_gap=2):
    Tn, N = hot.shape
    padded = np.zeros((Tn + 2, N), dtype=np.int8)
    padded[1:-1] = hot
    dv = np.diff(padded, axis=0)                      # +1 at run start, -1 at end+1
    sr, sc = np.where(dv == 1)                        # starts (row, col)
    er, ec = np.where(dv == -1)                       # ends (exclusive row, col)
    os_, oe = np.lexsort((sr, sc)), np.lexsort((er, ec))   # order by column, then row
    assert np.array_equal(sc[os_], ec[oe])
    sc, sr = sc[os_], sr[os_]
    ec, er = ec[oe], er[oe]
    L = er - sr
    keep = L >= min_run
    cs_col, cs_row, ce_col, ce_row = sc[keep], sr[keep], ec[keep], er[keep]
    segs = []
    if len(cs_row):
        pc, ps, pe = int(cs_col[0]), int(cs_row[0]), int(ce_row[0])
        for c, s, e in zip(cs_col[1:], cs_row[1:], ce_row[1:]):
            c, s, e = int(c), int(s), int(e)
            if c == pc and s - pe <= max_gap:
                pe = e
            else:
                segs.append((pc, ps, pe)); pc, ps, pe = c, s, e
        segs.append((pc, ps, pe))
    mhw = np.zeros_like(hot)
    for c, s, e in segs:
        mhw[s:e, c] = True
    return mhw, segs, int(keep.sum()), len(cs_row)

mhw_flat, segs, n_runs5, n_runs_all = per_cell_mhw(hot)
print("runs total:", n_runs_all, "| runs >=5:", n_runs5, "| per-cell MHW segments after join:", len(segs))
print("non-hot gap days inside per-cell MHWs:", int((mhw_flat & ~hot).sum()))

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
                 'n_runs5': n_runs5, 'segs': segs}, fh)
print("saved stepB")
