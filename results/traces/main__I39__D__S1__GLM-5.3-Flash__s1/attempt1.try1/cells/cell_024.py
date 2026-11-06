import numpy as np

# 1) verify nanquantile method='hazen' equals manual Hyndman-Fan type 5
rng = np.random.default_rng(0)
for trial in range(200):
    n = rng.integers(20, 130)
    x = rng.normal(size=n)
    x[rng.choice(n, size=3, replace=False)] = np.nan
    p = 0.9
    v = np.sort(x[~np.isnan(x)])
    m = len(v)
    h = m * p + 0.5            # type 5: h = n*p + 0.5 (1-based), clipped to [1, m]
    lo = int(np.floor(h)); hi = int(np.ceil(h))
    lo = max(1, min(m, lo)); hi = max(1, min(m, hi))
    manual = v[lo-1] + (h - lo) * (v[hi-1] - v[lo-1])
    q = np.nanquantile(x, p, method='hazen')
    if not np.isclose(manual, q, rtol=0, atol=1e-12):
        print('MISMATCH', trial, manual, q); break
else:
    print('hazen (type 5) matches manual implementation on 200 random trials')

# 2) MHW run/join logic on synthetic examples
def mhw_intervals(hot1d):
    n = len(hot1d); ivs = []; j = 0
    while j < n:
        if hot1d[j]:
            e = j
            while e+1 < n and hot1d[e+1]: e += 1
            if e - j + 1 >= 5: ivs.append([j, e])
            j = e + 1
        else:
            j += 1
    merged = []
    for s, e in ivs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    return merged

cases = [
    ([1]*5, [[0,4]]),                                   # exactly 5 -> event
    ([1]*4, []),                                        # 4 -> no event
    ([1]*3+[0]*2+[1]*3, []),                            # short runs with 2-gap -> still <5 overall? 
    ([1]*5+[0]+[1]*5, [[0,10]]),                        # 1-day gap -> joined
    ([1]*5+[0,0]+[1]*5, [[0,11]]),                      # 2-day gap -> joined
    ([1]*5+[0,0,0]+[1]*5, [[0,4],[8,12]]),              # 3-day gap -> not joined
    ([0,1,1,1,1,1,0], [[1,5]]),
    ([1]*6+[0]*3+[1]*4+[0]+[1]*6, [[0,16]]),            # short 4-run inside gaps? no: 6-run, 4-run too short, 6-run -> join? gap 3 between run1 and run3!
]
for hot_list, expected in cases:
    got = mhw_intervals(np.array(hot_list, dtype=bool))
    status = 'OK ' if got == expected else 'FAIL'
    print(status, hot_list, '->', got, 'expected', expected)
