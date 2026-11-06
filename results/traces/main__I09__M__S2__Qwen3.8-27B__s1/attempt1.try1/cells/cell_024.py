import numpy as np
st = np.load("cache/stage1.npz")
d = np.load("cache/region.npz")
hot = st['hot']; mhw = st['mhw']; nsea_all = st['nsea_all']; tt = d['time_tgt']
sst_t = d['sst_tgt']; thr_s = st['thr_s']
CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
def doy(s): return CUM[int(s[5:7])-1] + int(s[8:10])
doy_t = np.array([doy(s) for s in tt], dtype=int)
sea_idx = np.argwhere(nsea_all.reshape(60,60))

def brute_force_mhw(h):
    # independent: scan days, build merged MHW mask directly
    h = list(map(bool, h))
    NT = len(h)
    # step 1: mark runs of >=5 consecutive hot
    run = [False]*NT
    i = 0
    while i < NT:
        if h[i]:
            j = i
            while j < NT and h[j]: j += 1
            if j - i >= 5:
                for k in range(i, j): run[k] = True
            i = j
        else:
            i += 1
    # step 2: merge runs separated by 1-2 non-hot days
    changed = True
    while changed:
        changed = False
        # find segments of run
        segs = []
        i = 0
        while i < NT:
            if run[i]:
                j = i
                while j < NT and run[j]: j += 1
                segs.append([i, j-1]); i = j
            else:
                i += 1
        new_segs = []
        for s in segs:
            if new_segs and s[0] - new_segs[-1][1] - 1 in (1, 2):
                new_segs[-1][1] = s[1]; changed = True
            else:
                new_segs.append(s)
        run = [False]*NT
        for a, b in new_segs:
            for k in range(a, b+1): run[k] = True
    return np.array(run, dtype=np.uint8)

rng = np.random.default_rng(7)
bad = 0
for tc in rng.integers(0, mhw.shape[1], 40):
    bf = brute_force_mhw(hot[:, tc])
    if not np.array_equal(bf, mhw[:, tc]):
        bad += 1
        print("MISMATCH cell", tc)
print("brute-force MHW check on 40 cells:", "PASS" if bad == 0 else "FAIL")

# verify hot against raw comparison on a sample
la, lo = sea_idx[0]
h0 = (sst_t[:, la, lo] >= thr_s[doy_t-1, 0])
print("hot sample check:", bool(np.array_equal(h0, hot[:, 0])))

# event boundaries: inactive neighbours
active = mhw.any(axis=1)
events = st['events']
print("events:")
for s, e in events:
    before = active[s-1] if s > 0 else None
    after  = active[e+1] if e < 91 else None
    print(f"  {tt[s][:10]} .. {tt[e][:10]}  len={e-s+1}  active_before={before} active_after={after}")
# also print active-day counts
print("active days total:", int(active.sum()))