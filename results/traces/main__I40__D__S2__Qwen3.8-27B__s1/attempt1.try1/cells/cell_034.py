import numpy as np, datetime
hot = np.load('/work/hot.npy')          # (92, 3600)
sea = np.load('/work/sea.npy')          # (3600,)
C = hot.shape[1]

def cell_mhw_mask(h):
    """h: (T,) bool. Returns mask of days in merged per-cell MHWs."""
    T = len(h)
    prev = np.empty(T, bool); prev[0] = False; prev[1:] = h[:-1]
    nxt  = np.empty(T, bool); nxt[-1] = False; nxt[:-1] = h[1:]
    starts = np.flatnonzero(h & ~prev)
    ends   = np.flatnonzero(h & ~nxt)
    keep = (ends - starts + 1) >= 5
    ks, ke = starts[keep], ends[keep]
    out = []
    if ks.size:
        S, E = int(ks[0]), int(ke[0])
        for s2, e2 in zip(ks[1:], ke[1:]):
            if int(s2) - E - 1 <= 2:
                E = int(e2)
            else:
                out.append((S, E)); S, E = int(s2), int(e2)
        out.append((S, E))
    m = np.zeros(T, bool)
    for s, e in out:
        m[s:e+1] = True
    return m, out

mask = np.zeros_like(hot)
n_events_cells = 0
for c in np.flatnonzero(sea):
    m, ev = cell_mhw_mask(hot[:, c])
    mask[:, c] = m
    n_events_cells += len(ev)

tgt_dates = [datetime.date(2009,6,1) + datetime.timedelta(days=k) for k in range(92)]
active = mask.any(axis=1)
# regional events: maximal runs of active days
ev = []
in_ev = False
for k, a in enumerate(active):
    if a and not in_ev:
        s = k; in_ev = True
    if not a and in_ev:
        ev.append((s, k-1)); in_ev = False
if in_ev: ev.append((s, len(active)-1))

print("total per-cell MHW events (after merging):", n_events_cells)
print("active days:", active.sum(), "of", len(active))
print("first/last active:", tgt_dates[int(active.argmax())], "day idx", int(np.flatnonzero(active)[0]), "to", int(np.flatnonzero(active)[-1]))
print("\nRegional events:")
for s, e in ev:
    print(tgt_dates[s].isoformat(), "->", tgt_dates[e].isoformat(), f"({e-s+1} d)")

np.save('/work/mask.npy', mask)
np.save('/work/events.npy', np.array(ev))
print("first 12 active flags:", active[:12].astype(int).tolist())
