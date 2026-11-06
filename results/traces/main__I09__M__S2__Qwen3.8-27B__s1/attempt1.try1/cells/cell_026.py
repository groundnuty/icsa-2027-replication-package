import numpy as np
st2 = np.load("cache/stage2.npz")
st1 = np.load("cache/stage1.npz")
hot = st1['hot']; mhw = st2['mhw']

def brute_force_mhw(h):
    h = list(map(bool, h)); NT = len(h)
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
    changed = True
    while changed:
        changed = False
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
for tc in rng.integers(0, mhw.shape[1], 60):
    if not np.array_equal(brute_force_mhw(hot[:, tc]), mhw[:, tc]):
        bad += 1; print("MISMATCH", tc)
print("brute-force MHW check (60 cells):", "PASS" if bad == 0 else "FAIL")

# also verify every merged MHW day is either hot or a gap day (1-2 long) inside a merged run
# and that MHWs of length >=5 exist as hot-run cores
ok = True
for tc in range(0, mhw.shape[1], 97):
    h = hot[:, tc].astype(bool); m = mhw[:, tc].astype(bool)
    # MHW days must be covered by hot runs joined through gaps<=2
    exp = brute_force_mhw(h)
    if not np.array_equal(exp, m): ok = False
print("sampled full-grid check:", "PASS" if ok else "FAIL")
# stats
lens = []
for s, e in st2['events']:
    lens.append(e-s+1)
print("event lengths:", lens, " active days:", int(mhw.any(axis=1).sum()))