import numpy as np

def cell_mhw(h):
    m = np.zeros_like(h, bool)
    if not h.any():
        return m
    idx = np.flatnonzero(h)
    breaks = np.flatnonzero(np.diff(idx) > 1)
    starts = np.concatenate([[idx[0]], idx[breaks+1]])
    ends   = np.concatenate([idx[breaks], [idx[-1]]])
    runs = [(s,e) for s,e in zip(starts, ends) if e-s+1 >= 5]
    merged = []
    for s,e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s,e])
    for s,e in merged:
        m[s:e+1] = True
    return m

# reference implementation: explicit intervals with iterative merging
def ref_mhw(h):
    idx = np.flatnonzero(h)
    runs = []
    if len(idx):
        s = idx[0]; p = idx[0]
        for i in idx[1:]:
            if i == p+1: p = i
            else: runs.append([s,p]); s = i; p = i
        runs.append([s,p])
    runs = [r for r in runs if r[1]-r[0]+1 >= 5]
    changed = True
    while changed:
        changed = False
        new = [runs[0]]
        for r in runs[1:]:
            if r[0] - new[-1][1] - 1 <= 2:
                new[-1][1] = r[1]; changed = True
            else:
                new.append(r)
        runs = new
    m = np.zeros_like(h, bool)
    for s,e in runs: m[s:e+1] = True
    return m

rng = np.random.default_rng(42)
ok = True
for trial in range(20000):
    n = rng.integers(1, 120)
    p = rng.uniform(0.1, 0.9)
    h = rng.random(n) < p
    a, b = cell_mhw(h), ref_mhw(h)
    if not (a == b).all():
        ok = False
        print("MISMATCH", "".join(map(str, h.astype(int))))
        print(" got", "".join(map(str, a.astype(int))))
        print(" ref", "".join(map(str, b.astype(int))))
        break
print("random cross-check vs independent merge-to-fixed-point:", "PASS" if ok else "FAIL")

# deterministic spot checks with hand-verified expectations
tests = {
 "00000": "00000",
 "001111000": "000000000",
 "00111110000": "00111110000",
 "11111001111100": "11111111111100",
 "1111100011111000": "1111100011111000",
 "01111100111110011111100": "0" + "1"*19 + "00",
 "1111111": "1111111",
 "0001111100011111000": "000" + "1"*12 + "000",
 "00011111001111100": "000" + "1"*11 + "00",
 "111110000011111": "111110000011111",
 "0001111110011111100": "000" + "1"*14 + "000",
}
ok = True
for inp, exp in tests.items():
    got = "".join(map(str, cell_mhw(np.array([c=='1' for c in inp])).astype(int)))
    if got != exp:
        ok = False; print("FAIL:", inp, got, exp)
print("deterministic spot checks:", "PASS" if ok else "FAIL")
