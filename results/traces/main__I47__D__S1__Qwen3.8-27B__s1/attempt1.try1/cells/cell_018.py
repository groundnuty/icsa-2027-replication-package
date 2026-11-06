import numpy as np, datetime as dt
m = np.load('/work/mask.npz')
mask = m['mask']; tgt_dates = [d for d in m['tgt_dates']]
data = np.load('/work/S.npz', allow_pickle=True)
S_base = data['S_base']; S_tgt = data['S_tgt']
sea = np.isfinite(S_tgt).all(axis=0)
St = S_tgt[:, sea].astype(np.float64)
tc = np.load('/work/thrclim.npz')
def smooth366(arr):
    pad = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)
    cs = np.concatenate([np.zeros((1, arr.shape[1])), np.cumsum(pad, axis=0)], axis=0)
    return (cs[31:] - cs[:-31]) / 31.0
THR = smooth366(tc['THR'])
def doy(d): return (d.replace(year=2020) - dt.date(2020,1,1)).days + 1
td = [dt.date.fromisoformat(s) for s in tgt_dates]
hot = St >= THR[[doy(d)-1 for d in td]]

def mhw_independent(h):
    # independent style: iterate day by day, grow merged events
    n = len(h)
    # find maximal hot runs
    runs = []
    i = 0
    while i < n:
        if h[i]:
            j = i
            while j+1 < n and h[j+1]: j += 1
            runs.append((i, j)); i = j+1
        else:
            i += 1
    runs = [(s,e) for s,e in runs if e-s+1 >= 5]
    events = []
    for s,e in runs:
        if events and s - events[-1][1] - 1 <= 2:
            events[-1] = (events[-1][0], max(events[-1][1], e))
        else:
            events.append((s,e))
    days = set()
    for s,e in events: days.update(range(s, e+1))
    return sorted(days)

rng = np.random.default_rng(7)
cells = list(rng.choice(3311, size=200, replace=False))
# add cells that are active on boundary days of events
active_days = np.flatnonzero(mask.any(axis=1))
for dd in active_days:
    cells += list(np.flatnonzero(mask[dd] > 0)[:5])
bad = 0
for c in set(cells):
    ref = mhw_independent(hot[:, c])
    mine = list(np.flatnonzero(mask[:, c]))
    if ref != mine:
        bad += 1
        if bad < 5:
            print("MISMATCH cell", c, "ref", ref[:20], "mine", mine[:20])
print("independent check done, mismatches:", bad, "of", len(set(cells)))

# also verify active-day logic
active_ref = np.array([len(mhw_independent(hot[:, c])) > 0 for c in range(3311)]).any()
act_days = np.array(sorted(set().union(*[set(mhw_independent(hot[:,c])) for c in range(0,3311)]))) if False else None
# faster: recompute active from ref
act = np.zeros(92, bool)
for c in range(3311):
    for dday in mhw_independent(hot[:, c]):
        act[dday] = True
print("active matches:", bool((act == m['active']).all()))
