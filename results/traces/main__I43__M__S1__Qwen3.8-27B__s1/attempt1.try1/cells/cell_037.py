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

cases = [
    "00000|00000",                 # nothing
    "001111000|000000000",         # run of 4 -> none
    "00111110000|00111110000",     # run of 5 -> kept
    "11111001111100|11111111111100",   # gap 2 -> joined, gap days in
    "1111100011111000|1111100011111000",  # gap 3 -> separate
    "01111100111110011111100|011111111111100111111100",  # chained gap2+gap2 -> one
    "1111111|1111111",
    "0001111100011111000|00011111111111000",  # gap 2 -> join
    "00011111001111100|00011111111111000",    # gap 1 -> join
    "111110000011111|111110000011111",        # gap 4 -> separate
    "0001111110011111100|0001111110011111100",  # 6 and 6, gap 2 -> join all
]
ok = True
for inp_exp in cases:
    inp, exp = inp_exp.split("|")
    assert len(inp) == len(exp), (inp, exp)
    got = cell_mhw(np.array([c=='1' for c in inp]))
    g = "".join("1" if x else "0" for x in got)
    if g != exp:
        ok = False
        print("FAIL:", inp, "->", g, "expected", exp)
print("cell_mhw tests:", "PASS" if ok else "FAIL")
