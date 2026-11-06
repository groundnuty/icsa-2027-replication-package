import numpy as np, time, json
from datetime import date, timedelta

t0 = time.time()
thr = np.load('/work/data/thr_raw.npy').copy()
clim = np.load('/work/data/clim_raw.npy').copy()
si = np.load('/work/data/sea_idx.npy')
T = np.load('/work/data/T.npy')
tt = np.load('/work/data/tt.npy')
tb = np.load('/work/data/tb.npy')
B = np.load('/work/data/B.npy')

thr[59] = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])

ENDS = np.cumsum([31,29,31,30,31,30,31,31,30,31,30,31])
def doy_of(m, d):
    return d + (int(ENDS[m-2]) if m >= 2 else 0)
def md_of(doy):
    idx = int(np.searchsorted(ENDS, doy, side='left'))
    return idx+1, doy - (int(ENDS[idx-1]) if idx > 0 else 0)

# ---------- brute-force verification of pool intervals for several doys ----------
base_dates = []
d = date(1992,1,1)
while d <= date(2002,12,31):
    base_dates.append(d); d += timedelta(days=1)
d0 = date(1991,12,27)
for D in [1, 59, 61, 153, 200, 244, 336, 366]:
    m, dd = md_of(D)
    bs = [b for b in base_dates if doy_of(b.month, b.day) == D]
    union = set()
    for b in bs:
        t = b - timedelta(days=5)
        while t <= b + timedelta(days=5):
            union.add(t); t += timedelta(days=1)
    lo = min(union); hi = max(union)
    # is union contiguous?
    contig = all((x + timedelta(days=1)) in union for x in union if x != hi)
    # my interval
    my_lo = date(1992, m, dd) - timedelta(days=5)
    my_hi = date(2002, m, dd) + timedelta(days=5)
    print(D, "lo:", lo, "hi:", hi, "contiguous:", contig, "n:", len(union), " my:", my_lo, my_hi, " match:", (lo, hi) == (my_lo, my_hi))

# ---------- smoothing ----------
def circ31(A):
    A2 = np.concatenate([A[-15:], A, A[:15]], axis=0)
    W = np.lib.stride_tricks.sliding_window_view(A2, 31, axis=0)
    return W.mean(axis=2)
thr_s, clim_s = circ31(thr), circ31(clim)

# ---------- target hot mask ----------
tt_dates = [date.fromisoformat(str(np.datetime64(t))[:10]) for t in tt]
doy_t = np.array([doy_of(t.month, t.day) for t in tt_dates])
nsea = thr.shape[1]
Tsea = T[:, si//60, si%60]
assert np.isfinite(Tsea).all()
hot = Tsea >= thr_s[doy_t - 1]
counts = hot.sum(axis=1)
print("hot cell-days:", int(hot.sum()))
print("per-day counts:", list(counts))

def runs_bool(v):
    pad = np.concatenate(([0], v.view(np.int8), [0])).astype(np.int8)
    idx = np.flatnonzero(np.diff(pad))
    return [(int(idx[2*j]), int(idx[2*j+1])-1) for j in range(len(idx)//2)]

rng = np.random.default_rng(1)
for _ in range(300):
    v = rng.integers(0, 2, size=int(rng.integers(0, 100))).astype(bool)
    exp, s = [], None
    for j, x in enumerate(v):
        if x and s is None: s = j
        if (not x) and s is not None: exp.append((s, j-1)); s = None
    if s is not None: exp.append((s, len(v)-1))
    assert runs_bool(v) == exp
print("runs_bool verified (300 random vectors)")

mask = np.zeros((92, nsea), dtype=np.uint8)
n_mhw_cells = 0
for c in range(nsea):
    ivs = [(s, e) for s, e in runs_bool(hot[:, c]) if e - s + 1 >= 5]
    if not ivs: continue
    merged = [list(ivs[0])]
    for s, e in ivs[1:]:
        if s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    for s, e in merged:
        mask[s:e+1, c] = 1
    n_mhw_cells += 1
active = mask.any(axis=1)
print("cells with >=1 MHW:", n_mhw_cells, " mask cell-days:", int(mask.sum()))
print("active days:", int(active.sum()), "of 92; first/last active:",
      tt_dates[int(np.argmax(active))], "..." if active.sum() else "")
ev = []
s = None
for i, a in enumerate(active):
    if a and s is None: s = i
    if (not a) and s is not None:
        ev.append((s, i-1)); s = None
if s is not None: ev.append((s, 91))
evd = [(tt_dates[a].isoformat(), tt_dates[b].isoformat(), b-a+1) for a, b in ev]
print("events:", evd)
np.save('/work/data/thr_s.npy', thr_s)
np.save('/work/data/clim_s.npy', clim_s)
np.save('/work/data/mask.npy', mask)
with open('/work/data/events.json','w') as f:
    json.dump([{"onset": a, "end": b} for a, b, _ in evd], f, indent=1)
print("done", round(time.time()-t0, 1), "s")