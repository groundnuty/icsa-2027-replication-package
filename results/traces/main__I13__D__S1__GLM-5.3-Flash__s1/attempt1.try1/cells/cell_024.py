import numpy as np

def find_runs_per_cell(hot, sea):
    nt, nlat, nlon = hot.shape
    mhw = np.zeros_like(hot, dtype=bool)
    for a in range(nlat):
        for b in range(nlon):
            if not sea[a, b]: continue
            h = hot[:, a, b]
            idx = np.flatnonzero(h)
            if idx.size == 0: continue
            breaks = np.where(np.diff(idx) > 1)[0]
            starts = np.concatenate(([0], breaks+1))
            ends = np.concatenate((breaks, [idx.size-1]))
            runs = []
            for s, e in zip(starts, ends):
                if idx[e] - idx[s] + 1 >= 5:
                    runs.append([idx[s], idx[e]])
            if not runs: continue
            joined = [runs[0]]
            for r in runs[1:]:
                gap = r[0] - joined[-1][1] - 1
                if gap <= 2:
                    joined[-1][1] = r[1]
                else:
                    joined.append(r)
            for s, e in joined:
                mhw[s:e+1, a, b] = True
    return mhw

# synthetic tests: single cell series
tests = [
    ([1,1,1,1,1,0,0,1,1,1,1,1], [1]*12, '5-run + gap2 + 5-run -> joined all'),
    ([1,1,1,0,1,1,1,1,1], [0,0,0,0,1,1,1,1,1], '3-run too short; 5-run stands'),
    ([1]*6+[0]*3+[1]*5, [1]*6+[0]*3+[1]*5, 'gap3 -> two separate'),
    ([1,1,1,1], [0]*4, '4-run too short'),
    ([1,1,1,0,0,1,1,1,1,1], [0,0,0,0,0,1,1,1,1,1], '3-run + gap2 + 5-run: only 5-run'),
    ([1]*5+[0]*1+[1]*5, [1]*11, 'gap1 -> joined'),
    ([1]*5+[0]*2+[1]*4, [1]*5+[0]*2+[0]*4, '5-run + gap2 + 4-run -> joined? gap=2 -> yes; 4-run merges via gap rule'),
]
for hot1, expect, desc in tests:
    h = np.array(hot1, dtype=bool).reshape(-1,1,1)
    sea = np.array([[True]])
    m = find_runs_per_cell(h, sea)[:,0,0].astype(int)
    ok = np.array_equal(m, np.array(expect))
    print(('PASS' if ok else 'FAIL'), desc, '| got', ''.join(map(str,m)), 'expected', ''.join(map(str,expect)))
