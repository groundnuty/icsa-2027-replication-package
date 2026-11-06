import numpy as np, json, datetime as dt

def detect(h):
    h = np.asarray(h, dtype=np.int8)
    idx = np.flatnonzero(np.diff(np.concatenate(([0], h.view(np.int8), [0]))))
    runs = list(zip(idx[0::2], idx[1::2]))
    mhw_runs = [(int(s), int(e)) for s, e in runs if e - s >= 5]
    merged = []
    for s, e in mhw_runs:
        if merged and 1 <= s - merged[-1][1] <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    return [tuple(x) for x in merged]

tests = [
    ([1,1,1,1,1,0,0,1,1,1,1,1,1], [(0,13)], "gap2 join"),
    ([1]*5+[0]*3+[1]*5, [(0,5),(8,13)], "gap3 no join"),
    ([1,1,1,0,1,1,1,1,1], [(4,9)], "short run not MHW"),
    ([1]*4, [], "run<5"),
    ([1,1,1,1,0,1,1,1,1,1], [(5,10)], "4-day run not joined"),
    ([0,1,1,1,1,1,0,0,0,1,1,1,1,1,1,0,1,1,1,1,1], [(1,6),(9,21)], "gap2 no join, gap1 joins"),
    ([1]*7+[0]*2+[1]*6+[0]*3+[1]*5+[0]*1+[1]*5, [(0,15),(18,29)], "mixed: gap2 no, gap3 no, gap1 yes x2"),
    ([1]*5, [(0,5)], "exactly 5"),
    ([0,0,0,1,1,1,1,1,0,0,1,1,1,1,1,0], [(3,15)], "gap2 joins two 5-day runs"),
    ([0]*92, [], "all cold"),
    ([1]*92, [(0,92)], "all hot"),
]
for h, exp, name in tests:
    got = detect(h)
    assert got == exp, f"{name}: got {got}, expected {exp}"
    print(f"ok: {name}")
print("ALL 11 synthetic tests passed")

# rebuild full mask from scratch via detect() for every cell, compare to saved mask
tgt_stack = np.load('/tmp/tgt_stack.npy'); Ts = np.load('/tmp/thr_smooth.npy')
sea = np.load('/tmp/sea.npy'); mask = np.load('/tmp/mhw_mask.npy')
meta = json.load(open('/tmp/meta.json')); tgt = [dt.date.fromisoformat(s) for s in meta['tgt']]
t_doy = np.array([(d - dt.date(d.year,1,1)).days + 1 for d in tgt])
thr_t = Ts[t_doy - 1]
mask2 = np.zeros_like(mask)
counts = []
for a in range(60):
    for b in range(60):
        if not sea[a,b]: continue
        m = detect(tgt_stack[:,a,b] >= thr_t[:,a,b])
        for s,e in m:
            mask2[s:e,a,b] = 1; counts.append(e-s)
print('rebuild identical to production mask:', np.array_equal(mask, mask2))
print('cells with MHW:', len(counts), '| total per-cell MHWs:', len(counts) if False else None)
n_events = sum(len(detect(tgt_stack[:,a,b] >= thr_t[:,a,b])) for a in range(60) for b in range(60) if sea[a,b])
print('total per-cell MHWs:', n_events)
rng = np.random.default_rng(1)
for a,b in [(0,0),(30,30),(59,59),(12,47)] + [tuple(int(x) for x in rng.integers(0,60,2)) for _ in range(4)]:
    if not sea[a,b]:
        print(f'cell({a},{b}): land, mask sum', int(mask[:,a,b].sum())); continue
    m = detect(tgt_stack[:,a,b] >= thr_t[:,a,b])
    print(f'cell({a},{b}): MHW spans {m}')
print('mask sum:', int(mask.sum()), '| active days:', int(mask.any(axis=(1,2)).sum()), '| mask on land:', int(mask[:, ~sea].sum()))
