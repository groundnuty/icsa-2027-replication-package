import numpy as np, datetime as dt

def mhw_from_hot(h, nT, minlen=5, gap=2):
    m = np.zeros(nT, bool)
    t = 0; runs = []
    while t < nT:
        if h[t]:
            s = t
            while t < nT and h[t]: t += 1
            runs.append([s, t-1])
        else: t += 1
    groups = []
    for r in runs:
        if groups and r[0]-groups[-1][1]-1 <= gap: groups[-1][1] = r[1]
        else: groups.append(list(r))
    for s, e in groups:
        if e-s+1 >= minlen: m[s:e+1] = True
    return m

# unit tests
tests = [
    ([1,1,1,1,1],                 [1,1,1,1,1]),
    ([1,1,1,1],                   [0,0,0,0]),
    ([1,1,1,1,0,1,1,1,1,1],       [1]*10),
    ([1,1,1,1,0,0,1,1,1,1],       [1]*10),
    ([1,1,1,1,0,0,0,1,1,1,1,1],   [0]*12),
    ([1,1,1,1,0,0,1,1,1,1,0,0,0,1,1,1,1,1], [1]*10+[0]*4+[1]*5),
    ([0,0,1,1,1,1,1,0,0,0],       [0,0,1,1,1,1,1,0,0,0]),
    ([1,0,1,1,1,1,1],             [1,1,1,1,1,1,1]),
    ([0,0,0,0,0],                 [0]*5),
]
allok = True
for h, exp in tests:
    got = mhw_from_hot(np.array(h,bool), len(h)).astype(int).tolist()
    if got != exp: allok = False; print("FAIL", h, got, exp)
print("run/join unit tests:", "ALL PASS" if allok else "FAILURES")

# smoothing re-verify with roll
thr_s = np.load('/tmp/thr_s.npy'); thr_raw_src = None
thr_raw = np.load('/tmp/thr_s.npy')  # only smoothed saved; rebuild raw check differently
a = np.random.rand(366)
out = np.array([a[(d+np.arange(-15,16))%366].mean() for d in range(366)])
roll = np.convolve(np.concatenate([a, a, a]), np.ones(31)/31, mode='same')[366:732]
print("smooth31 vs convolve-roll check:", np.allclose(out, roll, atol=1e-12))

# verify events from saved mask state (recompute mhw fresh to be safe)
thr = np.load('/tmp/thr_s.npy'); tgt = np.load('/tmp/tgt_cube.npy')
def mdoy(d): return (dt.date(2000,d.month,d.day)-dt.date(2000,1,1)).days+1
tgt_days = [dt.date(2021,6,1)+dt.timedelta(days=i) for i in range(92)]
tdoy = np.array([mdoy(d) for d in tgt_days])
sea = np.isfinite(tgt).all(axis=0)
hot = (tgt >= thr[tdoy]) & sea
nT = 92
mhw = np.zeros((nT,60,60), bool)
for i in range(60):
    for j in range(60):
        if not sea[i,j]: continue
        mhw[:,i,j] = mhw_from_hot(hot[:,i,j], nT)
print("cell-days:", int(mhw.sum()), "(matches earlier 34487:", int(mhw.sum())==34487, ")")
act = mhw.sum(axis=(1,2)) > 0
events = []
t = 0
while t < nT:
    if act[t]:
        s = t
        while t < nT and act[t]: t += 1
        events.append((tgt_days[s], tgt_days[t-1]))
    else: t += 1
for e in events: print("event:", e[0], "->", e[1], "(", (e[1]-e[0]).days+1, "days )")
print("gaps between events:", [(events[k+1][0]-events[k][1]).days-1 for k in range(len(events)-1)])
np.save('/tmp/mhw_final.npy', mhw)
# spatial extent of events
for e in events:
    idxs = np.where(mhw[[k for k,d in enumerate(tgt_days) if e[0]<=d<=e[1]].__len__()>0] if False else mhw[tdoy_search:=0] if False else mhw[[k for k,d in enumerate(tgt_days) if e[0]<=d<=e[1]]].any(axis=0))
    ii, jj = idxs
    print("  cells involved:", len(ii), " lat range %.2f..%.2f lon range %.2f..%.2f" % (
        57.34+0.02*ii.min(), 57.34+0.02*ii.max(), 9.04+0.02*jj.min(), 9.04+0.02*jj.max()))
