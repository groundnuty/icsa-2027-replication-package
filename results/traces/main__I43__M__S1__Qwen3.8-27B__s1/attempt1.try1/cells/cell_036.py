import numpy as np

def cell_mhw(h):
    m = np.zeros_like(h)
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

def pat(s):
    h = np.zeros(len(s), bool)
    for ch in s:
        pass
    h = [ch=='1' for ch in s]
    return np.array(h)

# tests: string of '1'/'0'
cases = [
    ("00000", "00000"),                      # nothing
    ("001111000", "000000000"),              # run of 4 -> no MHW
    ("00111110000", "00111110000"),          # run of 5 -> MHW
    ("11111001111100", "11111001111100"),    # gap 2 -> join (gap days included)
    ("1111100011111000", "111110000001111100"),  # gap 3 -> keep separate
    ("111110011111001111100", "111110011111001111100"),  # two gap-2 joins
    ("00111110001111100", "00111110001111100"),  # gap 3
    ("1111111", "1111111"),
    ("0001111100011111000", "0001111100011111000"),  # gap 3
    ("00011111001111100", "00011111001111100"),  # gap 1 join
]
ok = True
for inp, exp in cases:
    got = cell_mhw(pat(inp))
    if (got != np.array([c=='1' for c in exp])).any():
        ok = False
        print("FAIL:", inp, "->", "".join(got.astype(str)), "expected", exp)
print("cell_mhw tests:", "PASS" if ok else "FAIL")

# chained merge: gap2 then gap2 -> all one
h = pat("01111100111110011111100")
print("chain:", "".join(cell_mhw(h).astype(str)), "expect 01111100111110011111100")
