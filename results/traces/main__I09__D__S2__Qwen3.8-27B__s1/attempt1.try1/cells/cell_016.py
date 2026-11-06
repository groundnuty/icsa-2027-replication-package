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
    return [tuple(m) for m in merged]

# expectations derived carefully (min-run-5 filter first, then merge gaps<=2)
cases = [
    ("1111100011111", [(0,4),(8,12)]),        # 5,5 runs gap3 -> separate
    ("111110011111", [(0,11)]),               # gap2 -> join
    ("1111011111", [(5,9)]),                  # 4-run dropped, 5-run kept
    ("1114" if False else "111111", [(0,5)]), # 6-run
    ("11111011111", [(0,10)]),                # 5,5 gap1 -> join
    ("01111110", [(1,6)]),                    # 6-run
    ("1111100111110011111", [(0,18)]),        # 5,5,5 gaps2,2 -> one
    ("11111000111111100011111", [(0,4),(8,14),(18,22)]),  # gaps3,3
    ("111110111110011111", [(0,10),(14,18)]), # join(1), gap3
]
ok = True
for x, exp in cases:
    got = detect([int(ch) for ch in x])
    ok &= got == exp
    print(x, "->", got, "OK" if got == exp else "MISMATCH exp %s" % exp)
print("ALL PASS" if ok else "SOME FAILED")
