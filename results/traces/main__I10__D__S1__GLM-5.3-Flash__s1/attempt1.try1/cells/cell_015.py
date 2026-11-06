import numpy as np, datetime as dt, json
hot = np.load('/work/hot.npy'); sea = np.load('/work/sea.npy'); mhw = np.load('/work/mhw.npy')
tstr = np.load('/work/target_datestr.npy')
T = np.load('/work/target_sst.npy'); thr_s = np.load('/work/thr_s.npy')
CUM=[0,31,60,91,121,152,182,213,244,274,305,335]
mdoy=lambda y,m,d: CUM[m-1]+d
tdoy=np.array([mdoy(int(s[:4]),int(s[4:6]),int(s[6:])) for s in tstr])

# --- synthetic tests of the run/join machinery ---
def runs_of_true(h):
    idx=np.flatnonzero(h)
    if idx.size==0: return []
    br=np.flatnonzero(np.diff(idx)>1)
    return list(zip(np.concatenate([[idx[0]],idx[br+1]]).tolist(),
                    np.concatenate([idx[br],[idx[-1]]]).tolist()))
def cell_mhw_intervals(h):
    runs=[(s,e) for s,e in runs_of_true(h) if e-s+1>=5]
    if not runs: return []
    merged=[list(runs[0])]
    for s,e in runs[1:]:
        if s-merged[-1][1]-1 <= 2: merged[-1][1]=e
        else: merged.append([s,e])
    return [(s,e) for s,e in merged]
tests = {
 '1111100000111110000000000': [(0,4)],                          # 5-run + short run dropped
 '1111100000111111110000000': [(0,16)],                         # gap 5 -> NOT joined
 '111110000011111000001111100': [(0,24)],                       # gaps 5 & 4 -> joined chain? check
 '0000011110000001111100000': [(12,16)],                        # 4-run + 5-run
 '1111110001111110000000000': [(0,14)],                         # gap 2 joined
 '1111110011111100000000000': [(0,13)],                         # gap 1 joined
 '1111110001111111000000000': [(0,16)],                         # gap 2 joined
 '1111110000111110000000000': [(0,5),(10,14)],                  # gap 3 NOT joined
}
for h,exp in tests.items():
    hb=np.array([c=='1' for c in h])
    got=cell_mhw_intervals(hb)
    print('PASS' if got==exp else 'FAIL', h, '->', got, 'expected', exp)

# --- real-cell inspection ---
onsets={}; 
evcells={}
for r in range(60):
    for c in range(60):
        if not sea[r,c]: continue
        for s,e in runs_of_true(hot[:,r,c]):
            if e-s+1>=5:
                onsets[s]=onsets.get(s,0)+1
                evcells[(r,c)]=(s,e)
print('per-cell event onset-day counts (day index: n):', dict(sorted(onsets.items())))
starts=[v[0] for v in evcells.values()]; ends=[v[1] for v in evcells.values()]
d=lambda i: tstr[i][:4]+'-'+tstr[i][4:6]+'-'+tstr[i][6:]
print('earliest onset:', d(min(starts)), 'latest onset:', d(max(starts)))
print('earliest end:', d(min(ends)), 'latest end:', d(max(ends)))

active=mhw.any(axis=(1,2))
print('\ndaily cells-in-MHW (nonzero days):')
for t in range(92):
    if active[t]:
        print(f'  {tstr[t]}: {int(mhw[t].sum())}')
