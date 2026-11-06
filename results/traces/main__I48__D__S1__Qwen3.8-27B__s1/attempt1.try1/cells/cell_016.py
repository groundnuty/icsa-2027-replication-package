import numpy as np, datetime

tgt = np.load('/work/tgt.npy')          # (92, 3600)
thr = np.load('/work/thr.npy')          # (366, 3600)
sea = np.load('/work/sea_mask.npy')     # (3600,)
ncells = tgt.shape[1]
nt = tgt.shape[0]

tgt_dates = []
d = datetime.date(2016,6,1)
while d <= datetime.date(2016,8,31):
    tgt_dates.append(d); d += datetime.timedelta(days=1)
doy = np.array([dt.timetuple().tm_yday for dt in tgt_dates])
assert (doy == np.arange(152, 244)).all()

# hot days (float64 comparison; land cells never hot)
thr_t = thr[doy-1]                      # (92, 3600)
hot = np.zeros((nt, ncells), dtype=bool)
hot[:, sea] = (tgt[:, sea] >= thr_t[:, sea])

def cell_mhw_runs(h):
    """h: bool vector length nt. Return list of (start, end) inclusive spans of joined per-cell MHWs."""
    idx = np.where(h)[0]
    runs = []
    if len(idx):
        split = np.where(np.diff(idx) > 1)[0] + 1
        starts = np.split(idx, split)
        for s in starts:
            if len(s) >= 5:
                runs.append([s[0], s[-1]])
    joined = []
    for r in runs:
        if joined and r[0] - joined[-1][1] - 1 <= 2:
            joined[-1][1] = r[1]
        else:
            joined.append(list(r))
    return [tuple(x) for x in joined]

mask = np.zeros((nt, ncells), dtype=np.uint8)
for c in range(ncells):
    if not sea[c]:
        continue
    for (s, e) in cell_mhw_runs(hot[:, c]):
        mask[s:e+1, c] = 1

# brute-force cross-check on 8 random cells
rng = np.random.default_rng(7)
def brute(h):
    # direct: day i in MHW if exists a run of >=5 hot days within gap<=2 chain ... emulate spec:
    runs = cell_mhw_runs.__wrapped__ if hasattr(cell_mhw_runs,'__wrapped__') else None
    # independent re-derivation:
    idx = np.where(h)[0]
    segs = []
    if len(idx):
        for i in range(len(idx)):
            if i+1 < len(idx) and idx[i+1] - idx[i] > 1:
                segs.append(idx[:i+1])
        segs.append(idx[i:])
    big = [seg for seg in segs if len(seg) >= 5]
    out = []
    for seg in big:
        if out and seg[0] - out[-1] - 1 <= 2:
            out = out[:-1] + [out[-1][0], seg[-1]]
        else:
            out.append([seg[0], seg[-1]])
    return [tuple(o) for o in out]

ok = True
for _ in range(8):
    c = int(rng.integers(0, ncells))
    r1 = cell_mhw_runs(hot[:, c]); r2 = brute(hot[:, c])
    if r1 != r2:
        ok = False; print("MISMATCH", c, r1, r2)
print("cross-check ok:", ok)

# regional activity & events
active = mask.any(axis=1)
print("active days:", int(active.sum()), "of", nt)
ev = []
i = 0
while i < nt:
    if active[i]:
        j = i
        while j+1 < nt and active[j+1]:
            j += 1
        ev.append((tgt_dates[i], tgt_dates[j]))
        i = j+1
    else:
        i += 1
print("events:")
for (a, b) in ev:
    print("  ", a, "->", b, f"({(b-a).days+1} days)")

np.save('/work/mask.npy', mask)
np.save('/work/events.npy', np.array(ev, dtype=object), allow_pickle=True)
