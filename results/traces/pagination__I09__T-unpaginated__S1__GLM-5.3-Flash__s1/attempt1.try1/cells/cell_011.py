import numpy as np, json, datetime as dt

def detect(h):
    idx = np.flatnonzero(np.diff(np.concatenate(([0], np.asarray(h, dtype=np.int8).view(np.int8), [0]))))
    runs = list(zip(idx[0::2], idx[1::2]))
    mhw_runs = [(s, e) for s, e in runs if e - s >= 5]
    merged = []
    for s, e in mhw_runs:
        if merged and 1 <= s - merged[-1][1] <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    return merged

# synthetic tests
assert detect([1,1,1,1,1,0,0,1,1,1,1,1,1]) == [[0,13]], "gap2 join"
assert detect([1]*5+[0]*3+[1]*5) == [[0,5],[8,13]], "gap3 no join"
assert detect([1,1,1,0,1,1,1,1,1]) == [[4,9]], "short run not MHW, not joined"
assert detect([1]*4) == [], "run<5"
assert detect([0,1,1,1,1,1,0,0,0,1,1,1,1,1,1,0,1,1,1,1,1]) == [[1,6],[9,15],[16,21]], "multiple"
assert detect([1,1,1,1,0,1,1,1,1,1]) == [[0,10]], "gap1 join"
print("all synthetic join/length tests passed")

# spot-check 3 real cells against the saved mask
tgt_stack = np.load('/tmp/tgt_stack.npy'); Ts = np.load('/tmp/thr_smooth.npy')
sea = np.load('/tmp/sea.npy'); mask = np.load('/tmp/mhw_mask.npy')
meta = json.load(open('/tmp/meta.json')); tgt = [dt.date.fromisoformat(s) for s in meta['tgt']]
t_doy = np.array([(d - dt.date(d.year,1,1)).days + 1 for d in tgt])
thr_t = Ts[t_doy - 1]
rng = np.random.default_rng(1)
cells = [(0,0),(30,30),(59,59),(12,47)] + [tuple(rng.integers(0,60,2)) for _ in range(4)]
for a,b in cells:
    if not sea[a,b]: 
        print(f'cell({a},{b}): land, mask sum =', int(mask[:,a,b].sum())); continue
    h = (tgt_stack[:,a,b] >= thr_t[:,a,b])
    m = detect(h)
    rebuilt = np.zeros(92, dtype=np.uint8)
    for s,e in m: rebuilt[s:e] = 1
    ok = np.array_equal(rebuilt, mask[:,a,b])
    print(f'cell({a},{b}): hot={int(h.sum())}d, MHW spans={[(s,e) for s,e in m]}, mask match={ok}')
# global consistency: mask ⊆ hot ∪ (joined gap days of that cell already verified per-cell)
print('mask sum:', int(mask.sum()), '| active days:', int(mask.any(axis=(1,2)).sum()))
