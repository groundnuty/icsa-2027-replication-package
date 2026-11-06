import numpy as np

def detect(x, min_len=5, gap=2):
    p = np.concatenate(([0], x, [0]))
    d = np.diff(p.astype(np.int8))
    s = np.flatnonzero(d == 1); e = np.flatnonzero(d == -1) - 1
    keep = (e - s + 1) >= min_len
    s, e = s[keep], e[keep]
    merged = []
    for a, b in zip(s, e):
        if merged and a - merged[-1][1] - 1 <= gap:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    return merged

# carefully hand-computed expectations
cases = [
    "1111100011111",          # runs(0,4),(8,12); gap3 -> separate
    "111110011111",           # runs(0,4),(7,11); gap2 -> (0,11)
    "1111011111",             # runs(0,3),(5,9); gap1 -> (0,9)
    "1111",                   # -> none
    "11111",                  # -> (0,4)
    "01111110",               # -> (1,5)
    "1111100111110011111",    # runs(0,4),(7,11),(14,18); gaps 2,2 -> (0,18)
    "11111000111111100011111",# runs(0,4),(8,13),(17,21); gaps 3,3 -> separate
    "1111111111",             # 10-run -> (0,9)
    "11111011111",            # runs(0,4),(6,10); gap1 -> (0,10)
]
expected = [
    [(0,4),(8,12)],
    [(0,11)],
    [(0,9)],
    [],
    [(0,4)],
    [(1,5)],
    [(0,18)],
    [(0,4),(8,13),(17,21)],
    [(0,9)],
    [(0,10)],
]
for x, exp in zip(cases, expected):
    got = detect([int(ch) for ch in x])
    print(x, "got", got, "exp", exp, "OK" if got == exp else "MISMATCH")
